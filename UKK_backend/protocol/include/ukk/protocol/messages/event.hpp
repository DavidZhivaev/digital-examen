// protocol/include/ukk/protocol/messages/event.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <msgpack.hpp>
#include <string>
#include <variant>
#include <cstdint>

namespace ukk::protocol::messages {

// Event type enumeration
enum class EventType : std::uint8_t {
    USB_CONNECTED    = 0x01,
    USB_DISCONNECTED = 0x02,
    P2P_DETECTED     = 0x03,
    TAMPER_DETECTED  = 0x04,
    PROCESS_KILLED   = 0x05,
    AGENT_OFFLINE    = 0x06,
    POLICY_VIOLATION = 0x07,
    GPU_THRESHOLD    = 0x08,
};

MSGPACK_ADD_ENUM(EventType);

// USB event details
struct UsbEventDetails {
    std::uint16_t vendor_id{0};
    std::uint16_t product_id{0};
    std::string   device_class{};
    std::string   serial{};

    MSGPACK_DEFINE(vendor_id, product_id, device_class, serial)
};

// P2P event details
struct P2pEventDetails {
    std::string local_ip{};
    std::string remote_ip{};
    std::uint16_t local_port{0};
    std::uint16_t remote_port{0};
    std::string protocol{};  // "TCP" or "UDP"

    MSGPACK_DEFINE(local_ip, remote_ip, local_port, remote_port, protocol)
};

// Process event details
struct ProcessEventDetails {
    std::uint32_t pid{0};
    std::string   process_name{};
    std::string   reason{};

    MSGPACK_DEFINE(pid, process_name, reason)
};

// Tamper event details
struct TamperEventDetails {
    std::string expected_hash{};
    std::string actual_hash{};
    std::string file_path{};

    MSGPACK_DEFINE(expected_hash, actual_hash, file_path)
};

using EventDetails = std::variant<
    UsbEventDetails,
    P2pEventDetails,
    ProcessEventDetails,
    TamperEventDetails,
    std::string  // Generic details
>;

// EVENT message: Security/monitoring events
struct Event {
    static constexpr MessageType message_type{MessageType::EVENT};
    static constexpr std::string_view type_name{"EVENT"};

    struct Args {
        EventType    event_type{};
        Severity     severity{Severity::LOW};
        EventDetails details{};

        MSGPACK_DEFINE(event_type, severity, details)
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args&) noexcept {
        return true; // Variant handles validation
    }
};

} // namespace ukk::protocol::messages
