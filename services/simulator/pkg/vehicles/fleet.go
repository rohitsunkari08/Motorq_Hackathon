package vehicles

import (
	"math"
	"math/rand"
	"sync"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/battery"
)

var OEMList = []string{"VoltX", "NordMotors", "AsiaDrive", "EuroEV", "ZephyrEV"}

type ModelInfo struct {
	Name         string
	CapacityKWh  float64
	MaxDCKW      float64
	MaxACKW      float64
	BaseEffKWhKM float64 // e.g. 0.18 kWh/km
}

var Models = []ModelInfo{
	{Name: "CityCompact", CapacityKWh: 40.0, MaxDCKW: 50.0, MaxACKW: 7.4, BaseEffKWhKM: 0.15},
	{Name: "FleetSedan", CapacityKWh: 60.0, MaxDCKW: 100.0, MaxACKW: 11.0, BaseEffKWhKM: 0.17},
	{Name: "DeliveryVan", CapacityKWh: 75.0, MaxDCKW: 120.0, MaxACKW: 11.0, BaseEffKWhKM: 0.24},
	{Name: "ExecutiveSUV", CapacityKWh: 85.0, MaxDCKW: 150.0, MaxACKW: 11.0, BaseEffKWhKM: 0.21},
	{Name: "HeavyHaul", CapacityKWh: 100.0, MaxDCKW: 150.0, MaxACKW: 22.0, BaseEffKWhKM: 0.28},
}

type ProfileType string

const (
	ProfileCommute  ProfileType = "COMMUTE"
	ProfileDelivery ProfileType = "DELIVERY"
	ProfileLongHaul ProfileType = "LONG_HAUL"
)

type VehicleState struct {
	Index       int
	VIN         string
	OEM         string
	Model       ModelInfo
	Profile     ProfileType
	Lat         float64
	Lon         float64
	SpeedKMH    float64
	SOCPct      float64
	OdoKM       float64
	BattTempC   float64
	Charging    int // 0 or 1
	ChargeKW    float64
	Seq         uint64
	EFC         float64
	DCFastShare float64
	HotExposure float64
	TrueSOH     float64
	DTCs        []string
	LastEvt     string
}

type Fleet struct {
	mu       sync.Mutex
	vehicles []*VehicleState
	rnd      *rand.Rand
}

func NewFleet(numVehicles int, seed int64) *Fleet {
	r := rand.New(rand.NewSource(seed))
	vehicles := make([]*VehicleState, numVehicles)

	profiles := []ProfileType{ProfileCommute, ProfileDelivery, ProfileLongHaul}

	for i := 0; i < numVehicles; i++ {
		oem := OEMList[i%len(OEMList)]
		model := Models[i%len(Models)]
		profile := profiles[i%len(profiles)]
		vin := GenerateVIN(oem, i+1)

		// Calibrated initial history
		yearsOfService := 0.5 + r.Float64()*3.0 // 0.5 to 3.5 years
		odoKM := yearsOfService * (12000.0 + r.Float64()*8000.0)
		efc := yearsOfService * 45.0 * (0.8 + r.Float64()*0.4)

		dcFastShare := 0.15 + r.Float64()*0.40 // 15% to 55% DC fast charging
		hotExposure := yearsOfService * (10.0 + r.Float64()*20.0)
		noise := (r.Float64() - 0.5) * 0.01

		trueSOH := battery.ComputeSoH(efc, dcFastShare, hotExposure, noise)

		// Base geo around metropolitan clusters (SF Bay, LA, Chicago, NY, Seattle)
		baseLats := []float64{37.77, 34.05, 41.87, 40.71, 47.60}
		baseLons := []float64{-122.41, -118.24, -87.62, -74.00, -122.33}
		cluster := i % len(baseLats)
		lat := baseLats[cluster] + (r.Float64()-0.5)*0.2
		lon := baseLons[cluster] + (r.Float64()-0.5)*0.2

		vehicles[i] = &VehicleState{
			Index:       i,
			VIN:         vin,
			OEM:         oem,
			Model:       model,
			Profile:     profile,
			Lat:         lat,
			Lon:         lon,
			SpeedKMH:    0.0,
			SOCPct:      50.0 + r.Float64()*45.0,
			OdoKM:       math.Round(odoKM*10) / 10,
			BattTempC:   22.0 + r.Float64()*8.0,
			Charging:    0,
			ChargeKW:    0.0,
			Seq:         1,
			EFC:         efc,
			DCFastShare: dcFastShare,
			HotExposure: hotExposure,
			TrueSOH:     trueSOH,
			DTCs:        []string{},
			LastEvt:     "NONE",
		}
	}

	return &Fleet{
		vehicles: vehicles,
		rnd:      r,
	}
}

