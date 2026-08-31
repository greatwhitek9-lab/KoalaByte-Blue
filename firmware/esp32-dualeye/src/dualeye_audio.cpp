#include "dualeye_audio.h"
#include <Wire.h>
#include <driver/i2s_std.h>
#include <driver/i2s_tdm.h>
#include <es7210.h>
#include <es8311.h>
#include <math.h>
#include "config.h"

namespace {
constexpr int kSpeakerVolume = AUDIO_OUTPUT_VOLUME;
constexpr int8_t kInputDigitalGainDb = MIC_INPUT_DIGITAL_GAIN_DB;
constexpr uint8_t kTdmInputSlots = 4;
constexpr uint8_t kCollapsedChannels = 2;
constexpr size_t kTdmScratchBytes = MIC_PCM_CHUNK_BYTES * 4U;

i2s_chan_handle_t txHandle = nullptr;
i2s_chan_handle_t rxHandle = nullptr;
es8311_handle_t outputCodec = nullptr;
es7210_dev_handle_t inputCodec = nullptr;
bool busReady = false;
bool micReady = false;
bool speakerReady = false;
bool playbackActive = false;
bool amplifierStateKnown = false;
bool amplifierEnabled = false;
const char *statusText = "not_initialized";
SemaphoreHandle_t audioMutex = nullptr;
uint32_t audioReadAttempts = 0;
size_t audioLastReadBytes = 0;
size_t audioLastRawReadBytes = 0;
uint32_t audioLastReadDurationMs = 0;
const char *audioLastReadState = "not_attempted";
uint8_t tdmScratch[kTdmScratchBytes] = {};

void setAmplifier(bool enabled) {
  pinMode(AUDIO_CODEC_PA_PIN, OUTPUT);
  if (amplifierStateKnown && amplifierEnabled == enabled) return;
  digitalWrite(AUDIO_CODEC_PA_PIN, enabled ? HIGH : LOW);
  amplifierEnabled = enabled;
  amplifierStateKnown = true;
  delay(enabled ? 45 : 10);
}

bool lockAudio(TickType_t timeout = pdMS_TO_TICKS(120)) {
  return audioMutex && xSemaphoreTake(audioMutex, timeout) == pdTRUE;
}

void unlockAudio() {
  if (audioMutex) xSemaphoreGive(audioMutex);
}

void releaseI2sChannels() {
  if (rxHandle) {
    i2s_channel_disable(rxHandle);
    i2s_del_channel(rxHandle);
    rxHandle = nullptr;
  }
  if (txHandle) {
    i2s_channel_disable(txHandle);
    i2s_del_channel(txHandle);
    txHandle = nullptr;
  }
}

bool beginVendorDuplexI2s() {
  i2s_chan_config_t channelConfig =
      I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
  if (i2s_new_channel(&channelConfig, &txHandle, &rxHandle) != ESP_OK ||
      !txHandle || !rxHandle) {
    statusText = "i2s_channel_create_failed";
    releaseI2sChannels();
    return false;
  }

  // Waveshare's DualEye reference uses standard I2S for ES8311 TX. In the
  // vendor esp_codec_dev path, opening the four-channel ES7210 input expands
  // the shared TX clock-master frame to 64 bits. Keep 16 valid speaker bits in
  // two 32-bit slots so BCLK/WS matches the four 16-bit TDM RX slots.
  i2s_std_config_t txConfig = {};
  txConfig.clk_cfg.sample_rate_hz = AUDIO_OUTPUT_SAMPLE_RATE;
  txConfig.clk_cfg.clk_src = I2S_CLK_SRC_DEFAULT;
  txConfig.clk_cfg.ext_clk_freq_hz = 0;
  txConfig.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
  txConfig.slot_cfg.data_bit_width = I2S_DATA_BIT_WIDTH_16BIT;
  txConfig.slot_cfg.slot_bit_width = I2S_SLOT_BIT_WIDTH_32BIT;
  txConfig.slot_cfg.slot_mode = I2S_SLOT_MODE_STEREO;
  txConfig.slot_cfg.slot_mask = I2S_STD_SLOT_BOTH;
  txConfig.slot_cfg.ws_width = 32;
  txConfig.slot_cfg.ws_pol = false;
  txConfig.slot_cfg.bit_shift = true;
  txConfig.slot_cfg.left_align = true;
  txConfig.slot_cfg.big_endian = false;
  txConfig.slot_cfg.bit_order_lsb = false;
  txConfig.gpio_cfg.mclk = static_cast<gpio_num_t>(AUDIO_I2S_MCLK_PIN);
  txConfig.gpio_cfg.bclk = static_cast<gpio_num_t>(AUDIO_I2S_BCLK_PIN);
  txConfig.gpio_cfg.ws = static_cast<gpio_num_t>(AUDIO_I2S_WS_PIN);
  txConfig.gpio_cfg.dout = static_cast<gpio_num_t>(AUDIO_I2S_DOUT_PIN);
  txConfig.gpio_cfg.din = I2S_GPIO_UNUSED;
  txConfig.gpio_cfg.invert_flags.mclk_inv = false;
  txConfig.gpio_cfg.invert_flags.bclk_inv = false;
  txConfig.gpio_cfg.invert_flags.ws_inv = false;

  // ES7210 is explicitly configured for 1xFS TDM. Match the vendor's four-slot
  // TDM RX framing instead of reading it through a standard stereo receiver.
  i2s_tdm_config_t rxConfig = {};
  rxConfig.clk_cfg.sample_rate_hz = AUDIO_INPUT_SAMPLE_RATE;
  rxConfig.clk_cfg.clk_src = I2S_CLK_SRC_DEFAULT;
  rxConfig.clk_cfg.ext_clk_freq_hz = 0;
  rxConfig.clk_cfg.mclk_multiple = I2S_MCLK_MULTIPLE_256;
  rxConfig.clk_cfg.bclk_div = 8;
  rxConfig.slot_cfg.data_bit_width = I2S_DATA_BIT_WIDTH_16BIT;
  rxConfig.slot_cfg.slot_bit_width = I2S_SLOT_BIT_WIDTH_AUTO;
  rxConfig.slot_cfg.slot_mode = I2S_SLOT_MODE_STEREO;
  rxConfig.slot_cfg.slot_mask = static_cast<i2s_tdm_slot_mask_t>(
      I2S_TDM_SLOT0 | I2S_TDM_SLOT1 | I2S_TDM_SLOT2 | I2S_TDM_SLOT3);
  rxConfig.slot_cfg.ws_width = I2S_TDM_AUTO_WS_WIDTH;
  rxConfig.slot_cfg.ws_pol = false;
  rxConfig.slot_cfg.bit_shift = true;
  rxConfig.slot_cfg.left_align = false;
  rxConfig.slot_cfg.big_endian = false;
  rxConfig.slot_cfg.bit_order_lsb = false;
  rxConfig.slot_cfg.skip_mask = false;
  rxConfig.slot_cfg.total_slot = I2S_TDM_AUTO_SLOT_NUM;
  rxConfig.gpio_cfg.mclk = static_cast<gpio_num_t>(AUDIO_I2S_MCLK_PIN);
  rxConfig.gpio_cfg.bclk = static_cast<gpio_num_t>(AUDIO_I2S_BCLK_PIN);
  rxConfig.gpio_cfg.ws = static_cast<gpio_num_t>(AUDIO_I2S_WS_PIN);
  rxConfig.gpio_cfg.dout = I2S_GPIO_UNUSED;
  rxConfig.gpio_cfg.din = static_cast<gpio_num_t>(AUDIO_I2S_DIN_PIN);
  rxConfig.gpio_cfg.invert_flags.mclk_inv = false;
  rxConfig.gpio_cfg.invert_flags.bclk_inv = false;
  rxConfig.gpio_cfg.invert_flags.ws_inv = false;

  if (i2s_channel_init_std_mode(txHandle, &txConfig) != ESP_OK) {
    statusText = "i2s_std_tx_init_failed";
    releaseI2sChannels();
    return false;
  }
  if (i2s_channel_init_tdm_mode(rxHandle, &rxConfig) != ESP_OK) {
    statusText = "i2s_tdm_rx_init_failed";
    releaseI2sChannels();
    return false;
  }
  if (i2s_channel_enable(txHandle) != ESP_OK) {
    statusText = "i2s_std_tx_enable_failed";
    releaseI2sChannels();
    return false;
  }
  if (i2s_channel_enable(rxHandle) != ESP_OK) {
    statusText = "i2s_tdm_rx_enable_failed";
    releaseI2sChannels();
    return false;
  }
  return true;
}
}  // namespace

