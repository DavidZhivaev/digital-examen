// protocol/include/ukk/protocol/messages/screenshot.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <msgpack.hpp>
#include <vector>
#include <cstdint>
#include <optional>

namespace ukk::protocol::messages {

// SCREENSHOT message: Screen capture data
struct Screenshot {
    static constexpr MessageType message_type{MessageType::SCREENSHOT};
    static constexpr std::string_view type_name{"SCREENSHOT"};

    struct Args {
        bool                           changed{true};      // True if screen changed
        std::optional<std::vector<std::uint8_t>> image_data{}; // zstd-compressed image
        std::uint32_t                  width{0};           // Image width
        std::uint32_t                  height{0};          // Image height
        std::uint64_t                  phash{0};           // Perceptual hash

        MSGPACK_DEFINE(changed, image_data, width, height, phash)
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (!args.changed) {
            return !args.image_data.has_value(); // NO_CHANGE has no data
        }
        return args.image_data.has_value() &&
               !args.image_data->empty() &&
               args.width > 0 && args.height > 0;
    }
};

} // namespace ukk::protocol::messages
