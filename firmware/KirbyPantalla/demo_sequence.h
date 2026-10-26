#pragma once
#include "avatar_state.h"

class DemoSequence {
 public:
  constexpr void reset(uint32_t now) { startedAt_ = now; }

  constexpr bool update(uint32_t now, AvatarState& avatar, bool manualChange) {
    // Give a manual press priority if it coincides with automatic advancement.
    // Each new expression gets its whole hold, regardless of how it was chosen.
    if (manualChange) {
      reset(now);
      return false;
    }
    const uint32_t holdMs = avatar.expressionId() == AvatarExpressionId::Sleeping
                                ? 6000 : 12000;
    if (static_cast<uint32_t>(now - startedAt_) < holdMs) return false;
    avatar.nextExpression(now);
    reset(now);  // Never skip expressions to catch up after a delayed update.
    return true;
  }

 private:
  uint32_t startedAt_ = 0;
};
