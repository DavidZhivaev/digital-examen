// protocol/include/ukk/protocol/messages/heartbeat.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <msgpack.hpp>
#include <cstdint>
#include <string>

namespace ukk::protocol::messages {

// HEARTBEAT message: Periodic activity confirmation
struct Heartbeat {
    static constexpr MessageType message_type{MessageType::HEARTBEAT};
    static constexpr std::string_view type_name{"HEARTBEAT"};

    struct Args {
        std::uint8_t  cpu_pct{0};           // CPU usage percentage (0-100)
        std::uint8_t  ram_pct{0};           // RAM usage percentage (0-100)
        std::uint8_t  gpu_pct{0};           // GPU usage percentage (0-100)
        float         disk_free_gb{0.0f};   // Free disk space in GB
        std::string   active_policy{};      // Currently active policy ID
        AgentStatus   status{AgentStatus::ONLINE};

        MSGPACK_DEFINE(cpu_pct, ram_pct, gpu_pct, disk_free_gb, active_policy, status)
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args& args) noexcept {
        return args.cpu_pct <= 100 &&
               args.ram_pct <= 100 &&
               args.gpu_pct <= 100 &&
               args.disk_free_gb >= 0.0f;
    }
};

} // namespace ukk::protocol::messages
