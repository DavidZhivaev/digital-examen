// protocol/include/ukk/protocol/messages/policy_update.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <msgpack.hpp>
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

MSGPACK_ADD_ENUM(PolicyProfile);

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

    MSGPACK_DEFINE(dns_whitelist, dns_blacklist, whitelist_only, bandwidth_limit_kbps,
                   blocked_processes, gpu_threshold_pct, auto_kill_violations,
                   block_mass_storage, blocked_usb_classes,
                   screenshot_interval_ms, screenshot_quality,
                   detect_p2p, allow_screen_blackout)
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

        MSGPACK_DEFINE(policy_id, profile, rules, effective_from, effective_until)
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (args.effective_until.has_value()) {
            return args.effective_until->epoch_ms > args.effective_from.epoch_ms;
        }
        return true;
    }
};

} // namespace ukk::protocol::messages