bool dualEyeAudioBegin() {
  if (busReady) return micReady || speakerReady;
  statusText = "initializing";
  audioMutex = xSemaphoreCreateMutex();
  if (!audioMutex) {
    statusText = "mutex_alloc_failed";
    return false;
  }

  Wire.begin(AUDIO_CODEC_I2C_SDA_PIN, AUDIO_CODEC_I2C_SCL_PIN);
  Wire.setClock(400000);
  setAmplifier(false);

  if (!beginVendorDuplexI2s()) return false;
  busReady = true;

#if ENABLE_AUDIO_SPEAKER
  outputCodec = es8311_create(I2C_NUM_0, AUDIO_CODEC_ES8311_ADDR);
  if (outputCodec) {
    es8311_clock_config_t clockConfig = {};
    clockConfig.mclk_from_mclk_pin = true;
    clockConfig.mclk_frequency = AUDIO_OUTPUT_SAMPLE_RATE * AUDIO_MCLK_MULTIPLE;
    clockConfig.sample_frequency = AUDIO_OUTPUT_SAMPLE_RATE;
    if (es8311_init(outputCodec, &clockConfig, ES8311_RESOLUTION_16,
                    ES8311_RESOLUTION_16) == ESP_OK &&
        es8311_voice_volume_set(outputCodec, kSpeakerVolume, nullptr) == ESP_OK &&
        es8311_microphone_config(outputCodec, false) == ESP_OK) {
      es8311_voice_mute(outputCodec, true);
      speakerReady = true;
    }
  }
#endif

#if ENABLE_MIC_WAKE
  es7210_i2c_config_t inputI2c = {};
  inputI2c.i2c_port = I2C_NUM_0;
  inputI2c.i2c_addr = AUDIO_CODEC_ES7210_ADDR;
  if (es7210_new_codec(&inputI2c, &inputCodec) == ESP_OK && inputCodec) {
    es7210_codec_config_t inputConfig = {};
    inputConfig.sample_rate_hz = AUDIO_INPUT_SAMPLE_RATE;
    inputConfig.mclk_ratio = AUDIO_MCLK_MULTIPLE;
    inputConfig.i2s_format = ES7210_I2S_FMT_I2S;
    inputConfig.bit_width = ES7210_I2S_BITS_16B;
    inputConfig.mic_bias = ES7210_MIC_BIAS_2V87;
    inputConfig.mic_gain = ES7210_MIC_GAIN_37_5DB;
    inputConfig.flags.tdm_enable = true;
    if (es7210_config_codec(inputCodec, &inputConfig) == ESP_OK &&
        es7210_config_volume(inputCodec, kInputDigitalGainDb) == ESP_OK) {
      micReady = true;
    }
  }
#endif

  if (micReady && speakerReady)
    statusText = "es7210_tdm4_es8311_std64_ready";
  else if (micReady)
    statusText = "es7210_tdm4_ready_speaker_failed";
  else if (speakerReady)
    statusText = "es8311_std64_ready_mic_failed";
  else
    statusText = "codec_init_failed";
  return micReady || speakerReady;
}

