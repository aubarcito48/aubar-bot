#pragma once
#include <Arduino.h>
#include <esp_heap_caps.h>
#include <miniz.h>
#include "portrait_assets.h"
#include "portrait_routes.h"
#include "portrait_diagnostics.h"
#include "portrait_speech_face.h"

// Bounded-seek keyframe/XOR zlib frames; indexed and crossfade buffers in RAM.
class PortraitPlayer {
 public:
  PortraitDiagnostics diagnostics;
  bool begin() {
    diagnostics.psramBytes=ESP.getPsramSize();
    pixels_=static_cast<uint16_t*>(allocate(PORTRAIT_PIXELS*2,true));
    previous_=static_cast<uint16_t*>(allocate(PORTRAIT_PIXELS*2));
    indices_=static_cast<uint8_t*>(allocate(PORTRAIT_PIXELS));
    delta_=static_cast<uint8_t*>(allocate(PORTRAIT_PIXELS));
    face_=static_cast<uint8_t*>(allocate(PORTRAIT_PIXELS));
    // ROM's convenience helper puts this large state on the stack. Keep it
    // on the heap to avoid overflowing the Arduino loop task during decode.
    inflater_=static_cast<tinfl_decompressor*>(allocate(sizeof(tinfl_decompressor)));
    diagnostics.ready=pixels_ && previous_ && indices_ && delta_ && face_ && inflater_;
    if(!diagnostics.ready) return false;
    for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) pixels_[i]=swap(PORTRAIT_BACKGROUND);
    return true;
  }
  uint16_t* pixels() { return pixels_; }
  bool render(uint32_t now,const AvatarController& controller) {
    if(!diagnostics.ready || (hasDrawn_ && now-lastDrawAt_<41)) return false;
    const auto scene=portraitScene(controller);
    const bool speaking=controller.speaking(now);
    if(speaking && !wasSpeaking_) speechStartedAt_=now;
    wasSpeaking_=speaking;
    const auto face=speaking?portraitSpeechFace(scene):PortraitSpeechFace{0xffff,90,142};
    const bool plainSpeech=scene==PortraitScene::Front || scene==PortraitScene::IdleVideo ||
      scene==PortraitScene::ListeningVideo || scene==PortraitScene::SearchVideo;
    const bool mouthTrack=speaking && (face.frame!=0xffff || plainSpeech);
    // A logical eye-step change must not restart the same portrait animation.
    const uint32_t selection=speaking ? 0x80000000u|static_cast<uint32_t>(scene) : (static_cast<uint32_t>(scene)<<16) |
      (controller.animation()==AvatarAnimationId::None ?
        static_cast<uint8_t>(controller.avatar().expressionId()) :
        256+static_cast<uint8_t>(controller.animation())) |
      (controller.hasLookOverride()?0x8000:0);
    if(selection!=selection_) {
      memcpy(previous_,pixels_,PORTRAIT_PIXELS*2);
      startedAt_=now; selection_=selection; fade_=hasDrawn_; lastBlend_=0;
    }
    const uint16_t frame=mouthTrack ? PORTRAIT_SPEECH+speechFrame(now-speechStartedAt_) :
      portraitFrame(scene,now-startedAt_);
    const uint32_t elapsed=now-startedAt_;
    const uint16_t blend=!fade_ || elapsed>=220 ? 256 : elapsed*256/220;
    if(hasDrawn_ && frame==diagnostics.frame && blend==lastBlend_) return false;
    if(frame>=PORTRAIT_FRAME_COUNT) { ++diagnostics.errors; return false; }
    bool faceChanged=face.frame!=0xffff && face.frame!=cachedFace_;
    if(faceChanged) {
      if(!decode(face.frame)) { decoded_=0xffff; ++diagnostics.errors; return false; }
      memcpy(face_,indices_,PORTRAIT_PIXELS); cachedFace_=face.frame;
    }
    if(!hasDrawn_ || frame!=diagnostics.frame || faceChanged) {
      if(!decode(frame)) {
        decoded_=0xffff;
        ++diagnostics.errors; return false;
      }
      uint32_t hash=2166136261u;
      for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) hash=(hash^indices_[i])*16777619u;
      diagnostics.checksum=hash;
    }
    for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) {
      uint16_t target=PORTRAIT_PALETTE[face.frame==0xffff?indices_[i]:face_[i]];
      if(face.frame!=0xffff) {
        const int16_t dx=static_cast<int16_t>(i%PORTRAIT_WIDTH)-face.x;
        const int16_t dy=static_cast<int16_t>(i/PORTRAIT_WIDTH)-face.y;
        const int16_t ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
        if(ax<16 && ay<11) {
          int16_t edge=(16-ax)<(11-ay)?16-ax:11-ay;
          const uint16_t weight=edge>=4?256:edge*64;
          const auto mouth=indices_[(142+dy)*PORTRAIT_WIDTH+90+dx];
          target=mix(target,PORTRAIT_PALETTE[mouth],weight);
        }
      }
      if(blend==256) pixels_[i]=swap(target);
      else {
        const uint16_t from=swap(previous_[i]);
        pixels_[i]=swap(mix(from,target,blend));
      }
    }
    diagnostics.frame=frame; ++diagnostics.drawn;
    diagnostics.face=speaking && !mouthTrack?frame:face.frame;
    hasDrawn_=true; lastDrawAt_=now; lastBlend_=blend;
    return true;
  }
 private:
  static uint16_t mix(uint16_t from,uint16_t to,uint16_t blend) {
    const uint16_t r=(((from>>11)*(256-blend)+(to>>11)*blend)>>8);
    const uint16_t g=((((from>>5)&63)*(256-blend)+((to>>5)&63)*blend)>>8);
    const uint16_t b=(((from&31)*(256-blend)+(to&31)*blend)>>8);
    return (r<<11)|(g<<5)|b;
  }
  bool unpack(uint16_t frame,bool difference,bool reverse=false) {
    uint8_t* target=difference?delta_:indices_;
    tinfl_init(inflater_);
    size_t input=reverse?PORTRAIT_REVERSE_LENGTHS[frame]:PORTRAIT_LENGTHS[frame],output=PORTRAIT_PIXELS;
    const auto offset=reverse?PORTRAIT_REVERSE_OFFSETS[frame]:PORTRAIT_OFFSETS[frame];
    const auto result=tinfl_decompress(inflater_,aubarPortraitData+offset,
      &input,target,target,&output,TINFL_FLAG_PARSE_ZLIB_HEADER|TINFL_FLAG_USING_NON_WRAPPING_OUTPUT_BUF);
    if(result!=TINFL_STATUS_DONE || output!=PORTRAIT_PIXELS) return false;
    if(difference) for(uint32_t i=0;i<PORTRAIT_PIXELS;++i) indices_[i]^=delta_[i];
    return true;
  }
  bool decode(uint16_t frame) {
    if(frame==decoded_) return true;
    // XOR is reversible: the speech ping-pong can step back without seeking.
    if(decoded_!=0xffff && frame+1==decoded_ &&
       (PORTRAIT_DELTA[decoded_] || PORTRAIT_REVERSE_LENGTHS[decoded_])) {
      if(!unpack(decoded_,true,!PORTRAIT_DELTA[decoded_])) return false;
      decoded_=frame; return true;
    }
    uint16_t key=frame;
    while(PORTRAIT_DELTA[key]) --key;
    uint16_t next=key;
    if(decoded_!=0xffff && decoded_>=key && decoded_<frame) next=decoded_+1;
    for(uint16_t i=next;i<=frame;++i) {
      if(!unpack(i,PORTRAIT_DELTA[i])) return false;
      decoded_=i;
    }
    return true;
  }
  static uint16_t speechFrame(uint32_t elapsed) {
    // Keep natural source motion. Never restart per syllable or per heartbeat.
    // Ping-pong avoids a discontinuous last-to-first cut in this supplied clip.
    constexpr uint16_t first=0,last=PORTRAIT_SPEECH_COUNT-1,span=last-first;
    const uint32_t tick=elapsed*24/1000;
    const uint16_t p=tick%(span*2);
    return first+(p<=span?p:span*2-p);
  }
  static uint16_t swap(uint16_t c) { return (c>>8)|(c<<8); }
  static void* allocate(size_t size,bool internalFirst=false) {
    void* p=heap_caps_malloc(size,(internalFirst?MALLOC_CAP_INTERNAL:MALLOC_CAP_SPIRAM)|MALLOC_CAP_8BIT);
    if(!p) p=heap_caps_malloc(size,MALLOC_CAP_8BIT);
    return p;
  }
  uint16_t *pixels_=nullptr,*previous_=nullptr;
  uint8_t *indices_=nullptr,*delta_=nullptr,*face_=nullptr;
  tinfl_decompressor* inflater_=nullptr;
  uint32_t selection_=0xffffffffu,startedAt_=0,lastDrawAt_=0,speechStartedAt_=0;
  uint16_t lastBlend_=0,decoded_=0xffff,cachedFace_=0xffff;
  bool hasDrawn_=false,fade_=false,wasSpeaking_=false;
};
