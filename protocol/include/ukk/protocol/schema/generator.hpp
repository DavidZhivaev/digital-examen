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
        if (!first_def_) definitions_ << ",\n";
        definitions_ << "\"" << name << "\": " << schema;
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
