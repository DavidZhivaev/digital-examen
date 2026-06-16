// protocol/include/ukk/protocol/messages/metrics.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <vector>
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// DNS query summary entry
struct DnsQueryEntry {
    std::string   domain{};
    std::uint32_t query_count{0};
    bool          blocked{false};
};

// Application focus entry
struct AppFocusEntry {
    std::string   app_name{};
    std::string   window_title{};
    std::uint32_t duration_seconds{0};
    Timestamp     start_time{};
};

// Process info entry
struct ProcessInfo {
    std::uint32_t pid{0};
    std::string   name{};
    std::string   cmdline{};
    std::uint8_t  cpu_pct{0};
    std::uint32_t memory_mb{0};
};

// METRICS message: Aggregated telemetry
struct Metrics {
    static constexpr MessageType message_type{MessageType::METRICS};
    static constexpr std::string_view type_name{"METRICS"};

    struct Args {
        Timestamp                   period_start{};
        Timestamp                   period_end{};
        std::vector<DnsQueryEntry>  dns_summary{};
        std::vector<AppFocusEntry>  app_focus_timeline{};
        std::vector<ProcessInfo>    process_list{};
        std::uint32_t               unique_domains{0};
        std::uint32_t               blocked_queries{0};
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return args.period_end.value >= args.period_start.value;
    }
};

} // namespace ukk::protocol::messages
