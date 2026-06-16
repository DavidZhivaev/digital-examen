// protocol/include/ukk/protocol/messages/agent_update.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// AGENT_UPDATE message: Binary update command
struct AgentUpdate {
    static constexpr MessageType message_type{MessageType::AGENT_UPDATE};
    static constexpr std::string_view type_name{"AGENT_UPDATE"};

    struct Args {
        std::string  new_version{};         // Target version string
        std::string  download_url{};        // URL to download from relay
        std::string  sha256_hash{};         // Expected SHA-256 hash (hex)
        std::uint64_t file_size{0};         // Expected file size in bytes
        bool         force{false};          // Force update even if same version
        bool         restart_required{true}; // Restart agent after update
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return !args.new_version.empty() &&
               !args.download_url.empty() &&
               args.sha256_hash.size() == 64 && // SHA-256 hex
               args.file_size > 0;
    }
};

} // namespace ukk::protocol::messages
