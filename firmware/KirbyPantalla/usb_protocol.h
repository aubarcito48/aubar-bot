#pragma once
#include <stddef.h>
#include <string.h>
#include "avatar_types.h"

enum class UsbCommandType { Ping, Expression, Look, Mode };
enum class UsbLook { Left, Center, Right };
enum class UsbMode { Manual, Auto };
enum class UsbParseResult { Incomplete, Valid, Empty, UnknownCommand, InvalidArgument,
                            TooLong, InvalidCharacter };

struct UsbCommand {
  UsbCommandType type = UsbCommandType::Ping;
  AvatarExpressionId expression = AvatarExpressionId::Neutral;
  UsbLook look = UsbLook::Center;
  UsbMode mode = UsbMode::Auto;
};

class UsbProtocol {
 public:
  static constexpr size_t MAX_LINE = 64;
  const UsbCommand& command() const { return command_; }

  UsbParseResult feed(char byte) {
    if (byte != '\n') {
      if (length_ >= MAX_LINE) overflow_ = true;
      else if (!overflow_) buffer_[length_++] = byte;
      return UsbParseResult::Incomplete;
    }
    UsbParseResult result;
    if (overflow_) result = UsbParseResult::TooLong;
    else {
      if (length_ && buffer_[length_-1] == '\r') --length_;
      buffer_[length_] = '\0';
      result = parse();
    }
    length_ = 0;
    overflow_ = false;
    return result;
  }

 private:
  UsbParseResult parse() {
    if (!length_) return UsbParseResult::Empty;
    for (size_t i = 0; i < length_; ++i) {
      if (buffer_[i] < 32 || buffer_[i] > 126) return UsbParseResult::InvalidCharacter;
    }
    char* argument = strchr(buffer_, ' ');
    if (argument) *argument++ = '\0';
    UsbCommand parsed;
    if (strcmp(buffer_, "PING") == 0) {
      if (argument) return UsbParseResult::InvalidArgument;
      parsed.type = UsbCommandType::Ping;
    } else if (strcmp(buffer_, "EXPRESSION") == 0) {
      parsed.type = UsbCommandType::Expression;
      if (!argument) return UsbParseResult::InvalidArgument;
      if (strcmp(argument, "neutral") == 0) parsed.expression = AvatarExpressionId::Neutral;
      else if (strcmp(argument, "contento") == 0) parsed.expression = AvatarExpressionId::Happy;
      else if (strcmp(argument, "sorprendido") == 0) parsed.expression = AvatarExpressionId::Surprised;
      else if (strcmp(argument, "dormido") == 0) parsed.expression = AvatarExpressionId::Sleeping;
      else if (strcmp(argument, "enojado") == 0) parsed.expression = AvatarExpressionId::Angry;
      else return UsbParseResult::InvalidArgument;
    } else if (strcmp(buffer_, "LOOK") == 0) {
      parsed.type = UsbCommandType::Look;
      if (!argument) return UsbParseResult::InvalidArgument;
      if (strcmp(argument, "izquierda") == 0) parsed.look = UsbLook::Left;
      else if (strcmp(argument, "centro") == 0) parsed.look = UsbLook::Center;
      else if (strcmp(argument, "derecha") == 0) parsed.look = UsbLook::Right;
      else return UsbParseResult::InvalidArgument;
    } else if (strcmp(buffer_, "MODE") == 0) {
      parsed.type = UsbCommandType::Mode;
      if (!argument) return UsbParseResult::InvalidArgument;
      if (strcmp(argument, "manual") == 0) parsed.mode = UsbMode::Manual;
      else if (strcmp(argument, "auto") == 0) parsed.mode = UsbMode::Auto;
      else return UsbParseResult::InvalidArgument;
    } else return UsbParseResult::UnknownCommand;
    command_ = parsed;  // Invalid messages never overwrite a valid command.
    return UsbParseResult::Valid;
  }

  char buffer_[MAX_LINE+1] = {};
  size_t length_ = 0;
  bool overflow_ = false;
  UsbCommand command_;
};
