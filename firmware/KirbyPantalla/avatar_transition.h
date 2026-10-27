#pragma once
#include "avatar_types.h"

constexpr float transitionProgress(uint32_t now, uint32_t startedAt, uint32_t duration) {
  const uint32_t elapsed = now - startedAt;
  if (duration == 0 || elapsed >= duration) return 1.0f;
  const float t = static_cast<float>(elapsed) / duration;
  return t*t*(3.0f - 2.0f*t);  // Smoothstep: start and finish at rest.
}

constexpr float transitionMix(float from, float to, float t) {
  return from + (to - from) * t;
}

constexpr AvatarEye transitionEye(const AvatarEye& from, const AvatarEye& to, float t) {
  return {transitionMix(from.width, to.width, t), transitionMix(from.height, to.height, t),
          transitionMix(from.x, to.x, t), transitionMix(from.y, to.y, t),
          transitionMix(from.angle, to.angle, t)};
}

constexpr uint16_t transitionColor(uint16_t a, uint16_t b, float t) {
  return (static_cast<uint16_t>(transitionMix(a>>11,b>>11,t))<<11) |
         (static_cast<uint16_t>(transitionMix((a>>5)&63,(b>>5)&63,t))<<5) |
         static_cast<uint16_t>(transitionMix(a&31,b&31,t));
}

class ExpressionTransition {
 public:
  constexpr explicit ExpressionTransition(const AvatarExpression& initial)
      : from_(initial), to_(initial) {}

  constexpr AvatarExpression value(uint32_t now) const {
    const float t = transitionProgress(now, startedAt_, duration_);
    if (t >= 1.0f) return to_;
    return {to_.name, transitionEye(from_.left, to_.left, t),
            transitionEye(from_.right, to_.right, t),
            transitionMix(from_.spacing, to_.spacing, t), to_.blinks,
            transitionMix(from_.headX,to_.headX,t), transitionMix(from_.headY,to_.headY,t),
            transitionMix(from_.headZ,to_.headZ,t),
            transitionColor(from_.bodyColor,to_.bodyColor,t),
            transitionColor(from_.eyeColor,to_.eyeColor,t), to_.bodyMotion,to_.eyeMotion,
            transitionMix(from_.perspective,to_.perspective,t)};
  }

  constexpr void setTarget(const AvatarExpression& target, uint32_t now, uint32_t duration = 450) {
    from_ = value(now);  // Retarget from the current pose, even mid-transition.
    to_ = target;
    startedAt_ = now;
    duration_ = duration;
  }

  constexpr bool active(uint32_t now) const { return now - startedAt_ < duration_; }

 private:
  AvatarExpression from_, to_;
  uint32_t startedAt_ = 0;
  uint32_t duration_ = 0;
};

class GazeTransition {
 public:
  constexpr float value(uint32_t now) const {
    const float t = transitionProgress(now, startedAt_, duration_);
    return t >= 1.0f ? to_ : transitionMix(from_, to_, t);
  }

  constexpr void setTarget(float target, uint32_t now) {
    from_ = value(now);
    to_ = target;
    startedAt_ = now;
    duration_ = 350;
  }

  constexpr bool active(uint32_t now) const { return now - startedAt_ < duration_; }

 private:
  float from_ = 0, to_ = 0;
  uint32_t startedAt_ = 0;
  uint32_t duration_ = 0;
};
