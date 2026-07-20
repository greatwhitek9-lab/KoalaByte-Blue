#include "dualeye_audio.h"
#include <ESP_I2S.h>
#include <Wire.h>
#include <es7210.h>
#include <es8311.h>
#include <math.h>
#include "config.h"

namespace {
constexpr int kSpeakerVolume = AUDIO_OUTPUT_VOLUME;
constexpr int8_t kInputDigitalGainDb = 16;
I2SClass audioBus;
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

  audioBus.setPins(AUDIO_I2S_BCLK_PIN, AUDIO_I2S_WS_PIN,
                   AUDIO_I2S_DOUT_PIN, AUDIO_I2S_DIN_PIN,
                   AUDIO_I2S_MCLK_PIN);
  audioBus.setTimeout(80);
  if (!audioBus.begin(I2S_MODE_STD, AUDIO_INPUT_SAMPLE_RATE,
                      I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO)) {
    statusText = "i2s_full_duplex_init_failed";
    return false;
  }
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
    inputConfig.mic_gain = ES7210_MIC_GAIN_36DB;
    inputConfig.flags.tdm_enable = true;
    if (es7210_config_codec(inputCodec, &inputConfig) == ESP_OK &&
        es7210_config_volume(inputCodec, kInputDigitalGainDb) == ESP_OK) {
      micReady = true;
    }
  }
#endif

  if (micReady && speakerReady)
    statusText = "es7210_es8311_ready";
  else if (micReady)
    statusText = "es7210_ready_speaker_failed";
  else if (speakerReady)
    statusText = "es8311_ready_mic_failed";
  else
    statusText = "codec_init_failed";
  return micReady || speakerReady;
}

bool dualEyeAudioReady() { return busReady && (micReady || speakerReady); }
bool dualEyeMicrophoneReady() { return micReady; }
bool dualEyeSpeakerReady() { return speakerReady; }
bool dualEyeAudioBusy() { return playbackActive; }
const char *dualEyeAudioStatus() { return statusText; }
I2SClass &dualEyeAudioBus() { return audioBus; }

size_t dualEyeAudioRead(uint8_t *buffer, size_t length) {
  if (!micReady || !buffer || !length || playbackActive ||
      !lockAudio(pdMS_TO_TICKS(30))) {
    return 0;
  }
  size_t count = audioBus.readBytes(reinterpret_cast<char *>(buffer), length);
  unlockAudio();
  return count;
}

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
  if (!speakerReady || !data || !length ||
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
    size_t count = audioBus.write(data + written, length - written);
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
