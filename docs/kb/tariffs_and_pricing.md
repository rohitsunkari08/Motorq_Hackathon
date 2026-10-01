# Time-of-Use Tariffs and Energy Cost Optimization

## Tariff Structures

### Time-of-Use (ToU) Windows
Commercial EV fleets face structured time-of-use tariffs divided into three standard tiers:
1. **Super Off-Peak / Off-Peak (22:00 - 06:00)**: Lowest energy cost (typically $0.05 to $0.09 per kWh). Ideal for depot overnight charging.
2. **Mid-Peak / Standard (06:00 - 16:00, 21:00 - 22:00)**: Moderate cost ($0.12 to $0.18 per kWh). Acceptable for scheduled daytime top-ups.
3. **On-Peak (16:00 - 21:00)**: Highest energy cost ($0.28 to $0.45 per kWh) plus potential peak demand penalties. Avoid charging during this window unless vehicle is in mission-critical alert state.

### Peak Demand Charges
- Commercial electric utilities assess peak demand charges based on the maximum 15-minute average power draw (kW) recorded within a billing cycle.
- Staggering vehicle plug-in start times prevents synchronized coincident demand spikes at the depot transformer.

## Optimization Strategy
- Dynamic Programming (DP) optimizes charging schedules across 15-minute discrete time steps.
- The objective function minimizes:
  `Total Cost = Energy Cost(slot) + lambda * Degradation_Penalty(power)`
- By shifting charging from on-peak to super off-peak and smoothing power delivery, fleet energy costs drop by 15% to 30% compared to uncoordinated charge-on-arrival policies.
