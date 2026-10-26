#pragma once
#include "avatar_render.h"

// Covers all current eye poses and their gaze limits (including angry eyes).
// The body does not move, so the rest of the display is drawn only at startup.
constexpr int FACE_X = 20;
constexpr int FACE_Y = 140;
constexpr int FACE_WIDTH = 132;
constexpr int FACE_HEIGHT = 68;

struct FaceEyeRaster {
  AvatarEye eye;
  float cx, cosine, sine, halfWidth, halfHeight, radius;

  FaceEyeRaster(const AvatarEye& shape, float center, float openness)
      : eye(shape), cx(center) {
    const float angle = eye.angle * 0.01745329252f;
    cosine = cosf(angle);
    sine = sinf(angle);
    halfWidth = eye.width * 0.5f;
    halfHeight = fmaxf(5.0f, eye.height * openness) * 0.5f;
    radius = fminf(halfWidth, halfHeight);
  }

  bool contains(float x, float y) const {
    const float dx = x - cx - eye.x;
    const float dy = y - 34.0f - eye.y;
    const float u = dx*cosine + dy*sine;
    const float v = -dx*sine + dy*cosine;
    const float rx = fmaxf(fabsf(u) - (halfWidth-radius), 0.0f);
    const float ry = fmaxf(fabsf(v) - (halfHeight-radius), 0.0f);
    return rx*rx + ry*ry <= radius*radius;
  }
};

static void renderFaceFrame(uint16_t* pixels, const AvatarExpression& expression,
                            float openness, float requestedGaze) {
  // The silhouette never changes in this sprint. Cache it once in a bit mask;
  // eye geometry and trigonometry are prepared only once per frame.
  static uint8_t bodyMask[(FACE_WIDTH*FACE_HEIGHT+7)/8] = {};
  static bool initialized = false;
  if (!initialized) {
    for (int y = 0; y < FACE_HEIGHT; ++y) {
      for (int x = 0; x < FACE_WIDTH; ++x) {
        int index = y*FACE_WIDTH+x;
        if (avatarPixel(FACE_X+x, FACE_Y+y, expression, openness) != AVATAR_BACKGROUND) {
          bodyMask[index/8] |= 1u << (index%8);
        }
      }
    }
    initialized = true;
  }
  const float gazeOffset = avatarGazeOffset(expression, requestedGaze);
  const FaceEyeRaster left(expression.left,
      -(expression.spacing+expression.left.width)*0.5f+gazeOffset, openness);
  const FaceEyeRaster right(expression.right,
      (expression.spacing+expression.right.width)*0.5f+gazeOffset, openness);
  for (int y = 0; y < FACE_HEIGHT; ++y) {
    const float modelY = (FACE_Y+y-160.0f)/0.48f;
    for (int x = 0; x < FACE_WIDTH; ++x) {
      const int index = y*FACE_WIDTH+x;
      uint16_t color = AVATAR_BACKGROUND;
      if (bodyMask[index/8] & (1u << (index%8))) {
        const float modelX = (FACE_X+x-86.0f)/0.48f;
        color = left.contains(modelX, modelY) || right.contains(modelX, modelY)
                    ? AVATAR_EYES : AVATAR_BODY;
      }
      pixels[index] = (color >> 8) | (color << 8);
    }
  }
}
