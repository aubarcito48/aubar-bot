#include "../../firmware/KirbyPantalla/demo_sequence.h"

constexpr bool runsFullCycle() {
  AvatarState avatar;
  DemoSequence demo;
  demo.reset(100);
  if (demo.update(12099, avatar, false)) return false;
  if (!demo.update(12100, avatar, false) || avatar.expressionId() != AvatarExpressionId::Happy) return false;
  if (!demo.update(24100, avatar, false) || avatar.expressionId() != AvatarExpressionId::Surprised) return false;
  if (!demo.update(36100, avatar, false) || avatar.expressionId() != AvatarExpressionId::Sleeping) return false;
  if (avatar.expression().blinks || demo.update(42099, avatar, false)) return false;
  if (!demo.update(42100, avatar, false) || avatar.expressionId() != AvatarExpressionId::Angry) return false;
  if (!avatar.expression().blinks || demo.update(54099, avatar, false)) return false;
  if (!demo.update(54100, avatar, false) || avatar.expressionId() != AvatarExpressionId::Neutral) return false;
  return avatar.openness() == 1 && !avatar.update(57599, false) && avatar.update(57600, false);
}

constexpr bool manualPressWinsAtDeadline() {
  AvatarState avatar;
  DemoSequence demo;
  avatar.update(11960, true);
  const auto previous = avatar.expressionId();
  avatar.update(12000, true);
  const bool manualChange = avatar.expressionId() != previous;
  if (!manualChange || demo.update(12000, avatar, manualChange)) return false;
  if (avatar.expressionId() != AvatarExpressionId::Happy) return false;
  if (demo.update(23999, avatar, false)) return false;
  return demo.update(24000, avatar, false) && avatar.expressionId() == AvatarExpressionId::Surprised;
}

constexpr bool blinkAndRenderDoNotRestartDemo() {
  AvatarState avatar;
  DemoSequence demo;
  for (uint32_t now = 0; now < 12000; now += 100) {
    avatar.update(now, false);
    avatar.framePresented(now);
    if (demo.update(now, avatar, false)) return false;
  }
  return demo.update(12000, avatar, false) && avatar.expressionId() == AvatarExpressionId::Happy;
}

constexpr bool handlesRolloverLateUpdatesAndRestart() {
  AvatarState avatar;
  DemoSequence demo;
  demo.reset(UINT32_MAX - 99);
  if (demo.update(11899, avatar, false) || !demo.update(11900, avatar, false)) return false;
  if (avatar.expressionId() != AvatarExpressionId::Happy) return false;
  if (!demo.update(100000, avatar, false) || avatar.expressionId() != AvatarExpressionId::Surprised) return false;
  if (demo.update(100000, avatar, false)) return false;
  AvatarState restarted;
  demo.reset(100000);
  return restarted.expressionId() == AvatarExpressionId::Neutral &&
         !demo.update(111999, restarted, false) && demo.update(112000, restarted, false);
}

static_assert(runsFullCycle(), "Demo cycle or wake-up blink failed");
static_assert(manualPressWinsAtDeadline(), "Manual press caused double advancement");
static_assert(blinkAndRenderDoNotRestartDemo(), "Other animation clocks postponed demo");
static_assert(handlesRolloverLateUpdatesAndRestart(), "Demo clock or restart failed");

void setup() {}
void loop() {}
