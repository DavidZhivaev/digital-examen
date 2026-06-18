// protocol/include/ukk/protocol/header.hpp
#pragma once

#include "types.hpp"
#include "version.hpp"
#include <cstdint>
#include <array>

namespace ukk::protocol {

// Fixed-size message header (cache-line aligned)
struct alignas(64) MessageHeader {
    std::uint32_t magic{PROTOCOL_MAGIC};        // 4 bytes: "UKKP"
    std::uint32_t version{PROTOCOL_VERSION_MAJOR}; // 4 bytes
    MessageType   type{};                        // 1 byte
    std::uint8_t  flags{0};                      // 1 byte (reserved)
    std::uint16_t reserved{0};                   // 2 bytes (alignment)
    std::uint32_t payload_size{0};               // 4 bytes
    UUID          message_id{};                  // 16 bytes
    std::int64_t  timestamp{0};                  // 8 bytes (epoch ms)
    std::array<std::uint8_t, 24> padding{};      // padding to 64 bytes

    [[nodiscard]] constexpr bool is_valid() const noexcept {
        return magic == PROTOCOL_MAGIC &&
               version <= PROTOCOL_VERSION_MAJOR &&
               payload_size <= MAX_MESSAGE_SIZE;
    }

    [[nodiscard]] constexpr bool is_agent_message() const noexcept {
        return static_cast<std::uint8_t>(type) < 0x80;
    }

    [[nodiscard]] constexpr bool is_relay_message() const noexcept {
        return static_cast<std::uint8_t>(type) >= 0x80;
    }
};

static_assert(sizeof(MessageHeader) == 64, "MessageHeader must be 64 bytes");
static_assert(alignof(MessageHeader) == 64, "MessageHeader must be cache-aligned");

} // namespace ukk::protocol
