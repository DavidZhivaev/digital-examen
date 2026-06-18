// protocol/tests/test_serialization.cpp
// Unit tests for protocol serialization

#include <gtest/gtest.h>
#include <ukk/protocol/serialization/msgpack.hpp>
#include <ukk/protocol/serialization/traits.hpp>
#include <ukk/protocol/messages/register.hpp>
#include <ukk/protocol/messages/heartbeat.hpp>
#include <ukk/protocol/messages/ping_pong.hpp>
#include <ukk/protocol/messages/ack_error.hpp>

namespace ukk::protocol::serialization::test {

// UUID Serialization Tests
class UUIDSerializationTest : public ::testing::Test {
protected:
    UUID create_test_uuid() {
        UUID uuid{};
        for (std::size_t i = 0; i < 16; ++i) {
            uuid.bytes[i] = static_cast<std::uint8_t>(i + 1);
        }
        return uuid;
    }
};

TEST_F(UUIDSerializationTest, RoundTrip) {
    UUID original = create_test_uuid();

    // Serialize
    msgpack::sbuffer buffer;
    msgpack::pack(buffer, original);

    // Deserialize
    auto handle = msgpack::unpack(buffer.data(), buffer.size());
    UUID result;
    handle.get().convert(result);

    EXPECT_EQ(original, result);
}

TEST_F(UUIDSerializationTest, NilUUIDRoundTrip) {
    UUID original{};

    msgpack::sbuffer buffer;
    msgpack::pack(buffer, original);

    auto handle = msgpack::unpack(buffer.data(), buffer.size());
    UUID result;
    handle.get().convert(result);

    EXPECT_EQ(original, result);
    EXPECT_TRUE(result.is_nil());
}

// Timestamp Serialization Tests
class TimestampSerializationTest : public ::testing::Test {};

TEST_F(TimestampSerializationTest, RoundTrip) {
    Timestamp original{1718524800000};  // Some timestamp

    msgpack::sbuffer buffer;
    msgpack::pack(buffer, original);

    auto handle = msgpack::unpack(buffer.data(), buffer.size());
    Timestamp result;
    handle.get().convert(result);

    EXPECT_EQ(original, result);
}

TEST_F(TimestampSerializationTest, ZeroTimestampRoundTrip) {
    Timestamp original{0};

    msgpack::sbuffer buffer;
    msgpack::pack(buffer, original);

    auto handle = msgpack::unpack(buffer.data(), buffer.size());
    Timestamp result;
    handle.get().convert(result);

    EXPECT_EQ(original.epoch_ms, 0);
}

// Message Serialization Tests
class MessageSerializationTest : public ::testing::Test {};

TEST_F(MessageSerializationTest, PingMessageRoundTrip) {
    messages::Ping::Args original;
    original.sequence = 42;
    original.sent_at = Timestamp{1718524800000};

    auto serialized = serialize<messages::Ping>(original);
    ASSERT_TRUE(serialized.has_value());

    auto deserialized = deserialize<messages::Ping>(serialized.value());
    ASSERT_TRUE(deserialized.has_value());

    EXPECT_EQ(deserialized->sequence, 42);
    EXPECT_EQ(deserialized->sent_at.epoch_ms, 1718524800000);
}

TEST_F(MessageSerializationTest, PongMessageRoundTrip) {
    messages::Pong::Args original;
    original.sequence = 42;
    original.ping_sent_at = Timestamp{1718524800000};
    original.pong_sent_at = Timestamp{1718524800100};

    auto serialized = serialize<messages::Pong>(original);
    ASSERT_TRUE(serialized.has_value());

    auto deserialized = deserialize<messages::Pong>(serialized.value());
    ASSERT_TRUE(deserialized.has_value());

    EXPECT_EQ(deserialized->sequence, 42);
    EXPECT_EQ(deserialized->ping_sent_at.epoch_ms, 1718524800000);
    EXPECT_EQ(deserialized->pong_sent_at.epoch_ms, 1718524800100);
}

TEST_F(MessageSerializationTest, AckMessageRoundTrip) {
    UUID test_uuid{};
    test_uuid.bytes[0] = 0xAB;
    test_uuid.bytes[15] = 0xCD;

    messages::Ack::Args original;
    original.acked_message_id = test_uuid;

    auto serialized = serialize<messages::Ack>(original);
    ASSERT_TRUE(serialized.has_value());

    auto deserialized = deserialize<messages::Ack>(serialized.value());
    ASSERT_TRUE(deserialized.has_value());

    EXPECT_EQ(deserialized->acked_message_id, test_uuid);
}

TEST_F(MessageSerializationTest, ErrorMessageRoundTrip) {
    UUID test_uuid{};
    test_uuid.bytes[0] = 0x12;

    messages::Error::Args original;
    original.reference_id = test_uuid;
    original.code = messages::ErrorCode::INVALID_PAYLOAD;
    original.message = "Test error message";
    original.details = "{\"key\": \"value\"}";

    auto serialized = serialize<messages::Error>(original);
    ASSERT_TRUE(serialized.has_value());

    auto deserialized = deserialize<messages::Error>(serialized.value());
    ASSERT_TRUE(deserialized.has_value());

    EXPECT_EQ(deserialized->reference_id, test_uuid);
    EXPECT_EQ(deserialized->code, messages::ErrorCode::INVALID_PAYLOAD);
    EXPECT_EQ(deserialized->message, "Test error message");
    EXPECT_EQ(deserialized->details, "{\"key\": \"value\"}");
}

// Header Parsing Tests
class HeaderParsingTest : public ::testing::Test {
protected:
    std::vector<std::uint8_t> create_message_with_header(MessageType type) {
        std::vector<std::uint8_t> buffer(sizeof(MessageHeader), 0);
        MessageHeader header{};
        header.magic = PROTOCOL_MAGIC;
        header.version = PROTOCOL_VERSION_MAJOR;
        header.type = type;
        header.payload_size = 0;
        header.timestamp = 1718524800000;

        std::memcpy(buffer.data(), &header, sizeof(MessageHeader));
        return buffer;
    }
};

TEST_F(HeaderParsingTest, ParseValidHeader) {
    auto buffer = create_message_with_header(MessageType::REGISTER);

    auto result = parse_header(std::span{buffer});
    ASSERT_TRUE(result.has_value());

    EXPECT_EQ(result->magic, PROTOCOL_MAGIC);
    EXPECT_EQ(result->version, PROTOCOL_VERSION_MAJOR);
    EXPECT_EQ(result->type, MessageType::REGISTER);
    EXPECT_EQ(result->timestamp, 1718524800000);
}

TEST_F(HeaderParsingTest, ParseHeaderTooSmall) {
    std::vector<std::uint8_t> buffer(32, 0);  // Too small

    auto result = parse_header(std::span{buffer});
    EXPECT_FALSE(result.has_value());
}

// Full Message Serialization Tests
class FullMessageSerializationTest : public ::testing::Test {};

TEST_F(FullMessageSerializationTest, SerializeMessageWithHeader) {
    UUID message_id{};
    message_id.bytes[0] = 0x42;

    messages::Ping::Args payload;
    payload.sequence = 100;
    payload.sent_at = Timestamp::now();

    auto result = serialize_message<messages::Ping>(message_id, payload);
    ASSERT_TRUE(result.has_value());

    // Verify header
    ASSERT_GE(result->size(), sizeof(MessageHeader));

    MessageHeader header;
    std::memcpy(&header, result->data(), sizeof(MessageHeader));

    EXPECT_EQ(header.magic, PROTOCOL_MAGIC);
    EXPECT_EQ(header.version, PROTOCOL_VERSION_MAJOR);
    EXPECT_EQ(header.type, MessageType::PING);
    EXPECT_EQ(header.message_id, message_id);
    EXPECT_GT(header.payload_size, 0);

    // Verify payload can be deserialized
    std::span<const std::uint8_t> payload_span{
        result->data() + sizeof(MessageHeader),
        header.payload_size
    };

    auto deserialized = deserialize<messages::Ping>(payload_span);
    ASSERT_TRUE(deserialized.has_value());
    EXPECT_EQ(deserialized->sequence, 100);
}

// Traits Tests
class TraitsTest : public ::testing::Test {};

TEST_F(TraitsTest, SerializeResultType) {
    using ResultType = SerializeResult<messages::Ping>;

    // Test successful result
    ResultType success{};
    success.data = {1, 2, 3};
    success.success = true;
    EXPECT_TRUE(success.has_value());
    EXPECT_EQ(success.value().size(), 3);

    // Test error result
    ResultType error{};
    error.success = false;
    error.error = "test error";
    EXPECT_FALSE(error.has_value());
}

TEST_F(TraitsTest, DeserializeResultType) {
    using TestArgs = messages::Ping::Args;
    using ResultType = DeserializeResult<TestArgs>;

    // Test successful result
    ResultType success{};
    success.value_ = TestArgs{};
    success.value_.sequence = 42;
    success.success = true;
    EXPECT_TRUE(success.has_value());
    EXPECT_EQ(success.value().sequence, 42);

    // Test error result
    ResultType error{};
    error.success = false;
    error.error = "parse error";
    EXPECT_FALSE(error.has_value());
}

// Edge Cases
class EdgeCasesTest : public ::testing::Test {};

TEST_F(EdgeCasesTest, EmptyBuffer) {
    std::vector<std::uint8_t> empty;
    auto result = parse_header(std::span{empty});
    EXPECT_FALSE(result.has_value());
}

TEST_F(EdgeCasesTest, DeserializeEmptyPayload) {
    std::vector<std::uint8_t> empty;
    auto result = deserialize<messages::Ping>(std::span{empty});
    EXPECT_FALSE(result.has_value());
}

TEST_F(EdgeCasesTest, DeserializeCorruptedData) {
    std::vector<std::uint8_t> garbage{0xFF, 0xFE, 0xFD, 0xFC};
    auto result = deserialize<messages::Ping>(std::span{garbage});
    EXPECT_FALSE(result.has_value());
}

} // namespace ukk::protocol::serialization::test
