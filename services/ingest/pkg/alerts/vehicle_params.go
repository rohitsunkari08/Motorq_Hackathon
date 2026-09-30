package alerts

import (
	"context"
	"database/sql"
	"strconv"
	"sync"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
)

type VehicleParams struct {
	CapacityKWH float64 `json:"capacity_kwh"`
	SOH         float64 `json:"soh"`
	EffKWHPerKM float64 `json:"eff_kwh_per_km"`
}

type VehicleParamsStore struct {
	mu     sync.RWMutex
	params map[string]VehicleParams
	rdb    *redis.Client
}

func NewVehicleParamsStore(rdb *redis.Client) *VehicleParamsStore {
	return &VehicleParamsStore{
		params: make(map[string]VehicleParams),
		rdb:    rdb,
	}
}

func (s *VehicleParamsStore) Set(vin string, p VehicleParams) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.params[vin] = p
}

func (s *VehicleParamsStore) Get(ctx context.Context, vin string) VehicleParams {
	s.mu.RLock()
	p, exists := s.params[vin]
	s.mu.RUnlock()

	if exists {
		return p
	}

	// Try querying Redis if available
	if s.rdb != nil {
		key := "veh:params:" + vin
		res, err := s.rdb.HGetAll(ctx, key).Result()
		if err == nil && len(res) > 0 {
			capVal, _ := strconv.ParseFloat(res["capacity"], 64)
			sohVal, _ := strconv.ParseFloat(res["soh"], 64)
			effVal, _ := strconv.ParseFloat(res["eff"], 64)
			if capVal > 0 {
				if sohVal <= 0 {
					sohVal = 0.98
				}
				if effVal <= 0 {
					effVal = 0.18
				}
				p = VehicleParams{
					CapacityKWH: capVal,
					SOH:         sohVal,
					EffKWHPerKM: effVal,
				}
				s.Set(vin, p)
				return p
			}
		}
	}

	// Default fallback specs
	defaultParams := VehicleParams{
		CapacityKWH: 75.0,
		SOH:         0.98,
		EffKWHPerKM: 0.18,
	}
	return defaultParams
}

func (s *VehicleParamsStore) LoadFromPostgres(ctx context.Context, postgresURL string) error {
	if postgresURL == "" {
		return nil
	}

	db, err := sql.Open("pgx", postgresURL)
	if err != nil {
		return err
	}
	defer db.Close()

	query := `
		SELECT v.vin, vm.battery_kwh, 0.98 AS soh, 
		       CASE WHEN vm.rated_range_km > 0 THEN vm.battery_kwh / vm.rated_range_km ELSE 0.18 END AS eff
		FROM vehicle v
		JOIN vehicle_model vm ON v.model_id = vm.model_id
	`
	rows, err := db.QueryContext(ctx, query)
	if err != nil {
		log.Warn().Err(err).Msg("Failed querying vehicle params from postgres")
		return err
	}
	defer rows.Close()

	loaded := 0
	for rows.Next() {
		var vin string
		var p VehicleParams
		if err := rows.Scan(&vin, &p.CapacityKWH, &p.SOH, &p.EffKWHPerKM); err == nil {
			s.Set(vin, p)
			loaded++
		}
	}

	log.Info().Int("count", loaded).Msg("Loaded vehicle params from postgres")
	return nil
}
