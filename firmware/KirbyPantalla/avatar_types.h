#pragma once
#include <stdint.h>

enum class AvatarExpressionId : uint8_t { Neutral, Happy, Surprised, Sleeping, Angry, Count };

struct AvatarEye {
  float width, height, x, y, angle;
};

struct AvatarExpression {
  const char* name;
  AvatarEye left, right;
  float spacing;
  bool blinks;
};
