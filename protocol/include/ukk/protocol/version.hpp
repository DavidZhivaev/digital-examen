// protocol/include/ukk/protocol/version.hpp
#pragma once

#include <cstdint>
#include <string_view>

namespace ukk::protocol {

inline constexpr std::uint32_t PROTOCOL_VERSION_MAJOR{1};
inline constexpr std::uint32_t PROTOCOL_VERSION_MINOR{0};
inline constexpr std::uint32_t PROTOCOL_VERSION_PATCH{0};

inline constexpr std::string_view PROTOCOL_VERSION{"1.0.0"};

// Magic value for protocol identification
inline constexpr std::uint32_t PROTOCOL_MAGIC{0x554B4B50}; // "UKKP"

// Maximum message size (30MB as per Havoc)
inline constexpr std::size_t MAX_MESSAGE_SIZE{0x1E00000};

} // namespace ukk::protocol
