#include <Arduino.h>
#include "Display_ST7789.h"
#include "avatar_controller.h"
#include "portrait_player.h"
#include "usb_control.h"

// Existing USB/voice commands now drive the supplied portrait assets.
static AvatarController controller;
static PortraitPlayer portrait;
static UsbControl usb;
constexpr int EXPRESSION_BUTTON_PIN=0;
static uint16_t scanline[LCD_WIDTH];

void setup() {
  Serial.setRxBufferSize(2048);
  Serial.setTxTimeoutMs(0);
  Serial.begin(115200);
  pinMode(EXPRESSION_BUTTON_PIN,INPUT_PULLUP);
  LCD_Init();
  Set_Backlight(70);
  for(int x=0;x<LCD_WIDTH;++x) scanline[x]=(PORTRAIT_BACKGROUND>>8)|(PORTRAIT_BACKGROUND<<8);
  for(int y=0;y<LCD_HEIGHT;++y) LCD_addWindow(0,y,LCD_WIDTH-1,y,scanline);
  portrait.begin();
  usb.setPortraitDiagnostics(&portrait.diagnostics);
  controller.start(millis());
}

void loop() {
  const uint32_t now=millis();
  controller.update(now,digitalRead(EXPRESSION_BUTTON_PIN)==LOW);
  // Apply USB commands before selecting the next displayed portrait.
  usb.poll(Serial,controller,now);
  const uint32_t started=micros();
  if(portrait.render(now,controller)) {
    LCD_addWindow(0,0,LCD_WIDTH-1,LCD_HEIGHT-1,portrait.pixels());
    const uint32_t elapsed=micros()-started;
    if(elapsed>portrait.diagnostics.maxFrameUs) portrait.diagnostics.maxFrameUs=elapsed;
    controller.framePresented(millis());
    controller.gazeFramePresented(millis());
  }
}
