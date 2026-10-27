#include "../../firmware/KirbyPantalla/avatar_transition.h"
#include "../../firmware/KirbyPantalla/avatar_frame.h"
#include "../../firmware/KirbyPantalla/avatar_state.h"

constexpr bool interpolatesAndRetargetsWithoutJumping() {
  ExpressionTransition pose(avatarExpression(AvatarExpressionId::Neutral));
  const auto happy = avatarExpression(AvatarExpressionId::Happy);
  pose.setTarget(happy, 100);
  if (pose.value(100).left.width != 20 || !pose.active(549)) return false;
  const float halfway = pose.value(325).left.width;
  if (!(halfway > 20 && halfway < happy.left.width)) return false;
  pose.setTarget(avatarExpression(AvatarExpressionId::Sleeping), 325);
  if (pose.value(325).left.width != halfway) return false;
  if (pose.active(775)) return false;
  return pose.value(775).left.width == avatarExpression(AvatarExpressionId::Sleeping).left.width;
}

constexpr bool gazeReachesEndpointsAndHandlesRollover() {
  GazeTransition gaze;
  gaze.setTarget(-24, UINT32_MAX - 99);
  if (gaze.value(UINT32_MAX - 99) != 0) return false;
  if (!gaze.active(249) || gaze.active(250) || gaze.value(250) != -24) return false;
  gaze.setTarget(24, 300);
  const float mid = gaze.value(475);
  if (mid != 0) return false;
  gaze.setTarget(0, 475);
  return gaze.value(475) == mid && gaze.value(825) == 0;
}

constexpr bool expressionHandlesRolloverAndIrregularFrames() {
  ExpressionTransition pose(avatarExpression(AvatarExpressionId::Neutral));
  const auto target = avatarExpression(AvatarExpressionId::Surprised);
  pose.setTarget(target, UINT32_MAX - 99);
  if (!pose.active(349) || pose.active(350)) return false;
  return pose.value(350).right.width == target.right.width &&
         pose.value(50000).spacing == target.spacing &&
         transitionProgress(0, 0, 0) == 1;
}

static_assert(interpolatesAndRetargetsWithoutJumping(), "Expression transition jumped");
static_assert(gazeReachesEndpointsAndHandlesRollover(), "Gaze transition timing failed");
static_assert(expressionHandlesRolloverAndIrregularFrames(), "Expression timing failed");

static uint16_t pixels[FACE_WIDTH * FACE_HEIGHT];
bool passed = true;
uint32_t maxRenderUs = 0;

void setup() {
  Serial.begin(115200);
  constexpr uint8_t count=static_cast<uint8_t>(AvatarExpressionId::Count);
  for(uint8_t from=0;from<count;++from) for(uint8_t to=0;to<count;++to) {
    ExpressionTransition transition(avatarExpression(static_cast<AvatarExpressionId>(from)));
    transition.setTarget(avatarExpression(static_cast<AvatarExpressionId>(to)),0,500);
    for(uint32_t time: {0u,250u,500u}) for(float requested: {-24.0f,24.0f}) {
      auto pose=transition.value(time);
      uint32_t start=micros();
      renderFaceFrame(pixels,pose,1,requested,time);
      maxRenderUs=max(maxRenderUs,static_cast<uint32_t>(micros()-start));
      int eyes=0;
      const uint16_t background=(AVATAR_BACKGROUND>>8)|(AVATAR_BACKGROUND<<8);
      const uint16_t eye=(pose.eyeColor>>8)|(pose.eyeColor<<8);
      for(int y=0;y<FACE_HEIGHT;++y) for(int x=0;x<FACE_WIDTH;++x) {
        const auto pixel=pixels[y*FACE_WIDTH+x];
        if(pixel==eye) ++eyes;
        if(x==0||y==0||x==FACE_WIDTH-1||y==FACE_HEIGHT-1) passed=passed&&pixel==background;
      }
      passed=passed&&eyes>0;
    }
  }
}

void loop() {
  Serial.print(passed ? "TK12 TESTS PASS; max render us=" : "TK12 TESTS FAIL; max render us=");
  Serial.println(maxRenderUs);
  delay(1000);
}
