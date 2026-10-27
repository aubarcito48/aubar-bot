#include <Arduino.h>
#include "Display_ST7789.h"
#include "avatar_render.h"
#include "avatar_state.h"
#include "gaze_animation.h"
#include "avatar_transition.h"
#include "avatar_frame.h"
#include "usb_control.h"

// Imported catalog with an orthographic renderer adapted for the ESP32 LCD.
static uint16_t scanline[LCD_WIDTH];
static AvatarController controller;
static UsbControl usb;
static ExpressionTransition expressionTransition(avatarExpression(AvatarExpressionId::Neutral));
static GazeTransition gazeTransition;
static uint16_t facePixels[FACE_WIDTH * FACE_HEIGHT];
static uint32_t lastFrameAt = 0;
static bool needsFrame = false;
static bool blinkPendingPresentation = false;
static bool gazePendingPresentation = false;
constexpr int EXPRESSION_BUTTON_PIN = 0;  // Waveshare BOOT, active low.

void clearDisplay() {
  // Stream one row at a time: no full-screen buffer or microSD needed.
  for (int y = 0; y < LCD_HEIGHT; ++y) {
    for (int x = 0; x < LCD_WIDTH; ++x) {
      uint16_t color = AVATAR_BACKGROUND;
      scanline[x] = (color >> 8) | (color << 8);
    }
    LCD_SetCursor(0, y, LCD_WIDTH - 1, y);
    LCD_WriteData_nbyte(reinterpret_cast<uint8_t*>(scanline), nullptr,
                        sizeof(scanline));
  }
}

void setup() {
  Serial.setRxBufferSize(2048);
  Serial.setTxTimeoutMs(0);
  Serial.begin(115200);
  pinMode(EXPRESSION_BUTTON_PIN, INPUT_PULLUP);
  LCD_Init();
  Set_Backlight(70);
  clearDisplay();
  renderFaceFrame(facePixels, controller.pose(), controller.avatar().openness(), 0);
  LCD_addWindow(FACE_X, FACE_Y, FACE_X+FACE_WIDTH-1, FACE_Y+FACE_HEIGHT-1, facePixels);
  controller.start(millis());
}

void loop() {
  const uint32_t now = millis();
  const auto& avatar = controller.avatar();
  const auto previousExpression = avatar.expressionId();
  const auto previousVersion = controller.poseVersion();
  const float previousGaze = controller.gazeOffset();
  const float previousOpenness = controller.openness();
  bool faceChanged = controller.update(now, digitalRead(EXPRESSION_BUTTON_PIN) == LOW);
  // USB takes priority if a physical button or a demo tick coincides with it.
  usb.poll(Serial, controller, now);
  const bool blinkChanged = avatar.expressionId()!=previousExpression ||
                            controller.openness()!=previousOpenness;
  const bool expressionChanged = avatar.expressionId() != previousExpression || controller.poseVersion()!=previousVersion;
  faceChanged = faceChanged || expressionChanged || controller.openness() != previousOpenness;
  if (expressionChanged) {
    expressionTransition.setTarget(controller.pose(), now, controller.transitionMs());
  }
  const bool gazeChanged = controller.gazeOffset() != previousGaze;
  if (gazeChanged || expressionChanged) gazeTransition.setTarget(controller.gazeOffset(), now);
  if (faceChanged || gazeChanged || avatar.expression().bodyMotion!=AvatarMotion::None ||
      avatar.expression().eyeMotion!=AvatarMotion::None) {
    needsFrame = true;
    blinkPendingPresentation = blinkPendingPresentation || blinkChanged;
    gazePendingPresentation = gazePendingPresentation || gazeChanged || expressionChanged;
  }

  // Retain one final frame after a transition finishes, even if the previous
  // sample was still in motion. Idle states do not redraw continuously.
  if (needsFrame && static_cast<uint32_t>(now - lastFrameAt) >= 33) {
    const AvatarExpression pose = expressionTransition.value(now);
    renderFaceFrame(facePixels, pose, controller.openness(), gazeTransition.value(now), now);
    LCD_addWindow(FACE_X, FACE_Y, FACE_X+FACE_WIDTH-1, FACE_Y+FACE_HEIGHT-1, facePixels);
    lastFrameAt = now;
    needsFrame = expressionTransition.active(now) || gazeTransition.active(now);
    // Only a logical phase change restarts its hold, not every tween frame.
    if (blinkPendingPresentation) controller.framePresented(millis());
    if (gazePendingPresentation) controller.gazeFramePresented(millis());
    blinkPendingPresentation = false;
    gazePendingPresentation = false;
  }
}
