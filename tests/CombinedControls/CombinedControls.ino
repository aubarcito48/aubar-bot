#include <Arduino.h>
#include "../../firmware/KirbyPantalla/usb_control.h"
#include "../../firmware/KirbyPantalla/avatar_frame.h"
#include "../../firmware/KirbyPantalla/avatar_transition.h"
namespace controlTests {
#include "../AvatarControl/AvatarControl.ino"
}
namespace usbTests {
#include "../UsbProtocol/UsbProtocol.ino"
}

constexpr bool allCombinationsSurviveStepsAndStandaloneLook() {
  for(uint8_t kind=0;kind<2;++kind) {
    uint8_t count=kind?static_cast<uint8_t>(AvatarAnimationId::Count):static_cast<uint8_t>(AvatarExpressionId::Count);
    for(uint8_t i=0;i<count;++i) for(UsbLook direction:{UsbLook::Left,UsbLook::Center,UsbLook::Right}) {
      AvatarController c;
      UsbCommand command;
      command.type=kind?UsbCommandType::Animation:UsbCommandType::Expression;
      command.expression=static_cast<AvatarExpressionId>(i);
      command.animation=static_cast<AvatarAnimationId>(i);
      command.look=direction; command.hasLook=true;
      c.apply(command,0);
      if(c.look()!=direction||c.mode()!=UsbMode::Manual) return false;
      if(kind) {
        uint32_t now=0;
        const auto& animation=avatarAnimation(command.animation);
        for(uint8_t cycle=0;cycle<2;++cycle) for(uint8_t s=0;s<animation.count;++s) {
          if(c.animation()!=command.animation||c.look()!=direction) return false;
          const auto& step=AVATAR_STEPS[animation.first+s];
          if(c.avatar().expressionId()!=step.expression) return false;
          now+=step.holdMs+step.transitionMs;
          c.update(now,false);
        }
        c.apply({UsbCommandType::Look,AvatarExpressionId::Neutral,UsbLook::Right},now+1);
        if(c.animation()!=command.animation||c.look()!=UsbLook::Right) return false;
      } else if(c.avatar().expressionId()!=command.expression) return false;
      c.apply({UsbCommandType::Mode,AvatarExpressionId::Neutral,UsbLook::Center,UsbMode::Auto},999999);
      if(c.look()!=UsbLook::Center||c.pose().headY!=avatarExpression(AvatarExpressionId::Neutral).headY) return false;
    }
  }
  return true;
}
static_assert(allCombinationsSurviveStepsAndStandaloneLook(),"Combined controller rules failed");

bool passed=true;
uint32_t maxRenderUs=0;
static uint16_t pixels[FACE_WIDTH*FACE_HEIGHT];
void run() {
  usbTests::setup();
  passed=usbTests::passed;
  UsbProtocol parser;
  for(const char* invalid:{"EXPRESSION enojado arriba\n","ANIMATION celebrate izquierda extra\n",
      "LOOK derecha izquierda\n","MODE auto derecha\n","ANIMATION celebrate \n"}) {
    passed=passed&&usbTests::line(parser,invalid)==UsbParseResult::InvalidArgument;
  }
  for(uint8_t kind=0;kind<2;++kind) {
    uint8_t count=kind?23:28;
    for(uint8_t i=0;i<count;++i) for(UsbLook look:{UsbLook::Left,UsbLook::Center,UsbLook::Right}) {
      UsbCommand command;
      command.type=kind?UsbCommandType::Animation:UsbCommandType::Expression;
      command.expression=static_cast<AvatarExpressionId>(i);
      command.animation=static_cast<AvatarAnimationId>(i);
      command.hasLook=true; command.look=look;
      AvatarController c; c.apply(command,0);
      const char* name=kind?avatarAnimation(command.animation).name:avatarExpression(command.expression).name;
      const char* direction=look==UsbLook::Left?"izquierda":look==UsbLook::Right?"derecha":"centro";
      char text[96]; snprintf(text,sizeof(text),"%s %s %s\n",kind?"ANIMATION":"EXPRESSION",name,direction);
      passed=passed&&usbTests::line(parser,text)==UsbParseResult::Valid&&parser.command().hasLook&&parser.command().look==look;
      uint8_t steps=kind?avatarAnimation(command.animation).count:1;
      uint32_t now=0;
      for(uint8_t s=0;s<steps;++s) {
        auto pose=c.pose();
        for(float openness:{1.0f,.05f}) {
          uint32_t start=micros();
          renderFaceFrame(pixels,pose,openness,c.gazeOffset(),now);
          maxRenderUs=max(maxRenderUs,static_cast<uint32_t>(micros()-start));
          uint16_t eyes=(pose.eyeColor>>8)|(pose.eyeColor<<8);
          uint16_t background=(AVATAR_BACKGROUND>>8)|(AVATAR_BACKGROUND<<8);
          int eyePixels=0;
          for(int y=0;y<FACE_HEIGHT;++y) for(int x=0;x<FACE_WIDTH;++x) {
            auto pixel=pixels[y*FACE_WIDTH+x];
            if(pixel==eyes) ++eyePixels;
            if(x==0||y==0||x==FACE_WIDTH-1||y==FACE_HEIGHT-1) passed=passed&&pixel==background;
          }
          passed=passed&&eyePixels>0;
        }
        if(kind) {
          const auto& step=AVATAR_STEPS[avatarAnimation(command.animation).first+s];
          now+=step.holdMs+step.transitionMs; c.update(now,false);
        }
      }
    }
  }
  Serial.printf("COMBINATIONS %s; 153 commands; maxRenderUs=%lu\n",passed?"PASS":"FAIL",static_cast<unsigned long>(maxRenderUs));
}
void setup(){Serial.setTxTimeoutMs(5000);Serial.begin(115200);}
void loop(){if(Serial.available()&&Serial.read()=='R') run();}
