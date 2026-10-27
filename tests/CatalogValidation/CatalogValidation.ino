#include <Arduino.h>
#include "../../firmware/KirbyPantalla/avatar_controller.h"
#include "../../firmware/KirbyPantalla/avatar_transition.h"
#include "../../firmware/KirbyPantalla/avatar_frame.h"
#include "../../firmware/KirbyPantalla/usb_control.h"
#include "../../firmware/KirbyPantalla/demo_sequence.h"

namespace blinkTests {
#include "../BlinkAnimation/BlinkAnimation.ino"
}
namespace controlTests {
#include "../AvatarControl/AvatarControl.ino"
}
namespace expressionTests {
#include "../AvatarExpressions/AvatarExpressions.ino"
}
namespace transitionTests {
#include "../AvatarTransitions/AvatarTransitions.ino"
}
namespace usbTests {
#include "../UsbProtocol/UsbProtocol.ino"
}
namespace demoTests {
#include "../DemoSequence/DemoSequence.ino"
}

constexpr bool playerTiming() {
  for(uint8_t i=0;i<static_cast<uint8_t>(AvatarAnimationId::Count);++i) {
    AnimationPlayer player;
    auto id=static_cast<AvatarAnimationId>(i);
    uint32_t now=UINT32_MAX-99;
    player.start(id,now);
    const auto& config=avatarAnimation(id);
    for(uint8_t j=0;j<config.count;++j) {
      const auto& expected=AVATAR_STEPS[config.first+j];
      if(player.step().expression!=expected.expression) return false;
      uint32_t duration=expected.transitionMs+expected.holdMs;
      if(player.update(now+duration-1,false)) return false;
      now+=duration;
      if(!player.update(now,false)||player.id()!=id) return false;
    }
    if(player.step().expression!=AVATAR_STEPS[config.first].expression) return false;
    if(player.openness(now)<.05f||player.openness(now)>1) return false;
    player.stop();
    if(player.active()||player.update(now+100000,false)) return false;
  }
  return true;
}
constexpr bool playlistAndInterruptions() {
  AvatarController c;
  c.start(0); c.update(999,false);
  if(c.animation()!=AvatarAnimationId::None) return false;
  c.update(1000,false);
  if(c.animation()!=AvatarAnimationId::Idle) return false;
  uint32_t now=1000;
  for(uint8_t a=0;a<23;++a) {
    auto id=c.animation();
    const auto& anim=avatarAnimation(id);
    for(uint8_t s=0;s<anim.count;++s) {
      const auto& step=AVATAR_STEPS[anim.first+s];
      if(c.avatar().expressionId()!=step.expression) return false;
      now+=step.transitionMs+step.holdMs;
      c.update(now,false);
    }
    if(c.animation()==id) return false;
  }
  if(c.animation()!=AvatarAnimationId::Idle) return false;
  c.apply({UsbCommandType::Look,AvatarExpressionId::Neutral,UsbLook::Left},now);
  if(c.animation()!=AvatarAnimationId::None||c.mode()!=UsbMode::Manual) return false;
  auto pose=c.avatar().expressionId();
  c.update(now+99999,false);
  return c.avatar().expressionId()==pose;
}
constexpr bool blinkConfigAndManualFreeze() {
  for(uint8_t i=0;i<23;++i) {
    AnimationPlayer p;
    auto id=static_cast<AvatarAnimationId>(i);
    p.start(id,100);
    const auto& b=avatarAnimation(id).blink;
    if(p.openness(100+b.initialDelayMs-1)!=1) return false;
    p.openness(100+b.initialDelayMs);
    float closed=p.openness(100+b.initialDelayMs+b.durationMs/2);
    if(closed<.049f||closed>.051f) return false;
    if(p.openness(100+b.initialDelayMs+b.durationMs)!=1) return false;
  }
  AvatarController c;
  c.apply({UsbCommandType::Look,AvatarExpressionId::Neutral,UsbLook::Right},0);
  UsbCommand animation;
  animation.type=UsbCommandType::Animation;
  animation.animation=AvatarAnimationId::Happy;
  c.apply(animation,100);
  if(c.look()!=UsbLook::Center) return false;
  c.apply({UsbCommandType::Mode,AvatarExpressionId::Neutral,UsbLook::Center,UsbMode::Manual},200);
  return c.look()==UsbLook::Center&&c.animation()==AvatarAnimationId::None;
}
static_assert(playerTiming(),"Imported step timing / rollover failed");
static_assert(playlistAndInterruptions(),"Playlist or manual interruption failed");
static_assert(blinkConfigAndManualFreeze(),"Blink config or animation freeze failed");

void setup() { Serial.setTxTimeoutMs(5000); Serial.begin(115200); }
void loop() {
  if(!Serial.available()) return;
  char command=Serial.read();
  if(command=='R') {
    expressionTests::setup();
    transitionTests::setup();
    usbTests::setup();
    Serial.printf("CATALOG expressions=%s transitions=%s usb=%s maxRenderUs=%lu\n",
      expressionTests::passed?"PASS":"FAIL",transitionTests::passed?"PASS":"FAIL",
      usbTests::passed?"PASS":"FAIL",static_cast<unsigned long>(transitionTests::maxRenderUs));
  }
}
