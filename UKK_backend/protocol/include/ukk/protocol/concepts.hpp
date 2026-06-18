// protocol/include/ukk/protocol/concepts.hpp
#pragma once

#include "types.hpp"
#include <concepts>
#include <type_traits>
#include <cstdint>
#include <vector>

namespace ukk::protocol {

// Concept for serializable types
template<typename T>
concept Serializable = requires {
    { T::message_type } -> std::convertible_to<MessageType>;
    requires std::is_standard_layout_v<T>;
    requires std::is_trivially_copyable_v<T> || requires(const T& t) {
        { t.serialize() } -> std::same_as<std::vector<std::uint8_t>>;
    };
};

// Concept for message payload
template<typename T>
concept MessagePayload = requires(T t) {
    typename T::args_type;
    { T::message_type } -> std::convertible_to<MessageType>;
    { T::type_name } -> std::convertible_to<std::string_view>;
};

// Concept for validatable messages
template<typename T>
concept Validatable = requires(const T& t) {
    { t.validate() } -> std::same_as<bool>;
};

// Concept for agent-to-relay messages
template<typename T>
concept AgentMessage = MessagePayload<T> && requires {
    requires static_cast<std::uint8_t>(T::message_type) < 0x80;
};

// Concept for relay-to-agent messages
template<typename T>
concept RelayMessage = MessagePayload<T> && requires {
    requires static_cast<std::uint8_t>(T::message_type) >= 0x80;
};

} // namespace ukk::protocol
