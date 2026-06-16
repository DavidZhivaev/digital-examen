# UKK Protocol Specification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Define a complete, versioned protocol specification for agent-relay communication with JSON Schema validation, MessagePack binary encoding, and C++ code generators following the project's strict C++ metaprogramming standards.

**Architecture:** The protocol uses WebSocket transport with JSON-encoded messages for human readability during development and MessagePack for production binary efficiency. All message types are defined as C++ template structs with compile-time validation via concepts. Code generators produce both JSON Schema files and C++ serialization code from a single source of truth.

**Tech Stack:** C++20 (concepts, constexpr, CRTP), MessagePack (msgpack-c), JSON Schema Draft 2020-12, Boost.PFR for reflection, CMake build system

---

## Protocol Message Types Summary

Based on technical documentation analysis:

### Agent -> Relay Messages
| Type | Purpose |
|------|---------|
| `REGISTER` | Initial agent registration |
| `HEARTBEAT` | Periodic activity confirmation |
| `SCREENSHOT` | Screen capture data |
| `TASK_RESULT` | Task execution response |
| `EVENT` | Security/monitoring events |
| `METRICS` | Aggregated telemetry |
| `PONG` | Response to PING |

### Relay -> Agent Messages
| Type | Purpose |
|------|---------|
| `TASK` | Command for execution |
| `POLICY_UPDATE` | New policy rules |
| `PING` | Connection health check |
| `AGENT_UPDATE` | Binary update command |
| `ACK` | Message acknowledgment |
| `ERROR` | Error response |

---

## Task 1: Create Protocol Directory Structure

**Files:**
- Create: `protocol/CMakeLists.txt`
- Create: `protocol/include/ukk/protocol/version.hpp`
- Create: `protocol/include/ukk/protocol/types.hpp`

**Step 1: Create directory structure**

```bash
mkdir -p protocol/include/ukk/protocol
mkdir -p protocol/include/ukk/protocol/messages
mkdir -p protocol/include/ukk/protocol/schema
mkdir -p protocol/include/ukk/protocol/codegen
mkdir -p protocol/src
mkdir -p protocol/tests
mkdir -p protocol/schemas
```

**Step 2: Create CMakeLists.txt**

```cmake
# protocol/CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(ukk_protocol VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler flags for low-latency
add_compile_options(-O3 -march=native -Wall -Wextra -Wpedantic)

find_package(msgpack-cxx REQUIRED)

add_library(ukk_protocol INTERFACE)
target_include_directories(ukk_protocol INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(ukk_protocol INTERFACE msgpack-cxx)

# Tests
enable_testing()
add_subdirectory(tests)
```

**Step 3: Create version.hpp**

```cpp
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
```

**Step 4: Create types.hpp with base types**

```cpp
// protocol/include/ukk/protocol/types.hpp
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <optional>
#include <variant>
#include <chrono>

namespace ukk::protocol {

// UUID as fixed-size array (cache-aligned)
struct alignas(16) UUID {
    std::array<std::uint8_t, 16> bytes{};

    [[nodiscard]] constexpr bool operator==(const UUID&) const noexcept = default;
    [[nodiscard]] std::string to_string() const;
    [[nodiscard]] static UUID generate();
    [[nodiscard]] static UUID from_string(std::string_view str);
};

// ISO 8601 timestamp wrapper
struct Timestamp {
    std::chrono::system_clock::time_point value{};

    [[nodiscard]] std::string to_iso8601() const;
    [[nodiscard]] static Timestamp now();
    [[nodiscard]] static Timestamp from_iso8601(std::string_view str);
};

// Message type enumeration
enum class MessageType : std::uint8_t {
    // Agent -> Relay
    REGISTER        = 0x01,
    HEARTBEAT       = 0x02,
    SCREENSHOT      = 0x03,
    TASK_RESULT     = 0x04,
    EVENT           = 0x05,
    METRICS         = 0x06,
    PONG            = 0x07,

    // Relay -> Agent
    TASK            = 0x81,
    POLICY_UPDATE   = 0x82,
    PING            = 0x83,
    AGENT_UPDATE    = 0x84,
    ACK             = 0x85,
    ERROR           = 0x86,
};

// Event severity levels
enum class Severity : std::uint8_t {
    LOW      = 0,
    MEDIUM   = 1,
    HIGH     = 2,
    CRITICAL = 3,
};

// Task priority
enum class Priority : std::uint8_t {
    NORMAL = 0,
    HIGH   = 1,
};

// Task status
enum class TaskStatus : std::uint8_t {
    OK      = 0,
    ERROR   = 1,
    TIMEOUT = 2,
};

// Agent status
enum class AgentStatus : std::uint8_t {
    ONLINE  = 0,
    OFFLINE = 1,
    ERROR   = 2,
};

// Constexpr string for message type names
[[nodiscard]] constexpr std::string_view message_type_name(MessageType type) noexcept {
    switch (type) {
        case MessageType::REGISTER:       return "REGISTER";
        case MessageType::HEARTBEAT:      return "HEARTBEAT";
        case MessageType::SCREENSHOT:     return "SCREENSHOT";
        case MessageType::TASK_RESULT:    return "TASK_RESULT";
        case MessageType::EVENT:          return "EVENT";
        case MessageType::METRICS:        return "METRICS";
        case MessageType::PONG:           return "PONG";
        case MessageType::TASK:           return "TASK";
        case MessageType::POLICY_UPDATE:  return "POLICY_UPDATE";
        case MessageType::PING:           return "PING";
        case MessageType::AGENT_UPDATE:   return "AGENT_UPDATE";
        case MessageType::ACK:            return "ACK";
        case MessageType::ERROR:          return "ERROR";
    }
    return "UNKNOWN";
}

} // namespace ukk::protocol
```

**Step 5: Commit**

```bash
git add protocol/
git commit -m "feat(protocol): база модуля протокола

- Добавил cmake для cpp 20 и зависимости msgpack
- Добавил version.cpp с константами зависимочтей протокола
- Добавил types.hpp

``

---

## Task 2: Define Message Header and Base Concepts

**Files:**
- Create: `protocol/include/ukk/protocol/concepts.hpp`
- Create: `protocol/include/ukk/protocol/header.hpp`

**Step 1: Create concepts.hpp with C++20 concepts**

```cpp
// protocol/include/ukk/protocol/concepts.hpp
#pragma once

#include <concepts>
#include <type_traits>
#include <cstdint>

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
```

**Step 2: Create header.hpp with message header**

```cpp
// protocol/include/ukk/protocol/header.hpp
#pragma once

#include "types.hpp"
#include "version.hpp"
#include <cstdint>
#include <array>

namespace ukk::protocol {

// Fixed-size message header (cache-line aligned)
struct alignas(64) MessageHeader {
    std::uint32_t magic{PROTOCOL_MAGIC};        // 4 bytes: "UKKP"
    std::uint32_t version{PROTOCOL_VERSION_MAJOR}; // 4 bytes
    MessageType   type{};                        // 1 byte
    std::uint8_t  flags{0};                      // 1 byte (reserved)
    std::uint16_t reserved{0};                   // 2 bytes (alignment)
    std::uint32_t payload_size{0};               // 4 bytes
    UUID          message_id{};                  // 16 bytes
    Timestamp     timestamp{};                   // 8 bytes (epoch)
    std::array<std::uint8_t, 24> padding{};      // padding to 64 bytes

    [[nodiscard]] constexpr bool is_valid() const noexcept {
        return magic == PROTOCOL_MAGIC &&
               version <= PROTOCOL_VERSION_MAJOR &&
               payload_size <= MAX_MESSAGE_SIZE;
    }

    [[nodiscard]] constexpr bool is_agent_message() const noexcept {
        return static_cast<std::uint8_t>(type) < 0x80;
    }

    [[nodiscard]] constexpr bool is_relay_message() const noexcept {
        return static_cast<std::uint8_t>(type) >= 0x80;
    }
};

static_assert(sizeof(MessageHeader) == 64, "MessageHeader must be 64 bytes");
static_assert(alignof(MessageHeader) == 64, "MessageHeader must be cache-aligned");

} // namespace ukk::protocol
```

**Step 3: Commit**

```bash
git add protocol/include/ukk/protocol/concepts.hpp protocol/include/ukk/protocol/header.hpp
git commit -m "feat(protocol): хэдера сообщений протокола

