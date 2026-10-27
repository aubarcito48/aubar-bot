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
  {"neutral", {20.000000f, 60.473828f, 0.000000f, -7.000000f, 0.000000f}, {20.000000f, 60.473828f, 0.000000f, -7.000000f, 0.000000f}, 28.749219f, true, 0.000000f, 0.000000f, 0.000000f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // joyful-wide
  {"contento", {34.200868f, 95.804688f, 0.000000f, 0.000000f, 0.000000f}, {34.200868f, 93.651585f, 0.000000f, 0.000000f, 0.000000f}, 53.163672f, true, -2.092969f, -15.899609f, -14.469922f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // surprised-wide-left
  {"sorprendido", {51.400000f, 60.573828f, 0.000000f, 0.000000f, 0.000000f}, {50.500000f, 59.873828f, 0.000000f, 0.000000f, 0.000000f}, 62.749219f, true, -5.428125f, -11.713281f, -13.472266f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // eyes-closed
  {"dormido", {56.133984f, 25.973828f, 0.000000f, 0.000000f, 0.000000f}, {56.133984f, 25.629297f, 0.000000f, 0.000000f, 0.000000f}, 63.025391f, false, -8.752344f, -8.743359f, -10.773828f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // angry-right
  {"enojado", {20.908203f, 50.874609f, 0.000000f, 0.000000f, -30.865625f}, {20.908203f, 50.874609f, 0.000000f, 0.000000f, 28.781641f}, 45.808984f, true, 8.063672f, 17.626563f, -11.116797f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // upward-side-glance
  {"upward-side-glance", {22.501172f, 52.851562f, 0.000000f, -20.500000f, 0.000000f}, {22.501172f, 52.851562f, 0.000000f, -20.500000f, 0.000000f}, 48.049219f, true, 7.300000f, 27.800000f, -16.100000f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // downward-gaze
  {"downward-gaze", {22.401172f, 65.044141f, 0.000000f, 0.000000f, 0.000000f}, {22.401172f, 65.044141f, 0.000000f, 0.000000f, 0.000000f}, 51.449219f, true, -15.057813f, 0.142969f, -14.549219f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // skeptical-right
  {"skeptical-right", {23.090625f, 68.153516f, 0.000000f, 0.000000f, 0.000000f}, {49.924609f, 22.905469f, 0.000000f, 0.000000f, 0.000000f}, 50.049219f, true, -16.528516f, -3.767969f, -13.729688f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // small-attentive
  {"small-attentive", {22.066797f, 50.073047f, 0.000000f, 0.000000f, 0.000000f}, {22.066797f, 50.073047f, 0.000000f, 0.000000f, 0.000000f}, 44.649219f, true, -4.232422f, 14.362109f, 11.204297f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // wide-downward-gaze
  {"wide-downward-gaze", {52.084766f, 61.940988f, 0.000000f, 0.000000f, 0.000000f}, {53.114109f, 62.661528f, 0.000000f, 0.000000f, 0.000000f}, 63.249219f, true, -19.208594f, 15.200000f, 11.800000f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // surprised-left
  {"surprised-left", {51.683367f, 62.214369f, 0.000000f, 0.000000f, 0.000000f}, {51.683367f, 62.214369f, 0.000000f, 0.000000f, 0.000000f}, 64.649219f, true, 2.946875f, -16.051172f, -20.916016f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // sleepy-squint
  {"sleepy-squint", {51.775000f, 23.501172f, 0.000000f, 0.000000f, 0.000000f}, {51.775000f, 23.501172f, 0.000000f, 0.000000f, 0.000000f}, 57.621484f, false, 3.400000f, 13.225781f, 8.976953f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // curious-left
  {"curious-left", {20.605859f, 58.243750f, 0.000000f, 0.000000f, 23.523047f}, {20.605859f, 58.243750f, 0.000000f, 0.000000f, -24.042578f}, 48.649219f, true, -12.303516f, -17.601172f, 5.910938f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // asymmetric-down-right
  {"asymmetric-down-right", {42.500000f, 52.273828f, 0.000000f, 0.000000f, 0.000000f}, {22.100000f, 32.673828f, 0.000000f, 0.000000f, 0.000000f}, 55.449219f, true, -20.058203f, 12.607422f, -12.700000f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // attentive-left
  {"attentive-left", {23.836719f, 68.603906f, 0.000000f, 0.000000f, 0.000000f}, {23.836719f, 68.603906f, 0.000000f, 0.000000f, 0.000000f}, 50.549219f, true, 1.433594f, 6.194141f, 10.560156f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // joyful-down-right
  {"joyful-down-right", {31.253906f, 87.194531f, 0.000000f, 0.000000f, 0.000000f}, {31.253906f, 87.194531f, 0.000000f, 0.000000f, 0.000000f}, 62.449219f, true, -15.287109f, 15.006641f, 12.787891f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // skeptical-left
  {"skeptical-left", {24.306250f, 69.755469f, 0.000000f, 0.000000f, 0.000000f}, {48.924219f, 23.882031f, 0.000000f, 0.000000f, 0.000000f}, 55.967578f, true, 3.529297f, -7.076562f, 9.830078f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // far-right-glance
  {"far-right-glance", {22.460938f, 50.294531f, 0.000000f, 0.000000f, 0.000000f}, {22.460938f, 50.294531f, 0.000000f, 0.000000f, 0.000000f}, 47.649219f, true, 0.319141f, 35.307422f, -10.904297f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // angry-left
  {"angry-left", {19.602344f, 59.113672f, 0.000000f, 0.000000f, -27.606641f}, {19.602344f, 59.113672f, 0.000000f, 0.000000f, 26.148438f}, 48.849219f, true, -14.750781f, -19.350000f, 5.631641f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // playful-right
  {"playful-right", {19.045146f, 53.844531f, 0.000000f, 0.000000f, 26.292188f}, {19.045146f, 53.844531f, 0.000000f, 0.000000f, -20.249219f}, 45.480469f, true, -4.395313f, 14.072656f, -16.126172f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // asymmetric-up-left
  {"asymmetric-up-left", {42.100000f, 52.173828f, 0.000000f, 0.000000f, 0.000000f}, {22.200000f, 32.573828f, 0.000000f, 0.000000f, 0.000000f}, 54.149219f, true, 6.585547f, 4.737109f, 12.840234f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // gentle-downward-gaze
  {"gentle-downward-gaze", {23.045703f, 69.158984f, 0.000000f, 0.000000f, 0.000000f}, {23.045703f, 69.158984f, 0.000000f, 0.000000f, 0.000000f}, 49.949219f, true, -6.077734f, -11.035156f, -13.965625f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // wide-down-left
  {"wide-down-left", {35.452734f, 89.578125f, 0.000000f, 0.000000f, 0.000000f}, {35.452734f, 89.578125f, 0.000000f, 0.000000f, 0.000000f}, 64.549219f, true, -17.127734f, 18.070703f, 13.891797f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // drowsy-closed
  {"drowsy-closed", {55.672266f, 25.089844f, 0.000000f, 0.000000f, 0.000000f}, {55.672266f, 25.089844f, 0.000000f, 0.000000f, 0.000000f}, 62.166016f, false, 10.292578f, 3.399219f, 7.583203f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // suspicious-right
  {"suspicious-right", {23.969922f, 66.366797f, 0.000000f, -9.800000f, 0.000000f}, {53.563281f, 23.807422f, 0.000000f, -9.800000f, 0.000000f}, 53.692969f, true, -17.800000f, 10.000000f, -10.894922f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // shy-downward
  {"shy-downward", {21.500000f, 42.473828f, 0.000000f, 40.000000f, 0.000000f}, {23.200000f, 43.973828f, 0.000000f, 40.000000f, 0.000000f}, 44.949219f, true, 7.131641f, 7.782812f, 3.935547f, 0xFE1D, 0x3A6C, AvatarMotion::None, AvatarMotion::None, 1.000000f},
  // angry-brows
  {"angry-brows", {27.126562f, 73.501953f, 0.000000f, 0.000000f, -36.244531f}, {27.126562f, 73.501953f, 0.000000f, 0.000000f, 27.730078f}, 62.449219f, true, 10.473975f, 5.087294f, 4.698252f, 0xB9A6, 0x6000, AvatarMotion::Shake, AvatarMotion::None, 1.000000f},
  // uneasy-left
  {"uneasy-left", {20.605859f, 58.243750f, 0.000000f, 0.000000f, 23.523047f}, {20.605859f, 58.243750f, 0.000000f, 0.000000f, -24.042578f}, 48.649219f, true, -12.303516f, -17.601172f, 5.910938f, 0xAE1F, 0x3A6C, AvatarMotion::SlowDrift, AvatarMotion::Shake, 1.000000f},
};
constexpr const AvatarExpression& avatarExpression(AvatarExpressionId id) {
  return AVATAR_EXPRESSIONS[static_cast<uint8_t>(id)];
}
struct AvatarNode { float x, y, width, height, angle, z, depth; };
constexpr AvatarNode AVATAR_NODES[] = {
  {-103.304379f, 30.444971f, 108.110156f, 81.600000f, -14.843359f, -9.784766f, 81.600000f},
  {98.154293f, 32.550030f, 108.110156f, 81.600000f, 15.175000f, -9.784766f, 81.600000f},
};
