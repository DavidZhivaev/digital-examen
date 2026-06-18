// protocol/include/ukk/protocol/validation/validator.hpp
#pragma once

#include "../header.hpp"
#include "../types.hpp"
#include "../concepts.hpp"
#include <span>
#include <expected>
#include <string>
#include <functional>
#include <cstring>
#include <cstdio>
#include <array>
#include <variant>

namespace ukk::protocol::validation {

// Validation error types
enum class ValidationError {
    OK,
    BUFFER_TOO_SMALL,
    INVALID_MAGIC,
    UNSUPPORTED_VERSION,
    INVALID_MESSAGE_TYPE,
    PAYLOAD_TOO_LARGE,
    PAYLOAD_PARSE_ERROR,
    PAYLOAD_VALIDATION_FAILED,
    CHECKSUM_MISMATCH,
};

[[nodiscard]] constexpr std::string_view validation_error_string(ValidationError e) {
    switch (e) {
        case ValidationError::OK: return "OK";
        case ValidationError::BUFFER_TOO_SMALL: return "Buffer too small";
        case ValidationError::INVALID_MAGIC: return "Invalid magic value";
        case ValidationError::UNSUPPORTED_VERSION: return "Unsupported protocol version";
        case ValidationError::INVALID_MESSAGE_TYPE: return "Invalid message type";
        case ValidationError::PAYLOAD_TOO_LARGE: return "Payload exceeds maximum size";
        case ValidationError::PAYLOAD_PARSE_ERROR: return "Failed to parse payload";
        case ValidationError::PAYLOAD_VALIDATION_FAILED: return "Payload validation failed";
        case ValidationError::CHECKSUM_MISMATCH: return "Checksum mismatch";
    }
    return "Unknown error";
}

// Validation result
struct ValidationResult {
    ValidationError error{ValidationError::OK};
    std::string details{};
    MessageHeader header{};

    [[nodiscard]] constexpr bool ok() const noexcept {
        return error == ValidationError::OK;
    }

    [[nodiscard]] explicit constexpr operator bool() const noexcept {
        return ok();
    }
};

// Protocol validator
class Validator {
public:
    // Validate raw message buffer
    [[nodiscard]] static ValidationResult validate(std::span<const std::uint8_t> buffer) {
        ValidationResult result{};

        // Check minimum size
        if (buffer.size() < sizeof(MessageHeader)) {
            result.error = ValidationError::BUFFER_TOO_SMALL;
            result.details = "Buffer size: " + std::to_string(buffer.size()) +
                           ", required: " + std::to_string(sizeof(MessageHeader));
            return result;
        }

        // Parse header
        std::memcpy(&result.header, buffer.data(), sizeof(MessageHeader));

        // Validate magic
        if (result.header.magic != PROTOCOL_MAGIC) {
            result.error = ValidationError::INVALID_MAGIC;
            result.details = "Got: 0x" + to_hex(result.header.magic) +
                           ", expected: 0x" + to_hex(PROTOCOL_MAGIC);
            return result;
        }

        // Validate version
        if (result.header.version > PROTOCOL_VERSION_MAJOR) {
            result.error = ValidationError::UNSUPPORTED_VERSION;
            result.details = "Got: " + std::to_string(result.header.version) +
                           ", max supported: " + std::to_string(PROTOCOL_VERSION_MAJOR);
            return result;
        }

        // Validate message type
        if (!is_valid_message_type(result.header.type)) {
            result.error = ValidationError::INVALID_MESSAGE_TYPE;
            result.details = "Unknown type: 0x" +
                           to_hex(static_cast<std::uint8_t>(result.header.type));
            return result;
        }

        // Validate payload size
        if (result.header.payload_size > MAX_MESSAGE_SIZE) {
            result.error = ValidationError::PAYLOAD_TOO_LARGE;
            result.details = "Payload: " + std::to_string(result.header.payload_size) +
                           ", max: " + std::to_string(MAX_MESSAGE_SIZE);
            return result;
        }

        // Check buffer contains full payload
        std::size_t total_size = sizeof(MessageHeader) + result.header.payload_size;
        if (buffer.size() < total_size) {
            result.error = ValidationError::BUFFER_TOO_SMALL;
            result.details = "Buffer: " + std::to_string(buffer.size()) +
                           ", required: " + std::to_string(total_size);
            return result;
        }

        return result;
    }

    // Validate message type is known
    [[nodiscard]] static constexpr bool is_valid_message_type(MessageType type) noexcept {
        switch (type) {
            case MessageType::REGISTER:
            case MessageType::HEARTBEAT:
            case MessageType::SCREENSHOT:
            case MessageType::TASK_RESULT:
            case MessageType::EVENT:
            case MessageType::METRICS:
            case MessageType::PONG:
            case MessageType::TASK:
            case MessageType::POLICY_UPDATE:
            case MessageType::PING:
            case MessageType::AGENT_UPDATE:
            case MessageType::ACK:
            case MessageType::ERROR:
                return true;
            default:
                return false;
        }
    }

private:
    [[nodiscard]] static std::string to_hex(std::uint32_t value) {
        std::array<char, 16> buf{};
        std::snprintf(buf.data(), buf.size(), "%08X", value);
        return std::string{buf.data()};
    }

    [[nodiscard]] static std::string to_hex(std::uint8_t value) {
        std::array<char, 8> buf{};
        std::snprintf(buf.data(), buf.size(), "%02X", value);
        return std::string{buf.data()};
    }
};

// CRTP base for validation strategies (no virtual functions per .claudecode.md)
template<typename Derived>
class ValidationStrategyBase {
public:
    [[nodiscard]] ValidationResult validate(std::span<const std::uint8_t> buffer) {
        return static_cast<Derived*>(this)->do_validate(buffer);
    }
};

// Strict validation (production)
class StrictValidationStrategy : public ValidationStrategyBase<StrictValidationStrategy> {
public:
    [[nodiscard]] ValidationResult do_validate(std::span<const std::uint8_t> buffer) {
        return Validator::validate(buffer);
    }
};

// Lenient validation (debugging)
class LenientValidationStrategy : public ValidationStrategyBase<LenientValidationStrategy> {
public:
    [[nodiscard]] ValidationResult do_validate(std::span<const std::uint8_t> buffer) {
        auto result = Validator::validate(buffer);
        // Log but don't fail on certain errors
        if (result.error == ValidationError::UNSUPPORTED_VERSION) {
            // Allow newer versions for forward compatibility
            result.error = ValidationError::OK;
        }
        return result;
    }
};

// Type-erased validation strategy using std::variant (no vtables)
using ValidationStrategy = std::variant<StrictValidationStrategy, LenientValidationStrategy>;

// Helper to invoke validation on variant
[[nodiscard]] inline ValidationResult validate_with_strategy(
    ValidationStrategy& strategy,
    std::span<const std::uint8_t> buffer) {
    return std::visit([&buffer](auto& s) { return s.validate(buffer); }, strategy);
}

} // namespace ukk::protocol::validation