- Сделал базу для Serializable, MessagePayload и для Validatable
- Добавил AgentMessage и RelayMessage
- Добавил 64 байтную MessageHeader структуру с выравниванием кэшей

```

---

## Task 3: Define Agent -> Relay Message Structs

**Files:**
- Create: `protocol/include/ukk/protocol/messages/register.hpp`
- Create: `protocol/include/ukk/protocol/messages/heartbeat.hpp`
- Create: `protocol/include/ukk/protocol/messages/screenshot.hpp`
- Create: `protocol/include/ukk/protocol/messages/task_result.hpp`
- Create: `protocol/include/ukk/protocol/messages/event.hpp`
- Create: `protocol/include/ukk/protocol/messages/metrics.hpp`

**Step 1: Create register.hpp**

```cpp
// protocol/include/ukk/protocol/messages/register.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// REGISTER message: Agent registration on relay
struct Register {
    static constexpr MessageType message_type{MessageType::REGISTER};
    static constexpr std::string_view type_name{"REGISTER"};

    struct Args {
        UUID        machine_id{};           // Unique machine identifier
        std::string building_id{};          // Building identifier
        std::string room_id{};              // Room identifier
        std::string seat_id{};              // Seat identifier
        std::string agent_version{};        // Agent software version
        std::string hw_fingerprint{};       // SHA-256(CPU + MB + MAC)
        std::string os_version{};           // Operating system version
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return !args.building_id.empty() &&
               !args.room_id.empty() &&
               !args.agent_version.empty() &&
               args.hw_fingerprint.size() == 64; // SHA-256 hex
    }
};

// Response to REGISTER (sent by relay)
struct RegisterResponse {
    std::string session_token{};            // Session authentication token
    std::string relay_ws_url{};             // WebSocket URL for reconnection
    // initial_policy embedded as separate POLICY_UPDATE
};

} // namespace ukk::protocol::messages
```

**Step 2: Create heartbeat.hpp**

```cpp
// protocol/include/ukk/protocol/messages/heartbeat.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <cstdint>
#include <string>

namespace ukk::protocol::messages {

// HEARTBEAT message: Periodic activity confirmation
struct Heartbeat {
    static constexpr MessageType message_type{MessageType::HEARTBEAT};
    static constexpr std::string_view type_name{"HEARTBEAT"};

    struct Args {
        std::uint8_t  cpu_pct{0};           // CPU usage percentage (0-100)
        std::uint8_t  ram_pct{0};           // RAM usage percentage (0-100)
        std::uint8_t  gpu_pct{0};           // GPU usage percentage (0-100)
        float         disk_free_gb{0.0f};   // Free disk space in GB
        std::string   active_policy{};      // Currently active policy ID
        AgentStatus   status{AgentStatus::ONLINE};
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args& args) noexcept {
        return args.cpu_pct <= 100 &&
               args.ram_pct <= 100 &&
               args.gpu_pct <= 100 &&
               args.disk_free_gb >= 0.0f;
    }
};

} // namespace ukk::protocol::messages
```

**Step 3: Create screenshot.hpp**

```cpp
// protocol/include/ukk/protocol/messages/screenshot.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <vector>
#include <cstdint>
#include <optional>

namespace ukk::protocol::messages {

// SCREENSHOT message: Screen capture data
struct Screenshot {
    static constexpr MessageType message_type{MessageType::SCREENSHOT};
    static constexpr std::string_view type_name{"SCREENSHOT"};

    struct Args {
        bool                           changed{true};      // True if screen changed
        std::optional<std::vector<std::uint8_t>> image_data{}; // zstd-compressed image
        std::uint32_t                  width{0};           // Image width
        std::uint32_t                  height{0};          // Image height
        std::uint64_t                  phash{0};           // Perceptual hash
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (!args.changed) {
            return !args.image_data.has_value(); // NO_CHANGE has no data
        }
        return args.image_data.has_value() &&
               !args.image_data->empty() &&
               args.width > 0 && args.height > 0;
    }
};

} // namespace ukk::protocol::messages
```

**Step 4: Create task_result.hpp**

```cpp
// protocol/include/ukk/protocol/messages/task_result.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <optional>
#include <cstdint>

namespace ukk::protocol::messages {

// TASK_RESULT message: Task execution response
struct TaskResult {
    static constexpr MessageType message_type{MessageType::TASK_RESULT};
    static constexpr std::string_view type_name{"TASK_RESULT"};

    struct Args {
        UUID                      task_id{};        // Original task ID
        TaskStatus                status{TaskStatus::OK};
        std::string               output{};         // Command output
        std::optional<std::int32_t> error_code{};   // Error code if failed
        std::uint64_t             execution_time_ms{0}; // Execution duration
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (args.status == TaskStatus::ERROR) {
            return args.error_code.has_value();
        }
        return true;
    }
};

} // namespace ukk::protocol::messages
```

**Step 5: Create event.hpp**

```cpp
// protocol/include/ukk/protocol/messages/event.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <variant>
#include <cstdint>

namespace ukk::protocol::messages {

// Event type enumeration
enum class EventType : std::uint8_t {
    USB_CONNECTED    = 0x01,
    USB_DISCONNECTED = 0x02,
    P2P_DETECTED     = 0x03,
    TAMPER_DETECTED  = 0x04,
    PROCESS_KILLED   = 0x05,
    AGENT_OFFLINE    = 0x06,
    POLICY_VIOLATION = 0x07,
    GPU_THRESHOLD    = 0x08,
};

// USB event details
struct UsbEventDetails {
    std::uint16_t vendor_id{0};
    std::uint16_t product_id{0};
    std::string   device_class{};
    std::string   serial{};
};

// P2P event details
struct P2pEventDetails {
    std::string local_ip{};
    std::string remote_ip{};
    std::uint16_t local_port{0};
    std::uint16_t remote_port{0};
    std::string protocol{};  // "TCP" or "UDP"
};

// Process event details
struct ProcessEventDetails {
    std::uint32_t pid{0};
    std::string   process_name{};
    std::string   reason{};
};

// Tamper event details
struct TamperEventDetails {
    std::string expected_hash{};
    std::string actual_hash{};
    std::string file_path{};
};

using EventDetails = std::variant<
    UsbEventDetails,
    P2pEventDetails,
    ProcessEventDetails,
    TamperEventDetails,
    std::string  // Generic details
>;

// EVENT message: Security/monitoring events
struct Event {
    static constexpr MessageType message_type{MessageType::EVENT};
    static constexpr std::string_view type_name{"EVENT"};

    struct Args {
        EventType    event_type{};
        Severity     severity{Severity::LOW};
        EventDetails details{};
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args&) noexcept {
        return true; // Variant handles validation
    }
};

} // namespace ukk::protocol::messages
```

**Step 6: Create metrics.hpp**

```cpp
// protocol/include/ukk/protocol/messages/metrics.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <vector>
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// DNS query summary entry
struct DnsQueryEntry {
    std::string   domain{};
    std::uint32_t query_count{0};
    bool          blocked{false};
};

// Application focus entry
struct AppFocusEntry {
    std::string   app_name{};
    std::string   window_title{};
    std::uint32_t duration_seconds{0};
    Timestamp     start_time{};
};

// Process info entry
struct ProcessInfo {
    std::uint32_t pid{0};
    std::string   name{};
    std::string   cmdline{};
    std::uint8_t  cpu_pct{0};
    std::uint32_t memory_mb{0};
};

// METRICS message: Aggregated telemetry
struct Metrics {
    static constexpr MessageType message_type{MessageType::METRICS};
    static constexpr std::string_view type_name{"METRICS"};

    struct Args {
        Timestamp                   period_start{};
        Timestamp                   period_end{};
        std::vector<DnsQueryEntry>  dns_summary{};
        std::vector<AppFocusEntry>  app_focus_timeline{};
        std::vector<ProcessInfo>    process_list{};
        std::uint32_t               unique_domains{0};
        std::uint32_t               blocked_queries{0};
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return args.period_end.value >= args.period_start.value;
    }
};

} // namespace ukk::protocol::messages
```

**Step 7: Commit**

```bash
git add protocol/include/ukk/protocol/messages/
git commit -m "feat(protocol): обьявление для агет - реле сообщение

