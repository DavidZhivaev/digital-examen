// protocol/tests/test_types.cpp
// Unit tests for protocol types

#include <gtest/gtest.h>
#include <ukk/protocol/types.hpp>
#include <ukk/protocol/version.hpp>

namespace ukk::protocol::test {

// UUID Tests
class UUIDTest : public ::testing::Test {};

TEST_F(UUIDTest, DefaultConstructorCreatesNilUUID) {
    UUID uuid{};
    for (auto byte : uuid.bytes) {
        EXPECT_EQ(byte, 0);
    }
}

TEST_F(UUIDTest, NilUUIDIsNil) {
    UUID uuid{};
    EXPECT_TRUE(uuid.is_nil());
}

TEST_F(UUIDTest, NonNilUUIDIsNotNil) {
    UUID uuid{};
    uuid.bytes[0] = 1;
    EXPECT_FALSE(uuid.is_nil());
}

TEST_F(UUIDTest, SizeIs16Bytes) {
    static_assert(sizeof(UUID) == 16);
    EXPECT_EQ(sizeof(UUID), 16);
}

TEST_F(UUIDTest, AlignmentIs16Bytes) {
    static_assert(alignof(UUID) == 16);
    EXPECT_EQ(alignof(UUID), 16);
}

TEST_F(UUIDTest, EqualityOperator) {
    UUID a{}, b{};
    EXPECT_EQ(a, b);

    a.bytes[0] = 1;
    EXPECT_NE(a, b);

    b.bytes[0] = 1;
    EXPECT_EQ(a, b);
}

// Timestamp Tests
class TimestampTest : public ::testing::Test {};

TEST_F(TimestampTest, DefaultConstructorCreatesZeroTimestamp) {
    Timestamp ts{};
    EXPECT_EQ(ts.epoch_ms, 0);
}

TEST_F(TimestampTest, ConstructorWithValue) {
    Timestamp ts{1234567890123};
    EXPECT_EQ(ts.epoch_ms, 1234567890123);
}

TEST_F(TimestampTest, NowReturnsNonZero) {
    auto ts = Timestamp::now();
    EXPECT_GT(ts.epoch_ms, 0);
}

TEST_F(TimestampTest, ComparisonOperators) {
    Timestamp a{100}, b{200};
    EXPECT_LT(a, b);
    EXPECT_LE(a, b);
    EXPECT_GT(b, a);
    EXPECT_GE(b, a);
    EXPECT_NE(a, b);

    Timestamp c{100};
    EXPECT_EQ(a, c);
    EXPECT_LE(a, c);
    EXPECT_GE(a, c);
}

// MessageType Tests
class MessageTypeTest : public ::testing::Test {};

TEST_F(MessageTypeTest, AgentMessagesInRange) {
    // Agent messages: 0x01 - 0x7F
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::REGISTER), 0x01);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::HEARTBEAT), 0x02);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::SCREENSHOT), 0x03);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::TASK_RESULT), 0x04);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::EVENT), 0x05);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::METRICS), 0x06);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::PONG), 0x07);
}

TEST_F(MessageTypeTest, RelayMessagesInRange) {
    // Relay messages: 0x80 - 0xFF
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::TASK), 0x81);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::POLICY_UPDATE), 0x82);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::PING), 0x83);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::AGENT_UPDATE), 0x84);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::ACK), 0x85);
    EXPECT_EQ(static_cast<std::uint8_t>(MessageType::ERROR), 0x86);
}

TEST_F(MessageTypeTest, MessageTypeNameReturnsCorrectStrings) {
    EXPECT_EQ(message_type_name(MessageType::REGISTER), "REGISTER");
    EXPECT_EQ(message_type_name(MessageType::HEARTBEAT), "HEARTBEAT");
    EXPECT_EQ(message_type_name(MessageType::SCREENSHOT), "SCREENSHOT");
    EXPECT_EQ(message_type_name(MessageType::TASK_RESULT), "TASK_RESULT");
    EXPECT_EQ(message_type_name(MessageType::EVENT), "EVENT");
    EXPECT_EQ(message_type_name(MessageType::METRICS), "METRICS");
    EXPECT_EQ(message_type_name(MessageType::PONG), "PONG");
    EXPECT_EQ(message_type_name(MessageType::TASK), "TASK");
    EXPECT_EQ(message_type_name(MessageType::POLICY_UPDATE), "POLICY_UPDATE");
    EXPECT_EQ(message_type_name(MessageType::PING), "PING");
    EXPECT_EQ(message_type_name(MessageType::AGENT_UPDATE), "AGENT_UPDATE");
    EXPECT_EQ(message_type_name(MessageType::ACK), "ACK");
    EXPECT_EQ(message_type_name(MessageType::ERROR), "ERROR");
}

// Severity Tests
class SeverityTest : public ::testing::Test {};

TEST_F(SeverityTest, SeverityValues) {
    EXPECT_EQ(static_cast<int>(Severity::LOW), 0);
    EXPECT_EQ(static_cast<int>(Severity::MEDIUM), 1);
    EXPECT_EQ(static_cast<int>(Severity::HIGH), 2);
    EXPECT_EQ(static_cast<int>(Severity::CRITICAL), 3);
}

// Priority Tests
class PriorityTest : public ::testing::Test {};

TEST_F(PriorityTest, PriorityValues) {
    EXPECT_EQ(static_cast<int>(Priority::NORMAL), 0);
    EXPECT_EQ(static_cast<int>(Priority::HIGH), 1);
}

// AgentStatus Tests
class AgentStatusTest : public ::testing::Test {};

TEST_F(AgentStatusTest, StatusValues) {
    EXPECT_EQ(static_cast<int>(AgentStatus::ONLINE), 0);
    EXPECT_EQ(static_cast<int>(AgentStatus::OFFLINE), 1);
    EXPECT_EQ(static_cast<int>(AgentStatus::ERROR), 2);
}

// TaskStatus Tests
class TaskStatusTest : public ::testing::Test {};

TEST_F(TaskStatusTest, StatusValues) {
    EXPECT_EQ(static_cast<int>(TaskStatus::OK), 0);
    EXPECT_EQ(static_cast<int>(TaskStatus::ERROR), 1);
    EXPECT_EQ(static_cast<int>(TaskStatus::TIMEOUT), 2);
}

// Version Constants Tests
class VersionTest : public ::testing::Test {};

TEST_F(VersionTest, ProtocolMagic) {
    EXPECT_EQ(PROTOCOL_MAGIC, 0x554B4B50); // "UKKP"
}

TEST_F(VersionTest, ProtocolVersion) {
    EXPECT_EQ(PROTOCOL_VERSION_MAJOR, 1);
    EXPECT_EQ(PROTOCOL_VERSION_MINOR, 0);
    EXPECT_EQ(PROTOCOL_VERSION_PATCH, 0);
}

TEST_F(VersionTest, MaxMessageSize) {
    EXPECT_EQ(MAX_MESSAGE_SIZE, 0x1E00000); // 30MB
}

} // namespace ukk::protocol::test
