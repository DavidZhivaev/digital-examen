// protocol/include/ukk/protocol/protocol.hpp
// All-in-one include header for UKK Protocol
#pragma once

// Version and constants
#include <ukk/protocol/version.hpp>

// Core types
#include <ukk/protocol/types.hpp>
#include <ukk/protocol/concepts.hpp>
#include <ukk/protocol/header.hpp>

// Messages - Agent -> Relay
#include <ukk/protocol/messages/register.hpp>
#include <ukk/protocol/messages/heartbeat.hpp>
#include <ukk/protocol/messages/screenshot.hpp>
#include <ukk/protocol/messages/task_result.hpp>
#include <ukk/protocol/messages/event.hpp>
#include <ukk/protocol/messages/metrics.hpp>

// Messages - Relay -> Agent
#include <ukk/protocol/messages/task.hpp>
#include <ukk/protocol/messages/policy_update.hpp>
#include <ukk/protocol/messages/agent_update.hpp>

// Messages - Bidirectional
#include <ukk/protocol/messages/ping_pong.hpp>
#include <ukk/protocol/messages/ack_error.hpp>

// Serialization
#include <ukk/protocol/serialization/traits.hpp>
#include <ukk/protocol/serialization/msgpack.hpp>

// Schema generation
#include <ukk/protocol/schema/generator.hpp>

// Validation
#include <ukk/protocol/validation/validator.hpp>

namespace ukk::protocol {

// Convenience type aliases
using namespace messages;
using namespace serialization;
using namespace validation;

} // namespace ukk::protocol