- REGISTER: Регистрация агента с информацией о машине
- HEARTBEAT: Периодический статус с использованием ресурсов
- SCREENSHOT: Захват экрана с дедупликацией pHash
- TASK_RESULT:Реакция на выполнение задачи
- EVENT: Все ивенты типа вставки USB, аномалий в внутренем трафике и тд
- METRICS: Здесь все телеметрия агентов

```

---

## Task 4: Define Relay -> Agent Message Structs

**Files:**
- Create: `protocol/include/ukk/protocol/messages/task.hpp`
- Create: `protocol/include/ukk/protocol/messages/policy_update.hpp`
- Create: `protocol/include/ukk/protocol/messages/ping_pong.hpp`
- Create: `protocol/include/ukk/protocol/messages/agent_update.hpp`
- Create: `protocol/include/ukk/protocol/messages/ack_error.hpp`

**Step 1: Create task.hpp**

```cpp
// protocol/include/ukk/protocol/messages/task.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <variant>
#include <vector>
#include <cstdint>
#include <optional>

namespace ukk::protocol::messages {

// Task type enumeration (from documentation)
enum class TaskType : std::uint16_t {
    SCREENSHOT      = 0x0001,
    NET_POLICY      = 0x0002,
    PROCESS_POLICY  = 0x0003,
    CURSOR_CONTROL  = 0x0004,
    SCREEN_CONTROL  = 0x0005,
    TRAFFIC_LIMIT   = 0x0006,
    USB_POLICY      = 0x0007,
    AGENT_UPDATE    = 0x0008,
    GET_METRICS     = 0x0009,
    SHELL_EXEC      = 0x000A,
};

// Screenshot task payload
struct ScreenshotPayload {
    std::uint8_t quality{80};           // JPEG quality 1-100
    bool         force_capture{false};  // Ignore pHash comparison
};

// Network policy payload
struct NetPolicyPayload {
    std::vector<std::string> whitelist{};
    std::vector<std::string> blacklist{};
    bool                     whitelist_only{false};
    std::optional<std::uint32_t> bandwidth_limit_kbps{};
};

// Process policy payload
struct ProcessPolicyPayload {
    std::vector<std::string> blocked_processes{};
    std::uint8_t             gpu_threshold_pct{40};
    std::uint32_t            gpu_check_duration_sec{30};
    bool                     auto_kill{false};
};

// Screen control payload
struct ScreenControlPayload {
    enum class Action : std::uint8_t {
        BLACKOUT = 0,
        RESTORE  = 1,
        DPMS_OFF = 2,
        DPMS_ON  = 3,
    };
    Action action{Action::BLACKOUT};
};

// USB policy payload
struct UsbPolicyPayload {
    std::vector<std::uint8_t> blocked_classes{}; // USB device classes
    bool                      block_mass_storage{true};
};

// Traffic limit payload
struct TrafficLimitPayload {
    std::string              target_domain{};
    std::uint32_t            limit_kbps{0};
    bool                     remove{false};
};

// Shell execution payload
struct ShellExecPayload {
    std::string command{};
    std::uint32_t timeout_ms{30000};
};

using TaskPayload = std::variant<
    ScreenshotPayload,
    NetPolicyPayload,
    ProcessPolicyPayload,
    ScreenControlPayload,
    UsbPolicyPayload,
    TrafficLimitPayload,
    ShellExecPayload
>;

// TASK message: Command for execution
struct Task {
    static constexpr MessageType message_type{MessageType::TASK};
    static constexpr std::string_view type_name{"TASK"};

    struct Args {
        UUID         task_id{};
        TaskType     task_type{};
        TaskPayload  payload{};
        Priority     priority{Priority::NORMAL};
        Timestamp    deadline{};          // Task must complete by this time
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        // Validate payload matches task_type
        return std::visit([&](auto&& p) -> bool {
            using T = std::decay_t<decltype(p)>;
            if constexpr (std::is_same_v<T, ScreenshotPayload>) {
                return args.task_type == TaskType::SCREENSHOT;
            } else if constexpr (std::is_same_v<T, NetPolicyPayload>) {
                return args.task_type == TaskType::NET_POLICY;
            } else if constexpr (std::is_same_v<T, ProcessPolicyPayload>) {
                return args.task_type == TaskType::PROCESS_POLICY;
            } else if constexpr (std::is_same_v<T, ScreenControlPayload>) {
                return args.task_type == TaskType::SCREEN_CONTROL;
            } else if constexpr (std::is_same_v<T, UsbPolicyPayload>) {
                return args.task_type == TaskType::USB_POLICY;
            } else if constexpr (std::is_same_v<T, TrafficLimitPayload>) {
                return args.task_type == TaskType::TRAFFIC_LIMIT;
            } else if constexpr (std::is_same_v<T, ShellExecPayload>) {
                return args.task_type == TaskType::SHELL_EXEC;
            }
            return false;
        }, args.payload);
    }
};

} // namespace ukk::protocol::messages
```

**Step 2: Create policy_update.hpp**

```cpp
// protocol/include/ukk/protocol/messages/policy_update.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <vector>
#include <cstdint>
#include <optional>

namespace ukk::protocol::messages {

// Policy profile type
enum class PolicyProfile : std::uint8_t {
    FREE        = 0,    // No restrictions
    LESSON      = 1,    // Standard educational
    EXAM        = 2,    // Exam mode (strict)
    LOCKDOWN    = 3,    // Administrative lockdown
};

// Full policy rules structure
struct PolicyRules {
    // Network rules
    std::vector<std::string> dns_whitelist{};
    std::vector<std::string> dns_blacklist{};
    bool                     whitelist_only{false};
    std::optional<std::uint32_t> bandwidth_limit_kbps{};

    // Process rules
    std::vector<std::string> blocked_processes{};
    std::uint8_t             gpu_threshold_pct{40};
    bool                     auto_kill_violations{false};

    // USB rules
    bool                     block_mass_storage{false};
    std::vector<std::uint8_t> blocked_usb_classes{};

    // Screenshot rules
    std::uint32_t            screenshot_interval_ms{20000};
    std::uint8_t             screenshot_quality{80};

    // P2P detection
    bool                     detect_p2p{false};

    // Screen control
    bool                     allow_screen_blackout{true};
};

// POLICY_UPDATE message: New policy rules
struct PolicyUpdate {
    static constexpr MessageType message_type{MessageType::POLICY_UPDATE};
    static constexpr std::string_view type_name{"POLICY_UPDATE"};

    struct Args {
        UUID          policy_id{};
        PolicyProfile profile{PolicyProfile::FREE};
        PolicyRules   rules{};
        Timestamp     effective_from{};
        std::optional<Timestamp> effective_until{};
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        if (args.effective_until.has_value()) {
            return args.effective_until->value > args.effective_from.value;
        }
        return true;
    }
};

} // namespace ukk::protocol::messages
```

**Step 3: Create ping_pong.hpp**

```cpp
// protocol/include/ukk/protocol/messages/ping_pong.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <cstdint>

namespace ukk::protocol::messages {

// PING message: Connection health check (Relay -> Agent)
struct Ping {
    static constexpr MessageType message_type{MessageType::PING};
    static constexpr std::string_view type_name{"PING"};

    struct Args {
        std::uint64_t sequence{0};      // Sequence number for RTT calc
        Timestamp     sent_at{};
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args&) noexcept {
        return true;
    }
};

// PONG message: Response to PING (Agent -> Relay)
struct Pong {
    static constexpr MessageType message_type{MessageType::PONG};
    static constexpr std::string_view type_name{"PONG"};

    struct Args {
        std::uint64_t sequence{0};      // Echo sequence number
        Timestamp     ping_sent_at{};   // Original ping timestamp
        Timestamp     pong_sent_at{};   // This response timestamp
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args& args) noexcept {
        return args.pong_sent_at.value >= args.ping_sent_at.value;
    }
};

} // namespace ukk::protocol::messages
```

**Step 4: Create agent_update.hpp**

```cpp
// protocol/include/ukk/protocol/messages/agent_update.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// AGENT_UPDATE message: Binary update command
struct AgentUpdate {
    static constexpr MessageType message_type{MessageType::AGENT_UPDATE};
    static constexpr std::string_view type_name{"AGENT_UPDATE"};

