#include "../../firmware/KirbyPantalla/avatar_controller.h"

constexpr UsbCommand expression(AvatarExpressionId id) {
  return {UsbCommandType::Expression, id, UsbLook::Center, UsbMode::Auto};
}
constexpr UsbCommand look(UsbLook direction) {
  return {UsbCommandType::Look, AvatarExpressionId::Neutral, direction, UsbMode::Auto};
}
constexpr UsbCommand mode(UsbMode value) {
  return {UsbCommandType::Mode, AvatarExpressionId::Neutral, UsbLook::Center, value};
}

constexpr bool manualSelectionSurvivesDemoTimers() {
  AvatarController controller;
  controller.start(0);
  controller.apply(expression(AvatarExpressionId::Angry), 100);
  controller.apply(look(UsbLook::Left), 200);
  controller.update(3600, false);
  if (controller.avatar().openness() != 0.45f) return false;
  controller.update(100000, false);
  return controller.mode() == UsbMode::Manual && controller.look() == UsbLook::Left &&
         controller.avatar().expressionId() == AvatarExpressionId::Angry;
}

constexpr bool sleepingCentersWithoutLosingSelection() {
  AvatarController controller;
  controller.apply(look(UsbLook::Right), 0);
  controller.apply(expression(AvatarExpressionId::Sleeping), 1);
  if (controller.look() != UsbLook::Center || controller.avatar().openness() != 1) return false;
  controller.update(100000, false);
  if (controller.avatar().expressionId() != AvatarExpressionId::Sleeping) return false;
  controller.apply(expression(AvatarExpressionId::Happy), 100001);
  return controller.look() == UsbLook::Right && controller.avatar().openness() == 1;
}

constexpr bool manualModeFreezesCurrentTargetsAndPingDoesNotResetBlink() {
  AvatarController controller;
  controller.start(0);
  controller.update(500, false);
  controller.apply(mode(UsbMode::Manual), 500);
  controller.apply({UsbCommandType::Ping}, 3000);
  controller.apply({UsbCommandType::Status}, 3400);
  controller.update(3500, false);
  return controller.look() == UsbLook::Center && controller.avatar().openness() == 0.45f;
}

constexpr bool autoRestartsAndButtonKeepsItsMode() {
  AvatarController c;
  c.apply(expression(AvatarExpressionId::Angry),0);
  c.apply(look(UsbLook::Left),0);
  c.update(10,true); c.update(50,true);
  if(c.avatar().expressionId()!=AvatarExpressionId::UpwardSideGlance || c.mode()!=UsbMode::Manual) return false;
  c.update(60,false); c.update(100,false);
  c.apply(mode(UsbMode::Auto),200);
  c.update(1200,false);
  if(c.animation()!=AvatarAnimationId::Idle) return false;
  c.update(1210,true); c.update(1250,true);
  return c.mode()==UsbMode::Auto && c.animation()==AvatarAnimationId::Listening;
}

constexpr bool usbWinsAndRepeatedCommandsKeepBlinking() {
  AvatarController controller;
  controller.start(0);
  controller.update(12000, false);  // Automatic happy selection.
  controller.apply(expression(AvatarExpressionId::Angry), 12000);  // USB wins.
  controller.update(15500, false);
  if (controller.avatar().openness() != 0.45f) return false;
  controller.apply(expression(AvatarExpressionId::Angry), 15501);
  return controller.mode() == UsbMode::Manual && controller.avatar().openness() == 0.45f;
}

static_assert(manualSelectionSurvivesDemoTimers(), "Demo overwrote manual selection");
static_assert(sleepingCentersWithoutLosingSelection(), "Sleeping gaze rules failed");
static_assert(manualModeFreezesCurrentTargetsAndPingDoesNotResetBlink(), "Query changed animation");
static_assert(autoRestartsAndButtonKeepsItsMode(), "BOOT or mode restart failed");
static_assert(usbWinsAndRepeatedCommandsKeepBlinking(), "Command priority or repeated expression failed");

void setup() {}
void loop() {}
