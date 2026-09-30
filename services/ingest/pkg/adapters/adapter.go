package adapters

import (
	"bytes"
	"errors"
	"fmt"
	"strings"
	"sync"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/valyala/fastjson"
)

var (
	ErrUnknownOEM      = errors.New("unknown OEM")
	ErrMalformedPayload = errors.New("malformed OEM payload")
)

type Adapter interface {
	OEM() string
	CanParse(raw []byte) bool
	Parse(raw []byte) (*canonical.Event, error)
}

type Registry struct {
	mu       sync.RWMutex
	adapters map[string]Adapter
}

func NewRegistry() *Registry {
	return &Registry{
		adapters: make(map[string]Adapter),
	}
}

func (r *Registry) Register(adapter Adapter) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.adapters[strings.ToLower(adapter.OEM())] = adapter
}

func (r *Registry) Get(oem string) (Adapter, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	a, ok := r.adapters[strings.ToLower(oem)]
	return a, ok
}

// DetectAndParse attempts to find the correct adapter via OEM hint or automatic detection, then parses to canonical.
func (r *Registry) DetectAndParse(oemHint string, raw []byte) (*canonical.Event, error) {
	if len(bytes.TrimSpace(raw)) == 0 {
		return nil, errors.New("empty payload")
	}

	// 1. If OEM hint is provided (e.g., from Kafka header or envelope), try that adapter first
	if oemHint != "" {
		if adapter, ok := r.Get(oemHint); ok {
			event, err := adapter.Parse(raw)
			if err == nil {
				return event, nil
			}
			return nil, fmt.Errorf("adapter %s failed to parse: %w", oemHint, err)
		}
		return nil, fmt.Errorf("%w: %s", ErrUnknownOEM, oemHint)
	}

	// 2. Try to extract "oem" field if it's JSON
	var p fastjson.Parser
	if v, err := p.ParseBytes(raw); err == nil {
		if oemVal := v.GetStringBytes("oem"); len(oemVal) > 0 {
			if adapter, ok := r.Get(string(oemVal)); ok {
				return adapter.Parse(raw)
			}
			return nil, fmt.Errorf("%w: %s", ErrUnknownOEM, string(oemVal))
		}
	}

	// 3. Fallback: Probe registered adapters via CanParse
	r.mu.RLock()
	defer r.mu.RUnlock()
	for _, adapter := range r.adapters {
		if adapter.CanParse(raw) {
			if event, err := adapter.Parse(raw); err == nil {
				return event, nil
			}
		}
	}

	return nil, fmt.Errorf("%w: unable to detect OEM format for payload", ErrUnknownOEM)
}

var DefaultRegistry = NewRegistry()

func init() {
	DefaultRegistry.Register(&VoltXAdapter{})
	DefaultRegistry.Register(&NordMotorsAdapter{})
	DefaultRegistry.Register(&AsiaDriveAdapter{})
	DefaultRegistry.Register(&EuroEVAdapter{})
	DefaultRegistry.Register(&ZephyrEVAdapter{})
}
