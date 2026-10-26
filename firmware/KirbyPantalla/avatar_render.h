#pragma once
#include <math.h>
#include <stdint.h>
#include "avatar_data.h"

// A frontal 2D adaptation of the exported sphere surfaces, not the 3D
// projection and keyframe engine used by the browser package.
static bool avatarEllipse(float x, float y, float cx, float cy,
                          float width, float height, float degrees) {
  float a = degrees * 0.01745329252f;
  float dx = x - cx, dy = y - cy;
  float u = (dx * cosf(a) + dy * sinf(a)) / (width * 0.5f);
  float v = (-dx * sinf(a) + dy * cosf(a)) / (height * 0.5f);
  return u*u + v*v <= 1.0f;
}

static bool avatarEye(float x, float y, float cx, float cy,
                      float width, float height) {
  // Rounded rectangle, including very flat closed eyes.
  float radius = fminf(width, height) * 0.5f;
  float dx = fmaxf(fabsf(x-cx) - (width*0.5f-radius), 0.0f);
  float dy = fmaxf(fabsf(y-cy) - (height*0.5f-radius), 0.0f);
  return dx*dx + dy*dy <= radius*radius;
}

static bool avatarExpressionEye(float x, float y, float cx,
                                const AvatarEye& eye, float openness) {
  float angle = eye.angle * 0.01745329252f;
  float dx = x - cx - eye.x;
  float dy = y - 34.0f - eye.y;
  float u = dx * cosf(angle) + dy * sinf(angle);
  float v = -dx * sinf(angle) + dy * cosf(angle);
  return avatarEye(u, v, 0, 0, eye.width,
                   fmaxf(5.0f, eye.height * openness));
}

static uint16_t avatarPixel(int screenX, int screenY,
                            const AvatarExpression& expression, float openness) {
  // Fit the entire avatar, including its arms, into the narrow screen.
  constexpr float scale = 0.48f;
  float x = (screenX - 86.0f) / scale;
  float y = (screenY - 160.0f) / scale;
  bool body = avatarEllipse(x, y, 0, 0, AVATAR_WIDTH, AVATAR_HEIGHT, 0);
  for (const auto& node : AVATAR_NODES) {
    body = body || avatarEllipse(x, y, node.x, node.y,
                                node.width, node.height, node.angle);
  }
  if (!body) return AVATAR_BACKGROUND;
  // Eye spacing is the gap between the two eye shapes.
  float leftX = -(expression.spacing + expression.left.width) * 0.5f;
  float rightX = (expression.spacing + expression.right.width) * 0.5f;
  if (avatarExpressionEye(x, y, leftX, expression.left, openness) ||
      avatarExpressionEye(x, y, rightX, expression.right, openness)) {
    return AVATAR_EYES;
  }
  return AVATAR_BODY;
}
