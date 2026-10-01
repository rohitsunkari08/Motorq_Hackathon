# Battery Care and Degradation Management Guide

## Overview
Fleet lithium-ion traction batteries degrade through two primary mechanisms: calendar aging and cyclic aging. Maintaining battery State of Health (SoH) over multi-year commercial fleet operations requires active management of depth-of-discharge, high C-rate fast charging exposure, and cell temperature.

## Key Degradation Drivers

### 1. High DC Fast-Charging (C-Rates > 1.0C)
- Charging above 50 kW (and especially > 100 kW) induces high local current densities within the anode, accelerating solid electrolyte interphase (SEI) growth and increasing lithium plating risks.
- Fleet evidence shows vehicles exposed to >50% DC fast charging degrade at approximately 3.0% per year, compared to 1.5% per year for vehicles predominantly utilizing AC Level 2 charging (7–11 kW).
- Guideline: Prioritize AC charging whenever dwell time allows (e.g. overnight 6-8 hour slots). Limit DC fast charging to necessary en-route top-ups.

### 2. High State of Charge (SoC) Dwell and Depth of Discharge (DoD)
- Holding battery state at 100% SoC under elevated temperatures maximizes electrochemical stress.
- Deep discharge below 10% SoC causes mechanical stress on electrode particles.
- Guideline: Keep standard operational SoC in the 20% to 80% window. Target 100% SoC only immediately prior to scheduled departure.

### 3. Temperature Extremes and Thermal Stress
- Sustained cell temperatures exceeding 45°C–50°C during charging dramatically accelerate parasitic chemical reactions.
- Low temperature (<0°C) charging induces lithium plating unless cells are preheated.
- Guideline: If battery temperature exceeds 50°C, the system issues a THERMAL alert and charging rate must be derated by 50% or paused until thermal equilibrium is restored.

## Best Practice Charging Policy
1. Schedule charging so the vehicle reaches the target SoC within 30 minutes of scheduled departure.
2. Use dynamic programming to schedule charge sessions during lowest tariff slots while minimizing high-power peaks.
3. Reserve high-power DC fast charging for urgent unscheduled missions or when battery buffer falls below critical safety thresholds.
