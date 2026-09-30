# references.md — Verified sources for the Solution Document (put in docs/references.md)
Retrieved 30 Sep 2026. Before the final PDF: open each link once, confirm the figure, and cite the primary source where noted. Never add a number that is not here or not verified by you.

## A. Web sources verified in research (use in §2.2 evidence table)
| # | Source | What it shows (paraphrase) | Confidence | Use |
|---|---|---|---|---|
| R1 | Geotab EV battery degradation study (3rd study), published 14 Jan 2026. Coverage: zemo.org.uk news (https://www.zemo.org.uk/news-events/news,new-study-shows-that-ev-battery-health-remains-robust-even-with-fast-chargi_4813.htm), FreightWaves (https://www.freightwaves.com/news/ev-battery-degradation-geotab-study-2026), electrive (https://www.electrive.com/2026/01/14/geotab-analysis-impact-of-fast-charging-on-battery-capacity-loss), InsideEVs (https://insideevs.com/news/784160/leading-cause-ev-battery-degradation/) | >22,700 EVs, 21 models. Average degradation 2.3%/yr (1.8% in 2024 study). Heavy DC fast charging above 100 kW ~3.0%/yr vs ~1.5%/yr for AC/lower-power. Charging behaviour is the dominant factor. | High (large real telematics; read Geotab primary page too) | Problem evidence; **simulator calibration** (mean ~2.3%/yr, low-DC group ~1.5%, heavy >100 kW group ~3.0%) |
| R1b | evchargingstations.com summary of Geotab (https://evchargingstations.com/chargingnews/frequent-fast-charging-accelerates-ev-battery-degradation/) | Split by DC-fast session share: <12% of sessions ~1.5%/yr, >12% ~2.5%/yr | Medium (secondary summary; confirm on Geotab page) | Extra calibration point / feature `dc_fast_share` |
| R2 | Rivian telematics study, arXiv:2503.03167 (https://arxiv.org/abs/2503.03167) | 72% of home charging started at plug-in regardless of TOU tariffs; <26% of sessions actively scheduled; optimising within existing plug windows could save avg ~$140/yr per EV and cut charging emissions by up to 28% | High (peer-style preprint, real data; home charging, not fleets) | Pain + baseline = "charge on arrival"; supports our savings target |
| R3 | RFF Working Paper 25-22, "Impact of Electric Tariffs on Medium- and Heavy-Duty Vehicle Charging Costs and Loads" (https://www.rff.org/publications/working-papers/impact-of-electric-tariffs-on-medium-and-heavy-duty-vehicle-charging-costs-and-loads/) | Models real fleet duty cycles against thousands of NREL URDB rates; managed charging gives substantial fleet cost savings and lowers peak demand | High (research institute) | Fleet-specific evidence for managed charging |
| R4 | Brattle Group / EnergyHub "Demonstrating the Full Value of Managed EV Charging", via chargedevs (https://chargedevs.com/?p=590933) | Active managed charging: peaks cut up to 50%, up to $400/EV/yr saved, ~95% of charging off-peak, all plugged-in EVs with enough time reached target SoC | Medium (vendor-commissioned, secondary coverage) | Upper-range benchmark; customer-need-met constraint (our DP enforces target SoC) |
| R5 | CleanTechnica (2021) "Cost-Effectively Transitioning Fleets To EVs Without Disrupting Operations" (https://cleantechnica.com/2021/02/11/cost-effectively-transitioning-fleets-to-evs-without-disrupting-operations/) | States managed charging on TOU rates can cut fleet electricity bills ~30-50% on average; demand-charge avoidance | Low-Medium (older, secondary; do not headline) | Context only; our own target (15-30% energy-cost cut) is deliberately more conservative |

## B. From the hackathon problem statement (cite as "Hackathon Problem Statement, Talenciaglobal")
~25 GB/hour per connected car (McKinsey/S&P estimate); connected cars ~95% of new sales by 2030; AWS IoT FleetWise closed to new customers April 2026 (lock-in risk); UNECE R155/R156 cybersecurity and software-update regulation; India DPDP Rules notified Nov 2025; GDPR in Europe; Motorq figures (25+ brands, 500K+ vehicles/day, 250B+ signals/month, Fuse April 2026). **Verify Motorq Fuse capabilities on Motorq's public site before comparing to it.**

## C. Standard technical references (stable, well-known; confirm link/DOI when adding)
- Dwork & Roth (2014), *The Algorithmic Foundations of Differential Privacy*, Foundations and Trends in TCS. (Laplace mechanism, epsilon, sensitivity)
- Bloom, B. H. (1970), "Space/time trade-offs in hash coding with allowable errors", CACM. (dedupe filter)
- Hart, Nilsson, Raphael (1968), "A formal basis for the heuristic determination of minimum cost paths", IEEE Trans. SSC. (A*); Dijkstra (1959).
- Kreps, Narkhede, Rao (2011), "Kafka: a distributed messaging system for log processing", NetDB. (partitioned log, replay)
- Chen & Guestrin (2016), "XGBoost: A scalable tree boosting system", KDD. 
- Lewis et al. (2020), "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS. (RAG)
- Kleppmann (2017), *Designing Data-Intensive Applications*, O'Reilly. (idempotency, CAP/PACELC framing, CQRS, delivery semantics)
- Abadi (2012), "Consistency tradeoffs in modern distributed database system design", IEEE Computer. (PACELC)
- ISO 3779 (VIN structure) and 49 CFR Part 565 (VIN check digit); SAE J1979 / ISO 15031 (OBD-II diagnostic trouble codes).
- OWASP Top 10 and OWASP API Security Top 10; Microsoft STRIDE threat modelling.
- ClickHouse, Redpanda, PostgreSQL/pgvector official documentation (cite versions used).
- Regulation: Digital Personal Data Protection Act 2023 (India) and DPDP Rules (Nov 2025); GDPR Art. 5, 17, 25; UNECE R155/R156.

## D. Ready-to-use §2.2 table rows (edit wording, keep figures exact)
| Evidence / Assumption | Source or Method | What It Shows | Confidence |
|---|---|---|---|
| Heavy high-power DC fast charging roughly doubles annual battery degradation | R1 Geotab 2026 (22,700 EVs) | ~3.0%/yr vs ~1.5%/yr; charging behaviour is the top factor | High |
| Drivers rarely schedule charging; most sessions start at plug-in | R2 Rivian/arXiv 2025 | 72% start at plug-in; smart scheduling ~$140/EV/yr, up to 28% lower emissions | High (home, not fleet) |
| Managed charging lowers fleet charging cost and peaks | R3 RFF WP 25-22; R4 Brattle/EnergyHub | Substantial savings; up to ~$400/EV/yr, peaks down up to 50% | High / Medium |
| Our simulator reproduces realistic degradation spread | Calibration to R1 | Mean ~2.3%/yr, low-DC ~1.5%, heavy-DC ~3.0% | Medium (calibration, not validation) |
| Our savings numbers transfer to real fleets | Assumption | Simulation only; no real fleet pilot | Low (state honestly) |
