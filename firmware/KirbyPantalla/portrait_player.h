#pragma once
#include <Arduino.h>
#include <esp_heap_caps.h>
#include <miniz.h>
#include "portrait_assets.h"
#include "portrait_routes.h"
#include "portrait_diagnostics.h"

// Random-access zlib frames in flash; indexed image and crossfade buffers in RAM.
class PortraitPlayer {
 public:
  PortraitDiagnostics diagnostics;
  bool begin() {
    diagnostics.psramBytes=ESP.getPsramSize();
    pixels_=static_cast<uint16_t*>(allocate(PORTRAIT_PIXELS*2,true));
    previous_=static_cast<uint16_t*>(allocate(PORTRAIT_PIXELS*2));
    indices_=static_cast<uint8_t*>(allocate(PORTRAIT_PIXELS));
    // ROM's convenience helper puts this large state on the stack. Keep it
    // on the heap to avoid overflowing the Arduino loop task during decode.
    inflater_=static_cast<tinfl_decompressor*>(allocate(sizeof(tinfl_decompressor)));
    diagnostics.ready=pixels_ && previous_ && indices_ && inflater_;
    if(!diagnostics.ready) return false;
    for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) pixels_[i]=swap(PORTRAIT_BACKGROUND);
    return true;
  }
  uint16_t* pixels() { return pixels_; }
  bool render(uint32_t now,const AvatarController& controller) {
    if(!diagnostics.ready || (hasDrawn_ && now-lastDrawAt_<41)) return false;
    const auto scene=portraitScene(controller);
    // A logical eye-step change must not restart the same portrait animation.
    const uint32_t selection=(static_cast<uint32_t>(scene)<<16) |
      (controller.animation()==AvatarAnimationId::None ?
        static_cast<uint8_t>(controller.avatar().expressionId()) :
        256+static_cast<uint8_t>(controller.animation())) |
      (controller.hasLookOverride()?0x8000:0);
    if(selection!=selection_) {
      memcpy(previous_,pixels_,PORTRAIT_PIXELS*2);
      startedAt_=now; selection_=selection; fade_=hasDrawn_; lastBlend_=0;
    }
    const uint16_t frame=portraitFrame(scene,now-startedAt_);
    const uint32_t elapsed=now-startedAt_;
    const uint16_t blend=!fade_ || elapsed>=220 ? 256 : elapsed*256/220;
    if(hasDrawn_ && frame==diagnostics.frame && blend==lastBlend_) return false;
    if(frame>=PORTRAIT_FRAME_COUNT) { ++diagnostics.errors; return false; }
    if(!hasDrawn_ || frame!=diagnostics.frame) {
      tinfl_init(inflater_);
      size_t input=PORTRAIT_LENGTHS[frame],output=PORTRAIT_PIXELS;
      const auto result=tinfl_decompress(inflater_,
        aubarPortraitData+PORTRAIT_OFFSETS[frame],&input,indices_,indices_,&output,
        TINFL_FLAG_PARSE_ZLIB_HEADER|TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF);
      if(result!=TINFL_STATUS_DONE || output!=PORTRAIT_PIXELS) {
        ++diagnostics.errors; return false;
      }
      uint32_t hash=2166136261u;
      for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) hash=(hash^indices_[i])*16777619u;
      diagnostics.checksum=hash;
    }
    for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) {
      const uint16_t target=PORTRAIT_PALETTE[indices_[i]];
      if(blend==256) pixels_[i]=swap(target);
      else {
        const uint16_t from=swap(previous_[i]);
        const uint16_t r=(((from>>11)*(256-blend)+(target>>11)*blend)>>8);
        const uint16_t g=((((from>>5)&63)*(256-blend)+((target>>5)&63)*blend)>>8);
        const uint16_t b=(((from&31)*(256-blend)+(target&31)*blend)>>8);
        pixels_[i]=swap((r<<11)|(g<<5)|b);
      }
    }
    diagnostics.frame=frame; ++diagnostics.drawn;
    hasDrawn_=true; lastDrawAt_=now; lastBlend_=blend;
    return true;
  }
 private:
  static uint16_t swap(uint16_t c) { return (c>>8)|(c<<8); }
  static void* allocate(size_t size,bool internalFirst=false) {
    void* p=heap_caps_malloc(size,(internalFirst?MALLOC_CAP_INTERNAL:MALLOC_CAP_SPIRAM)|MALLOC_CAP_8BIT);
    if(!p) p=heap_caps_malloc(size,MALLOC_CAP_8BIT);
    return p;
  }
  uint16_t *pixels_=nullptr,*previous_=nullptr;
  uint8_t* indices_=nullptr;
  tinfl_decompressor* inflater_=nullptr;
  uint32_t selection_=0xffffffffu,startedAt_=0,lastDrawAt_=0;
  uint16_t lastBlend_=0;
  bool hasDrawn_=false,fade_=false;
};
