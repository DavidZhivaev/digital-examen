// protocol/include/ukk/protocol/messages/ping_pong.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <cstdint>

namespace ukk::protocol::messages {

// PING message: Connection health check (Relay -> Agent)
struct Ping {
    static constexpr MessageType message_type{MessageType::PING};
    static constexpr std::string_view type_name{"PING"};

    struct Args {
        std::uint64_t sequence{0};      // Sequence number for RTT calc
        Timestamp     sent_at{};
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args&) noexcept {
        return true;
    }
};

// PONG message: Response to PING (Agent -> Relay)
struct Pong {
    static constexpr MessageType message_type{MessageType::PONG};
    static constexpr std::string_view type_name{"PONG"};

    struct Args {
        std::uint64_t sequence{0};      // Echo sequence number
        Timestamp     ping_sent_at{};   // Original ping timestamp
        Timestamp     pong_sent_at{};   // This response timestamp
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args& args) noexcept {
        return args.pong_sent_at.value >= args.ping_sent_at.value;
    }
};

} // namespace ukk::protocol::messages