func (f *Fleet) Size() int {
	return len(f.vehicles)
}

func (f *Fleet) GetVehicle(idx int) *VehicleState {
	return f.vehicles[idx]
}

// Step advances a vehicle state by dtSeconds of simulated time.
func (f *Fleet) Step(v *VehicleState, dtSeconds float64) {
	v.Seq++
	v.LastEvt = "NONE"
	v.DTCs = []string{}

	hours := dtSeconds / 3600.0

	// Check if battery is low -> transition to charging
	if v.SOCPct < 15.0 && v.Charging == 0 {
		v.Charging = 1
		v.SpeedKMH = 0.0
		// Choose AC or DC
		if f.rnd.Float64() < v.DCFastShare {
			v.ChargeKW = v.Model.MaxDCKW * (0.6 + f.rnd.Float64()*0.4)
		} else {
			v.ChargeKW = v.Model.MaxACKW
		}
		v.LastEvt = "PLUG_IN"
		return
	}

	// If charging and reached 90%+ -> unplug
	if v.Charging == 1 && v.SOCPct >= 90.0 {
		v.Charging = 0
		v.ChargeKW = 0.0
		v.LastEvt = "PLUG_OUT"
		return
	}

	if v.Charging == 1 {
		// Charging physics
		kwhAdded := v.ChargeKW * hours * 0.92 // 92% charger efficiency
		deltaSOC := (kwhAdded / (v.Model.CapacityKWh * v.TrueSOH)) * 100.0
		v.SOCPct = math.Min(100.0, v.SOCPct+deltaSOC)
		v.EFC += kwhAdded / v.Model.CapacityKWh

		// Batt temp warms up during charging
		if v.ChargeKW > 50.0 {
			v.BattTempC = math.Min(48.0, v.BattTempC+0.05*dtSeconds)
		} else {
			v.BattTempC = math.Max(25.0, v.BattTempC-0.01*dtSeconds)
		}
	} else {
		// Driving physics
		// Target speed according to profile
		switch v.Profile {
		case ProfileCommute:
			v.SpeedKMH = 30.0 + f.rnd.Float64()*50.0
		case ProfileDelivery:
			v.SpeedKMH = 20.0 + f.rnd.Float64()*40.0
		case ProfileLongHaul:
			v.SpeedKMH = 70.0 + f.rnd.Float64()*30.0
		}

		distKM := v.SpeedKMH * hours
		v.OdoKM += distKM

		// Subtle lat/lon wander
		v.Lat += (f.rnd.Float64() - 0.5) * 0.001
		v.Lon += (f.rnd.Float64() - 0.5) * 0.001

		// Energy consumption
		// kWh/km increases with higher speed and extreme temp
		tempFactor := 1.0
		if v.BattTempC < 10.0 {
			tempFactor = 1.2
		} else if v.BattTempC > 38.0 {
			tempFactor = 1.15
		}
		speedFactor := 1.0 + (v.SpeedKMH/120.0)*(v.SpeedKMH/120.0)*0.5

		kwhUsed := distKM * v.Model.BaseEffKWhKM * tempFactor * speedFactor
		deltaSOC := (kwhUsed / (v.Model.CapacityKWh * v.TrueSOH)) * 100.0
		v.SOCPct = math.Max(0.0, v.SOCPct-deltaSOC)

		// Occasional events
		roll := f.rnd.Float64()
		if roll < 0.002 {
			v.LastEvt = "HARSH_BRAKE"
			v.SpeedKMH = math.Max(0, v.SpeedKMH-25.0)
		} else if roll < 0.003 {
			v.DTCs = []string{"P0A1F"} // Battery management system fault
		}
	}

	v.SOCPct = math.Round(v.SOCPct*100) / 100
	v.SpeedKMH = math.Round(v.SpeedKMH*10) / 10
	v.BattTempC = math.Round(v.BattTempC*10) / 10
	v.OdoKM = math.Round(v.OdoKM*10) / 10
}