    struct Args {
        std::string  new_version{};         // Target version string
        std::string  download_url{};        // URL to download from relay
        std::string  sha256_hash{};         // Expected SHA-256 hash (hex)
        std::uint64_t file_size{0};         // Expected file size in bytes
        bool         force{false};          // Force update even if same version
        bool         restart_required{true}; // Restart agent after update
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return !args.new_version.empty() &&
               !args.download_url.empty() &&
               args.sha256_hash.size() == 64 && // SHA-256 hex
               args.file_size > 0;
    }
};

} // namespace ukk::protocol::messages
```

**Step 5: Create ack_error.hpp**

```cpp
// protocol/include/ukk/protocol/messages/ack_error.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <cstdint>

namespace ukk::protocol::messages {

// ACK message: Message acknowledgment
struct Ack {
    static constexpr MessageType message_type{MessageType::ACK};
    static constexpr std::string_view type_name{"ACK"};

    struct Args {
        UUID acked_message_id{};    // ID of acknowledged message
    };

    using args_type = Args;

    [[nodiscard]] static constexpr bool validate(const Args&) noexcept {
        return true;
    }
};

// Error codes
enum class ErrorCode : std::uint16_t {
    UNKNOWN               = 0x0000,
    INVALID_MESSAGE       = 0x0001,
    INVALID_PAYLOAD       = 0x0002,
    UNSUPPORTED_VERSION   = 0x0003,
    AUTHENTICATION_FAILED = 0x0004,
    TASK_NOT_FOUND        = 0x0005,
    TASK_EXECUTION_FAILED = 0x0006,
    POLICY_INVALID        = 0x0007,
    RESOURCE_UNAVAILABLE  = 0x0008,
    RATE_LIMITED          = 0x0009,
    INTERNAL_ERROR        = 0x00FF,
};

// ERROR message: Error response
struct Error {
    static constexpr MessageType message_type{MessageType::ERROR};
    static constexpr std::string_view type_name{"ERROR"};

    struct Args {
        UUID         reference_id{};    // ID of message that caused error
        ErrorCode    code{ErrorCode::UNKNOWN};
        std::string  message{};         // Human-readable error
        std::string  details{};         // Additional context (JSON)
    };

    using args_type = Args;

    [[nodiscard]] static bool validate(const Args& args) noexcept {
        return !args.message.empty();
    }
};

} // namespace ukk::protocol::messages
```

**Step 6: Commit**

```bash
git add protocol/include/ukk/protocol/messages/
git commit -m "feat(protocol): опять сообщения агент - реле

- TASK:Выполнение команд с типизированной полезной нагрузкой
- POLICY_UPDATE:Полная структура правил политики
- PING/PONG:Проверка работоспособности соединения
- AGENT_UPDATE: команда для апдейта агентов
- ACK/ERROR: команда на случай появления ошибок

```

---

## Task 5: Create MessagePack Serialization Layer

**Files:**
- Create: `protocol/include/ukk/protocol/serialization/msgpack.hpp`
- Create: `protocol/include/ukk/protocol/serialization/traits.hpp`

**Step 1: Create traits.hpp with PFR-based reflection**

```cpp
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
```

**Step 2: Create msgpack.hpp with serialization functions**

```cpp
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
```

**Step 3: Commit**

```bash
git add protocol/include/ukk/protocol/serialization/
git commit -m "feat(protocol): MessagePack сериализация

- добавил кастомный msgpack адапторы для UUID и для таймстампов
- добавил сериализацию/десериализацию
- добавил сериализацию всего сообщения с хэдерами
- добавил error handling

```

---

## Task 6: Create JSON Schema Generator

**Files:**
- Create: `protocol/include/ukk/protocol/schema/generator.hpp`
- Create: `protocol/tools/generate_schemas.cpp`

**Step 1: Create generator.hpp**

```cpp
// protocol/include/ukk/protocol/schema/generator.hpp
#pragma once

#include "../types.hpp"
#include "../concepts.hpp"
#include <string>
#include <sstream>
#include <type_traits>
#include <vector>
#include <optional>

namespace ukk::protocol::schema {

// JSON Schema type mapping
template<typename T>
struct JsonSchemaType {
    static constexpr std::string_view type = "object";
    static constexpr std::string_view format = "";
};

template<> struct JsonSchemaType<bool> {
    static constexpr std::string_view type = "boolean";
    static constexpr std::string_view format = "";
};

template<> struct JsonSchemaType<std::int8_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "int8";
};

template<> struct JsonSchemaType<std::uint8_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "uint8";
};

template<> struct JsonSchemaType<std::int16_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "int16";
};

template<> struct JsonSchemaType<std::uint16_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "uint16";
};

template<> struct JsonSchemaType<std::int32_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "int32";
};

template<> struct JsonSchemaType<std::uint32_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "uint32";
};

template<> struct JsonSchemaType<std::int64_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "int64";
};

template<> struct JsonSchemaType<std::uint64_t> {
    static constexpr std::string_view type = "integer";
    static constexpr std::string_view format = "uint64";
};

template<> struct JsonSchemaType<float> {
    static constexpr std::string_view type = "number";
    static constexpr std::string_view format = "float";
};

template<> struct JsonSchemaType<double> {
    static constexpr std::string_view type = "number";
    static constexpr std::string_view format = "double";
};

template<> struct JsonSchemaType<std::string> {
    static constexpr std::string_view type = "string";
    static constexpr std::string_view format = "";
};

template<> struct JsonSchemaType<UUID> {
    static constexpr std::string_view type = "string";
    static constexpr std::string_view format = "uuid";
};

template<> struct JsonSchemaType<Timestamp> {
    static constexpr std::string_view type = "string";
    static constexpr std::string_view format = "date-time";
};

template<typename T>
struct JsonSchemaType<std::vector<T>> {
    static constexpr std::string_view type = "array";
    static constexpr std::string_view format = "";
};

template<typename T>
struct JsonSchemaType<std::optional<T>> {
    static constexpr std::string_view type = JsonSchemaType<T>::type;
    static constexpr std::string_view format = JsonSchemaType<T>::format;
    static constexpr bool nullable = true;
};

// Schema generation context
class SchemaGenerator {
public:
    void add_definition(std::string_view name, std::string_view schema) {
        definitions_ << "\"" << name << "\": " << schema;
        if (!first_def_) definitions_ << ",\n";
        first_def_ = false;
    }

    [[nodiscard]] std::string generate_root_schema(
        std::string_view title,
        std::string_view description) const {

        std::ostringstream ss;
        ss << "{\n"
           << "  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\",\n"
           << "  \"$id\": \"https://ukk.school.local/protocol/v1/" << title << ".json\",\n"
           << "  \"title\": \"" << title << "\",\n"
           << "  \"description\": \"" << description << "\",\n"
           << "  \"$defs\": {\n"
           << definitions_.str()
           << "\n  }\n"
           << "}";
        return ss.str();
    }

private:
    std::ostringstream definitions_;
    bool first_def_{true};
};

// Generate JSON Schema for message type
template<MessagePayload T>
[[nodiscard]] std::string generate_message_schema() {
    std::ostringstream ss;
    ss << "{\n"
       << "  \"type\": \"object\",\n"
       << "  \"title\": \"" << T::type_name << "\",\n"
       << "  \"properties\": {\n"
       << "    \"type\": {\n"
       << "      \"const\": \"" << T::type_name << "\"\n"
       << "    },\n"
       << "    \"message_id\": {\n"
       << "      \"type\": \"string\",\n"
       << "      \"format\": \"uuid\"\n"
       << "    },\n"
       << "    \"timestamp\": {\n"
       << "      \"type\": \"string\",\n"
       << "      \"format\": \"date-time\"\n"
       << "    },\n"
       << "    \"payload\": {\n"
       << "      \"$ref\": \"#/$defs/" << T::type_name << "Payload\"\n"
       << "    }\n"
       << "  },\n"
       << "  \"required\": [\"type\", \"message_id\", \"timestamp\", \"payload\"]\n"
       << "}";
    return ss.str();
}

} // namespace ukk::protocol::schema
```

**Step 2: Create generate_schemas.cpp tool**

```cpp
// protocol/tools/generate_schemas.cpp
#include <ukk/protocol/messages/register.hpp>
#include <ukk/protocol/messages/heartbeat.hpp>
#include <ukk/protocol/messages/screenshot.hpp>
#include <ukk/protocol/messages/task_result.hpp>
#include <ukk/protocol/messages/event.hpp>
#include <ukk/protocol/messages/metrics.hpp>
#include <ukk/protocol/messages/task.hpp>
#include <ukk/protocol/messages/policy_update.hpp>
#include <ukk/protocol/messages/ping_pong.hpp>
#include <ukk/protocol/messages/agent_update.hpp>
#include <ukk/protocol/messages/ack_error.hpp>

