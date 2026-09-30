package alerts

import (
	"context"
	"database/sql"
	"math"
	"sync"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/mmcloughlin/geohash"
	"github.com/rs/zerolog/log"
)

type Charger struct {
	ID       int     `json:"id"`
	Network  string  `json:"network"`
	Geohash7 string  `json:"geohash7"`
	Lat      float64 `json:"lat"`
	Lon      float64 `json:"lon"`
	PowerKW  float64 `json:"power_kw"`
}

type ChargerIndex struct {
	mu          sync.RWMutex
	cells       map[string][]Charger // keyed by geohash5
	allChargers []Charger
}

func NewChargerIndex() *ChargerIndex {
	return &ChargerIndex{
		cells:       make(map[string][]Charger),
		allChargers: make([]Charger, 0),
	}
}

func (ci *ChargerIndex) AddCharger(c Charger) {
	ci.mu.Lock()
	defer ci.mu.Unlock()

	if len(c.Geohash7) < 5 {
		c.Geohash7 = geohash.EncodeWithPrecision(c.Lat, c.Lon, 7)
	}
	prefix := c.Geohash7[:5]

	ci.cells[prefix] = append(ci.cells[prefix], c)
	ci.allChargers = append(ci.allChargers, c)
}

func (ci *ChargerIndex) Count() int {
	ci.mu.RLock()
	defer ci.mu.RUnlock()
	return len(ci.allChargers)
}

// NearestCharger returns the closest charger and haversine distance in km.
func (ci *ChargerIndex) NearestCharger(lat, lon float64) (Charger, float64, bool) {
	ci.mu.RLock()
	defer ci.mu.RUnlock()

	if len(ci.allChargers) == 0 {
		return Charger{}, 0, false
	}

	cell5 := geohash.EncodeWithPrecision(lat, lon, 5)
	neighborCells := geohash.Neighbors(cell5)
	searchCells := append([]string{cell5}, neighborCells...)

	minDist := math.MaxFloat64
	var best Charger
	found := false

	for _, c5 := range searchCells {
		if chargers, ok := ci.cells[c5]; ok {
			for _, chg := range chargers {
				d := HaversineDistance(lat, lon, chg.Lat, chg.Lon)
				if d < minDist {
					minDist = d
					best = chg
					found = true
				}
			}
		}
	}

	if found {
		return best, minDist, true
	}

	// Fallback to all chargers if no chargers in immediate 9 geohash cells
	for _, chg := range ci.allChargers {
		d := HaversineDistance(lat, lon, chg.Lat, chg.Lon)
		if d < minDist {
			minDist = d
			best = chg
			found = true
		}
	}

	return best, minDist, found
}

// HaversineDistance computes great circle distance in km between two lat/lon coordinates
func HaversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const earthRadiusKm = 6371.0

	dLat := (lat2 - lat1) * math.Pi / 180.0
	dLon := (lon2 - lon1) * math.Pi / 180.0

	radLat1 := lat1 * math.Pi / 180.0
	radLat2 := lat2 * math.Pi / 180.0

	a := math.Sin(dLat/2.0)*math.Sin(dLat/2.0) +
		math.Cos(radLat1)*math.Cos(radLat2)*math.Sin(dLon/2.0)*math.Sin(dLon/2.0)
	c := 2.0 * math.Atan2(math.Sqrt(a), math.Sqrt(1.0-a))

	return earthRadiusKm * c
}

// LoadFromPostgres loads chargers from the Postgres database or seeds representative default chargers
func (ci *ChargerIndex) LoadFromPostgres(ctx context.Context, postgresURL string) error {
	if postgresURL == "" {
		ci.seedDefaultChargers()
		return nil
	}

	db, err := sql.Open("pgx", postgresURL)
	if err != nil {
		log.Warn().Err(err).Msg("Failed opening postgres connection for chargers, using defaults")
		ci.seedDefaultChargers()
		return nil
	}
	defer db.Close()

	rows, err := db.QueryContext(ctx, "SELECT charger_id, network, geohash7, lat, lon, power_kw FROM charger")
	if err != nil {
		log.Warn().Err(err).Msg("Failed querying chargers from postgres, using defaults")
		ci.seedDefaultChargers()
		return nil
	}
	defer rows.Close()

	loaded := 0
	for rows.Next() {
		var c Charger
		if err := rows.Scan(&c.ID, &c.Network, &c.Geohash7, &c.Lat, &c.Lon, &c.PowerKW); err == nil {
			ci.AddCharger(c)
			loaded++
		}
	}

	if loaded == 0 {
		log.Info().Msg("No chargers found in postgres charger table; seeding representative chargers")
		ci.seedDefaultChargers()
		// Try to insert seeded chargers into Postgres for future use
		go ci.persistSeededChargers(postgresURL)
	} else {
		log.Info().Int("count", loaded).Msg("Loaded chargers from postgres into geohash5 index")
	}

	return nil
}

func (ci *ChargerIndex) persistSeededChargers(postgresURL string) {
	db, err := sql.Open("pgx", postgresURL)
	if err != nil {
		return
	}
	defer db.Close()

	ci.mu.RLock()
	defer ci.mu.RUnlock()

	for _, chg := range ci.allChargers {
		_, _ = db.Exec(
			"INSERT INTO charger (charger_id, network, geohash7, lat, lon, power_kw) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (charger_id) DO NOTHING",
			chg.ID, chg.Network, chg.Geohash7, chg.Lat, chg.Lon, chg.PowerKW,
		)
	}
}

func (ci *ChargerIndex) seedDefaultChargers() {
	// Representative fast chargers across test hubs (NYC, LA, SF, Chicago, Dallas, Seattle, etc.)
	samples := []Charger{
		{ID: 1, Network: "Electrify America", Lat: 40.7128, Lon: -74.0060, PowerKW: 150.0},
		{ID: 2, Network: "EVgo", Lat: 40.7589, Lon: -73.9851, PowerKW: 100.0},
		{ID: 3, Network: "ChargePoint", Lat: 40.7831, Lon: -73.9712, PowerKW: 62.5},
		{ID: 4, Network: "Tesla Supercharger", Lat: 40.6782, Lon: -73.9442, PowerKW: 250.0},
		{ID: 5, Network: "Electrify America", Lat: 37.7749, Lon: -122.4194, PowerKW: 350.0},
		{ID: 6, Network: "EVgo", Lat: 37.7833, Lon: -122.4167, PowerKW: 100.0},
		{ID: 7, Network: "Tesla Supercharger", Lat: 34.0522, Lon: -118.2437, PowerKW: 250.0},
		{ID: 8, Network: "ChargePoint", Lat: 34.0689, Lon: -118.4452, PowerKW: 50.0},
		{ID: 9, Network: "Electrify America", Lat: 41.8781, Lon: -87.6298, PowerKW: 150.0},
		{ID: 10, Network: "EVgo", Lat: 32.7767, Lon: -96.7970, PowerKW: 100.0},
		{ID: 11, Network: "ChargePoint", Lat: 47.6062, Lon: -122.3321, PowerKW: 62.5},
		{ID: 12, Network: "Electrify America", Lat: 25.7617, Lon: -80.1918, PowerKW: 150.0},
	}

	for _, s := range samples {
		ci.AddCharger(s)
	}
	log.Info().Int("count", len(samples)).Msg("Seeded default chargers into geohash5 index")
}