bool dualEyeAudioReady() { return busReady && (micReady || speakerReady); }
bool dualEyeMicrophoneReady() { return micReady; }
bool dualEyeSpeakerReady() { return speakerReady; }
bool dualEyeAudioBusy() { return playbackActive; }
const char *dualEyeAudioStatus() { return statusText; }

size_t dualEyeAudioRead(uint8_t *buffer, size_t length) {
  ++audioReadAttempts;
  const uint32_t startedAt = millis();
  audioLastReadBytes = 0;
  audioLastRawReadBytes = 0;

  if (!micReady) {
    audioLastReadState = "mic_not_ready";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }
  if (!buffer || length < (kCollapsedChannels * sizeof(int16_t))) {
    audioLastReadState = "invalid_buffer";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }
  if (playbackActive) {
    audioLastReadState = "playback_active";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }
  if (!rxHandle) {
    audioLastReadState = "rx_not_initialized";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }
  if (!lockAudio(pdMS_TO_TICKS(30))) {
    audioLastReadState = "mutex_timeout";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }

  const size_t requestedFrames = length / (kCollapsedChannels * sizeof(int16_t));
  const size_t scratchFrames = sizeof(tdmScratch) / (kTdmInputSlots * sizeof(int16_t));
  const size_t framesToRead = min(requestedFrames, scratchFrames);
  const size_t rawRequested = framesToRead * kTdmInputSlots * sizeof(int16_t);
  size_t rawCount = 0;
  const esp_err_t readResult =
      i2s_channel_read(rxHandle, tdmScratch, rawRequested, &rawCount, 80);
  unlockAudio();

  audioLastRawReadBytes = rawCount;
  if (readResult == ESP_ERR_TIMEOUT && rawCount == 0) {
    audioLastReadState = "read_timeout";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }
  if (readResult != ESP_OK && readResult != ESP_ERR_TIMEOUT) {
    audioLastReadState = "read_error";
    audioLastReadDurationMs = millis() - startedAt;
    return 0;
  }

  const size_t completeFrames = min(rawCount / (kTdmInputSlots * sizeof(int16_t)),
                                    requestedFrames);
  const int16_t *raw = reinterpret_cast<const int16_t *>(tdmScratch);
  int16_t *collapsed = reinterpret_cast<int16_t *>(buffer);
  for (size_t frame = 0; frame < completeFrames; ++frame) {
    // Waveshare's input_reference path requests logical channels 0 and 1 from
    // the ES7210's four-slot TDM stream. Preserve those two channels here so
    // the existing adaptive stereo wake/STT layer can choose the stronger one.
    collapsed[frame * 2] = raw[frame * kTdmInputSlots];
    collapsed[frame * 2 + 1] = raw[frame * kTdmInputSlots + 1];
  }

  const size_t count = completeFrames * kCollapsedChannels * sizeof(int16_t);
  audioLastReadBytes = count;
  audioLastReadDurationMs = millis() - startedAt;
  audioLastReadState = count ? "read_ok_tdm4_to_stereo" : "read_zero";
  return count;
}

