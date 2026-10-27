#include "../../firmware/KirbyPantalla/gaze_animation.h"
#include "../../firmware/KirbyPantalla/avatar_state.h"
#include "../../firmware/KirbyPantalla/avatar_render.h"

constexpr bool keepsDirectionAndTiming() {
  GazeAnimation gaze;
  gaze.reset(100);
  if (gaze.offset() != 0 || gaze.update(2599, true)) return false;
  if (!gaze.update(2600, true) || gaze.offset() >= 0) return false;
  gaze.framePresented(2700);  // Include the LCD transfer time in the hold.
  if (gaze.update(5199, true) || !gaze.update(5200, true) || gaze.offset() != 0) return false;
  if (!gaze.update(7700, true) || gaze.offset() <= 0) return false;
  return gaze.update(10200, true) && gaze.offset() == 0;
}

constexpr bool handlesSleepLateUpdatesAndRollover() {
  GazeAnimation gaze;
  gaze.update(10000, true);  // One step, no catch-up through hidden frames.
  if (gaze.offset() >= 0 || gaze.update(10000, true)) return false;
  if (!gaze.update(10001, false) || gaze.offset() != 0) return false;
  if (gaze.update(50000, false) || gaze.update(52499, true)) return false;
  if (!gaze.update(52500, true) || gaze.offset() >= 0) return false;
  gaze.reset(UINT32_MAX - 99);
  return !gaze.update(2399, true) && gaze.update(2400, true) && gaze.offset() < 0;
}

constexpr bool gazeDoesNotPostponeBlink() {
  GazeAnimation gaze;
  AvatarState avatar;
  if (!gaze.update(2500, true) || avatar.update(2500, false)) return false;
  return avatar.update(3500, false) && avatar.openness() == 0.45f;
}

static_assert(keepsDirectionAndTiming(), "Gaze direction or frame timing changed");
static_assert(handlesSleepLateUpdatesAndRollover(), "Gaze sleep or clock handling failed");
static_assert(gazeDoesNotPostponeBlink(), "Gaze clock interfered with blinking");

bool fullEyesFit(const AvatarExpression& expression, float offset) {
  const AvatarEye eyes[] = {expression.left, expression.right};
  const float centers[] = {-(expression.spacing + expression.left.width) * 0.5f,
                           (expression.spacing + expression.right.width) * 0.5f};
  for (int i = 0; i < 2; ++i) {
    const auto& eye = eyes[i];
    const float angle = eye.angle * 0.01745329252f;
    for (int sx : {-1, 1}) {
      for (int sy : {-1, 1}) {
        float u = sx * eye.width * 0.5f;
        float v = sy * fmaxf(eye.height, 5.0f) * 0.5f;
        float x = centers[i] + eye.x + offset + u*cosf(angle) - v*sinf(angle);
        float y = 34.0f + eye.y + u*sinf(angle) + v*cosf(angle);
        float nx = x / (AVATAR_WIDTH * 0.5f);
        float ny = y / (AVATAR_HEIGHT * 0.5f);
        if (nx*nx + ny*ny >= 1.0f) return false;
      }
    }
  }
  return true;
}

float eyeCentroid(const AvatarExpression& expression, float offset, float openness) {
  int count = 0;
  int sum = 0;
  for (int y = 0; y < 320; ++y) {
    for (int x = 0; x < 172; ++x) {
      if (avatarPixel(x, y, expression, openness, offset) == AVATAR_EYES) {
        ++count;
        sum += x;
      }
    }
  }
  return count ? static_cast<float>(sum) / count : -1000.0f;
}

bool passed = true;
void setup() {
  Serial.begin(115200);
  for (uint8_t i = 0; i < static_cast<uint8_t>(AvatarExpressionId::Count); ++i) {
    const auto& expression = avatarExpression(static_cast<AvatarExpressionId>(i));
    for (float requested : {-10000.0f, -24.0f, 0.0f, 24.0f, 10000.0f}) {
      passed = fullEyesFit(expression, avatarGazeOffset(expression, requested)) && passed;
    }
    for (float openness : {1.0f, 0.05f}) {
      float left = eyeCentroid(expression, avatarGazeOffset(expression, -24), openness);
      float center = eyeCentroid(expression, avatarGazeOffset(expression, 0), openness);
      float right = eyeCentroid(expression, avatarGazeOffset(expression, 24), openness);
      passed = passed && left > 0 && left + 3 < center && center + 3 < right;
    }
  }
}

void loop() {
  Serial.println(passed ? "TK11 TESTS PASS" : "TK11 TESTS FAIL");
  delay(1000);
}
