#include <Arduino.h>
#include "Display_ST7789.h"
#include "avatar_render.h"
#include "avatar_state.h"
#include "gaze_animation.h"
#include "avatar_transition.h"
#include "avatar_frame.h"

// Frontal expressions adapted from the original Avatar Lab export.
// This does not execute Avatar Lab's web animation engine.
static uint16_t scanline[LCD_WIDTH];
static AvatarState avatar;
static GazeAnimation gaze;
static ExpressionTransition expressionTransition(avatarExpression(AvatarExpressionId::Neutral));
static GazeTransition gazeTransition;
static uint16_t facePixels[FACE_WIDTH * FACE_HEIGHT];
static uint32_t lastFrameAt = 0;
static bool needsFrame = false;
static bool blinkPendingPresentation = false;
static bool gazePendingPresentation = false;
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
  // Prepare the static silhouette before the first animation starts.
  renderFaceFrame(facePixels, avatar.expression(), avatar.openness(), 0);
  avatar.framePresented(millis());
  gaze.reset(millis());
  Serial.println("Kirby listo. BOOT: neutral > contento > sorprendido > dormido");
}

void loop() {
  const uint32_t now = millis();
  const auto previousExpression = avatar.expressionId();
  const bool faceChanged = avatar.update(now, digitalRead(EXPRESSION_BUTTON_PIN) == LOW);
  const bool expressionChanged = avatar.expressionId() != previousExpression;
  if (expressionChanged) {
    expressionTransition.setTarget(avatar.expression(), now);
    gaze.reset(now);
  }
  const bool gazeChanged = gaze.update(now, avatar.expression().blinks);
  if (gazeChanged || expressionChanged) gazeTransition.setTarget(gaze.offset(), now);
  if (faceChanged || gazeChanged) {
    needsFrame = true;
    blinkPendingPresentation = blinkPendingPresentation || faceChanged;
    gazePendingPresentation = gazePendingPresentation || gazeChanged || expressionChanged;
  }

  // Retain one final frame after a transition finishes, even if the previous
  // sample was still in motion. Idle states do not redraw continuously.
  if (needsFrame && static_cast<uint32_t>(now - lastFrameAt) >= 33) {
    const AvatarExpression pose = expressionTransition.value(now);
    renderFaceFrame(facePixels, pose, avatar.openness(), gazeTransition.value(now));
    LCD_addWindow(FACE_X, FACE_Y, FACE_X+FACE_WIDTH-1, FACE_Y+FACE_HEIGHT-1, facePixels);
    lastFrameAt = now;
    needsFrame = expressionTransition.active(now) || gazeTransition.active(now);
    // Only a logical phase change restarts its hold, not every tween frame.
    if (blinkPendingPresentation) avatar.framePresented(millis());
    if (gazePendingPresentation) gaze.framePresented(millis());
    blinkPendingPresentation = false;
    gazePendingPresentation = false;
  }
}
