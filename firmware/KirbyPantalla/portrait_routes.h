#pragma once
#include "portrait_assets.h"
#include "avatar_controller.h"

// Available portrait poses; unsupported legacy emotions use explicit fallbacks.
enum class PortraitScene : uint8_t {
  Front, Computer, Thinking, Sleeping, MouthHalf, MouthOpen,
  IdleVideo, SearchVideo, ListeningVideo, HappyVideo, UpVideo,
  Left, Right, Down, Up, Smile
};

constexpr PortraitScene portraitExpressionScene(AvatarExpressionId id) {
  constexpr PortraitScene poses[] = {
    PortraitScene::Front, PortraitScene::Smile, PortraitScene::MouthOpen,
    PortraitScene::Sleeping, PortraitScene::Thinking, PortraitScene::Up,
    PortraitScene::Down, PortraitScene::Thinking, PortraitScene::Front,
    PortraitScene::Down, PortraitScene::Left, PortraitScene::Sleeping,
    PortraitScene::Left, PortraitScene::Down, PortraitScene::Left,
    PortraitScene::Smile, PortraitScene::Thinking, PortraitScene::Right,
    PortraitScene::Thinking, PortraitScene::Smile, PortraitScene::Up,
    PortraitScene::Computer, PortraitScene::Down, PortraitScene::Sleeping,
    PortraitScene::Thinking, PortraitScene::Down, PortraitScene::Thinking,
    PortraitScene::Thinking
  };
  static_assert(sizeof(poses)/sizeof(poses[0]) == static_cast<uint8_t>(AvatarExpressionId::Count));
  return id < AvatarExpressionId::Count ? poses[static_cast<uint8_t>(id)] : PortraitScene::Front;
}

constexpr PortraitScene portraitAnimationScene(AvatarAnimationId id) {
  constexpr PortraitScene scenes[] = {
    PortraitScene::Sleeping, PortraitScene::Front, PortraitScene::IdleVideo,
    PortraitScene::ListeningVideo, PortraitScene::Thinking, PortraitScene::SearchVideo,
    PortraitScene::Computer, PortraitScene::HappyVideo, PortraitScene::Sleeping,
    PortraitScene::Thinking, PortraitScene::Thinking, PortraitScene::Sleeping,
    PortraitScene::HappyVideo, PortraitScene::UpVideo, PortraitScene::Thinking,
    PortraitScene::MouthOpen, PortraitScene::Smile, PortraitScene::Down,
    PortraitScene::Sleeping, PortraitScene::MouthHalf, PortraitScene::MouthOpen,
    PortraitScene::HappyVideo, PortraitScene::HappyVideo
  };
  static_assert(sizeof(scenes)/sizeof(scenes[0]) == static_cast<uint8_t>(AvatarAnimationId::Count));
  return id < AvatarAnimationId::Count ? scenes[static_cast<uint8_t>(id)] : PortraitScene::Front;
}

constexpr PortraitScene portraitScene(const AvatarController& controller) {
  const auto scene=controller.animation()==AvatarAnimationId::None ?
    portraitExpressionScene(controller.avatar().expressionId()) :
    portraitAnimationScene(controller.animation());
  if (controller.hasLookOverride()) {
    if(controller.look()==UsbLook::Left) return PortraitScene::Left;
    if(controller.look()==UsbLook::Right) return PortraitScene::Right;
    // Explicit center must stop a directional pose or a looking-around video.
    if(scene>=PortraitScene::IdleVideo && scene<=PortraitScene::Up)
      return PortraitScene::Front;
  }
  return scene;
}

constexpr uint16_t portraitFrame(PortraitScene scene, uint32_t elapsedMs) {
  const uint32_t tick = static_cast<uint64_t>(elapsedMs) * 24 / 1000;
  switch(scene) {
    case PortraitScene::Front: return PORTRAIT_STILLS;
    case PortraitScene::Computer: return PORTRAIT_STILLS+1;
    case PortraitScene::Thinking: return PORTRAIT_STILLS+2;
    case PortraitScene::Sleeping: return PORTRAIT_STILLS+3;
    case PortraitScene::MouthHalf: return PORTRAIT_STILLS+4;
    case PortraitScene::MouthOpen: return PORTRAIT_STILLS+5;
    case PortraitScene::IdleVideo: return PORTRAIT_VERTICAL+tick%240;
    case PortraitScene::SearchVideo: return PORTRAIT_HORIZONTAL+tick%240;
    case PortraitScene::ListeningVideo: {
      const uint32_t p=tick%180;
      return PORTRAIT_VERTICAL+(p<=90?p:180-p);
    }
    case PortraitScene::HappyVideo: {
      const uint32_t p=tick%94;
      return PORTRAIT_VERTICAL+192+(p<=47?p:94-p);
    }
    case PortraitScene::UpVideo: {
      const uint32_t p=tick%72;
      return PORTRAIT_VERTICAL+108+(p<=36?p:72-p);
    }
    case PortraitScene::Left: return PORTRAIT_VERTICAL+90-(tick<18?tick:18);
    case PortraitScene::Right: return PORTRAIT_VERTICAL+24+(tick<18?tick:18);
    case PortraitScene::Down: return PORTRAIT_VERTICAL+178-(tick<22?tick:22);
    case PortraitScene::Up: return PORTRAIT_VERTICAL+108+(tick<18?tick:18);
    case PortraitScene::Smile: return PORTRAIT_VERTICAL+222;
  }
  return PORTRAIT_STILLS;
}
