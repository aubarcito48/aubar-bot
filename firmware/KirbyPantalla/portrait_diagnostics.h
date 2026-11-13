#pragma once
#include <stdint.h>
struct PortraitDiagnostics {
  bool ready=false;
  uint16_t frame=0;
  uint16_t face=0xffff;
  uint32_t drawn=0, errors=0, checksum=0, maxFrameUs=0, psramBytes=0;
};
