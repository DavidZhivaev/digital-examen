## Формат сообщений

Все сообщения состоят из хэдеров фиксированного размера за которыми идет значени длины.

### Хэдера(64 байта)

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

### Типы сообщений

#### Агент -> Реле (0x01 - 0x7F)

| Type | Value | Description |
|------|-------|-------------|
| REGISTER | 0x01 | Initial agent registration |
| HEARTBEAT | 0x02 | Periodic status update |
| SCREENSHOT | 0x03 | Screen capture data |
| TASK_RESULT | 0x04 | Task execution response |
| EVENT | 0x05 | Security/monitoring event |
| METRICS | 0x06 | Aggregated telemetry |
| PONG | 0x07 | Response to PING |

#### Реле -> Агет (0x80 - 0xFF)

| Type | Value | Description |
|------|-------|-------------|
| TASK | 0x81 | Command for execution |
| POLICY_UPDATE | 0x82 | Policy rules update |
| PING | 0x83 | Connection health check |
| AGENT_UPDATE | 0x84 | Binary update command |
| ACK | 0x85 | Message acknowledgment |
| ERROR | 0x86 | Error response |

## Энкод пэйлоада

Пэйлоад кодируется через MessagePack.
Для отладки и ведения журнала поддерживается кодировка в JSON.

### MessagePack типы

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

## Валидация

все сообщения ОБЯЗАТЕЛЬНО проходят валидацию перед отправкой:

1. **Magic Check**: Header magic must equal `0x554B4B50`
2. **Version Check**: Version must be <= current major version
3. **Type Check**: Message type must be known
4. **Size Check**: Payload size must be <= 30MB
5. **Schema Check**: Payload must conform to message schema

## Баги

Все баги проходят через формат ACL/ERROR сообщения

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

