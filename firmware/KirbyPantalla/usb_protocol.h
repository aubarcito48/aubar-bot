#pragma once
#include <stddef.h>
#include <string.h>
#include "animation_data.h"

enum class UsbCommandType { Ping, Status, Expression, Look, Mode, Animation };
enum class UsbLook { Left, Center, Right };
enum class UsbMode { Manual, Auto };
enum class UsbParseResult { Incomplete, Valid, Empty, UnknownCommand, InvalidArgument,
                            TooLong, InvalidCharacter };

struct UsbCommand {
  UsbCommandType type = UsbCommandType::Ping;
  AvatarExpressionId expression = AvatarExpressionId::Neutral;
  UsbLook look = UsbLook::Center;
  UsbMode mode = UsbMode::Auto;
  AvatarAnimationId animation = AvatarAnimationId::None;
  bool hasLook = false;
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
    // An optional final gaze is part of the same atomic expression/animation.
    if (strcmp(buffer_,"EXPRESSION")==0 || strcmp(buffer_,"ANIMATION")==0) {
      char* gaze = argument ? strchr(argument,' ') : nullptr;
      if (gaze) {
        *gaze++ = '\0';
        parsed.hasLook = true;
        if (strcmp(gaze,"izquierda")==0) parsed.look=UsbLook::Left;
        else if (strcmp(gaze,"centro")==0) parsed.look=UsbLook::Center;
        else if (strcmp(gaze,"derecha")==0) parsed.look=UsbLook::Right;
        else return UsbParseResult::InvalidArgument;
      }
    }
    if (strcmp(buffer_, "PING") == 0) {
      if (argument) return UsbParseResult::InvalidArgument;
      parsed.type = UsbCommandType::Ping;
    } else if (strcmp(buffer_, "STATUS") == 0) {
      if (argument) return UsbParseResult::InvalidArgument;
      parsed.type = UsbCommandType::Status;
    } else if (strcmp(buffer_, "EXPRESSION") == 0) {
      parsed.type = UsbCommandType::Expression;
      if (!argument) return UsbParseResult::InvalidArgument;
      bool found = false;
      for (uint8_t i=0; i<static_cast<uint8_t>(AvatarExpressionId::Count); ++i) {
        if (strcmp(argument, AVATAR_EXPRESSIONS[i].name)==0) {
          parsed.expression=static_cast<AvatarExpressionId>(i); found=true; break;
        }
      }
      if (!found) return UsbParseResult::InvalidArgument;
    } else if (strcmp(buffer_, "ANIMATION") == 0) {
      parsed.type = UsbCommandType::Animation;
      if (!argument) return UsbParseResult::InvalidArgument;
      bool found = false;
      for (uint8_t i=0; i<static_cast<uint8_t>(AvatarAnimationId::Count); ++i) {
        if (strcmp(argument, AVATAR_ANIMATIONS[i].name)==0) {
          parsed.animation=static_cast<AvatarAnimationId>(i); found=true; break;
        }
      }
      if (!found) return UsbParseResult::InvalidArgument;
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
