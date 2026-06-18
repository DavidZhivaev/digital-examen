package protocol

import (
	"encoding/hex"
	"time"
)

const (
	ProtocolMagic   uint32 = 0x554B4B50
	ProtocolVersion uint32 = 1
	MaxPayloadSize  uint32 = 30 * 1024 * 1024
	HeaderSize      int    = 64
)

type MessageType uint8

const (
	MsgRegister   MessageType = 0x01
	MsgHeartbeat  MessageType = 0x02
	MsgScreenshot MessageType = 0x03
	MsgTaskResult MessageType = 0x04
	MsgEvent      MessageType = 0x05
	MsgMetrics    MessageType = 0x06
	MsgPong       MessageType = 0x07
)

const (
	MsgTask         MessageType = 0x81
	MsgPolicyUpdate MessageType = 0x82
	MsgPing         MessageType = 0x83
	MsgAgentUpdate  MessageType = 0x84
	MsgAck          MessageType = 0x85
	MsgError        MessageType = 0x86
)

func (t MessageType) IsAgentMessage() bool {
	return t < 0x80
}

func (t MessageType) IsRelayMessage() bool {
	return t >= 0x80
}

func (t MessageType) String() string {
	switch t {
	case MsgRegister:
		return "REGISTER"
	case MsgHeartbeat:
		return "HEARTBEAT"
	case MsgScreenshot:
		return "SCREENSHOT"
	case MsgTaskResult:
		return "TASK_RESULT"
	case MsgEvent:
		return "EVENT"
	case MsgMetrics:
		return "METRICS"
	case MsgPong:
		return "PONG"
	case MsgTask:
		return "TASK"
	case MsgPolicyUpdate:
		return "POLICY_UPDATE"
	case MsgPing:
		return "PING"
	case MsgAgentUpdate:
		return "AGENT_UPDATE"
	case MsgAck:
		return "ACK"
	case MsgError:
		return "ERROR"
	default:
		return "UNKNOWN"
	}
}

type UUID [16]byte

func (u UUID) String() string {
	return hex.EncodeToString(u[:4]) + "-" +
		hex.EncodeToString(u[4:6]) + "-" +
		hex.EncodeToString(u[6:8]) + "-" +
		hex.EncodeToString(u[8:10]) + "-" +
		hex.EncodeToString(u[10:])
}

func (u UUID) IsNil() bool {
	for _, b := range u {
		if b != 0 {
			return false
		}
	}
	return true
}

type Severity uint8

const (
	SeverityLow      Severity = 0
	SeverityMedium   Severity = 1
	SeverityHigh     Severity = 2
	SeverityCritical Severity = 3
)

type Priority uint8

const (
	PriorityNormal Priority = 0
	PriorityHigh   Priority = 1
)

type TaskStatus uint8

const (
	TaskStatusOK      TaskStatus = 0
	TaskStatusError   TaskStatus = 1
	TaskStatusTimeout TaskStatus = 2
)

type AgentStatus uint8

const (
	AgentStatusOnline  AgentStatus = 0
	AgentStatusOffline AgentStatus = 1
	AgentStatusError   AgentStatus = 2
)

type MessageHeader struct {
	Magic       uint32
	Version     uint32
	Type        MessageType
	Flags       uint8
	Reserved    uint16
	PayloadSize uint32
	MessageID   UUID
	Timestamp   int64
}

type Message struct {
	Header  MessageHeader
	Payload interface{}
}

func Now() int64 {
	return time.Now().UnixMilli()
}

func FromUnixMilli(ms int64) time.Time {
	return time.UnixMilli(ms)
}
