// protocol/include/ukk/protocol/messages/task.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <msgpack.hpp>
#include <string>
#include <variant>
#include <vector>
#include <cstdint>
#include <optional>

namespace ukk::protocol::messages {

// Task type enumeration (from documentation)
enum class TaskType : std::uint16_t {
    SCREENSHOT      = 0x0001,
    NET_POLICY      = 0x0002,
    PROCESS_POLICY  = 0x0003,
    CURSOR_CONTROL  = 0x0004,
    SCREEN_CONTROL  = 0x0005,
    TRAFFIC_LIMIT   = 0x0006,
    USB_POLICY      = 0x0007,
    AGENT_UPDATE    = 0x0008,
    GET_METRICS     = 0x0009,
    SHELL_EXEC      = 0x000A,
};

MSGPACK_ADD_ENUM(TaskType);

// Screenshot task payload
struct ScreenshotPayload {
    std::uint8_t quality{80};           // JPEG quality 1-100
    bool         force_capture{false};  // Ignore pHash comparison

    MSGPACK_DEFINE(quality, force_capture)
};

// Network policy payload
struct NetPolicyPayload {
    std::vector<std::string> whitelist{};
    std::vector<std::string> blacklist{};
    bool                     whitelist_only{false};
    std::optional<std::uint32_t> bandwidth_limit_kbps{};

    MSGPACK_DEFINE(whitelist, blacklist, whitelist_only, bandwidth_limit_kbps)
};

// Process policy payload
struct ProcessPolicyPayload {
    std::vector<std::string> blocked_processes{};
    std::uint8_t             gpu_threshold_pct{40};
    std::uint32_t            gpu_check_duration_sec{30};
    bool                     auto_kill{false};

    MSGPACK_DEFINE(blocked_processes, gpu_threshold_pct, gpu_check_duration_sec, auto_kill)
};

// Screen control payload
struct ScreenControlPayload {
    enum class Action : std::uint8_t {
        BLACKOUT = 0,
        RESTORE  = 1,
        DPMS_OFF = 2,
        DPMS_ON  = 3,
    };
    Action action{Action::BLACKOUT};

    MSGPACK_DEFINE(action)
};

MSGPACK_ADD_ENUM(ScreenControlPayload::Action);

// USB policy payload
struct UsbPolicyPayload {
    std::vector<std::uint8_t> blocked_classes{}; // USB device classes
    bool                      block_mass_storage{true};

    MSGPACK_DEFINE(blocked_classes, block_mass_storage)
};

// Traffic limit payload
struct TrafficLimitPayload {
    std::string              target_domain{};
    std::uint32_t            limit_kbps{0};
    bool                     remove{false};

    MSGPACK_DEFINE(target_domain, limit_kbps, remove)
};

// Shell execution payload
struct ShellExecPayload {
    std::string command{};
    std::uint32_t timeout_ms{30000};

    MSGPACK_DEFINE(command, timeout_ms)
};

using TaskPayload = std::variant<
    ScreenshotPayload,
    NetPolicyPayload,
    ProcessPolicyPayload,
    ScreenControlPayload,
    UsbPolicyPayload,
    TrafficLimitPayload,
    ShellExecPayload
>;

// TASK message: Command for execution
struct Task {
    static constexpr MessageType message_type{MessageType::TASK};
    static constexpr std::string_view type_name{"TASK"};

    struct Args {
        UUID         task_id{};
        TaskType     task_type{};
        TaskPayload  payload{};
        Priority     priority{Priority::NORMAL};
        Timestamp    deadline{};          // Task must complete by this time

        MSGPACK_DEFINE(task_id, task_type, payload, priority, deadline)
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        // Validate payload matches task_type
        return std::visit([&](auto&& p) -> bool {
            using T = std::decay_t<decltype(p)>;
            if constexpr (std::is_same_v<T, ScreenshotPayload>) {
                return args.task_type == TaskType::SCREENSHOT;
            } else if constexpr (std::is_same_v<T, NetPolicyPayload>) {
                return args.task_type == TaskType::NET_POLICY;
            } else if constexpr (std::is_same_v<T, ProcessPolicyPayload>) {
                return args.task_type == TaskType::PROCESS_POLICY;
            } else if constexpr (std::is_same_v<T, ScreenControlPayload>) {
                return args.task_type == TaskType::SCREEN_CONTROL;
            } else if constexpr (std::is_same_v<T, UsbPolicyPayload>) {
                return args.task_type == TaskType::USB_POLICY;
            } else if constexpr (std::is_same_v<T, TrafficLimitPayload>) {
                return args.task_type == TaskType::TRAFFIC_LIMIT;
            } else if constexpr (std::is_same_v<T, ShellExecPayload>) {
                return args.task_type == TaskType::SHELL_EXEC;
            }
            return false;
        }, args.payload);
    }
};

} // namespace ukk::protocol::messages
