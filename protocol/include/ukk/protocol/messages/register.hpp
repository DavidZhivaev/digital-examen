// protocol/include/ukk/protocol/messages/register.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// REGISTER message: Agent registration on relay
struct Register {
    static constexpr MessageType message_type{MessageType::REGISTER};
    static constexpr std::string_view type_name{"REGISTER"};

    struct Args {
        UUID        machine_id{};           // Unique machine identifier
        std::string building_id{};          // Building identifier
        std::string room_id{};              // Room identifier
        std::string seat_id{};              // Seat identifier
        std::string agent_version{};        // Agent software version
        std::string hw_fingerprint{};       // SHA-256(CPU + MB + MAC)
        std::string os_version{};           // Operating system version
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return !args.building_id.empty() &&
               !args.room_id.empty() &&
               !args.agent_version.empty() &&
               args.hw_fingerprint.size() == 64; // SHA-256 hex
    }
};

// Response to REGISTER (sent by relay)
struct RegisterResponse {
    std::string session_token{};            // Session authentication token
    std::string relay_ws_url{};             // WebSocket URL for reconnection
    // initial_policy embedded as separate POLICY_UPDATE
};

} // namespace ukk::protocol::messages