#include <fstream>
#include <iostream>
#include <filesystem>

using namespace ukk::protocol;
using namespace ukk::protocol::messages;

// Hand-written JSON schemas (compile-time generation would require more infrastructure)
constexpr std::string_view REGISTER_SCHEMA = R"({
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ukk.school.local/protocol/v1/register.json",
  "title": "REGISTER",
  "description": "Agent registration message",
  "type": "object",
  "properties": {
    "type": { "const": "REGISTER" },
    "message_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "properties": {
        "machine_id": { "type": "string", "format": "uuid" },
        "building_id": { "type": "string", "minLength": 1 },
        "room_id": { "type": "string", "minLength": 1 },
        "seat_id": { "type": "string" },
        "agent_version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
        "hw_fingerprint": { "type": "string", "minLength": 64, "maxLength": 64 },
        "os_version": { "type": "string" }
      },
      "required": ["machine_id", "building_id", "room_id", "agent_version", "hw_fingerprint"]
    }
  },
  "required": ["type", "message_id", "timestamp", "payload"]
})";

constexpr std::string_view HEARTBEAT_SCHEMA = R"({
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ukk.school.local/protocol/v1/heartbeat.json",
  "title": "HEARTBEAT",
  "description": "Periodic activity confirmation",
  "type": "object",
  "properties": {
    "type": { "const": "HEARTBEAT" },
    "message_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "properties": {
        "cpu_pct": { "type": "integer", "minimum": 0, "maximum": 100 },
        "ram_pct": { "type": "integer", "minimum": 0, "maximum": 100 },
        "gpu_pct": { "type": "integer", "minimum": 0, "maximum": 100 },
        "disk_free_gb": { "type": "number", "minimum": 0 },
        "active_policy": { "type": "string" },
        "status": { "enum": ["online", "offline", "error"] }
      },
      "required": ["cpu_pct", "ram_pct", "gpu_pct", "disk_free_gb", "status"]
    }
  },
  "required": ["type", "message_id", "timestamp", "payload"]
})";

constexpr std::string_view SCREENSHOT_SCHEMA = R"({
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ukk.school.local/protocol/v1/screenshot.json",
  "title": "SCREENSHOT",
  "description": "Screen capture data",
  "type": "object",
  "properties": {
    "type": { "const": "SCREENSHOT" },
    "message_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "properties": {
        "changed": { "type": "boolean" },
        "image_data": { "type": "string", "contentEncoding": "base64" },
        "width": { "type": "integer", "minimum": 1 },
        "height": { "type": "integer", "minimum": 1 },
        "phash": { "type": "string", "description": "Perceptual hash as hex" }
      },
      "required": ["changed"],
      "if": { "properties": { "changed": { "const": true } } },
      "then": { "required": ["image_data", "width", "height"] }
    }
  },
  "required": ["type", "message_id", "timestamp", "payload"]
})";

constexpr std::string_view TASK_SCHEMA = R"({
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ukk.school.local/protocol/v1/task.json",
  "title": "TASK",
  "description": "Command for agent execution",
  "type": "object",
  "properties": {
    "type": { "const": "TASK" },
    "message_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "properties": {
        "task_id": { "type": "string", "format": "uuid" },
        "task_type": {
          "enum": ["SCREENSHOT", "NET_POLICY", "PROCESS_POLICY", "CURSOR_CONTROL",
                   "SCREEN_CONTROL", "TRAFFIC_LIMIT", "USB_POLICY", "AGENT_UPDATE",
                   "GET_METRICS", "SHELL_EXEC"]
        },
        "payload": { "type": "object" },
        "priority": { "enum": ["normal", "high"], "default": "normal" },
        "deadline": { "type": "string", "format": "date-time" }
      },
      "required": ["task_id", "task_type", "payload"]
    }
  },
  "required": ["type", "message_id", "timestamp", "payload"]
})";

constexpr std::string_view POLICY_UPDATE_SCHEMA = R"({
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ukk.school.local/protocol/v1/policy_update.json",
  "title": "POLICY_UPDATE",
  "description": "Policy rules update",
  "type": "object",
  "properties": {
    "type": { "const": "POLICY_UPDATE" },
    "message_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "properties": {
        "policy_id": { "type": "string", "format": "uuid" },
        "profile": { "enum": ["free", "lesson", "exam", "lockdown"] },
        "rules": {
          "type": "object",
          "properties": {
            "dns_whitelist": { "type": "array", "items": { "type": "string" } },
            "dns_blacklist": { "type": "array", "items": { "type": "string" } },
            "whitelist_only": { "type": "boolean" },
            "bandwidth_limit_kbps": { "type": "integer", "minimum": 0 },
            "blocked_processes": { "type": "array", "items": { "type": "string" } },
            "gpu_threshold_pct": { "type": "integer", "minimum": 0, "maximum": 100 },
            "auto_kill_violations": { "type": "boolean" },
            "block_mass_storage": { "type": "boolean" },
            "screenshot_interval_ms": { "type": "integer", "minimum": 1000 },
            "screenshot_quality": { "type": "integer", "minimum": 1, "maximum": 100 },
            "detect_p2p": { "type": "boolean" }
          }
        },
        "effective_from": { "type": "string", "format": "date-time" },
        "effective_until": { "type": "string", "format": "date-time" }
      },
      "required": ["policy_id", "profile", "rules", "effective_from"]
    }
  },
  "required": ["type", "message_id", "timestamp", "payload"]
})";

constexpr std::string_view EVENT_SCHEMA = R"({
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ukk.school.local/protocol/v1/event.json",
  "title": "EVENT",
  "description": "Security or monitoring event",
  "type": "object",
  "properties": {
    "type": { "const": "EVENT" },
    "message_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "properties": {
        "event_type": {
          "enum": ["USB_CONNECTED", "USB_DISCONNECTED", "P2P_DETECTED",
                   "TAMPER_DETECTED", "PROCESS_KILLED", "AGENT_OFFLINE",
                   "POLICY_VIOLATION", "GPU_THRESHOLD"]
        },
        "severity": { "enum": ["low", "medium", "high", "critical"] },
        "details": { "type": "object" }
      },
      "required": ["event_type", "severity"]
    }
  },
  "required": ["type", "message_id", "timestamp", "payload"]
})";

void write_schema(const std::filesystem::path& dir,
                  std::string_view name,
                  std::string_view content) {
    auto path = dir / (std::string{name} + ".json");
    std::ofstream file{path};
    file << content;
    std::cout << "Generated: " << path << "\n";
}

int main(int argc, char** argv) {
    std::filesystem::path output_dir = "schemas";
    if (argc > 1) {
        output_dir = argv[1];
    }

    std::filesystem::create_directories(output_dir);

    write_schema(output_dir, "register", REGISTER_SCHEMA);
    write_schema(output_dir, "heartbeat", HEARTBEAT_SCHEMA);
    write_schema(output_dir, "screenshot", SCREENSHOT_SCHEMA);
    write_schema(output_dir, "task", TASK_SCHEMA);
    write_schema(output_dir, "policy_update", POLICY_UPDATE_SCHEMA);
    write_schema(output_dir, "event", EVENT_SCHEMA);

    std::cout << "Schema generation complete.\n";
    return 0;
}
```

**Step 3: Commit**

```bash
mkdir -p protocol/tools
git add protocol/include/ukk/protocol/schema/ protocol/tools/
git commit -m "feat(protocol): генератор json схем

```

---

## Task 7: Create Protocol Validator

**Files:**
- Create: `protocol/include/ukk/protocol/validation/validator.hpp`

**Step 1: Create validator.hpp**

```cpp
// protocol/include/ukk/protocol/validation/validator.hpp
#pragma once

#include "../header.hpp"
#include "../types.hpp"
#include "../concepts.hpp"
#include <span>
#include <expected>
#include <string>
#include <functional>

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
        char buf[16];
        std::snprintf(buf, sizeof(buf), "%08X", value);
        return buf;
    }

    [[nodiscard]] static std::string to_hex(std::uint8_t value) {
        char buf[8];
        std::snprintf(buf, sizeof(buf), "%02X", value);
        return buf;
    }
};

