#pragma once
#include "animation_data.h"

// Nonblocking player. Holds begin after each transition, including step zero.
class AnimationPlayer {
 public:
  constexpr AvatarAnimationId id() const { return id_; }
  constexpr bool active() const { return id_ != AvatarAnimationId::None; }
  constexpr const AvatarAnimationStep& step() const {
    return AVATAR_STEPS[avatarAnimation(id_).first + step_];
  }
  constexpr void stop() { id_ = AvatarAnimationId::None; }
  constexpr void start(AvatarAnimationId id, uint32_t now) {
    id_ = id; step_ = 0; startedAt_ = blinkAt_ = now;
    blinkDelay_ = avatarAnimation(id).blink.initialDelayMs;
    blinking_ = false;
  }
  // Returns true for a new pose, also when a one-step animation repeats.
  constexpr bool update(uint32_t now, bool playlist) {
    if (!active() || now-startedAt_ < step().transitionMs+step().holdMs) return false;
    if (++step_ == avatarAnimation(id_).count) {
      step_ = 0;
      if (playlist) {
        start(static_cast<AvatarAnimationId>((static_cast<uint8_t>(id_)+1) %
              static_cast<uint8_t>(AvatarAnimationId::Count)), now);
        return true;
      }
    }
    startedAt_ = now;
    return true;
  }
  constexpr float openness(uint32_t now) {
    if (!active()) return 1;
    const auto& config = avatarAnimation(id_).blink;
    if (!config.enabled) return 1;
    if (!blinking_ && now-blinkAt_ >= blinkDelay_) {
      blinking_ = true; blinkAt_ = now;
    }
    if (!blinking_) return 1;
    const uint32_t elapsed = now-blinkAt_;
    if (elapsed >= config.durationMs) {
      blinking_ = false; blinkAt_ = now;
      random_ = random_*1664525u+1013904223u;
      blinkDelay_ = config.minIntervalMs + random_%(config.maxIntervalMs-config.minIntervalMs+1);
      return 1;
    }
    const float t = static_cast<float>(elapsed)/config.durationMs;
    return t < .4f ? 1-t/.4f*.95f : t < .6f ? .05f : .05f+(t-.6f)/.4f*.95f;
  }
 private:
  AvatarAnimationId id_ = AvatarAnimationId::None;
  uint8_t step_ = 0;
  uint32_t startedAt_ = 0, blinkAt_ = 0, blinkDelay_ = 0, random_ = 481;
  bool blinking_ = false;
};
