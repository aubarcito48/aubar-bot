#pragma once
#include "avatar_types.h"
// Generated from avatar-original/kirby.avatar.json.
constexpr uint16_t AVATAR_BODY = 0xFE1D;
constexpr uint16_t AVATAR_EYES = 0x3A6C;
constexpr uint16_t AVATAR_BACKGROUND = 0x0882;
constexpr float AVATAR_WIDTH = 240.000000f;
constexpr float AVATAR_HEIGHT = 240.000000f;
constexpr AvatarExpression AVATAR_EXPRESSIONS[] = {
  // neutral
  {"neutral", {20.000000f, 60.473828f, 0.000000f, -7.000000f, 0.000000f}, {20.000000f, 60.473828f, 0.000000f, -7.000000f, 0.000000f}, 28.749219f, true},
  // joyful-wide
  {"contento", {34.200868f, 95.804688f, 0.000000f, 0.000000f, 0.000000f}, {34.200868f, 93.651585f, 0.000000f, 0.000000f, 0.000000f}, 53.163672f, true},
  // surprised-wide-left
  {"sorprendido", {51.400000f, 60.573828f, 0.000000f, 0.000000f, 0.000000f}, {50.500000f, 59.873828f, 0.000000f, 0.000000f, 0.000000f}, 62.749219f, true},
  // eyes-closed
  {"dormido", {56.133984f, 25.973828f, 0.000000f, 0.000000f, 0.000000f}, {56.133984f, 25.629297f, 0.000000f, 0.000000f, 0.000000f}, 63.025391f, false},
  // angry-right
  {"enojado", {20.908203f, 50.874609f, 0.000000f, 0.000000f, -30.865625f}, {20.908203f, 50.874609f, 0.000000f, 0.000000f, 28.781641f}, 45.808984f, true},
};
static_assert(sizeof(AVATAR_EXPRESSIONS) / sizeof(AVATAR_EXPRESSIONS[0]) ==
              static_cast<uint8_t>(AvatarExpressionId::Count), "Expression count mismatch");
constexpr const AvatarExpression& avatarExpression(AvatarExpressionId id) {
  return AVATAR_EXPRESSIONS[static_cast<uint8_t>(id)];
}
struct AvatarNode { float x, y, width, height, angle; };
constexpr AvatarNode AVATAR_NODES[] = {
  {-103.304379f, 30.444971f, 108.110156f, 81.600000f, -14.843359f},
  {98.154293f, 32.550030f, 108.110156f, 81.600000f, 15.175000f},
};
