// protocol/include/ukk/protocol/serialization/msgpack.hpp
#pragma once

#include "traits.hpp"
#include "../header.hpp"
#include "../types.hpp"
#include "../concepts.hpp"
#include <msgpack.hpp>
#include <vector>
#include <cstdint>
#include <span>
#include <expected>
#include <cstring>
#include <type_traits>

namespace ukk::protocol::serialization {

// Custom msgpack adaptors for UKK types
} // namespace ukk::protocol::serialization

// UUID adaptor
namespace msgpack {
MSGPACK_API_VERSION_NAMESPACE(MSGPACK_DEFAULT_API_NS) {
namespace adaptor {

template<>
struct pack<ukk::protocol::UUID> {
    template<typename Stream>
    msgpack::packer<Stream>& operator()(
        msgpack::packer<Stream>& o,
        const ukk::protocol::UUID& v) const {
        o.pack_bin(16);
        o.pack_bin_body(reinterpret_cast<const char*>(v.bytes.data()), 16);
        return o;
    }
};

template<>
struct convert<ukk::protocol::UUID> {
    const msgpack::object& operator()(
        const msgpack::object& o,
        ukk::protocol::UUID& v) const {
        if (o.type != msgpack::type::BIN || o.via.bin.size != 16) {
            throw msgpack::type_error();
        }
        std::memcpy(v.bytes.data(), o.via.bin.ptr, 16);
        return o;
    }
};

template<>
struct pack<ukk::protocol::Timestamp> {
    template<typename Stream>
    msgpack::packer<Stream>& operator()(
        msgpack::packer<Stream>& o,
        const ukk::protocol::Timestamp& v) const {
        o.pack(v.epoch_ms);
        return o;
    }
};

template<>
struct convert<ukk::protocol::Timestamp> {
    const msgpack::object& operator()(
        const msgpack::object& o,
        ukk::protocol::Timestamp& v) const {
        o.convert(v.epoch_ms);
        return o;
    }
};

// Generic enum pack/convert helper macro
#define UKK_MSGPACK_ENUM_ADAPTOR(EnumType) \
template<> \
struct pack<EnumType> { \
    template<typename Stream> \
    msgpack::packer<Stream>& operator()( \
        msgpack::packer<Stream>& o, \
        const EnumType& v) const { \
        o.pack(static_cast<std::underlying_type_t<EnumType>>(v)); \
        return o; \
    } \
}; \
template<> \
struct convert<EnumType> { \
    const msgpack::object& operator()( \
        const msgpack::object& o, \
        EnumType& v) const { \
        std::underlying_type_t<EnumType> tmp; \
        o.convert(tmp); \
        v = static_cast<EnumType>(tmp); \
        return o; \
    } \
}

// Enum adaptors for types.hpp enums
UKK_MSGPACK_ENUM_ADAPTOR(ukk::protocol::AgentStatus);
UKK_MSGPACK_ENUM_ADAPTOR(ukk::protocol::TaskStatus);
UKK_MSGPACK_ENUM_ADAPTOR(ukk::protocol::Severity);
UKK_MSGPACK_ENUM_ADAPTOR(ukk::protocol::Priority);
UKK_MSGPACK_ENUM_ADAPTOR(ukk::protocol::MessageType);

#undef UKK_MSGPACK_ENUM_ADAPTOR

} // namespace adaptor
} // MSGPACK_API_VERSION_NAMESPACE
} // namespace msgpack

namespace ukk::protocol::serialization {

// Serialize message to binary
template<MessagePayload T>
[[nodiscard]] SerializeResult<T> serialize(const typename T::args_type& args) {
    SerializeResult<T> result{};

    if (!T::validate(args)) {
        result.error = "Validation failed";
        return result;
    }

    try {
        msgpack::sbuffer buffer;
        msgpack::pack(buffer, args);
        result.data.assign(buffer.data(), buffer.data() + buffer.size());
        result.success = true;
    } catch (const std::exception& e) {
        result.error = e.what();
    }

    return result;
}

// Deserialize message from binary
template<MessagePayload T>
[[nodiscard]] DeserializeResult<typename T::args_type> deserialize(
    std::span<const std::uint8_t> data) {

    DeserializeResult<typename T::args_type> result{};

    try {
        auto handle = msgpack::unpack(
            reinterpret_cast<const char*>(data.data()),
            data.size());
        handle.get().convert(result.value_);

        if (!T::validate(result.value_)) {
            result.error = "Validation failed after deserialization";
            return result;
        }

        result.success = true;
    } catch (const std::exception& e) {
        result.error = e.what();
    }

    return result;
}

// Serialize full message with header
// Signature: serialize_message<T>(message_id, payload) for tests compatibility
template<MessagePayload T>
[[nodiscard]] std::expected<std::vector<std::uint8_t>, std::string>
serialize_message(const UUID& message_id, const typename T::args_type& args) {

    auto payload_result = serialize<T>(args);
    if (!payload_result) {
        return std::unexpected(payload_result.error);
    }

    // Build header
    MessageHeader header{};
    header.type = T::message_type;
    header.message_id = message_id;
    header.timestamp = Timestamp::now().epoch_ms;
    header.payload_size = static_cast<std::uint32_t>(payload_result.data.size());

    // Combine header + payload
    std::vector<std::uint8_t> result;
    result.reserve(sizeof(MessageHeader) + payload_result.data.size());

    auto header_bytes = reinterpret_cast<const std::uint8_t*>(&header);
    result.insert(result.end(), header_bytes, header_bytes + sizeof(MessageHeader));
    result.insert(result.end(), payload_result.data.begin(), payload_result.data.end());

    return result;
}

// Overload with auto-generated message_id
template<MessagePayload T>
[[nodiscard]] std::expected<std::vector<std::uint8_t>, std::string>
serialize_message(const typename T::args_type& args) {
    return serialize_message<T>(UUID::generate(), args);
}

// Parse header from buffer
[[nodiscard]] inline std::expected<MessageHeader, std::string>
parse_header(std::span<const std::uint8_t> data) {
    if (data.size() < sizeof(MessageHeader)) {
        return std::unexpected("Buffer too small for header");
    }

    MessageHeader header;
    std::memcpy(&header, data.data(), sizeof(MessageHeader));

    if (!header.is_valid()) {
        return std::unexpected("Invalid header");
    }

    return header;
}

} // namespace ukk::protocol::serialization
