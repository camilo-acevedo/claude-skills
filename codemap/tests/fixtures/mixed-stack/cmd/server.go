// Package server starts the HTTP listener.
package server

import "fmt"

const DefaultPort = 8080

type Config struct {
	Host string
	Port int
}

func Start(cfg Config) error {
	fmt.Println(cfg.Host)
	return nil
}

func (c *Config) Validate() bool {
	return c.Port > 0
}
