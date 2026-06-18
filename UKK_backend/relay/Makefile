.PHONY: build build-linux test lint clean run help

# Build variables
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME := $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')
LDFLAGS := -ldflags "-X main.Version=$(VERSION) -X main.Commit=$(COMMIT) -X main.BuildTime=$(BUILD_TIME) -s -w"

# Output directory
BIN_DIR := bin

# Default target
all: build

## build: Build the relay binary for current platform
build:
	@echo "Building ukk-relay $(VERSION)..."
	@mkdir -p $(BIN_DIR)
	CGO_ENABLED=0 go build $(LDFLAGS) -o $(BIN_DIR)/ukk-relay ./cmd/relay
	@echo "Built: $(BIN_DIR)/ukk-relay"

## build-linux: Cross-compile for Linux amd64
build-linux:
	@echo "Building ukk-relay $(VERSION) for linux/amd64..."
	@mkdir -p $(BIN_DIR)
	GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build $(LDFLAGS) -o $(BIN_DIR)/ukk-relay-linux-amd64 ./cmd/relay
	@echo "Built: $(BIN_DIR)/ukk-relay-linux-amd64"

## build-all: Build for all target platforms
build-all: build build-linux

## test: Run all tests with race detection
test:
	@echo "Running tests..."
	go test -race -cover -coverprofile=coverage.out ./...
	@echo "Coverage report: coverage.out"

## test-verbose: Run tests with verbose output
test-verbose:
	go test -race -cover -v ./...

## lint: Run golangci-lint
lint:
	@echo "Running linter..."
	@which golangci-lint > /dev/null || (echo "golangci-lint not installed" && exit 1)
	golangci-lint run ./...

## fmt: Format code
fmt:
	@echo "Formatting code..."
	go fmt ./...
	goimports -w .

## vet: Run go vet
vet:
	go vet ./...

## tidy: Tidy go modules
tidy:
	go mod tidy

## clean: Remove build artifacts
clean:
	@echo "Cleaning..."
	rm -rf $(BIN_DIR)
	rm -f coverage.out

## run: Build and run with default config
run: build
	./$(BIN_DIR)/ukk-relay --config config.yaml

## deps: Download dependencies
deps:
	go mod download

## help: Show this help
help:
	@echo "ukk-relay Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^## ' Makefile | sed 's/## /  /'
