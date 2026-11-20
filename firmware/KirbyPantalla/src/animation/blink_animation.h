#pragma once
#include <stdint.h>

enum class BlinkPhase : uint8_t { Open, Closing, Closed, Opening };

class BlinkAnimation {
 public:
  constexpr BlinkPhase phase() const { return phase_; }

  constexpr void reset(uint32_t now) {
    phase_ = BlinkPhase::Open;
    frameStartedAt_ = now;
  }

  constexpr float openness() const {
    switch (phase_) {
      case BlinkPhase::Open: return 1.0f;
      case BlinkPhase::Closed: return 0.05f;
      default: return 0.45f;
    }
  }

  // Begin each hold after the synchronous LCD transfer has finished, matching
  // the original sketch's delay-after-draw timing. Also used for the first frame.
  constexpr void framePresented(uint32_t now) { frameStartedAt_ = now; }

  // Advance at most one phase per call. A late update must not skip the closed
  // frame or rush through several frames to catch up.
  constexpr bool update(uint32_t now) {
    if (static_cast<uint32_t>(now - frameStartedAt_) < durationMs()) {
      return false;
    }

    switch (phase_) {
      case BlinkPhase::Open: phase_ = BlinkPhase::Closing; break;
      case BlinkPhase::Closing: phase_ = BlinkPhase::Closed; break;
      case BlinkPhase::Closed: phase_ = BlinkPhase::Opening; break;
      case BlinkPhase::Opening: phase_ = BlinkPhase::Open; break;
    }
    frameStartedAt_ = now;
    return true;
  }

 private:
  constexpr uint32_t durationMs() const {
    switch (phase_) {
      case BlinkPhase::Open: return 3500;
      case BlinkPhase::Closed: return 80;
      default: return 30;
    }
  }

  BlinkPhase phase_ = BlinkPhase::Open;
  uint32_t frameStartedAt_ = 0;
};
