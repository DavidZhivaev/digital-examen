// protocol/tests/test_validation.cpp
// Unit tests for protocol validation

#include <gtest/gtest.h>
#include <ukk/protocol/validation/validator.hpp>
#include <ukk/protocol/header.hpp>
#include <ukk/protocol/version.hpp>
#include <array>
#include <cstring>

namespace ukk::protocol::validation::test {

class ValidatorTest : public ::testing::Test {
protected:
    // Create a valid message header
    static std::array<std::uint8_t, sizeof(MessageHeader)> create_valid_header(
        MessageType type = MessageType::REGISTER,
        std::uint32_t payload_size = 0
    ) {
        std::array<std::uint8_t, sizeof(MessageHeader)> buffer{};
        MessageHeader header{};

        header.magic = PROTOCOL_MAGIC;
        header.version = PROTOCOL_VERSION_MAJOR;
        header.type = type;
        header.flags = 0;
        header.reserved = 0;
        header.payload_size = payload_size;
        header.timestamp = 0;

        std::memcpy(buffer.data(), &header, sizeof(MessageHeader));
        return buffer;
    }

    // Create a buffer with header + payload space
    static std::vector<std::uint8_t> create_message_buffer(
        MessageType type = MessageType::REGISTER,
        std::uint32_t payload_size = 0
    ) {
        std::vector<std::uint8_t> buffer(sizeof(MessageHeader) + payload_size, 0);
        auto header = create_valid_header(type, payload_size);
        std::memcpy(buffer.data(), header.data(), sizeof(MessageHeader));
        return buffer;
    }
};

// Buffer size validation tests
TEST_F(ValidatorTest, EmptyBufferFails) {
    std::array<std::uint8_t, 0> buffer{};
    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::BUFFER_TOO_SMALL);
}

TEST_F(ValidatorTest, SmallBufferFails) {
    std::array<std::uint8_t, 32> buffer{};  // Less than 64 bytes
    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::BUFFER_TOO_SMALL);
}

TEST_F(ValidatorTest, ExactHeaderSizeWithNoPayloadSucceeds) {
    auto buffer = create_valid_header();
    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
    EXPECT_EQ(result.error, ValidationError::OK);
}

// Magic validation tests
TEST_F(ValidatorTest, InvalidMagicFails) {
    auto buffer = create_valid_header();
    // Corrupt the magic value
    buffer[0] = 0xFF;

    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::INVALID_MAGIC);
}

TEST_F(ValidatorTest, ValidMagicSucceeds) {
    auto buffer = create_valid_header();
    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
    // Verify magic was parsed correctly
    EXPECT_EQ(result.header.magic, PROTOCOL_MAGIC);
}

// Version validation tests
TEST_F(ValidatorTest, FutureVersionFails) {
    auto buffer = create_valid_header();
    // Set version higher than supported
    MessageHeader* header = reinterpret_cast<MessageHeader*>(buffer.data());
    header->version = PROTOCOL_VERSION_MAJOR + 1;

    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::UNSUPPORTED_VERSION);
}

TEST_F(ValidatorTest, CurrentVersionSucceeds) {
    auto buffer = create_valid_header();
    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
    EXPECT_EQ(result.header.version, PROTOCOL_VERSION_MAJOR);
}

TEST_F(ValidatorTest, OlderVersionSucceeds) {
    auto buffer = create_valid_header();
    MessageHeader* header = reinterpret_cast<MessageHeader*>(buffer.data());
    header->version = 0;  // Older version

    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
}

// Message type validation tests
TEST_F(ValidatorTest, InvalidMessageTypeFails) {
    auto buffer = create_valid_header();
    MessageHeader* header = reinterpret_cast<MessageHeader*>(buffer.data());
    header->type = static_cast<MessageType>(0xFF);  // Invalid type

    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::INVALID_MESSAGE_TYPE);
}

TEST_F(ValidatorTest, AllAgentMessageTypesAreValid) {
    std::vector<MessageType> agent_types = {
        MessageType::REGISTER,
        MessageType::HEARTBEAT,
        MessageType::SCREENSHOT,
        MessageType::TASK_RESULT,
        MessageType::EVENT,
        MessageType::METRICS,
        MessageType::PONG
    };

    for (auto type : agent_types) {
        EXPECT_TRUE(Validator::is_valid_message_type(type))
            << "Type " << static_cast<int>(type) << " should be valid";
    }
}

