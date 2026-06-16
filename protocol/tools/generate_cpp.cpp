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
        {"TaskResult", "TASK_RESULT", true, {
            {"task_id", "UUID"},
            {"status", "TaskStatus"},
            {"output", "std::string"},
            {"error_code", "std::optional<std::int32_t>"},
            {"execution_time_ms", "std::uint64_t"}
        }},
        {"Event", "EVENT", true, {
            {"event_type", "EventType"},
            {"severity", "Severity"},
            {"details", "EventDetails"}
        }},
        {"Metrics", "METRICS", true, {
            {"period_start", "Timestamp"},
            {"period_end", "Timestamp"},
            {"dns_summary", "std::vector<DnsQueryEntry>"},
            {"app_focus_timeline", "std::vector<AppFocusEntry>"},
            {"process_list", "std::vector<ProcessInfo>"},
            {"unique_domains", "std::uint32_t"},
            {"blocked_queries", "std::uint32_t"}
        }},
        {"Pong", "PONG", true, {
            {"sequence", "std::uint64_t"},
            {"ping_sent_at", "Timestamp"},
            {"pong_sent_at", "Timestamp"}
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
        {"Ping", "PING", false, {
            {"sequence", "std::uint64_t"},
            {"sent_at", "Timestamp"}
        }},
        {"AgentUpdate", "AGENT_UPDATE", false, {
            {"new_version", "std::string"},
            {"download_url", "std::string"},
            {"sha256_hash", "std::string"},
            {"file_size", "std::uint64_t"},
            {"force", "bool"},
            {"restart_required", "bool"}
        }},
        {"Ack", "ACK", false, {
            {"acked_message_id", "UUID"}
        }},
        {"Error", "ERROR", false, {
            {"reference_id", "UUID"},
            {"code", "ErrorCode"},
            {"message", "std::string"},
            {"details", "std::string"}
        }},
    };

    std::filesystem::path output_dir = "generated";
    std::filesystem::create_directories(output_dir);

    // Generate dispatcher
    {
        std::ofstream file{output_dir / "dispatcher.gen.hpp"};
        file << "// AUTO-GENERATED - DO NOT EDIT\n";
        file << "#pragma once\n\n";
        file << "#include <ukk/protocol/header.hpp>\n";
        file << "#include <ukk/protocol/types.hpp>\n";
        file << "#include <ukk/protocol/messages/register.hpp>\n";
        file << "#include <ukk/protocol/messages/heartbeat.hpp>\n";
        file << "#include <ukk/protocol/messages/screenshot.hpp>\n";
        file << "#include <ukk/protocol/messages/task_result.hpp>\n";
        file << "#include <ukk/protocol/messages/event.hpp>\n";
        file << "#include <ukk/protocol/messages/metrics.hpp>\n";
        file << "#include <ukk/protocol/messages/task.hpp>\n";
        file << "#include <ukk/protocol/messages/policy_update.hpp>\n";
        file << "#include <ukk/protocol/messages/ping_pong.hpp>\n";
        file << "#include <ukk/protocol/messages/agent_update.hpp>\n";
        file << "#include <ukk/protocol/messages/ack_error.hpp>\n";
        file << "#include <ukk/protocol/serialization/msgpack.hpp>\n\n";
        file << "#include <expected>\n";
        file << "#include <span>\n\n";
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
        file << "#include <ukk/protocol/messages/register.hpp>\n";
        file << "#include <ukk/protocol/messages/heartbeat.hpp>\n";
        file << "#include <ukk/protocol/messages/screenshot.hpp>\n";
        file << "#include <ukk/protocol/messages/task_result.hpp>\n";
        file << "#include <ukk/protocol/messages/event.hpp>\n";
        file << "#include <ukk/protocol/messages/metrics.hpp>\n";
        file << "#include <ukk/protocol/messages/task.hpp>\n";
        file << "#include <ukk/protocol/messages/policy_update.hpp>\n";
        file << "#include <ukk/protocol/messages/ping_pong.hpp>\n";
        file << "#include <ukk/protocol/messages/agent_update.hpp>\n";
        file << "#include <ukk/protocol/messages/ack_error.hpp>\n\n";
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
