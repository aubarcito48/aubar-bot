#include "portrait_asset_path.h"
.section .rodata.aubarPortraitData,"a"
.balign 4
.global aubarPortraitData
aubarPortraitData:
.incbin AUBAR_PORTRAIT_DATA_FILE
