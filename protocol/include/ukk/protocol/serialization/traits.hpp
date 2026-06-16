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

// Serialization result (std::expected-like interface)
template<typename T>
struct SerializeResult {
    std::vector<std::uint8_t> data{};
    bool success{false};
    std::string error{};

    [[nodiscard]] explicit operator bool() const noexcept { return success; }
    [[nodiscard]] bool has_value() const noexcept { return success; }
    [[nodiscard]] std::vector<std::uint8_t>& value() & { return data; }
    [[nodiscard]] const std::vector<std::uint8_t>& value() const& { return data; }
    [[nodiscard]] std::vector<std::uint8_t>&& value() && { return std::move(data); }
};

// Deserialization result (std::expected-like interface)
template<typename T>
struct DeserializeResult {
    T value_{};
    bool success{false};
    std::string error{};

    [[nodiscard]] explicit operator bool() const noexcept { return success; }
    [[nodiscard]] bool has_value() const noexcept { return success; }
    [[nodiscard]] T& value() & { return value_; }
    [[nodiscard]] const T& value() const& { return value_; }
    [[nodiscard]] T&& value() && { return std::move(value_); }
    [[nodiscard]] T* operator->() noexcept { return &value_; }
    [[nodiscard]] const T* operator->() const noexcept { return &value_; }
    [[nodiscard]] T& operator*() & noexcept { return value_; }
    [[nodiscard]] const T& operator*() const& noexcept { return value_; }
};

} // namespace ukk::protocol::serialization