// Validation strategy interface (for extensibility)
class IValidationStrategy {
public:
    virtual ~IValidationStrategy() = default;
    virtual ValidationResult validate(std::span<const std::uint8_t> buffer) = 0;
};

// Strict validation (production)
class StrictValidationStrategy : public IValidationStrategy {
public:
    ValidationResult validate(std::span<const std::uint8_t> buffer) override {
        return Validator::validate(buffer);
    }
};

// Lenient validation (debugging)
class LenientValidationStrategy : public IValidationStrategy {
public:
    ValidationResult validate(std::span<const std::uint8_t> buffer) override {
        auto result = Validator::validate(buffer);
        // Log but don't fail on certain errors
        if (result.error == ValidationError::UNSUPPORTED_VERSION) {
            // Allow newer versions for forward compatibility
            result.error = ValidationError::OK;
        }
        return result;
    }
};

} // namespace ukk::protocol::validation
```

**Step 2: Commit**

```bash
git add protocol/include/ukk/protocol/validation/
git commit -m "feat(protocol): велидатор протокола

- добавил ValidationError enum
- добавил Validator класс с валидацией хэдеров/пейлоадов

```

---

## Task 8: Create C++ Code Generator

**Files:**
- Create: `protocol/tools/generate_cpp.cpp`

**Step 1: Create generate_cpp.cpp**

```cpp
// protocol/tools/generate_cpp.cpp
// Generates C++ boilerplate from protocol definitions

#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <filesystem>

struct MessageDef {
    std::string name;
    std::string type_value;
    bool is_agent_message;
    std::vector<std::pair<std::string, std::string>> fields;
};

void generate_msgpack_adaptor(std::ostream& os, const MessageDef& msg) {
    os << "// MessagePack adaptor for " << msg.name << "::Args\n";
    os << "template<>\n";
    os << "struct pack<ukk::protocol::messages::" << msg.name << "::Args> {\n";
    os << "    template<typename Stream>\n";
    os << "    msgpack::packer<Stream>& operator()(\n";
    os << "        msgpack::packer<Stream>& o,\n";
    os << "        const ukk::protocol::messages::" << msg.name << "::Args& v) const {\n";
    os << "        o.pack_map(" << msg.fields.size() << ");\n";
    for (const auto& [name, type] : msg.fields) {
        os << "        o.pack(\"" << name << "\");\n";
        os << "        o.pack(v." << name << ");\n";
    }
    os << "        return o;\n";
    os << "    }\n";
    os << "};\n\n";
}

void generate_dispatcher_case(std::ostream& os, const MessageDef& msg) {
    os << "        case MessageType::" << msg.type_value << ": {\n";
    os << "            auto result = serialization::deserialize<messages::"
       << msg.name << ">(payload);\n";
    os << "            if (result) {\n";
    os << "                return handler.template handle<messages::"
       << msg.name << ">(header, result.value);\n";
    os << "            }\n";
    os << "            return std::unexpected(result.error);\n";
    os << "        }\n";
}

int main() {
    std::vector<MessageDef> messages = {
        {"Register", "REGISTER", true, {
            {"machine_id", "UUID"},
            {"building_id", "std::string"},
            {"room_id", "std::string"},
            {"seat_id", "std::string"},
            {"agent_version", "std::string"},
            {"hw_fingerprint", "std::string"},
            {"os_version", "std::string"}
        }},
        {"Heartbeat", "HEARTBEAT", true, {
            {"cpu_pct", "std::uint8_t"},
            {"ram_pct", "std::uint8_t"},
            {"gpu_pct", "std::uint8_t"},
            {"disk_free_gb", "float"},
            {"active_policy", "std::string"},
            {"status", "AgentStatus"}
        }},
        {"Screenshot", "SCREENSHOT", true, {
            {"changed", "bool"},
            {"image_data", "std::optional<std::vector<std::uint8_t>>"},
            {"width", "std::uint32_t"},
            {"height", "std::uint32_t"},
            {"phash", "std::uint64_t"}
        }},
        {"Task", "TASK", false, {
            {"task_id", "UUID"},
            {"task_type", "TaskType"},
            {"payload", "TaskPayload"},
            {"priority", "Priority"},
            {"deadline", "Timestamp"}
        }},
        {"PolicyUpdate", "POLICY_UPDATE", false, {
            {"policy_id", "UUID"},
            {"profile", "PolicyProfile"},
            {"rules", "PolicyRules"},
            {"effective_from", "Timestamp"},
            {"effective_until", "std::optional<Timestamp>"}
        }},
    };

    std::filesystem::path output_dir = "generated";
    std::filesystem::create_directories(output_dir);

    // Generate dispatcher
    {
        std::ofstream file{output_dir / "dispatcher.gen.hpp"};
        file << "// AUTO-GENERATED - DO NOT EDIT\n";
        file << "#pragma once\n\n";
        file << "#include <ukk/protocol/messages.hpp>\n";
        file << "#include <ukk/protocol/serialization/msgpack.hpp>\n\n";
        file << "namespace ukk::protocol {\n\n";
        file << "template<typename Handler>\n";
        file << "std::expected<void, std::string> dispatch(\n";
        file << "    Handler& handler,\n";
        file << "    const MessageHeader& header,\n";
        file << "    std::span<const std::uint8_t> payload) {\n\n";
        file << "    switch (header.type) {\n";

        for (const auto& msg : messages) {
            generate_dispatcher_case(file, msg);
        }

        file << "        default:\n";
        file << "            return std::unexpected(\"Unknown message type\");\n";
        file << "    }\n";
        file << "}\n\n";
        file << "} // namespace ukk::protocol\n";

        std::cout << "Generated: " << (output_dir / "dispatcher.gen.hpp") << "\n";
    }

    // Generate msgpack adaptors
    {
        std::ofstream file{output_dir / "msgpack_adaptors.gen.hpp"};
        file << "// AUTO-GENERATED - DO NOT EDIT\n";
        file << "#pragma once\n\n";
        file << "#include <msgpack.hpp>\n";
        file << "#include <ukk/protocol/messages.hpp>\n\n";
        file << "namespace msgpack {\n";
        file << "MSGPACK_API_VERSION_NAMESPACE(MSGPACK_DEFAULT_API_NS) {\n";
        file << "namespace adaptor {\n\n";

        for (const auto& msg : messages) {
            generate_msgpack_adaptor(file, msg);
        }

        file << "} // namespace adaptor\n";
        file << "} // MSGPACK_API_VERSION_NAMESPACE\n";
        file << "} // namespace msgpack\n";

        std::cout << "Generated: " << (output_dir / "msgpack_adaptors.gen.hpp") << "\n";
    }

    std::cout << "Code generation complete.\n";
    return 0;
}
```

**Step 2: Commit**

```bash
git add protocol/tools/generate_cpp.cpp
git commit -m "feat(protocol): кодо генератор

- генератор switch-case из определения сообщений
- генератор msgpack адаптор для всех типов сообщений
- выхлоп в generated/ директорию

```

---

## Task 9: Create Protocol Documentation

**Files:**
- Create: `protocol/docs/PROTOCOL.md`
- Create: `protocol/docs/MESSAGE_REFERENCE.md`

**Step 1: Create PROTOCOL.md**

```markdown
# UKK Protocol Specification v1.0

## Overview

The UKK Protocol defines communication between agents running on managed workstations
and relay nodes within the school infrastructure. The protocol uses WebSocket transport
with binary MessagePack encoding for efficiency.

## Transport Layer

