# EV Diagnostic Trouble Code (DTC) Guide

## Diagnostic Trouble Code Structure
EV Diagnostic Trouble Codes conform to standard SAE J2019 / ISO 15031 formats:
`^[PCBU][0-3][0-9A-F]{3}$`
- **P**: Powertrain (Engine, Transmission, Electric Drive, High Voltage Battery)
- **C**: Chassis (Brakes, Steering, Suspension)
- **B**: Body (HVAC, Lighting, Airbags, Doors)
- **U**: Network / Communications (CAN Bus, LIN, Ethernet)

## Common High-Voltage EV Diagnostic Trouble Codes

### 1. `P0A80` - Replace Hybrid/EV Battery Pack
- **Severity**: High / Critical
- **Symptoms**: Significant cell imbalance (>80mV voltage delta between lowest and highest series cell block), reduced power output, turtle mode.
- **Recommended Action**: Restrict vehicle to depot transfer only. Schedule battery pack balancing or module module replacement. Do not fast charge.

### 2. `P0A7F` - Hybrid/EV Battery Pack Deterioration
- **Severity**: High
- **Symptoms**: Accelerated capacity fade, internal resistance increase beyond 25% of nominal, low SoH.
- **Recommended Action**: Perform full capacity test session, review degradation trends vs fleet peers, assess warranty claim threshold (typically 70% SoH within 8 years).

### 3. `P0A1F` - Battery Energy Control Module (BECM)
- **Severity**: Critical
- **Symptoms**: Intermittent communication loss with BMS slave boards, inaccurate SoC reporting, failure to preheat or cool pack.
- **Recommended Action**: Inspect low-voltage harness connection to BMS, check 12V auxiliary battery voltage, flash firmware update if known OEM bulletin applies.

### 4. `P0A0D` - High Voltage System Inter-lock Circuit High
- **Severity**: Critical
- **Symptoms**: Vehicle will not transition to READY mode; contactors open immediately on key cycle.
- **Recommended Action**: Verify high-voltage service disconnect plug is fully seated. Inspect HV safety interlock loop for physical damage or open circuit.

### 5. `P0AC0` - Hybrid/EV Battery Pack Current Sensor Circuit
- **Severity**: Medium / High
- **Symptoms**: Hall-effect current transducer out of calibration, erratic ampere draw readings, false overcurrent trip.
- **Recommended Action**: Calibrate zero-ampere offset with contactors open. Replace current sensor if drift exceeds +/- 2.5A.

### 6. `U0100` - Lost Communication with ECM/PCM
- **Severity**: High
- **Symptoms**: Dashboard warning lamps illuminated, fail-safe torque derating.
- **Recommended Action**: Check CAN bus termination resistance (nominal 60 ohms between CAN-H and CAN-L), inspect wiring harness for ground faults.
