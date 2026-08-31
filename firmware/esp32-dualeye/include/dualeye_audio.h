#pragma once
#include <Arduino.h>

bool dualEyeAudioBegin();
bool dualEyeAudioReady();
bool dualEyeMicrophoneReady();
bool dualEyeSpeakerReady();
bool dualEyeAudioBusy();
const char *dualEyeAudioStatus();
size_t dualEyeAudioRead(uint8_t *buffer, size_t length);
uint32_t dualEyeAudioReadAttempts();
size_t dualEyeAudioLastReadBytes();
size_t dualEyeAudioLastRawReadBytes();
uint32_t dualEyeAudioLastReadDurationMs();
const char *dualEyeAudioLastReadState();
uint8_t dualEyeAudioInputSlots();
float dualEyeAudioRms16Stereo(const uint8_t *buffer, size_t length);
bool dualEyeAudioWriteMono16(const int16_t *samples, size_t sampleCount);
bool dualEyeAudioWriteStereo16(const uint8_t *data, size_t length);
void dualEyeAudioStopPlayback();
void dualEyeAudioPlayCue(uint16_t frequencyHz, uint16_t durationMs);
