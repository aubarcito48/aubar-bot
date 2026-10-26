#pragma once
#include "avatar_state.h"
#include "gaze_animation.h"
#include "demo_sequence.h"
#include "usb_protocol.h"

class AvatarController {
 public:
  constexpr const AvatarState& avatar() const { return avatar_; }
  constexpr UsbMode mode() const { return mode_; }
  constexpr float gazeOffset() const {
    if (!avatar_.expression().blinks) return 0;  // Sleeping stays centered.
    return mode_ == UsbMode::Auto ? gaze_.offset() : manualGaze_;
  }
  constexpr UsbLook look() const {
    return gazeOffset() < 0 ? UsbLook::Left : gazeOffset() > 0 ? UsbLook::Right : UsbLook::Center;
  }
  constexpr void start(uint32_t now) {
    avatar_.framePresented(now);
    gaze_.reset(now);
    demo_.reset(now);
  }
  constexpr void framePresented(uint32_t now) { avatar_.framePresented(now); }
  constexpr void gazeFramePresented(uint32_t now) {
    if (mode_ == UsbMode::Auto) gaze_.framePresented(now);
  }

  constexpr bool update(uint32_t now, bool buttonDown) {
    const auto previous = avatar_.expressionId();
    bool faceChanged = avatar_.update(now, buttonDown);
    if (mode_ == UsbMode::Auto) {
      if (demo_.update(now, avatar_, avatar_.expressionId() != previous)) faceChanged = true;
      if (avatar_.expressionId() != previous) gaze_.reset(now);
      gaze_.update(now, avatar_.expression().blinks);
    }
    return faceChanged;
  }

  constexpr void apply(const UsbCommand& command, uint32_t now) {
    switch (command.type) {
      case UsbCommandType::Ping:
      case UsbCommandType::Status: break;
      case UsbCommandType::Expression:
        enterManual();
        avatar_.selectExpression(command.expression, now);
        break;
      case UsbCommandType::Look:
        enterManual();
        manualGaze_ = command.look == UsbLook::Left ? -24 : command.look == UsbLook::Right ? 24 : 0;
        break;
      case UsbCommandType::Mode:
        if (command.mode == UsbMode::Manual) enterManual();
        else {
          mode_ = UsbMode::Auto;
          avatar_.selectExpression(AvatarExpressionId::Neutral, now);
          manualGaze_ = 0;
          gaze_.reset(now);
          demo_.reset(now);
        }
        break;
    }
  }

 private:
  constexpr void enterManual() {
    if (mode_ == UsbMode::Auto) manualGaze_ = gaze_.offset();
    mode_ = UsbMode::Manual;
  }

  AvatarState avatar_;
  GazeAnimation gaze_;
  DemoSequence demo_;
  UsbMode mode_ = UsbMode::Auto;
  float manualGaze_ = 0;
};
