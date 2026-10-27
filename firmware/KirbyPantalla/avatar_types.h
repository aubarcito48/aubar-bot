#pragma once
#include "avatar_ids.h"

enum class AvatarMotion : uint8_t { None, Shake, SlowDrift };

struct AvatarEye {
  float width, height, x, y, angle;
};

struct AvatarExpression {
  const char* name;
  AvatarEye left, right;
  float spacing;
  bool blinks;
  float headX = 0, headY = 0, headZ = 0;
  uint16_t bodyColor = 0xFE1D, eyeColor = 0x3A6C;
  AvatarMotion bodyMotion = AvatarMotion::None, eyeMotion = AvatarMotion::None;
  float perspective = 1;
};
