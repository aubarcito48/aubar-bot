#include <Arduino.h>
#include "Display_ST7789.h"
#include "avatar_render.h"
#include "avatar_state.h"

// Frontal expressions adapted from the original Avatar Lab export.
// This does not execute Avatar Lab's web animation engine.
static uint16_t scanline[LCD_WIDTH];
static AvatarState avatar;
constexpr int EXPRESSION_BUTTON_PIN = 0;  // Waveshare BOOT, active low.

void drawAvatar(float openness) {
  // Stream one row at a time: no full-screen buffer or microSD needed.
  for (int y = 0; y < LCD_HEIGHT; ++y) {
    for (int x = 0; x < LCD_WIDTH; ++x) {
      uint16_t color = avatarPixel(x, y, avatar.expression(), openness);
      scanline[x] = (color >> 8) | (color << 8);
    }
    LCD_SetCursor(0, y, LCD_WIDTH - 1, y);
    LCD_WriteData_nbyte(reinterpret_cast<uint8_t*>(scanline), nullptr,
                        sizeof(scanline));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(EXPRESSION_BUTTON_PIN, INPUT_PULLUP);
  LCD_Init();
  Set_Backlight(70);
  drawAvatar(avatar.openness());
  avatar.framePresented(millis());
  Serial.println("Kirby listo. BOOT: neutral > contento > sorprendido > dormido");
}

void loop() {
  if (avatar.update(millis(), digitalRead(EXPRESSION_BUTTON_PIN) == LOW)) {
    drawAvatar(avatar.openness());
    avatar.framePresented(millis());
  }
}