- **Agent <-> Relay**: WebSocket (ws://) within building LAN
- **Relay <-> Server**: WebSocket Secure (wss://) with mTLS

## Message Format

All messages consist of a fixed-size header followed by a variable-length payload.

### Header Structure (64 bytes, cache-aligned)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | magic | Protocol magic: `0x554B4B50` ("UKKP") |
| 4 | 4 | version | Protocol major version |
| 8 | 1 | type | Message type enum |
| 9 | 1 | flags | Reserved flags |
| 10 | 2 | reserved | Alignment padding |
| 12 | 4 | payload_size | Payload length in bytes |
| 16 | 16 | message_id | UUID v4 |
| 32 | 8 | timestamp | Unix epoch milliseconds |
| 40 | 24 | padding | Cache line padding |

### Message Types

#### Agent -> Relay (0x01 - 0x7F)

| Type | Value | Description |
|------|-------|-------------|
| REGISTER | 0x01 | Initial agent registration |
| HEARTBEAT | 0x02 | Periodic status update |
| SCREENSHOT | 0x03 | Screen capture data |
| TASK_RESULT | 0x04 | Task execution response |
| EVENT | 0x05 | Security/monitoring event |
| METRICS | 0x06 | Aggregated telemetry |
| PONG | 0x07 | Response to PING |

#### Relay -> Agent (0x80 - 0xFF)

| Type | Value | Description |
|------|-------|-------------|
| TASK | 0x81 | Command for execution |
| POLICY_UPDATE | 0x82 | Policy rules update |
| PING | 0x83 | Connection health check |
| AGENT_UPDATE | 0x84 | Binary update command |
| ACK | 0x85 | Message acknowledgment |
| ERROR | 0x86 | Error response |

## Payload Encoding

Payloads are encoded using MessagePack for binary efficiency.
JSON encoding is supported for debugging and logging.

### MessagePack Type Mapping

| C++ Type | MessagePack Type |
|----------|------------------|
| bool | bool |
| uint8_t - uint64_t | positive integer |
| int8_t - int64_t | integer |
| float/double | float |
| std::string | str |
| std::vector<T> | array |
| std::optional<T> | T or nil |
| UUID | bin (16 bytes) |
| Timestamp | int64 (epoch ms) |

## Validation

All messages MUST pass validation before processing:

1. **Magic Check**: Header magic must equal `0x554B4B50`
2. **Version Check**: Version must be <= current major version
3. **Type Check**: Message type must be known
4. **Size Check**: Payload size must be <= 30MB
5. **Schema Check**: Payload must conform to message schema

## Error Handling

Errors are reported via ERROR messages with codes:

| Code | Name | Description |
|------|------|-------------|
| 0x0000 | UNKNOWN | Unknown error |
| 0x0001 | INVALID_MESSAGE | Message structure invalid |
| 0x0002 | INVALID_PAYLOAD | Payload parse/validation failed |
| 0x0003 | UNSUPPORTED_VERSION | Protocol version not supported |
| 0x0004 | AUTHENTICATION_FAILED | Auth failure |
| 0x0005 | TASK_NOT_FOUND | Referenced task unknown |
| 0x0006 | TASK_EXECUTION_FAILED | Task failed to execute |
| 0x0007 | POLICY_INVALID | Policy rules invalid |
| 0x0008 | RESOURCE_UNAVAILABLE | Required resource missing |
| 0x0009 | RATE_LIMITED | Request rate exceeded |
| 0x00FF | INTERNAL_ERROR | Internal server error |

## Versioning

The protocol uses semantic versioning. Major version changes indicate
breaking changes. Minor/patch versions are backward compatible.

Current version: **1.0.0**
```

**Step 2: Create MESSAGE_REFERENCE.md**

```markdown
# UKK Protocol Message Reference

## REGISTER

Agent registration message sent on connection.

**Direction**: Agent -> Relay

**Payload**:
```json
{
  "machine_id": "uuid",
  "building_id": "string",
  "room_id": "string",
  "seat_id": "string",
  "agent_version": "semver",
  "hw_fingerprint": "sha256-hex",
  "os_version": "string"
}
```

**Required**: machine_id, building_id, room_id, agent_version, hw_fingerprint

---

## HEARTBEAT

Periodic activity confirmation with resource usage.

**Direction**: Agent -> Relay

**Interval**: Every 30 seconds

**Payload**:
```json
{
  "cpu_pct": 0-100,
  "ram_pct": 0-100,
  "gpu_pct": 0-100,
  "disk_free_gb": float,
  "active_policy": "policy-id",
  "status": "online|offline|error"
}
```

---

## SCREENSHOT

Screen capture data with perceptual hash deduplication.

**Direction**: Agent -> Relay

**Interval**: Per active policy (default 20s)

**Payload (changed=true)**:
```json
{
  "changed": true,
  "image_data": "base64-zstd-compressed",
  "width": 1920,
  "height": 1080,
  "phash": "hex-perceptual-hash"
}
```

**Payload (changed=false)**:
```json
{
  "changed": false
}
```

---

## TASK_RESULT

Response to TASK execution.

**Direction**: Agent -> Relay

**Payload**:
```json
{
  "task_id": "uuid",
  "status": "ok|error|timeout",
  "output": "string",
  "error_code": null|int,
  "execution_time_ms": int
}
```

---

## EVENT

Security or monitoring event.

**Direction**: Agent -> Relay

**Payload**:
```json
{
  "event_type": "USB_CONNECTED|P2P_DETECTED|...",
  "severity": "low|medium|high|critical",
  "details": { /* event-specific */ }
}
```

### Event Types

| Type | Details Schema |
|------|----------------|
| USB_CONNECTED | `{vendor_id, product_id, device_class, serial}` |
| P2P_DETECTED | `{local_ip, remote_ip, local_port, remote_port, protocol}` |
| TAMPER_DETECTED | `{expected_hash, actual_hash, file_path}` |
| PROCESS_KILLED | `{pid, process_name, reason}` |

---

## TASK

Command for agent execution.

**Direction**: Relay -> Agent

**Payload**:
```json
{
  "task_id": "uuid",
  "task_type": "SCREENSHOT|NET_POLICY|...",
  "payload": { /* task-specific */ },
  "priority": "normal|high",
  "deadline": "ISO8601"
}
```

### Task Types

| Type | Payload Schema |
|------|----------------|
| SCREENSHOT | `{quality: 1-100, force_capture: bool}` |
| NET_POLICY | `{whitelist: [], blacklist: [], whitelist_only: bool}` |
| SCREEN_CONTROL | `{action: "BLACKOUT|RESTORE|DPMS_OFF|DPMS_ON"}` |
| USB_POLICY | `{blocked_classes: [], block_mass_storage: bool}` |

---

## POLICY_UPDATE

Full policy update.

**Direction**: Relay -> Agent

**Payload**:
```json
{
  "policy_id": "uuid",
  "profile": "free|lesson|exam|lockdown",
  "rules": {
    "dns_whitelist": [],
    "dns_blacklist": [],
    "blocked_processes": [],
    "screenshot_interval_ms": 20000,
    "detect_p2p": false
  },
  "effective_from": "ISO8601",
  "effective_until": "ISO8601|null"
}
```

---

## PING / PONG

Connection health check.

**PING (Relay -> Agent)**:
```json
{
  "sequence": int,
  "sent_at": "ISO8601"
}
```

**PONG (Agent -> Relay)**:
```json
{
  "sequence": int,
  "ping_sent_at": "ISO8601",
  "pong_sent_at": "ISO8601"
}
```

---

## AGENT_UPDATE

Binary update command.

**Direction**: Relay -> Agent

**Payload**:
```json
{
  "new_version": "semver",
  "download_url": "https://...",
  "sha256_hash": "hex",
  "file_size": int,
  "force": bool,
  "restart_required": bool
}
```
```

**Step 3: Commit**

```bash
mkdir -p protocol/docs
git add protocol/docs/
git commit -m "docs(protocol): документация для протокола
```

---

## Task 10: Create Unit Tests

**Files:**
- Create: `protocol/tests/CMakeLists.txt`
- Create: `protocol/tests/test_types.cpp`
- Create: `protocol/tests/test_validation.cpp`
- Create: `protocol/tests/test_serialization.cpp`

**Step 1: Create tests/CMakeLists.txt**

```cmake
# protocol/tests/CMakeLists.txt
find_package(GTest REQUIRED)

add_executable(protocol_tests
    test_types.cpp
    test_validation.cpp
    test_serialization.cpp
)

target_link_libraries(protocol_tests
    PRIVATE
    ukk_protocol
    GTest::gtest
    GTest::gtest_main
)

target_compile_options(protocol_tests PRIVATE -Wall -Wextra)

include(GoogleTest)
gtest_discover_tests(protocol_tests)
```

**Step 2: Create test_types.cpp**

```cpp
// protocol/tests/test_types.cpp
#include <gtest/gtest.h>
#include <ukk/protocol/types.hpp>
#include <ukk/protocol/header.hpp>

using namespace ukk::protocol;

TEST(TypesTest, MessageTypeNames) {
    EXPECT_EQ(message_type_name(MessageType::REGISTER), "REGISTER");
    EXPECT_EQ(message_type_name(MessageType::HEARTBEAT), "HEARTBEAT");
    EXPECT_EQ(message_type_name(MessageType::TASK), "TASK");
}

TEST(TypesTest, MessageHeaderSize) {
    EXPECT_EQ(sizeof(MessageHeader), 64);
    EXPECT_EQ(alignof(MessageHeader), 64);
}

TEST(TypesTest, MessageHeaderValidation) {
    MessageHeader header{};
    header.magic = PROTOCOL_MAGIC;
    header.version = PROTOCOL_VERSION_MAJOR;
    header.payload_size = 100;

    EXPECT_TRUE(header.is_valid());

    header.magic = 0xDEADBEEF;
    EXPECT_FALSE(header.is_valid());
}

TEST(TypesTest, AgentVsRelayMessages) {
    MessageHeader agent_msg{};
    agent_msg.type = MessageType::REGISTER;
    EXPECT_TRUE(agent_msg.is_agent_message());
    EXPECT_FALSE(agent_msg.is_relay_message());

    MessageHeader relay_msg{};
    relay_msg.type = MessageType::TASK;
    EXPECT_FALSE(relay_msg.is_agent_message());
    EXPECT_TRUE(relay_msg.is_relay_message());
}
```

**Step 3: Create test_validation.cpp**

```cpp
// protocol/tests/test_validation.cpp
#include <gtest/gtest.h>
#include <ukk/protocol/validation/validator.hpp>
#include <ukk/protocol/header.hpp>
#include <vector>
#include <cstring>

using namespace ukk::protocol;
using namespace ukk::protocol::validation;

TEST(ValidationTest, BufferTooSmall) {
    std::vector<std::uint8_t> buffer(32); // Less than header size
    auto result = Validator::validate(buffer);

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::BUFFER_TOO_SMALL);
}

TEST(ValidationTest, InvalidMagic) {
    MessageHeader header{};
    header.magic = 0xDEADBEEF; // Wrong magic
    header.version = 1;
    header.type = MessageType::REGISTER;
    header.payload_size = 0;

    std::vector<std::uint8_t> buffer(sizeof(MessageHeader));
    std::memcpy(buffer.data(), &header, sizeof(header));

    auto result = Validator::validate(buffer);

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::INVALID_MAGIC);
}

