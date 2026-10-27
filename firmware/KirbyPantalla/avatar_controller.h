#pragma once
#include "avatar_state.h"
#include "gaze_animation.h"
#include "animation_player.h"
#include "usb_protocol.h"

class AvatarController {
 public:
  constexpr const AvatarState& avatar() const { return avatar_; }
  constexpr UsbMode mode() const { return mode_; }
  constexpr AvatarAnimationId animation() const { return player_.id(); }
  constexpr uint32_t poseVersion() const { return poseVersion_; }
  constexpr uint32_t transitionMs() const { return transitionMs_; }
  constexpr float openness() const { return openness_; }
  constexpr AvatarExpression pose() const {
    AvatarExpression result=avatar_.expression();
    if(lookOverride_) result.headY=manualGaze_<0?-18:manualGaze_>0?18:0;
    return result;
  }
  constexpr float gazeOffset() const {
    if ((!avatar_.expression().blinks || player_.active()) && !lookOverride_) return 0;
    return mode_ == UsbMode::Auto ? gaze_.offset() : manualGaze_;
  }
  constexpr UsbLook look() const {
    return gazeOffset()<0 ? UsbLook::Left : gazeOffset()>0 ? UsbLook::Right : UsbLook::Center;
  }
  constexpr void start(uint32_t now) {
    avatar_.framePresented(now); gaze_.reset(now); introAt_=now;
  }
  constexpr void framePresented(uint32_t now) { avatar_.framePresented(now); }
  constexpr void gazeFramePresented(uint32_t now) { if (mode_==UsbMode::Auto) gaze_.framePresented(now); }
  constexpr bool update(uint32_t now, bool buttonDown) {
    const auto previous=avatar_.expressionId();
    bool changed=avatar_.update(now,buttonDown);
    // AvatarState owns the debounced physical input.
    if (avatar_.expressionId()!=previous) {
      if (mode_==UsbMode::Auto || player_.active()) {
        startAnimation(player_.active() ? static_cast<AvatarAnimationId>(
          (static_cast<uint8_t>(player_.id())+1)%static_cast<uint8_t>(AvatarAnimationId::Count))
          : AvatarAnimationId::Idle, now);
      } else { ++poseVersion_; transitionMs_=450; }
    }
    if (mode_==UsbMode::Auto && !player_.active() && now-introAt_>=1000)
      startAnimation(AvatarAnimationId::Idle,now);
    if (player_.update(now,mode_==UsbMode::Auto)) selectStep(now);
    const float next=player_.active()?player_.openness(now):avatar_.openness();
    changed=changed || next!=openness_;
    openness_=next;
    return changed;
  }
  constexpr void apply(const UsbCommand& command,uint32_t now) {
    switch(command.type) {
      case UsbCommandType::Ping: case UsbCommandType::Status: break;
      case UsbCommandType::Animation:
        if (command.animation>=AvatarAnimationId::Count) break;
        enterManual(); startAnimation(command.animation,now); break;
      case UsbCommandType::Expression:
        enterManual(); avatar_.selectExpression(command.expression,now);
        transitionMs_=450; ++poseVersion_; break;
      case UsbCommandType::Look:
        // A direction changes the gaze without cancelling a running sequence.
        mode_=UsbMode::Manual;
        manualGaze_=command.look==UsbLook::Left?-24:command.look==UsbLook::Right?24:0;
        lookOverride_=true; transitionMs_=450; ++poseVersion_; break;
      case UsbCommandType::Mode:
        if(command.mode==UsbMode::Manual) enterManual();
        else {
          mode_=UsbMode::Auto; player_.stop(); introAt_=now;
          avatar_.selectExpression(AvatarExpressionId::Neutral,now);
          manualGaze_=0; lookOverride_=false; gaze_.reset(now); transitionMs_=450; ++poseVersion_;
        }
        break;
    }
    if (command.hasLook && (command.type==UsbCommandType::Expression || command.type==UsbCommandType::Animation)) {
      manualGaze_=command.look==UsbLook::Left?-24:command.look==UsbLook::Right?24:0;
      lookOverride_=true;
    }
    if (!player_.active()) openness_=avatar_.openness();
  }
 private:
  constexpr void selectStep(uint32_t now) {
    avatar_.selectExpression(player_.step().expression,now);
    transitionMs_=player_.step().transitionMs; ++poseVersion_;
  }
  constexpr void startAnimation(AvatarAnimationId id,uint32_t now) {
    player_.start(id,now); selectStep(now);
  }
  constexpr void enterManual() {
    if(mode_==UsbMode::Auto || player_.active()) manualGaze_=gazeOffset();
    mode_=UsbMode::Manual; player_.stop();
  }
  AvatarState avatar_;
  GazeAnimation gaze_;
  AnimationPlayer player_;
  UsbMode mode_=UsbMode::Auto;
  float manualGaze_=0,openness_=1;
  bool lookOverride_=false;
  uint32_t introAt_=0,poseVersion_=0,transitionMs_=450;
};
