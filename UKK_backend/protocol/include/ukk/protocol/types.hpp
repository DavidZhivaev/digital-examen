// protocol/include/ukk/protocol/types.hpp
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <optional>
#include <variant>
#include <chrono>
#include <algorithm>

namespace ukk::protocol {

// UUID as fixed-size array (16-byte aligned)
struct alignas(16) UUID {
    std::array<std::uint8_t, 16> bytes{};

    [[nodiscard]] constexpr bool operator==(const UUID&) const noexcept = default;

    // Check if UUID is nil (all zeros)
    [[nodiscard]] constexpr bool is_nil() const noexcept {
        return std::all_of(bytes.begin(), bytes.end(),
                          [](std::uint8_t b) { return b == 0; });
    }

    [[nodiscard]] std::string to_string() const;
    [[nodiscard]] static UUID generate();
    [[nodiscard]] static UUID from_string(std::string_view str);
};

// ISO 8601 timestamp wrapper with epoch_ms accessor
struct Timestamp {
    std::int64_t epoch_ms{0};  // Milliseconds since Unix epoch

    // Default constructor
    constexpr Timestamp() noexcept = default;

    // Constructor from epoch milliseconds
    constexpr explicit Timestamp(std::int64_t ms) noexcept : epoch_ms{ms} {}

    // Constructor from chrono time_point
    explicit Timestamp(std::chrono::system_clock::time_point tp) noexcept
        : epoch_ms{std::chrono::duration_cast<std::chrono::milliseconds>(
              tp.time_since_epoch()).count()} {}

    // Get as chrono time_point
    [[nodiscard]] std::chrono::system_clock::time_point to_time_point() const noexcept {
        return std::chrono::system_clock::time_point{
            std::chrono::milliseconds{epoch_ms}};
    }

    // Comparison operators
    [[nodiscard]] constexpr bool operator==(const Timestamp&) const noexcept = default;
    [[nodiscard]] constexpr auto operator<=>(const Timestamp&) const noexcept = default;

    [[nodiscard]] std::string to_iso8601() const;
    [[nodiscard]] static Timestamp now();
    [[nodiscard]] static Timestamp from_iso8601(std::string_view str);
};

// Message type enumeration
enum class MessageType : std::uint8_t {
    // Agent -> Relay
    REGISTER        = 0x01,
    HEARTBEAT       = 0x02,
    SCREENSHOT      = 0x03,
    TASK_RESULT     = 0x04,
    EVENT           = 0x05,
    METRICS         = 0x06,
    PONG            = 0x07,

    // Relay -> Agent
    TASK            = 0x81,
    POLICY_UPDATE   = 0x82,
    PING            = 0x83,
    AGENT_UPDATE    = 0x84,
    ACK             = 0x85,
    ERROR           = 0x86,
};

// Event severity levels
enum class Severity : std::uint8_t {
    LOW      = 0,
    MEDIUM   = 1,
    HIGH     = 2,
    CRITICAL = 3,
};

// Task priority
enum class Priority : std::uint8_t {
    NORMAL = 0,
    HIGH   = 1,
};

// Task status
enum class TaskStatus : std::uint8_t {
    OK      = 0,
    ERROR   = 1,
    TIMEOUT = 2,
};

// Agent status
enum class AgentStatus : std::uint8_t {
    ONLINE  = 0,
    OFFLINE = 1,
    ERROR   = 2,
};

// Constexpr string for message type names
[[nodiscard]] constexpr std::string_view message_type_name(MessageType type) noexcept {
    switch (type) {
        case MessageType::REGISTER:       return "REGISTER";
        case MessageType::HEARTBEAT:      return "HEARTBEAT";
        case MessageType::SCREENSHOT:     return "SCREENSHOT";
        case MessageType::TASK_RESULT:    return "TASK_RESULT";
        case MessageType::EVENT:          return "EVENT";
        case MessageType::METRICS:        return "METRICS";
        case MessageType::PONG:           return "PONG";
        case MessageType::TASK:           return "TASK";
        case MessageType::POLICY_UPDATE:  return "POLICY_UPDATE";
        case MessageType::PING:           return "PING";
        case MessageType::AGENT_UPDATE:   return "AGENT_UPDATE";
        case MessageType::ACK:            return "ACK";
        case MessageType::ERROR:          return "ERROR";
    }
    return "UNKNOWN";
}

} // namespace ukk::protocol
