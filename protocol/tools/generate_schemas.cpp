// protocol/tools/generate_schemas.cpp
#include <fstream>
#include <iostream>
#include <filesystem>
#include <string_view>

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