uint32_t dualEyeAudioReadAttempts() { return audioReadAttempts; }
size_t dualEyeAudioLastReadBytes() { return audioLastReadBytes; }
size_t dualEyeAudioLastRawReadBytes() { return audioLastRawReadBytes; }
uint32_t dualEyeAudioLastReadDurationMs() { return audioLastReadDurationMs; }
const char *dualEyeAudioLastReadState() { return audioLastReadState; }
uint8_t dualEyeAudioInputSlots() { return kTdmInputSlots; }

float dualEyeAudioRms16Stereo(const uint8_t *buffer, size_t length) {
  if (!buffer || length < 4) return 0.0f;
  const int16_t *samples = reinterpret_cast<const int16_t *>(buffer);
  size_t sampleCount = length / sizeof(int16_t);
  size_t used = 0;
  double sum = 0.0;
  for (size_t i = 0; i < sampleCount; i += 2) {
    float normalized = samples[i] / 32768.0f;
    sum += normalized * normalized;
    ++used;
  }
  return used ? sqrt(sum / used) : 0.0f;
}

bool dualEyeAudioWriteStereo16(const uint8_t *data, size_t length) {
  if (!speakerReady || !txHandle || !data || !length ||
      !lockAudio(pdMS_TO_TICKS(300))) {
    return false;
  }

  if (!playbackActive) {
    playbackActive = true;
    es8311_voice_mute(outputCodec, false);
    setAmplifier(true);
  }

  size_t written = 0;
  while (written < length) {
    size_t count = 0;
    const esp_err_t result =
        i2s_channel_write(txHandle, data + written, length - written, &count, 300);
    if (result != ESP_OK && result != ESP_ERR_TIMEOUT) {
      unlockAudio();
      return false;
    }
    if (!count)
      delay(1);
    else
      written += count;
  }
  unlockAudio();
  return true;
}

bool dualEyeAudioWriteMono16(const int16_t *samples, size_t sampleCount) {
  if (!speakerReady || !samples || !sampleCount) return false;
  int16_t stereo[512];
  size_t offset = 0;
  while (offset < sampleCount) {
    size_t frames = min(static_cast<size_t>(256), sampleCount - offset);
    for (size_t i = 0; i < frames; ++i) {
      const int16_t sample = samples[offset + i];
      stereo[i * 2] = sample;
      stereo[i * 2 + 1] = sample;
    }
    if (!dualEyeAudioWriteStereo16(
            reinterpret_cast<const uint8_t *>(stereo),
            frames * 2 * sizeof(int16_t))) {
      return false;
    }
    offset += frames;
  }
  return true;
}

void dualEyeAudioStopPlayback() {
  if (!speakerReady || !lockAudio()) return;
  if (playbackActive) {
    es8311_voice_mute(outputCodec, true);
    delay(3);
    setAmplifier(false);
    playbackActive = false;
  }
  unlockAudio();
}

void dualEyeAudioPlayCue(uint16_t frequencyHz, uint16_t durationMs) {
  if (!speakerReady || frequencyHz < 80 || !durationMs) return;
  const size_t total = (AUDIO_OUTPUT_SAMPLE_RATE * durationMs) / 1000;
  int16_t chunk[256];
  size_t produced = 0;
  while (produced < total) {
    size_t count = min(static_cast<size_t>(256), total - produced);
    for (size_t i = 0; i < count; ++i) {
      chunk[i] = static_cast<int16_t>(
          sinf(2.0f * PI * frequencyHz * (produced + i) /
               AUDIO_OUTPUT_SAMPLE_RATE) *
          4200.0f);
    }
    if (!dualEyeAudioWriteMono16(chunk, count)) break;
    produced += count;
  }
  dualEyeAudioStopPlayback();
}