TEST_F(ValidatorTest, AllRelayMessageTypesAreValid) {
    std::vector<MessageType> relay_types = {
        MessageType::TASK,
        MessageType::POLICY_UPDATE,
        MessageType::PING,
        MessageType::AGENT_UPDATE,
        MessageType::ACK,
        MessageType::ERROR
    };

    for (auto type : relay_types) {
        EXPECT_TRUE(Validator::is_valid_message_type(type))
            << "Type " << static_cast<int>(type) << " should be valid";
    }
}

// Payload size validation tests
TEST_F(ValidatorTest, PayloadTooLargeFails) {
    auto buffer = create_valid_header();
    MessageHeader* header = reinterpret_cast<MessageHeader*>(buffer.data());
    header->payload_size = MAX_MESSAGE_SIZE + 1;

    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::PAYLOAD_TOO_LARGE);
}

TEST_F(ValidatorTest, MaxPayloadSizeSucceeds) {
    auto buffer = create_message_buffer(MessageType::REGISTER, MAX_MESSAGE_SIZE);
    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
}

TEST_F(ValidatorTest, BufferSmallerThanDeclaredPayloadFails) {
    auto buffer = create_valid_header(MessageType::REGISTER, 100);
    // Buffer only contains header, not the 100-byte payload

    auto result = Validator::validate(std::span{buffer});

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::BUFFER_TOO_SMALL);
}

TEST_F(ValidatorTest, BufferWithFullPayloadSucceeds) {
    auto buffer = create_message_buffer(MessageType::REGISTER, 100);
    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
    EXPECT_EQ(result.header.payload_size, 100);
}

// ValidationResult tests
TEST_F(ValidatorTest, ValidationResultOkMethod) {
    ValidationResult result;
    result.error = ValidationError::OK;

    EXPECT_TRUE(result.ok());
    EXPECT_TRUE(static_cast<bool>(result));
}

TEST_F(ValidatorTest, ValidationResultNotOk) {
    ValidationResult result;
    result.error = ValidationError::INVALID_MAGIC;

    EXPECT_FALSE(result.ok());
    EXPECT_FALSE(static_cast<bool>(result));
}

// ValidationError string tests
TEST_F(ValidatorTest, ValidationErrorStrings) {
    EXPECT_EQ(validation_error_string(ValidationError::OK), "OK");
    EXPECT_EQ(validation_error_string(ValidationError::BUFFER_TOO_SMALL), "Buffer too small");
    EXPECT_EQ(validation_error_string(ValidationError::INVALID_MAGIC), "Invalid magic value");
    EXPECT_EQ(validation_error_string(ValidationError::UNSUPPORTED_VERSION), "Unsupported protocol version");
    EXPECT_EQ(validation_error_string(ValidationError::INVALID_MESSAGE_TYPE), "Invalid message type");
    EXPECT_EQ(validation_error_string(ValidationError::PAYLOAD_TOO_LARGE), "Payload exceeds maximum size");
    EXPECT_EQ(validation_error_string(ValidationError::PAYLOAD_PARSE_ERROR), "Failed to parse payload");
    EXPECT_EQ(validation_error_string(ValidationError::PAYLOAD_VALIDATION_FAILED), "Payload validation failed");
    EXPECT_EQ(validation_error_string(ValidationError::CHECKSUM_MISMATCH), "Checksum mismatch");
}

// Validation strategy tests
TEST_F(ValidatorTest, StrictValidationStrategy) {
    StrictValidationStrategy strategy;

    auto buffer = create_valid_header();
    auto result = strategy.validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
}

TEST_F(ValidatorTest, LenientValidationAllowsFutureVersion) {
    LenientValidationStrategy strategy;

    auto buffer = create_valid_header();
    MessageHeader* header = reinterpret_cast<MessageHeader*>(buffer.data());
    header->version = PROTOCOL_VERSION_MAJOR + 1;

    auto result = strategy.validate(std::span{buffer});

    // Lenient validation allows future versions
    EXPECT_TRUE(result.ok());
}

// Header parsing tests
TEST_F(ValidatorTest, HeaderFieldsAreParsedCorrectly) {
    auto buffer = create_message_buffer(MessageType::HEARTBEAT, 64);
    MessageHeader* original = reinterpret_cast<MessageHeader*>(buffer.data());
    original->timestamp = 1234567890123;

    auto result = Validator::validate(std::span{buffer});

    EXPECT_TRUE(result.ok());
    EXPECT_EQ(result.header.magic, PROTOCOL_MAGIC);
    EXPECT_EQ(result.header.version, PROTOCOL_VERSION_MAJOR);
    EXPECT_EQ(result.header.type, MessageType::HEARTBEAT);
    EXPECT_EQ(result.header.payload_size, 64);
    EXPECT_EQ(result.header.timestamp, 1234567890123);
}

} // namespace ukk::protocol::validation::test
