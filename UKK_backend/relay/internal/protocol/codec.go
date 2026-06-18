package protocol

import (
	"encoding/binary"
	"errors"
	"fmt"
)

var (
	ErrInvalidMagic       = errors.New("invalid protocol magic")
	ErrUnsupportedVersion = errors.New("unsupported protocol version")
	ErrPayloadTooLarge    = errors.New("payload size exceeds maximum")
	ErrInvalidHeaderSize  = errors.New("invalid header size")
	ErrUnknownMessageType = errors.New("unknown message type")
)

type Codec struct{}

func NewCodec() *Codec {
	return &Codec{}
}

func (c *Codec) DecodeHeader(data []byte) (*MessageHeader, error) {
	if len(data) < HeaderSize {
		return nil, ErrInvalidHeaderSize
	}

	h := &MessageHeader{
		Magic:       binary.BigEndian.Uint32(data[0:4]),
		Version:     binary.BigEndian.Uint32(data[4:8]),
		Type:        MessageType(data[8]),
		Flags:       data[9],
		Reserved:    binary.BigEndian.Uint16(data[10:12]),
		PayloadSize: binary.BigEndian.Uint32(data[12:16]),
		Timestamp:   int64(binary.BigEndian.Uint64(data[32:40])),
	}

	copy(h.MessageID[:], data[16:32])

	return h, nil
}

func (c *Codec) EncodeHeader(h *MessageHeader) []byte {
	data := make([]byte, HeaderSize)

	binary.BigEndian.PutUint32(data[0:4], h.Magic)
	binary.BigEndian.PutUint32(data[4:8], h.Version)
	data[8] = byte(h.Type)
	data[9] = h.Flags
	binary.BigEndian.PutUint16(data[10:12], h.Reserved)
	binary.BigEndian.PutUint32(data[12:16], h.PayloadSize)
	copy(data[16:32], h.MessageID[:])
	binary.BigEndian.PutUint64(data[32:40], uint64(h.Timestamp))

	return data
}

func (c *Codec) ValidateHeader(h *MessageHeader) error {
	if h.Magic != ProtocolMagic {
		return fmt.Errorf("%w: got 0x%X, expected 0x%X", ErrInvalidMagic, h.Magic, ProtocolMagic)
	}
	if h.Version > ProtocolVersion {
		return fmt.Errorf("%w: got %d, max supported %d", ErrUnsupportedVersion, h.Version, ProtocolVersion)
	}
	if h.PayloadSize > MaxPayloadSize {
		return fmt.Errorf("%w: got %d, max %d", ErrPayloadTooLarge, h.PayloadSize, MaxPayloadSize)
	}
	return nil
}
