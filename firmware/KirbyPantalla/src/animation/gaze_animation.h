#pragma once
#include <stdint.h>

class GazeAnimation {
 public:
  constexpr float offset() const {
    return step_ == 1 ? -24.0f : step_ == 3 ? 24.0f : 0.0f;
  }

  constexpr void reset(uint32_t now) {
    step_ = 0;
    startedAt_ = now;
  }

  constexpr void framePresented(uint32_t now) { startedAt_ = now; }

  constexpr bool update(uint32_t now, bool awake) {
    if (!awake) {
      bool changed = offset() != 0;
      reset(now);
      return changed;
    }
    if (static_cast<uint32_t>(now - startedAt_) < 2500) return false;
    step_ = (step_ + 1) % 4;  // Center -> left -> center -> right.
    startedAt_ = now;
    return true;
  }

 private:
  uint32_t startedAt_ = 0;
  uint8_t step_ = 0;
};
