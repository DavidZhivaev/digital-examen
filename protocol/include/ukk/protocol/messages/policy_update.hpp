// protocol/include/ukk/protocol/messages/policy_update.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <vector>
#include <cstdint>
#include <optional>

namespace ukk::protocol::messages {

// Policy profile type
enum class PolicyProfile : std::uint8_t {
    FREE        = 0,    // No restrictions
    LESSON      = 1,    // Standard educational
    EXAM        = 2,    // Exam mode (strict)
    LOCKDOWN    = 3,    // Administrative lockdown
};

// Full policy rules structure
struct PolicyRules {
    // Network rules
    std::vector<std::string> dns_whitelist{};
    std::vector<std::string> dns_blacklist{};
    bool                     whitelist_only{false};
    std::optional<std::uint32_t> bandwidth_limit_kbps{};

    // Process rules
    std::vector<std::string> blocked_processes{};
    std::uint8_t             gpu_threshold_pct{40};
    bool                     auto_kill_violations{false};

    // USB rules
    bool                     block_mass_storage{false};
    std::vector<std::uint8_t> blocked_usb_classes{};

    // Screenshot rules
    std::uint32_t            screenshot_interval_ms{20000};
    std::uint8_t             screenshot_quality{80};

    // P2P detection
    bool                     detect_p2p{false};

    // Screen control
    bool                     allow_screen_blackout{true};
};

// POLICY_UPDATE message: New policy rules
struct PolicyUpdate {
    static constexpr MessageType message_type{MessageType::POLICY_UPDATE};
    static constexpr std::string_view type_name{"POLICY_UPDATE"};

    struct Args {
        UUID          policy_id{};
        PolicyProfile profile{PolicyProfile::FREE};
        PolicyRules   rules{};
        Timestamp     effective_from{};
        std::optional<Timestamp> effective_until{};
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (args.effective_until.has_value()) {
            return args.effective_until->value > args.effective_from.value;
        }
        return true;
    }
};

} // namespace ukk::protocol::messages
