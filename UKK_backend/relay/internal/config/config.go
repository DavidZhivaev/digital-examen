package config

import (
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	BuildingID          string        `yaml:"building_id"`
	AgentListenAddr     string        `yaml:"agent_listen_addr"`
	CentralServerURL    string        `yaml:"central_server_url"`
	CentralAuthToken    string        `yaml:"central_auth_token"`
	HeartbeatTimeout    time.Duration `yaml:"heartbeat_timeout"`
	PingInterval        time.Duration `yaml:"ping_interval"`
	ShutdownTimeout     time.Duration `yaml:"shutdown_timeout"`
	LogLevel            string        `yaml:"log_level"`
	MetricsAddr         string        `yaml:"metrics_addr"`
	MaxAgents           int           `yaml:"max_agents"`
	ReconnectBackoffMax time.Duration `yaml:"reconnect_backoff_max"`
}

func DefaultConfig() *Config {
	return &Config{
		AgentListenAddr:     ":8765",
		HeartbeatTimeout:    90 * time.Second,
		PingInterval:        30 * time.Second,
		ShutdownTimeout:     30 * time.Second,
		LogLevel:            "info",
		MetricsAddr:         ":9090",
		MaxAgents:           150,
		ReconnectBackoffMax: 60 * time.Second,
	}
}

func Load(path string) (*Config, error) {
	cfg := DefaultConfig()

	data, err := os.ReadFile(path)
	if err != nil {
		if !os.IsNotExist(err) {
			return nil, fmt.Errorf("reading config file: %w", err)
		}
	} else {
		if err := yaml.Unmarshal(data, cfg); err != nil {
			return nil, fmt.Errorf("parsing config file: %w", err)
		}
	}

	cfg.applyEnvOverrides()

	return cfg, nil
}

func (c *Config) applyEnvOverrides() {
	if v := os.Getenv("UKK_RELAY_BUILDING_ID"); v != "" {
		c.BuildingID = v
	}
	if v := os.Getenv("UKK_RELAY_AGENT_LISTEN_ADDR"); v != "" {
		c.AgentListenAddr = v
	}
	if v := os.Getenv("UKK_RELAY_CENTRAL_SERVER_URL"); v != "" {
		c.CentralServerURL = v
	}
	if v := os.Getenv("UKK_RELAY_CENTRAL_AUTH_TOKEN"); v != "" {
		c.CentralAuthToken = v
	}
	if v := os.Getenv("UKK_RELAY_LOG_LEVEL"); v != "" {
		c.LogLevel = v
	}
	if v := os.Getenv("UKK_RELAY_METRICS_ADDR"); v != "" {
		c.MetricsAddr = v
	}
}

func (c *Config) Validate() error {
	var errs []string

	if c.BuildingID == "" {
		errs = append(errs, "building_id is required")
	}
	if c.AgentListenAddr == "" {
		errs = append(errs, "agent_listen_addr is required")
	}
	if c.CentralServerURL == "" {
		errs = append(errs, "central_server_url is required")
	}
	if c.CentralAuthToken == "" {
		errs = append(errs, "central_auth_token is required")
	}
	if c.HeartbeatTimeout <= 0 {
		errs = append(errs, "heartbeat_timeout must be positive")
	}
	if c.PingInterval <= 0 {
		errs = append(errs, "ping_interval must be positive")
	}
	if c.PingInterval >= c.HeartbeatTimeout {
		errs = append(errs, "ping_interval must be less than heartbeat_timeout")
	}
	if c.MaxAgents <= 0 {
		errs = append(errs, "max_agents must be positive")
	}

	validLogLevels := map[string]bool{"debug": true, "info": true, "warn": true, "error": true}
	if !validLogLevels[strings.ToLower(c.LogLevel)] {
		errs = append(errs, "log_level must be one of: debug, info, warn, error")
	}

	if len(errs) > 0 {
		return errors.New(strings.Join(errs, "; "))
	}
	return nil
}
