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
        auto epoch = std::chrono::duration_cast<std::chrono::milliseconds>(
            v.value.time_since_epoch()).count();
        o.pack(epoch);
        return o;
    }
};

template<>
struct convert<ukk::protocol::Timestamp> {
    const msgpack::object& operator()(
        const msgpack::object& o,
        ukk::protocol::Timestamp& v) const {
        std::int64_t epoch{};
        o.convert(epoch);
        v.value = std::chrono::system_clock::time_point{
            std::chrono::milliseconds{epoch}};
        return o;
    }
};

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
        handle.get().convert(result.value);

        if (!T::validate(result.value)) {
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
template<MessagePayload T>
[[nodiscard]] std::expected<std::vector<std::uint8_t>, std::string>
serialize_message(const typename T::args_type& args, UUID message_id = UUID::generate()) {

    auto payload_result = serialize<T>(args);
    if (!payload_result) {
        return std::unexpected(payload_result.error);
    }

    // Build header
    MessageHeader header{};
    header.type = T::message_type;
    header.message_id = message_id;
    header.timestamp = Timestamp::now();
    header.payload_size = static_cast<std::uint32_t>(payload_result.data.size());

    // Combine header + payload
    std::vector<std::uint8_t> result;
    result.reserve(sizeof(MessageHeader) + payload_result.data.size());

    auto header_bytes = reinterpret_cast<const std::uint8_t*>(&header);
    result.insert(result.end(), header_bytes, header_bytes + sizeof(MessageHeader));
    result.insert(result.end(), payload_result.data.begin(), payload_result.data.end());

    return result;
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
