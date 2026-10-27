#include "../../firmware/KirbyPantalla/usb_control.h"

bool passed = true;
void check(bool condition) { passed = condition && passed; }

UsbParseResult feed(UsbProtocol& parser, const char* bytes, size_t length) {
  UsbParseResult result = UsbParseResult::Incomplete;
  for (size_t i = 0; i < length; ++i) result = parser.feed(bytes[i]);
  return result;
}

UsbParseResult line(UsbProtocol& parser, const char* text) {
  return feed(parser, text, strlen(text));
}

struct FakePort {
  const char* input = "";
  size_t length = 0, position = 0, outputLength = 0;
  int room = 0;
  char output[256] = {};
  void inputBytes(const char* data, size_t size) { input = data; length = size; position = 0; }
  int available() const { return length - position; }
  int read() { return static_cast<uint8_t>(input[position++]); }
  int availableForWrite() const { return room; }
  size_t write(const uint8_t* bytes, size_t count) {
    if (count > static_cast<size_t>(room) || outputLength+count >= sizeof(output)) {
      check(false);
      return 0;
    }
    memcpy(output+outputLength, bytes, count);
    outputLength += count;
    output[outputLength] = '\0';
    room -= count;
    return count;
  }
};

void testCommands() {
  UsbProtocol parser;
  char message[96];
  for (uint8_t i = 0; i < static_cast<uint8_t>(AvatarExpressionId::Count); ++i) {
    snprintf(message,sizeof(message),"EXPRESSION %s\n",AVATAR_EXPRESSIONS[i].name);
    check(line(parser, message) == UsbParseResult::Valid);
    check(parser.command().type == UsbCommandType::Expression &&
          parser.command().expression == static_cast<AvatarExpressionId>(i));
  }
  check(line(parser, "LOOK izquierda\n") == UsbParseResult::Valid && parser.command().look == UsbLook::Left);
  check(line(parser, "LOOK centro\n") == UsbParseResult::Valid && parser.command().look == UsbLook::Center);
  check(line(parser, "LOOK derecha\n") == UsbParseResult::Valid && parser.command().look == UsbLook::Right);
  check(line(parser, "MODE manual\n") == UsbParseResult::Valid && parser.command().mode == UsbMode::Manual);
  check(line(parser, "MODE auto\n") == UsbParseResult::Valid && parser.command().mode == UsbMode::Auto);
  check(line(parser, "PI") == UsbParseResult::Incomplete);
  check(line(parser, "NG\r\n") == UsbParseResult::Valid && parser.command().type == UsbCommandType::Ping);
  check(line(parser, "STATUS\n") == UsbParseResult::Valid && parser.command().type == UsbCommandType::Status);
}

void testInvalidLinesAndRecovery() {
  UsbProtocol parser;
  check(line(parser, "EXPRESSION enojado\n") == UsbParseResult::Valid);
  const char* invalid[] = {"EXPRESSION\n", "EXPRESSION contento extra\n", "LOOK arriba\n",
      "MODE falso\n", "PING extra\n", "STATUS extra\n", "LOOK  centro\n", "LOOK centro \n"};
  for (const char* message : invalid) check(line(parser, message) == UsbParseResult::InvalidArgument);
  check(parser.command().expression == AvatarExpressionId::Angry);
  check(line(parser, "HELLO\n") == UsbParseResult::UnknownCommand);
  check(line(parser, "\n") == UsbParseResult::Empty);
  const char nul[] = {'P','I','N','G','\0','\n'};
  check(feed(parser, nul, sizeof(nul)) == UsbParseResult::InvalidCharacter);
  check(line(parser, "PING\rX\n") == UsbParseResult::InvalidCharacter);
  check(line(parser, "PING\t\n") == UsbParseResult::InvalidCharacter);
  const char unicode[] = {'L', static_cast<char>(0xC3), static_cast<char>(0xA1), '\n'};
  check(feed(parser, unicode, sizeof(unicode)) == UsbParseResult::InvalidCharacter);
  for (size_t i = 0; i < UsbProtocol::MAX_LINE; ++i) parser.feed('X');
  check(parser.feed('\n') == UsbParseResult::UnknownCommand);  // Exact limit is not overflow.
  for (size_t i = 0; i < 1000; ++i) parser.feed('X');
  check(line(parser, "PING\n") == UsbParseResult::TooLong);  // Suffix must not execute.
  check(line(parser, "PING\n") == UsbParseResult::Valid);
}

void testTransportBackpressureAndBudget() {
  UsbControl usb;
  AvatarController controller;
  FakePort port;
  const char input[] = "EXPRESSION enojado\nPING\n";
  port.inputBytes(input, strlen(input));
  check(usb.poll(port, controller, 0));  // Applied even though the PC cannot read yet.
  check(usb.command().expression == AvatarExpressionId::Angry);
  check(controller.avatar().expressionId() == AvatarExpressionId::Angry && controller.mode() == UsbMode::Manual);
  const size_t stoppedAt = port.position;
  for (int i = 0; i < 10; ++i) check(!usb.poll(port, controller, 0) && port.position == stoppedAt);
  int commands = 1;
  for (int i = 0; i < 100; ++i) {
    port.room = 1;  // Force responses to span many polls.
    if (usb.poll(port, controller, 0)) ++commands;
  }
  check(commands == 2);
  check(strcmp(port.output, "OK APPLIED EXPRESSION enojado\nOK PONG 4\n") == 0);

  UsbControl flooded;
  FakePort floodPort;
  char flood[1000];
  memset(flood, 'X', sizeof(flood));
  floodPort.inputBytes(flood, sizeof(flood));
  while (floodPort.available()) {
    const size_t before = floodPort.position;
    check(!flooded.poll(floodPort, controller, 0));
    check(floodPort.position-before <= 128);
  }
  const char recovery[] = "\nPING\n";
  floodPort.inputBytes(recovery, strlen(recovery));
  floodPort.room = 200;
  check(!flooded.poll(floodPort, controller, 0));
  floodPort.room = 200;
  check(flooded.poll(floodPort, controller, 0));
  floodPort.room = 200;
  check(!flooded.poll(floodPort, controller, 0));
  check(strcmp(floodPort.output, "ERR LINE_TOO_LONG\nOK PONG 4\n") == 0);
  check(controller.avatar().expressionId() == AvatarExpressionId::Angry);
}

void testLineEndWaitsForPayloadDrain() {
  UsbControl usb;
  AvatarController controller;
  FakePort port;
  port.room=128;
  port.inputBytes("PING\n",5);
  check(usb.poll(port,controller,0));
  check(strcmp(port.output,"OK PONG 4")==0);
  check(!usb.poll(port,controller,1));
  check(strcmp(port.output,"OK PONG 4")==0);
  port.room=128;  // Host consumed the pending payload.
  check(!usb.poll(port,controller,2));
  check(strcmp(port.output,"OK PONG 4\n")==0);
}

void setup() {
  Serial.begin(115200);
  testCommands();
  testInvalidLinesAndRecovery();
  testTransportBackpressureAndBudget();
  testLineEndWaitsForPayloadDrain();
}

void loop() {
  Serial.println(passed ? "TK15 TESTS PASS" : "TK15 TESTS FAIL");
  delay(1000);
}
