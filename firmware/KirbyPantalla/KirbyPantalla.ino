#include <Arduino.h>
#include "Display_ST7789.h"
#include "avatar_render.h"
#include "blink_animation.h"

// First prototype: the exported shape and colors, with a simple blink.
// This does not execute Avatar Lab's web animation engine.
static uint16_t scanline[LCD_WIDTH];
static BlinkAnimation blink;

void drawAvatar(float openness) {
  // Stream one row at a time: no full-screen buffer or microSD needed.
  for (int y = 0; y < LCD_HEIGHT; ++y) {
    for (int x = 0; x < LCD_WIDTH; ++x) {
      uint16_t color = avatarPixel(x, y, openness);
      scanline[x] = (color >> 8) | (color << 8);
    }
    LCD_SetCursor(0, y, LCD_WIDTH - 1, y);
    LCD_WriteData_nbyte(reinterpret_cast<uint8_t*>(scanline), nullptr,
                        sizeof(scanline));
  }
}

void setup() {
  Serial.begin(115200);
  LCD_Init();
  Set_Backlight(70);
  drawAvatar(blink.openness());
  blink.framePresented(millis());
  Serial.println("Kirby listo. ESP32-S3-LCD-1.47B");
}

void loop() {
  if (blink.update(millis())) {
    drawAvatar(blink.openness());
    blink.framePresented(millis());
  }
}
