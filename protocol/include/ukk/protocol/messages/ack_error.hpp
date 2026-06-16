// protocol/include/ukk/protocol/messages/ack_error.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// ACK message: Message acknowledgment
struct Ack {
    static constexpr MessageType message_type{MessageType::ACK};
    static constexpr std::string_view type_name{"ACK"};

    struct Args {
        UUID acked_message_id{};    // ID of acknowledged message
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args&) noexcept {
        return true;
    }
};

// Error codes
enum class ErrorCode : std::uint16_t {
    UNKNOWN               = 0x0000,
    INVALID_MESSAGE       = 0x0001,
    INVALID_PAYLOAD       = 0x0002,
    UNSUPPORTED_VERSION   = 0x0003,
    AUTHENTICATION_FAILED = 0x0004,
    TASK_NOT_FOUND        = 0x0005,
    TASK_EXECUTION_FAILED = 0x0006,
    POLICY_INVALID        = 0x0007,
    RESOURCE_UNAVAILABLE  = 0x0008,
    RATE_LIMITED          = 0x0009,
    INTERNAL_ERROR        = 0x00FF,
};

// ERROR message: Error response
struct Error {
    static constexpr MessageType message_type{MessageType::ERROR};
    static constexpr std::string_view type_name{"ERROR"};

    struct Args {
        UUID         reference_id{};    // ID of message that caused error
        ErrorCode    code{ErrorCode::UNKNOWN};
        std::string  message{};         // Human-readable error
        std::string  details{};         // Additional context (JSON)
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return !args.message.empty();
    }
};

} // namespace ukk::protocol::messages
