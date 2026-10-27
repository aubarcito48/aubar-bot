#include "../../firmware/KirbyPantalla/blink_animation.h"

// Compile-time tests run against the production controller. They do not need
// to be uploaded to the device.
constexpr bool keepsEveryBlinkFrame() {
  BlinkAnimation blink;
  blink.framePresented(100);
  if (blink.phase() != BlinkPhase::Open || blink.openness() != 1.0f) return false;
  if (blink.update(3599) || !blink.update(3600)) return false;
  if (blink.phase() != BlinkPhase::Closing || blink.openness() != 0.45f) return false;
  if (blink.update(3629) || !blink.update(3630)) return false;
  if (blink.phase() != BlinkPhase::Closed || blink.openness() != 0.05f) return false;
  if (blink.update(3709) || !blink.update(3710)) return false;
  if (blink.phase() != BlinkPhase::Opening || blink.openness() != 0.45f) return false;
  if (blink.update(3739) || !blink.update(3740)) return false;
  return blink.phase() == BlinkPhase::Open && blink.openness() == 1.0f &&
         !blink.update(7239) && blink.update(7240);
}

constexpr bool holdsFramesAfterRendering() {
  BlinkAnimation blink;
  if (!blink.update(3500)) return false;
  // Simulate a slow LCD transfer that finishes 100 ms after the transition.
  blink.framePresented(3600);
  return !blink.update(3629) && blink.update(3630) &&
         blink.phase() == BlinkPhase::Closed;
}

constexpr bool handlesClockRollover() {
  BlinkAnimation blink;
  blink.framePresented(UINT32_MAX - 99);
  if (blink.update(3399) || !blink.update(3400)) return false;
  // Test rollover during a short phase too.
  blink.framePresented(UINT32_MAX - 9);
  return !blink.update(19) && blink.update(20) &&
         blink.phase() == BlinkPhase::Closed;
}

constexpr bool neverSkipsFramesWhenLate() {
  BlinkAnimation blink;
  if (!blink.update(50000) || blink.phase() != BlinkPhase::Closing) return false;
  if (blink.update(50000)) return false;
  return blink.update(60000) && blink.phase() == BlinkPhase::Closed;
}

static_assert(keepsEveryBlinkFrame(), "Blink sequence or timing changed");
static_assert(holdsFramesAfterRendering(), "LCD transfer consumed the hold time");
static_assert(handlesClockRollover(), "millis rollover broke scheduling");
static_assert(neverSkipsFramesWhenLate(), "Late update skipped a blink phase");

void setup() {}
void loop() {}
