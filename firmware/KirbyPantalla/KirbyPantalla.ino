#include <Arduino.h>
#include "Display_ST7789.h"
#include "avatar_render.h"
#include "avatar_state.h"
#include "gaze_animation.h"

// Frontal expressions adapted from the original Avatar Lab export.
// This does not execute Avatar Lab's web animation engine.
static uint16_t scanline[LCD_WIDTH];
static AvatarState avatar;
static GazeAnimation gaze;
constexpr int EXPRESSION_BUTTON_PIN = 0;  // Waveshare BOOT, active low.

void drawAvatar(float openness) {
  const float gazeOffset = avatarGazeOffset(avatar.expression(), gaze.offset());
  // Stream one row at a time: no full-screen buffer or microSD needed.
  for (int y = 0; y < LCD_HEIGHT; ++y) {
    for (int x = 0; x < LCD_WIDTH; ++x) {
      uint16_t color = avatarPixel(x, y, avatar.expression(), openness, gazeOffset);
      scanline[x] = (color >> 8) | (color << 8);
    }
    LCD_SetCursor(0, y, LCD_WIDTH - 1, y);
    LCD_WriteData_nbyte(reinterpret_cast<uint8_t*>(scanline), nullptr,
                        sizeof(scanline));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(EXPRESSION_BUTTON_PIN, INPUT_PULLUP);
  LCD_Init();
  Set_Backlight(70);
  drawAvatar(avatar.openness());
  avatar.framePresented(millis());
  gaze.reset(millis());
  Serial.println("Kirby listo. BOOT: neutral > contento > sorprendido > dormido");
}

void loop() {
  const auto previousExpression = avatar.expressionId();
  const bool faceChanged = avatar.update(millis(), digitalRead(EXPRESSION_BUTTON_PIN) == LOW);
  const bool expressionChanged = avatar.expressionId() != previousExpression;
  if (expressionChanged) gaze.reset(millis());
  const bool gazeChanged = gaze.update(millis(), avatar.expression().blinks);
  if (faceChanged || gazeChanged) {
    drawAvatar(avatar.openness());
    // A gaze-only redraw must not postpone blinking indefinitely.
    if (faceChanged) avatar.framePresented(millis());
    if (gazeChanged || expressionChanged) gaze.framePresented(millis());
  }
}