TEST(ValidationTest, ValidMessage) {
    MessageHeader header{};
    header.magic = PROTOCOL_MAGIC;
    header.version = PROTOCOL_VERSION_MAJOR;
    header.type = MessageType::HEARTBEAT;
    header.payload_size = 0;

    std::vector<std::uint8_t> buffer(sizeof(MessageHeader));
    std::memcpy(buffer.data(), &header, sizeof(header));

    auto result = Validator::validate(buffer);

    EXPECT_TRUE(result.ok());
    EXPECT_EQ(result.header.type, MessageType::HEARTBEAT);
}

TEST(ValidationTest, PayloadTooLarge) {
    MessageHeader header{};
    header.magic = PROTOCOL_MAGIC;
    header.version = PROTOCOL_VERSION_MAJOR;
    header.type = MessageType::SCREENSHOT;
    header.payload_size = MAX_MESSAGE_SIZE + 1;

    std::vector<std::uint8_t> buffer(sizeof(MessageHeader));
    std::memcpy(buffer.data(), &header, sizeof(header));

    auto result = Validator::validate(buffer);

    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error, ValidationError::PAYLOAD_TOO_LARGE);
}
```

**Step 4: Create test_serialization.cpp**

```cpp
// protocol/tests/test_serialization.cpp
#include <gtest/gtest.h>
#include <ukk/protocol/serialization/msgpack.hpp>
#include <ukk/protocol/messages/heartbeat.hpp>

using namespace ukk::protocol;
using namespace ukk::protocol::messages;
using namespace ukk::protocol::serialization;

TEST(SerializationTest, HeartbeatRoundTrip) {
    Heartbeat::Args original{};
    original.cpu_pct = 42;
    original.ram_pct = 65;
    original.gpu_pct = 10;
    original.disk_free_gb = 128.5f;
    original.active_policy = "exam-policy-123";
    original.status = AgentStatus::ONLINE;

    auto serialized = serialize<Heartbeat>(original);
    ASSERT_TRUE(serialized.success);
    ASSERT_FALSE(serialized.data.empty());

    auto deserialized = deserialize<Heartbeat>(serialized.data);
    ASSERT_TRUE(deserialized.success);

    EXPECT_EQ(deserialized.value.cpu_pct, 42);
    EXPECT_EQ(deserialized.value.ram_pct, 65);
    EXPECT_EQ(deserialized.value.gpu_pct, 10);
    EXPECT_FLOAT_EQ(deserialized.value.disk_free_gb, 128.5f);
    EXPECT_EQ(deserialized.value.active_policy, "exam-policy-123");
}

TEST(SerializationTest, HeartbeatValidationFails) {
    Heartbeat::Args invalid{};
    invalid.cpu_pct = 150; // Invalid: > 100

    EXPECT_FALSE(Heartbeat::validate(invalid));

    auto result = serialize<Heartbeat>(invalid);
    EXPECT_FALSE(result.success);
}
```

**Step 5: Commit**

```bash
git add protocol/tests/
git commit -m "test(protocol): юнит тесты

---

## Task 11: Create All-In-One Include Header

**Files:**
- Create: `protocol/include/ukk/protocol/protocol.hpp`

**Step 1: Create protocol.hpp**

```cpp
// protocol/include/ukk/protocol/protocol.hpp
// All-in-one header for UKK Protocol
#pragma once

// Version and types
#include "version.hpp"
#include "types.hpp"
#include "concepts.hpp"
#include "header.hpp"

// Agent -> Relay messages
#include "messages/register.hpp"
#include "messages/heartbeat.hpp"
#include "messages/screenshot.hpp"
#include "messages/task_result.hpp"
#include "messages/event.hpp"
#include "messages/metrics.hpp"

// Relay -> Agent messages
#include "messages/task.hpp"
#include "messages/policy_update.hpp"
#include "messages/ping_pong.hpp"
#include "messages/agent_update.hpp"
#include "messages/ack_error.hpp"

// Serialization
#include "serialization/traits.hpp"
#include "serialization/msgpack.hpp"

// Validation
#include "validation/validator.hpp"

// Schema generation
#include "schema/generator.hpp"

namespace ukk::protocol {

// Convenience namespace imports
namespace msg = messages;
namespace ser = serialization;
namespace val = validation;
namespace sch = schema;

} // namespace ukk::protocol
```

**Step 2: Commit**

```bash
git add protocol/include/ukk/protocol/protocol.hpp
git commit -m "feat(protocol): добавил основной хэдер

- все части протокола в одном хэдере
- ники для каждого неймспейса
```

---

## Task 12: Generate All Artifacts and Final Commit

**Step 1: Create build script**

```bash
#!/bin/bash
# protocol/build.sh
set -e

cd "$(dirname "$0")"

mkdir -p build
cd build

cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Run tests
ctest --output-on-failure

# Generate schemas
./generate_schemas ../schemas

# Generate C++ code
./generate_cpp

echo "Build complete!"
```

**Step 2: Run final verification**

```bash
chmod +x protocol/build.sh
# Note: Actual build requires dependencies installed
```

**Step 3: Final commit**

```bash
git add protocol/build.sh
git commit -m "chore(protocol): итоговый комит + билды
```

---

## Summary of Deliverables

| Artifact | Location |
|----------|----------|
| C++ Headers | `protocol/include/ukk/protocol/` |
| JSON Schemas | `protocol/schemas/*.json` |
| Protocol Docs | `protocol/docs/PROTOCOL.md` |
| Message Reference | `protocol/docs/MESSAGE_REFERENCE.md` |
| Code Generators | `protocol/tools/` |
| Unit Tests | `protocol/tests/` |
| Build Script | `protocol/build.sh` |

## Dependencies

- C++20 compiler (GCC 11+ or Clang 13+)
- msgpack-c (MessagePack for C++)
- GoogleTest (for tests)
- CMake 3.20+
