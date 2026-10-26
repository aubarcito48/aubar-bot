#pragma once
#include "avatar_data.h"
#include "blink_animation.h"

class AvatarState {
 public:
  constexpr AvatarExpressionId expressionId() const { return expressionId_; }
  constexpr const AvatarExpression& expression() const {
    return avatarExpression(expressionId_);
  }
  constexpr float openness() const { return expression().blinks ? blink_.openness() : 1.0f; }
  constexpr void framePresented(uint32_t now) { blink_.framePresented(now); }

  // BOOT is only sampled as an input after startup. Debounce both edges and
  // advance once per press, never repeatedly while the button is held.
  constexpr bool update(uint32_t now, bool buttonDown) {
    if (buttonDown != lastButtonDown_) {
      lastButtonDown_ = buttonDown;
      buttonChangedAt_ = now;
    }
    if (buttonDown != stableButtonDown_ &&
        static_cast<uint32_t>(now - buttonChangedAt_) >= 40) {
      stableButtonDown_ = buttonDown;
      if (buttonDown) {
        expressionId_ = static_cast<AvatarExpressionId>(
            (static_cast<uint8_t>(expressionId_) + 1) %
            static_cast<uint8_t>(AvatarExpressionId::Count));
        blink_.reset(now);
        return true;
      }
    }
    return expression().blinks && blink_.update(now);
  }

 private:
  AvatarExpressionId expressionId_ = AvatarExpressionId::Neutral;
  BlinkAnimation blink_;
  uint32_t buttonChangedAt_ = 0;
  bool lastButtonDown_ = false;
  bool stableButtonDown_ = false;
};
