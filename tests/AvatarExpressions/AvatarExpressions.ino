#include "../../firmware/KirbyPantalla/avatar_state.h"
#include "../../firmware/KirbyPantalla/avatar_frame.h"

constexpr void press(AvatarState& state, uint32_t now) {
  state.update(now, true);
  state.update(now + 40, true);
  state.update(now + 41, false);
  state.update(now + 81, false);
}

constexpr bool debouncesAndDoesNotRepeat() {
  AvatarState state;
  state.update(1, true);
  state.update(20, false);  // Bounce: no stable press.
  state.update(30, true);
  state.update(69, true);
  if (state.expressionId() != AvatarExpressionId::Neutral) return false;
  state.update(70, true);
  if (state.expressionId() != AvatarExpressionId::Happy) return false;
  state.update(10000, true);  // Holding must not advance again.
  return state.expressionId() == AvatarExpressionId::Happy;
}

constexpr bool cyclesAndKeepsSleepingEyesClosed() {
  AvatarState state;
  press(state, 100);
  if (state.expressionId() != AvatarExpressionId::Happy) return false;
  press(state, 200);
  if (state.expressionId() != AvatarExpressionId::Surprised) return false;
  press(state, 300);
  if (state.expressionId() != AvatarExpressionId::Sleeping || state.expression().blinks) return false;
  if (state.update(10000, false) || state.openness() != 1.0f) return false;
  press(state, 10100);
  if (state.expressionId() != AvatarExpressionId::Angry || !state.expression().blinks) return false;
  for(uint8_t i=4;i<static_cast<uint8_t>(AvatarExpressionId::Count);++i) press(state, 10200+(i-4)*100);
  return state.expressionId() == AvatarExpressionId::Neutral && state.openness() == 1.0f &&
         !state.update(16039, false) && state.update(16040, false);
}

constexpr bool changesExpressionDuringBlink() {
  AvatarState state;
  state.update(3500, false);
  state.update(3530, false);
  if (state.openness() != 0.05f) return false;
  press(state, 3540);
  return state.expressionId() == AvatarExpressionId::Happy && state.openness() == 1.0f;
}

constexpr bool buttonHandlesClockRollover() {
  AvatarState state;
  state.framePresented(UINT32_MAX - 19);
  state.update(UINT32_MAX - 19, true);
  state.update(19, true);
  if (state.expressionId() != AvatarExpressionId::Neutral) return false;
  state.update(20, true);
  return state.expressionId() == AvatarExpressionId::Happy;
}

static_assert(debouncesAndDoesNotRepeat(), "Button bounce or hold advanced expressions");
static_assert(cyclesAndKeepsSleepingEyesClosed(), "Expression cycle or sleeping blink is wrong");
static_assert(changesExpressionDuringBlink(), "Expression inherited a half-closed blink");
static_assert(buttonHandlesClockRollover(), "Button debounce failed across millis rollover");

// On-device render checks: all faces must produce distinct frames, with
// visible eyes, and the awake expressions must change when they blink.
uint32_t frameHash(const AvatarExpression& expression, float openness, int& eyePixels) {
  uint32_t hash = 2166136261u;
  eyePixels = 0;
  static uint16_t pixels[FACE_WIDTH*FACE_HEIGHT];
  renderFaceFrame(pixels,expression,openness,0);
  for (int y = 0; y < FACE_HEIGHT; ++y) {
    for (int x = 0; x < FACE_WIDTH; ++x) {
      uint16_t stored=pixels[y*FACE_WIDTH+x];
      uint16_t color=(stored>>8)|(stored<<8);
      if (color == expression.eyeColor) ++eyePixels;
      hash = (hash ^ color) * 16777619u;
    }
  }
  return hash;
}

bool passed = true;
void setup() {
  Serial.begin(115200);
  constexpr uint8_t count = static_cast<uint8_t>(AvatarExpressionId::Count);
  uint32_t hashes[count];
  for (uint8_t i = 0; i < count; ++i) {
    const auto& expression = avatarExpression(static_cast<AvatarExpressionId>(i));
    int eyePixels;
    hashes[i] = frameHash(expression, 1.0f, eyePixels);
    passed = passed && eyePixels > 0;
    for (uint8_t j = 0; j < i; ++j) passed = passed && hashes[i] != hashes[j];
    if (expression.blinks) {
      int closedEyePixels;
      uint32_t closedHash = frameHash(expression, 0.05f, closedEyePixels);
      passed = passed && hashes[i] != closedHash && closedEyePixels > 0 && closedEyePixels < eyePixels;
    }
  }
}

void loop() {
  Serial.println(passed ? "TK10 TESTS PASS" : "TK10 TESTS FAIL");
  delay(1000);
}
