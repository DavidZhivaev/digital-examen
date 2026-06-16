// protocol/include/ukk/protocol/serialization/traits.hpp
#pragma once

#include <msgpack.hpp>
#include <type_traits>
#include <tuple>
#include <string>
#include <vector>
#include <optional>
#include <variant>
#include <array>

// Boost.PFR-like compile-time struct reflection (simplified)
// In production, use actual Boost.PFR

namespace ukk::protocol::serialization {

// Type trait to detect if type has msgpack adaptor
template<typename T, typename = void>
struct has_msgpack_adaptor : std::false_type {};

template<typename T>
struct has_msgpack_adaptor<T, std::void_t<
    decltype(msgpack::adaptor::pack<T>{}(
        std::declval<msgpack::packer<msgpack::sbuffer>&>(),
        std::declval<const T&>()))
>> : std::true_type {};

template<typename T>
inline constexpr bool has_msgpack_adaptor_v = has_msgpack_adaptor<T>::value;

// Serialization result
template<typename T>
struct SerializeResult {
    std::vector<std::uint8_t> data{};
    bool success{false};
    std::string error{};

    [[nodiscard]] explicit operator bool() const noexcept { return success; }
};

// Deserialization result
template<typename T>
struct DeserializeResult {
    T value{};
    bool success{false};
    std::string error{};

    [[nodiscard]] explicit operator bool() const noexcept { return success; }
};

} // namespace ukk::protocol::serialization
