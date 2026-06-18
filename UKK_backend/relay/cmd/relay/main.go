package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"ukk-relay/internal/config"
	"ukk-relay/pkg/logger"
)

var Version = "dev"

func main() {
	var (
		configPath  = flag.String("config", "config.yaml", "Path to configuration file")
		showVersion = flag.Bool("version", false, "Show version and exit")
		buildingID  = flag.String("building-id", "", "Building ID (overrides config)")
		listenAddr  = flag.String("listen", "", "Agent listen address (overrides config)")
		centralURL  = flag.String("central-url", "", "Central server URL (overrides config)")
	)
	flag.Parse()

	if *showVersion {
		fmt.Printf("ukk-relay version %s\n", Version)
		os.Exit(0)
	}

	log, err := logger.New("info")
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer log.Sync()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	if *buildingID != "" {
		cfg.BuildingID = *buildingID
	}
	if *listenAddr != "" {
		cfg.AgentListenAddr = *listenAddr
	}
	if *centralURL != "" {
		cfg.CentralServerURL = *centralURL
	}

	if err := cfg.Validate(); err != nil {
		log.Fatalf("invalid configuration: %v", err)
	}

	log.Infow("starting ukk-relay",
		"version", Version,
		"building_id", cfg.BuildingID,
		"listen_addr", cfg.AgentListenAddr,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigCh
		log.Infow("received shutdown signal", "signal", sig)
		cancel()
	}()

	<-ctx.Done()
	log.Info("shutting down ukk-relay")
	log.Info("ukk-relay stopped")
}
