#pragma once
#include "portrait_routes.h"

// Rig geometry for the approved portraits, not language/emotion classification.
// Keep the selected face/body; animate only its mouth from the speech clip.
struct PortraitSpeechFace { uint16_t frame; int16_t x,y; };
constexpr PortraitSpeechFace portraitSpeechFace(PortraitScene scene) {
  switch(scene) {
    case PortraitScene::Angry: return {PORTRAIT_EMOTIONS+112,88,140};
    case PortraitScene::Suspicious: return {PORTRAIT_EMOTIONS+40,89,140};
    case PortraitScene::Confused: return {PORTRAIT_EMOTIONS+88,89,141};
    case PortraitScene::Sad: return {PORTRAIT_EMOTIONS+160,89,142};
    case PortraitScene::Scared: return {PORTRAIT_EMOTIONS+192,90,143};
    case PortraitScene::Shy: return {PORTRAIT_EMOTIONS+222,96,143};
    case PortraitScene::Bored: return {PORTRAIT_GESTURES+44,89,141};
    case PortraitScene::Surprised: return {PORTRAIT_GESTURES+88,90,142};
    case PortraitScene::Proud: return {PORTRAIT_GESTURES+120,89,142};
    case PortraitScene::Laughing: return {PORTRAIT_GESTURES+150,88,146};
    case PortraitScene::Excited: case PortraitScene::Celebrate: return {PORTRAIT_GESTURES+190,90,142};
    case PortraitScene::Joyful: return {PORTRAIT_GESTURES+204,90,142};
    case PortraitScene::Playful: return {PORTRAIT_GESTURES+220,88,142};
    default: return {0xffff,90,142};
  }
}

constexpr bool portraitSpeechRigFits() {
  for(uint8_t id=0;id<=static_cast<uint8_t>(PortraitScene::Celebrate);++id) {
    const auto face=portraitSpeechFace(static_cast<PortraitScene>(id));
    if(face.frame!=0xffff && (face.frame>=PORTRAIT_FRAME_COUNT ||
       face.x<16 || face.x+16>=PORTRAIT_WIDTH || face.y<11 || face.y+11>=PORTRAIT_HEIGHT)) return false;
  }
  return true;
}
static_assert(portraitSpeechRigFits(),"Speech mouth geometry must fit the supplied frame bank");
