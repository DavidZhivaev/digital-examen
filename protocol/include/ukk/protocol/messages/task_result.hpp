// protocol/include/ukk/protocol/messages/task_result.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <optional>
#include <cstdint>

namespace ukk::protocol::messages {

// TASK_RESULT message: Task execution response
struct TaskResult {
    static constexpr MessageType message_type{MessageType::TASK_RESULT};
    static constexpr std::string_view type_name{"TASK_RESULT"};

    struct Args {
        UUID                      task_id{};        // Original task ID
        TaskStatus                status{TaskStatus::OK};
        std::string               output{};         // Command output
        std::optional<std::int32_t> error_code{};   // Error code if failed
        std::uint64_t             execution_time_ms{0}; // Execution duration
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (args.status == TaskStatus::ERROR) {
            return args.error_code.has_value();
        }
        return true;
    }
};

} // namespace ukk::protocol::messages
