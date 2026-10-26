#pragma once
#include <stdio.h>
#include "usb_protocol.h"
#include "avatar_data.h"

class UsbControl {
 public:
  const UsbCommand& command() const { return protocol_.command(); }

  // Stream-like interface also permits testing with a bounded fake serial port.
  // Return one typed command at a time for the application layer (TK16).
  template <typename Port>
  bool poll(Port& port) {
    flush(port);
    if (sent_ < responseLength_) return false;
    for (size_t budget = 0; budget < 128 && port.available() > 0; ++budget) {
      const UsbParseResult result = protocol_.feed(static_cast<char>(port.read()));
      if (result == UsbParseResult::Incomplete) continue;
      makeResponse(result);
      flush(port);
      return result == UsbParseResult::Valid;
    }
    return false;
  }

 private:
  template <typename Port>
  void flush(Port& port) {
    const int space = port.availableForWrite();
    if (space <= 0 || sent_ >= responseLength_) return;
    const size_t remaining = responseLength_ - sent_;
    const size_t count = remaining < static_cast<size_t>(space) ? remaining : space;
    sent_ += port.write(reinterpret_cast<const uint8_t*>(response_+sent_), count);
  }

  void makeResponse(UsbParseResult result) {
    const char* response = nullptr;
    switch (result) {
      case UsbParseResult::Empty: response = "ERR EMPTY\n"; break;
      case UsbParseResult::UnknownCommand: response = "ERR UNKNOWN_COMMAND\n"; break;
      case UsbParseResult::InvalidArgument: response = "ERR INVALID_ARGUMENT\n"; break;
      case UsbParseResult::TooLong: response = "ERR LINE_TOO_LONG\n"; break;
      case UsbParseResult::InvalidCharacter: response = "ERR INVALID_CHARACTER\n"; break;
      default: break;
    }
    if (response) snprintf(response_, sizeof(response_), "%s", response);
    else {
      const auto& cmd = command();
      switch (cmd.type) {
        case UsbCommandType::Ping:
          snprintf(response_, sizeof(response_), "OK PONG 1\n"); break;
        case UsbCommandType::Expression:
          snprintf(response_, sizeof(response_), "OK VALIDATED EXPRESSION %s\n",
                   avatarExpression(cmd.expression).name); break;
        case UsbCommandType::Look:
          snprintf(response_, sizeof(response_), "OK VALIDATED LOOK %s\n",
                   cmd.look == UsbLook::Left ? "izquierda" : cmd.look == UsbLook::Right ? "derecha" : "centro"); break;
        case UsbCommandType::Mode:
          snprintf(response_, sizeof(response_), "OK VALIDATED MODE %s\n",
                   cmd.mode == UsbMode::Manual ? "manual" : "auto"); break;
      }
    }
    responseLength_ = strlen(response_);
    sent_ = 0;
  }

  UsbProtocol protocol_;
  char response_[80] = {};
  size_t responseLength_ = 0;
  size_t sent_ = 0;
};
