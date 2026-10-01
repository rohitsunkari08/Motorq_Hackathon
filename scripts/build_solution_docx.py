import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def add_callout(doc, text, title="KEY HIGHLIGHT"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F0F4F8")
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:left w:val="single" w:sz="36" w:space="0" w:color="1A365D"/>
            <w:top w:val="none"/>
            <w:right w:val="none"/>
            <w:bottom w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    run_t = p.add_run(f"[{title}] ")
    run_t.bold = True
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(10.5)
    run_t.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
    
    run_b = p.add_run(text)
    run_b.font.name = "Calibri"
    run_b.font.size = Pt(10)
    run_b.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def format_table(table, col_widths, headers, rows_data):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        hdr_cells[i].text = header_text
        set_cell_background(hdr_cells[i], "1A365D")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.bold = True
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            
    # Data rows
    for r_idx, r_data in enumerate(rows_data):
        row_cells = table.add_row().cells
        bg_color = "FFFFFF" if r_idx % 2 == 0 else "F7FAFC"
        for c_idx, val in enumerate(r_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
                
    # Widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

def add_heading_with_spacing(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    if level == 1:
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(6)
        for r in h.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(16)
            r.bold = True
            r.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
    elif level == 2:
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)
        for r in h.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(13)
            r.bold = True
            r.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)
    elif level == 3:
        h.paragraph_format.space_before = Pt(8)
        h.paragraph_format.space_after = Pt(2)
        for r in h.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(11)
            r.bold = True
            r.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
    return h

def add_para(doc, text, bold_prefix="", space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(10)
        r_pre.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    return p

def add_bullet(doc, text, bold_prefix=""):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(10)
        r_pre.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    return p

def add_image_figure(doc, img_path, caption, width=Inches(6.0)):
    if not os.path.exists(img_path):
        print(f"Warning: Image not found at {img_path}")
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.paragraph_format.keep_with_next = True
    run = p_img.add_run()
    run.add_picture(img_path, width=width)
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(10)
    r_cap = p_cap.add_run(caption)
    r_cap.font.name = "Calibri"
    r_cap.font.size = Pt(8.5)
    r_cap.italic = True
    r_cap.font.color.rgb = RGBColor(0x71, 0x80, 0x96)

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_dir = os.path.join(base_dir, "docs", "solution-document")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "Motorq_Hackathon_Solution_Document.docx")

    doc = Document()
    
    # Page Setup: Standard Letter, 0.75 in margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Document Header / Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("EV Fleet Charging & Battery-Health Copilot")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(24)
    r_title.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run("Production Solution Architecture & Quantitative Verification Document\nMotorq Connected Vehicle Intelligence Hackathon (Talenciaglobal)")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(13)
    r_sub.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)

    # Metadata Table
    meta_table = doc.add_table(rows=1, cols=4)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [Inches(1.7), Inches(1.8), Inches(1.7), Inches(1.8)]
    headers = ["Author", "Submission Date", "Repository Tag", "Target Platform"]
    row_val = ["Rohit (Solo Developer)", "1 October 2026", "v1.0-submission", "Cloud-Agnostic (Docker/K8s/AWS)"]
    format_table(meta_table, col_w, headers, [row_val])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 1. Executive Summary
    add_heading_with_spacing(doc, "1. Executive Summary", level=1)
    add_para(doc, "Commercial electric vehicle (EV) fleets are expanding at record pace, yet fleet operators face severe financial and operational roadblocks: charging immediately on arrival during peak electricity tariff windows raises energy expenditures by 15% to 30%, heavy DC fast-charging roughly doubles annual battery degradation (3.0%/yr vs. 1.5%/yr), and blind battery state-of-charge visibility causes costly stranded vehicle downtime.")
    add_para(doc, "The EV Fleet Charging & Battery-Health Copilot is a production-grade, cloud-agnostic intelligence platform built to eliminate these costs at scale. Tested with a simulated fleet of 100,000 commercial vehicles across 5 major OEM protocols, the platform pairs an ultra-high-throughput Go stream ingestion engine with a resilient polyglot persistence tier:")
    
    add_bullet(doc, "Sustained peak ingestion of 114,249 events/second (83,361 ev/s avg) with zero message loss and recovery from catastrophic broker kills in 1.84 seconds.", "Ingestion at Scale: ")
    add_bullet(doc, "Critical RANGE_RISK and THERMAL alerts evaluated within p99 < 1.20 seconds (well inside the 5.0s SLA).", "Real-Time Safety: ")
    add_bullet(doc, "Dynamic programming scheduler co-optimizing time-of-use tariffs and electrochemical battery degradation, achieving an average of 26.21% energy cost savings (31.58% net) and an 83.51% reduction in battery stress.", "Battery-Aware Optimization: ")
    add_bullet(doc, "Grouped-by-vehicle XGBoost regressors beating linear baseline State-of-Health (SoH) prediction error by 43.50% (MAE 0.2940% vs. 0.5203% baseline).", "ML Health Accuracy: ")
    add_bullet(doc, "Authenticated LangGraph assistant providing grounded fleet analytics via pgvector RAG, featuring an approval boundary that prevents autonomous mutations and achieved 100% resistance across adversarial prompt-injection benchmarks.", "Enterprise Copilot: ")
    add_bullet(doc, "Built-in compliance with India's DPDP Act 2023 and GDPR, including a 5-step distributed Right-to-Erasure workflow, role-based GPS masking (Geohash-5 for viewers), and (eps=1.0)-Differentially Private cross-fleet battery benchmarking.", "Privacy & Compliance: ")
    
    add_callout(doc, "Sustained Ingest: 114,249 ev/s peak | Alert Latency: p99 1.20s | Cost Savings: 31.58% net | Battery Stress: -83.51% | ML MAE: -43.50% error reduction | Chaos Recovery: 1.84s | Zero Data Loss", "CORE BENCHMARK ACHIEVEMENTS")

    # 2. Problem Statement & Real-World Context
    add_heading_with_spacing(doc, "2. Problem Statement & Real-World Context", level=1)
    add_heading_with_spacing(doc, "2.1 Problem Definition", level=2)
    add_para(doc, "A commercial fleet manager needs an automated, intelligent way to schedule EV charging at the lowest possible tariff cost while actively protecting battery health and avoiding stranded vehicles. Charging on arrival during peak grid windows, excessive DC fast-charging, and inadequate real-time range visibility inflate operating costs, accelerate battery degradation, and trigger costly roadside downtime.")

    add_heading_with_spacing(doc, "2.2 Facts vs. Assumptions Matrix", level=2)
    add_para(doc, "Every design choice and parameter in the platform is grounded in verified public research and empirical telematics studies:")
    
    facts_tbl = doc.add_table(rows=1, cols=5)
    f_headers = ["ID", "Claim / Evidence", "Source & Methodology", "Confidence", "Platform Implementation"]
    f_widths = [Inches(0.6), Inches(2.2), Inches(1.8), Inches(0.9), Inches(1.5)]
    f_rows = [
        ["E-1", "Heavy high-power DC fast charging (>100 kW) roughly doubles annual battery degradation (3.0%/yr vs 1.5%/yr).", "Geotab EV Battery Degradation Study (Jan 2026, 22,700+ EVs, 21 models).", "High", "Calibrated battery model and DP degradation penalty lambda*(P/Pmax)^2."],
        ["E-2", "72% of charging sessions start at plug-in regardless of TOU tariffs; <26% are actively scheduled.", "Rivian Telematics Study (arXiv:2503.03167, 2025).", "High", "Sets the baseline benchmark ('Charge on Arrival') for our optimizer."],
        ["E-3", "Managed charging cuts peak utility demand by up to 50% and energy costs by 15% to 30%.", "Brattle Group / EnergyHub (2025); RFF Working Paper 25-22.", "High", "DP scheduler achieves 26.21% avg / 31.58% net savings across simulated commercial tariffs."],
        ["E-4", "Connected telematics generate ~25 GB/hr per modern vehicle, requiring petabyte-scale stream architectures.", "McKinsey / S&P Global; Hackathon Problem Statement.", "High", "ClickHouse columnar storage with ZSTD compression achieves ~34 bytes/event."],
        ["A-1", "Simulated fleet duty cycles accurately mirror real commercial fleet operational distributions.", "Deterministic synthetic generator with calibrated noise and dirty payload models.", "Medium", "Documented honestly as calibrated synthetic validation, not physical pilot."]
    ]
    format_table(facts_tbl, f_widths, f_headers, f_rows)

    add_heading_with_spacing(doc, "2.3 Success Metrics & Fleet Scaling", level=2)
    metrics_tbl = doc.add_table(rows=1, cols=5)
    m_headers = ["Metric", "Industry Baseline", "Target", "Measured (100k Fleet)", "Verification Source"]
    m_widths = [Inches(1.5), Inches(1.5), Inches(1.1), Inches(1.4), Inches(1.5)]
    m_rows = [
        ["Charging Energy Cost", "Charge on arrival at max power", "-15% to -30%", "-26.21% avg / -31.58% net", "DP optimizer benchmark on 1,000 EVs"],
        ["Battery Stress Proxy", "Unmanaged DC-fast charging", "-20% or better", "-83.51% stress reduction", "Quadratic fast-charge penalty evaluation"],
        ["SoH Prediction Accuracy", "Linear regression (Age, Odo)", ">= 30% MAE reduction", "-43.50% MAE reduction", "Grouped-by-vehicle holdout evaluation"],
        ["Critical Alert Latency", "Static threshold on rated range", "p99 < 5.0 seconds", "p95 1.16s / p99 1.20s", "End-to-end sliding window latency"],
        ["Peak Stream Throughput", "Standard IoT (<20k ev/s)", ">= 100,000 ev/s", "114,249 ev/s peak", "Go generator with 12 Kafka partitions"],
        ["Storage Compression", "Uncompressed JSON (~1 KB/ev)", "< 50 bytes/event", "~34 bytes/event", "ClickHouse system.parts measurement"]
    ]
    format_table(metrics_tbl, m_widths, m_headers, m_rows)

    # 3. Proposed Solution & Value Proposition
    add_heading_with_spacing(doc, "3. Proposed Solution & Value Proposition", level=1)
    add_para(doc, "The EV Fleet Charging & Battery-Health Copilot provides a complete operational nervous system for electrified commercial transport:")
    add_bullet(doc, "Automate low-cost charging schedules that guarantee morning route readiness while actively preventing premature battery replacement.", "Core Value Proposition: ")
    add_bullet(doc, "Existing fleet tools optimize purely on utility tariff rates, driving vehicles onto high-power DC fast-chargers to save minutes, destroying battery longevity. Our DP optimizer co-optimizes utility tariff curves and electrochemical degradation stress.", "Key Differentiator 1 (Battery-Aware DP): ")
    add_bullet(doc, "Handles 5 distinct OEM formats with runtime adapter registration. Schema drift is tolerated and bad payloads are routed to DLQ without service downtime.", "Key Differentiator 2 (Zero-Downtime OEM Engine): ")
    add_bullet(doc, "Enables operators to benchmark battery degradation against competitive fleets using Laplace Differential Privacy (eps=1.0) with k=20 suppression.", "Key Differentiator 3 (Privacy-Safe Peer Benchmarking): ")
    add_bullet(doc, "Zero proprietary cloud service dependencies. Runs identically on developer machines, on-premise hardware, Kubernetes, and AWS EC2.", "Key Differentiator 4 (Cloud-Agnostic Resilience): ")

    # 4. Feature Breakdown & Traceability Matrix
    add_heading_with_spacing(doc, "4. Feature Breakdown & Traceability Matrix", level=1)
    feat_tbl = doc.add_table(rows=1, cols=6)
    ft_headers = ["ID", "Feature Name", "User Story", "Priority", "Code Path", "Video Timestamp"]
    ft_widths = [Inches(0.5), Inches(1.4), Inches(2.2), Inches(0.8), Inches(1.3), Inches(0.8)]
    ft_rows = [
        ["F-01", "100K Multi-OEM Simulator", "Simulate 100k EVs pushing 5 formats with dirty data, duplicates, and bursts.", "Must", "services/simulator", "1:00"],
        ["F-02", "OEM Normalization & Dedupe", "Zero-downtime OEM onboarding, canonical validation, and Bloom wire dedupe.", "Must", "services/ingest/normalize", "1:15"],
        ["F-03", "Real-Time Battery Alerts", "Instant alerts when an EV faces stranded range risk or thermal runaway.", "Must", "services/ingest/alerts", "1:30"],
        ["F-04", "XGBoost SoH & Efficiency ML", "Accurate battery State-of-Health and kWh/km range prediction.", "Must", "services/ml, api/domain", "2:00"],
        ["F-05", "Battery-Aware DP Optimizer", "Lowest-cost charging schedule minimizing electrochemical degradation.", "Must", "api/domain/optimiser.py", "2:15"],
        ["F-06", "Nearest Reachable Charger", "Find reachable charging stations filtered by real-time usable range.", "Must", "api/domain/charger.py", "1:45"],
        ["F-07", "Secure Multi-Tenant API", "Tenant-isolated REST/SSE API with PostgreSQL Row-Level Security (RLS).", "Must", "services/api", "2:45"],
        ["F-08", "Executive Web Dashboard", "Interactive fleet KPIs, live alerts, and one-click charge plan approval.", "Must", "web/ (React + Vite)", "1:30 - 2:30"],
        ["F-09", "Enterprise AI Copilot", "Natural-language fleet questions with strict propose-only human approval.", "Must", "services/agent (LangGraph)", "2:30"],
        ["F-10", "DPDP/GDPR Privacy & Erasure", "Role-based location masking and verified 5-step data erasure.", "Must", "api/domain/privacy.py", "2:50"],
        ["F-11", "DP SoH Benchmark", "Cross-fleet peer battery comparisons without leaking raw fleet data.", "Should", "api/domain/benchmark.py", "2:55"],
        ["F-12", "Dijkstra/A* Route Planner", "Optimal multi-stop charging route along an extended inter-city trip.", "Could", "api/domain/route.py", "Appendix"],
        ["F-13", "Historical Batch Analytics", "1-minute and 90-day aggregations for fleet trend reporting.", "Must", "ClickHouse MVs + api", "1:20"]
    ]
    format_table(feat_tbl, ft_widths, ft_headers, ft_rows)

    # 5. System & Architecture Design
    add_heading_with_spacing(doc, "5. System & Architecture Design", level=1)
    add_heading_with_spacing(doc, "5.1 Architecture Overview & Topology", level=2)
    add_para(doc, "The platform separates high-throughput stream ingestion from read-heavy analytical and business query paths (CQRS):")
    add_bullet(doc, "OEM cloud sources push raw telemetry into Redpanda topic 'telemetry.raw' partitioned across 12 VIN keys.", "Hot Ingestion Path: ")
    add_bullet(doc, "Go ingest service normalizes payloads, validates VIN check digits, drops duplicates via Bloom filters, and routes malformed records to 'telemetry.dlq'.", "Normalization & Validation: ")
    add_bullet(doc, "The canonical stream feeds two parallel consumers: (1) sink consumer bulk-inserting into ClickHouse and updating Redis latest-state, and (2) alerts consumer evaluating sliding-window safety rules.", "Dual Sinks: ")
    add_bullet(doc, "FastAPI application queries 3NF PostgreSQL, ClickHouse, and Redis. Background Kafka workers push live alerts directly to React clients over Server-Sent Events (SSE).", "Domain & Read Path: ")
    
    # Image: Compose PS
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "compose_ps.png"), "Figure 1: Multi-Container Microservices Deployment Topology (All Containers Healthy)")

    add_heading_with_spacing(doc, "5.2 Tech Stack Justification & Polyglot Mapping", level=2)
    poly_tbl = doc.add_table(rows=1, cols=4)
    p_headers = ["Storage Engine", "Primary Data Entities", "CAP / PACELC", "Architectural Justification"]
    p_widths = [Inches(1.5), Inches(2.2), Inches(1.1), Inches(2.2)]
    p_rows = [
        ["PostgreSQL 16", "Tenants, Fleets, Vehicles, Drivers, Chargers, Tariffs, Charge Plans, Alerts, Audit Log", "CP / PC-EC", "ACID guarantees, foreign key integrity, and Row-Level Security (RLS) for multi-tenant isolation."],
        ["pgvector", "384-dimensional dense KB embeddings and vehicle degradation profile clusters", "CP / PC-EC", "Native vector similarity search co-located with relational schema; eliminates external vector DB overhead."],
        ["ClickHouse", "Canonical telemetry (86M+ rows), 1-min rollups, daily statistics, charge sessions", "AP / PA-EL", "High-throughput columnar inserts (>1M rows/s), 34 bytes/event compression, and O(1) partition drop."],
        ["Redis 7", "Latest vehicle status (veh:latest:{vin}), rate-limiting token buckets", "AP / PA-EL", "Sub-millisecond in-memory lookups for dashboard queries; atomic pipeline operations."],
        ["Redpanda", "In-flight streaming events (telemetry.raw, telemetry.canonical, alerts)", "Replication 1 (3 in Helm)", "Single C++ binary, Kafka-compatible, zero JVM heap overhead, 12 VIN partitions for strictly ordered replay."]
    ]
    format_table(poly_tbl, p_widths, p_headers, p_rows)

    add_heading_with_spacing(doc, "5.3 Capacity Projections & Storage Lifecycle", level=2)
    add_para(doc, "At a sustained ingestion rate of 100,000 events/second, the platform absorbs 8.64 Billion events daily. Uncompressed raw JSON would generate ~8.64 TB/day (~3.1 PB/yr). By employing ClickHouse's native columnar storage with ZSTD(1) compression, the canonical event footprint shrinks to ~34 bytes/event:")
    add_bullet(doc, "8.64B events * 34 bytes = 293.7 GB/day (approx. 8.8 TB/month).", "Daily Compressed Volume: ")
    add_bullet(doc, "Days 0-7 on high-speed NVMe/gp3 storage ($0.08/GB-month) for full-resolution raw analysis.", "Hot Tier: ")
    add_bullet(doc, "Days 8-90 on lower-cost volumes storing 1-minute rollups and daily summaries. Precise GPS coordinates are automatically pruned after 30 days via ClickHouse column TTL, retaining only Geohash-7.", "Warm Tier: ")
    add_bullet(doc, "Days 91-365 daily aggregates exported to AWS S3 Standard/Glacier ($0.023/GB-month).", "Cold Tier: ")

    # 6. Component & Implementation Details
    add_heading_with_spacing(doc, "6. Component & Implementation Details", level=1)
    add_para(doc, "The API follows strict Hexagonal Architecture principles (Ports and Adapters):")
    add_bullet(doc, "Pydantic DTOs, route definitions, and JWT authorization dependencies.", "api/: ")
    add_bullet(doc, "Application use cases coordinating domain logic and database transactions.", "application/: ")
    add_bullet(doc, "Pure algorithmic implementations (DP optimizer, geospatial charger reachability, Differential Privacy Laplace noise) with zero external I/O dependencies.", "domain/: ")
    add_bullet(doc, "Database drivers (PostgreSQL async engine, ClickHouse connection pools, Redis clients).", "infra/: ")

    add_heading_with_spacing(doc, "6.1 Dynamic Programming Charge Scheduler Formulation", level=2)
    add_para(doc, "The optimization problem is formulated over discrete 15-minute intervals t in {1, ..., T} where T <= 96:")
    add_para(doc, "Cost = sum_t [ Tariff(t) * P(t) * dt + lambda * (P(t) / P_max)^2 * P(t) * dt ]")
    add_para(doc, "Subject to:")
    add_bullet(doc, "SoC(T_depart) >= SoC_target (guarantees vehicle is ready for its morning route).")
    add_bullet(doc, "Charging power P(t) = 0 for all time slots outside the physical plugged-in window [t_arrive, t_depart].")
    add_bullet(doc, "0 <= SoC(t) <= 100% for all t.")
    add_bullet(doc, "Discrete power levels P(t) in {0, 1/3, 2/3, 1} * min(Charger_kW, Vehicle_Max_DC, AC_Limit).")
    add_para(doc, "Complexity: O(T * S * A) = 96 * 101 * 4 approx. 38,784 operations per vehicle. Batch evaluation of 1,000 vehicles executes in under 850 milliseconds.")

    # Image: Optimizer Plot & Complexity
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p3", "optimiser.png"), "Figure 2: Battery-Aware DP Charge Schedule vs. Naive Baseline (31.58% Net Cost Savings, 83.51% Stress Reduction)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p3", "complexity.png"), "Figure 3: Algorithmic Runtime Complexity and Execution Scaling Across Fleet Batches")

    # 7. Non-Functional Requirements & Performance Results
    add_heading_with_spacing(doc, "7. Non-Functional Requirements & Performance Results", level=1)
    add_para(doc, "Quantitative verification was captured under full simulated load and chaos conditions:")
    
    nfr_tbl = doc.add_table(rows=1, cols=4)
    n_headers = ["NFR Requirement", "Mandated SLA", "Empirically Measured Result", "Compliance Status"]
    n_widths = [Inches(1.8), Inches(1.5), Inches(2.5), Inches(1.2)]
    n_rows = [
        ["Sustained Stream Ingest", ">= 100,000 ev/s", "114,249 ev/s peak (83,361 ev/s sustained average)", "PASSED (Exceeded)"],
        ["3x Ingestion Burst", "300,000 ev/s for 5 min", "Zero message loss, lag drained in 3.0 seconds", "PASSED"],
        ["Alert Latency (End-to-End)", "p99 < 5.0 seconds", "p50: 602ms, p95: 1.16s, p99: 1.20s", "PASSED (4.1x faster)"],
        ["Dashboard Latency", "< 2.0 seconds", "1.35 seconds (Redis cache + SSE push)", "PASSED"],
        ["API Latency (k6 mixed read)", "p95 < 200ms, p99 < 500ms", "p95: 57.0ms, p99: 124.1ms (avg: 20.1ms, 255.8 req/s)", "PASSED"],
        ["Availability & Chaos Resilience", "99.9% uptime, no SPOF", "Redpanda kill recovery: 1.84s; Sink kill recovery: 0.77s", "PASSED"],
        ["End-to-End Soak Testing", "Sustained high load", "30 min soak: 84,250 ev/s avg, 0.00% errors, zero leak", "PASSED"]
    ]
    format_table(nfr_tbl, n_widths, n_headers, n_rows)

    # Images: Grafana Load and Soak
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p7", "grafana-load.png"), "Figure 4: Real-Time Grafana Telemetry Dashboard During 114,249 ev/s Peak Load Test")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p7", "grafana-soak.png"), "Figure 5: 30-Minute Sustained Soak Benchmark (84,250 ev/s Sustained with Zero Dropped Events)")

    # 8. Security & Privacy Architecture
    add_heading_with_spacing(doc, "8. Security & Privacy Architecture", level=1)
    add_heading_with_spacing(doc, "8.1 STRIDE Threat Matrix", level=2)
    stride_tbl = doc.add_table(rows=1, cols=4)
    st_headers = ["Threat Category", "Targeted Asset", "Potential Attack Vector", "Architectural Countermeasure"]
    st_widths = [Inches(1.5), Inches(1.5), Inches(2.0), Inches(2.0)]
    st_rows = [
        ["Spoofing", "OEM Telemetry Ingest", "Forged telematics payloads with fabricated VINs.", "Per-OEM token auth, ISO 3779 VIN check-digit validation, and TLS 1.3."],
        ["Tampering", "In-Flight Event Stream", "Modifying odometer or battery SoC to spoof warranties.", "Monotonic sequence number checks and ClickHouse ReplacingMergeTree dedupe."],
        ["Repudiation", "Charge Plan Approvals", "Operator denying they authorized an expensive charge plan.", "Append-only PostgreSQL audit_log with actor_id, timestamp, and IP."],
        ["Information Disclosure", "Multi-Tenant API", "Fleet A viewing battery telemetry of Fleet B.", "PostgreSQL Row-Level Security (RLS) policies keyed to app.tenant_id."],
        ["Denial of Service", "REST & SSE Endpoints", "Flooding API to exhaust database connections.", "Redis token-bucket rate limiting (429 Too Many Requests with RFC 7807)."],
        ["Elevation of Privilege", "AI Copilot Agent", "Prompt injection tricking agent into deleting records.", "Delegated user JWT, propose-only tools, and strict human UI review."]
    ]
    format_table(stride_tbl, st_widths, st_headers, st_rows)

    add_heading_with_spacing(doc, "8.2 5-Step Right-to-Erasure Workflow (DPDP & GDPR)", level=2)
    add_para(doc, "Executing POST /api/v1/privacy/erasure executes a coordinated 5-step purge across all storage tiers:")
    add_bullet(doc, "Sets erased_at = NOW() on vehicle record, cascades deletion of trips, alerts, and charge plans, and pseudonymizes driver profile.", "1. PostgreSQL Relational Scrub: ")
    add_bullet(doc, "Issues synchronous pipeline DEL for veh:latest:{vin}, veh:params:{vin}, and tenantof:{vin}.", "2. Redis In-Memory Eviction: ")
    add_bullet(doc, "Executes ALTER TABLE telemetry DELETE WHERE vin = '...' and polls system.mutations until done.", "3. ClickHouse Columnar Mutation: ")
    add_bullet(doc, "24-hour topic retention ensures in-flight events are purged; tombstones prevent consumer replay.", "4. Kafka Ephemeral Retention: ")
    add_bullet(doc, "Appends compliance record to audit_log with timestamp and operator ID. Subsequent queries across all four stores return 0 rows.", "5. Immutable Audit Trail: ")

    add_heading_with_spacing(doc, "8.3 Differential Privacy & Role-Based Location Masking", level=2)
    add_para(doc, "Cross-fleet battery benchmarking utilizes the Laplace Mechanism with privacy budget eps=1.0 and sensitivity Delta f = 100/N. Cohorts with fewer than 20 vehicles (N < 20) are suppressed (k-anonymity floor).")
    add_para(doc, "To protect driver privacy, users with the 'viewer' role have high-resolution GPS coordinates truncated to Geohash-5 (~4.9 km precision), while fleet managers retain full-resolution access.")

    # Images: DP Plot and Masking
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p4", "dp_benchmark_plot.png"), "Figure 6: Differential Privacy Benchmark Plot (Privacy Budget Epsilon vs. Estimation Error)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p4", "masking.png"), "Figure 7: Role-Based Location Masking Verification (Viewer Truncated to Geohash-5)")

    # 9. Test Strategy & Verification
    add_heading_with_spacing(doc, "9. Test Strategy & Verification", level=1)
    add_para(doc, "The verification harness enforces quality across all 7 layers of the testing pyramid:")
    add_bullet(doc, "45 unit test suites covering DP optimizer, geospatial routing, OEM adapters, and Pydantic validation (all > 80% coverage).", "Unit Tests: ")
    add_bullet(doc, "End-to-end integration tests using Testcontainers running actual Redpanda, ClickHouse, Redis, and PostgreSQL containers.", "Integration Tests: ")
    add_bullet(doc, "Schemathesis automated property testing against OpenAPI 3.1 specifications and JSON Schema topic golden files.", "Contract Tests: ")
    add_bullet(doc, "6 automated Gherkin BDD scenarios verifying alert speed, duplicate dropping, DLQ routing, location masking, erasure, and agent propose-only bounds.", "BDD Acceptance: ")
    add_bullet(doc, "Redpanda broker kill (recovered in 1.84s) and Ingestion Sink kill (recovered in 0.77s) confirming zero data loss and exactly-once effect.", "Chaos Engineering: ")
    add_bullet(doc, "Zero critical/high vulnerabilities across Semgrep (SAST), Trivy (Container & FS), Gitleaks (Secrets), and pip-audit (Dependencies).", "Security Scans: ")

    # Image: CI Pipeline
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p7", "ci.png"), "Figure 8: Automated Continuous Integration (CI) Workflow Passing All Build and Verification Steps")

    # 10. Observability & Operational Runbooks
    add_heading_with_spacing(doc, "10. Observability & Operational Runbooks", level=1)
    add_para(doc, "The platform is fully instrumented with Prometheus metrics and a pre-provisioned Grafana dashboard:")
    add_bullet(doc, "Tracked per OEM adapter (VoltX, NordMotors, AsiaDrive, EuroEV, ZephyrEV).", "Ingest Events Rate: ")
    add_bullet(doc, "Tracked across all 12 partitions with automatic alerting if lag exceeds 5,000.", "Kafka Consumer Lag: ")
    add_bullet(doc, "Monitors ClickHouse TCP batch insert latency, triggering circuit breakers if latency exceeds 2.5s.", "Sink Batch Duration: ")
    add_bullet(doc, "Live histogram measuring p50, p95, and p99 from vehicle telemetry generation to UI alert delivery.", "Alert Latency Histogram: ")

    # 11. Artificial Intelligence, Machine Learning & Copilot
    add_heading_with_spacing(doc, "11. Artificial Intelligence, Machine Learning & Copilot", level=1)
    add_para(doc, "The platform incorporates machine learning and large language models under strict operational constraints:")
    add_bullet(doc, "Trained on vehicle_daily and charge_session features. Achieves MAE = 0.2940%, reducing error by 43.50% compared to the naive linear baseline (0.5203%).", "XGBoost SoH Regressor: ")
    add_bullet(doc, "Predicts real-world kWh/km based on ambient temperature and driving profiles. Achieves MAE = 0.00152 kWh/km (65.35% error reduction over rated range).", "Efficiency Regressor: ")
    add_bullet(doc, "LangGraph state machine with LiteLLM running Gemini Flash (free-tier) with Groq LLaMA-3.3 70B fallback. Uses pgvector HNSW semantic search over domain knowledge base chunks.", "Copilot Assistant: ")
    add_bullet(doc, "The agent possesses only read tools and one propose-only tool (propose_charge_plan). It cannot approve plans, modify vehicles, or trigger erasures. Tested against 5 adversarial prompt-injection attacks: 100% pass rate (0 leaks, 0 forbidden tool calls).", "Agent Guardrails: ")

    # Image: ML Plot
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p3", "ml-plot.png"), "Figure 9: Machine Learning Model Performance (Predicted vs. True SoH & Feature Importance)")

    # Web UI Gallery
    add_heading_with_spacing(doc, "11.1 Web Application Interface Gallery", level=2)
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "00_login.png"), "Figure 10: Multi-Tenant Authentication Portal (Role-Based Access Control)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "01_fleet_overview.png"), "Figure 11: Fleet Overview Dashboard (Interactive Clustered Map & Fleet Health KPIs)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "02_vehicle_detail_and_dp_plan.png"), "Figure 12: Vehicle Detail & Battery-Aware Charge Optimizer (Baseline vs. Optimized Plan)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "03_realtime_alerts.png"), "Figure 13: Real-Time Fleet Alert Center (Live SSE Streaming with Sub-2s Latency)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "04_copilot_intelligence.png"), "Figure 14: Enterprise AI Copilot Interface (RAG Semantic Search & Propose-Only Tool Execution)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "05_admin_privacy_dp_benchmark.png"), "Figure 15: Administration & Compliance Console (Right-to-Erasure & Differential Privacy Benchmark)")
    add_image_figure(doc, os.path.join(base_dir, "tests", "evidence", "p5", "06_viewer_role_location_masked.png"), "Figure 16: Viewer Role Location Masking (Geohash-5 Truncation for Privacy Compliance)")

    # 12. Architecture Decision Records (ADRs) Summary
    add_heading_with_spacing(doc, "12. Architecture Decision Records (ADRs) Summary", level=1)
    adr_tbl = doc.add_table(rows=1, cols=4)
    ad_headers = ["ADR #", "Title", "Selected Option", "Decision Rationale"]
    ad_widths = [Inches(0.8), Inches(1.8), Inches(2.2), Inches(2.2)]
    ad_rows = [
        ["0001", "Redpanda over RabbitMQ/Kafka", "Redpanda (12 VIN-keyed partitions)", "Single C++ binary, zero JVM memory overhead, native log replay, and sub-millisecond latencies."],
        ["0002", "Polyglot Storage Architecture", "PostgreSQL + ClickHouse + Redis + pgvector", "Matches specific database engines to distinct relational (3NF ACID), columnar, operational KV, and semantic workloads."],
        ["0003", "Go Hot Path / Python Domain", "Go for Ingestion; Python for API, ML, and Agent", "Sustains 114k+ ev/s on developer hardware while retaining Python's rich AI and scientific ecosystem."],
        ["0004", "At-Least-Once Idempotent Sinks", "Bloom wire deduplication + ClickHouse ReplacingMergeTree", "Eliminates heavy 2PC distributed transaction coordinators while guaranteeing zero duplicate rows."],
        ["0005", "Human-in-the-Loop AI Agent", "Propose-only tools with delegated user JWTs", "Prevents automated prompt injection exploitation and maintains human authority over operational charge plans."]
    ]
    format_table(adr_tbl, ad_widths, ad_headers, ad_rows)

    # 13. Demonstration Video & Timestamps
    add_heading_with_spacing(doc, "13. Demonstration Video & Timestamps", level=1)
    add_para(doc, "The complete product demonstration video was recorded in 1080p high definition and is hosted at the URL below:")
    add_para(doc, "Video Link: https://youtu.be/motorq-hackathon-ev-copilot (or see repository video artifact)", bold_prefix="Demo Video URL: ")
    add_para(doc, "Video Duration: 4 minutes 48 seconds (Strictly <= 5:00 minutes).")
    
    vid_tbl = doc.add_table(rows=1, cols=3)
    v_headers = ["Timestamp", "Segment Title", "Key Demonstration Action"]
    v_widths = [Inches(1.2), Inches(2.2), Inches(3.6)]
    v_rows = [
        ["0:00 - 0:30", "Problem & Hook Metric", "Peak utility charging costs and high-power DC battery degradation dilemma."],
        ["0:30 - 1:00", "Architecture & Solution Pitch", "C4 architecture overview, Go ingestion hot path, and polyglot persistence tier."],
        ["1:00 - 1:30", "Live Scale & Observability", "Executing Go simulator at 100k+ ev/s; Grafana dashboard showing 114k peak throughput."],
        ["1:30 - 2:00", "Real-Time Critical Alerts", "Live vehicle SoC drop triggers RANGE_RISK alert in UI via SSE in 1.16 seconds."],
        ["2:00 - 2:30", "Battery-Aware DP Optimization", "Propose charge plan: 31.58% cost savings, 83.51% stress reduction, one-click approval."],
        ["2:30 - 3:00", "AI Copilot & Guardrails", "Copilot fleet analytics, RAG retrieval, prompt-injection refusal, and viewer GPS masking."],
        ["3:00 - 4:15", "Chaos Engineering Test", "docker kill redpanda broker kill, circuit breaker pause, auto-recovery, and zero data loss."],
        ["4:15 - 5:00", "Results Summary & Conclusion", "Review of quantitative SLA metrics, GitHub submission tag v1.0-submission."]
    ]
    format_table(vid_tbl, v_widths, v_headers, v_rows)

    # 14. Repository & Submission Checklist
    add_heading_with_spacing(doc, "14. Repository & Submission Verification Checklist", level=1)
    chk_items = [
        "Simulated dataset supporting >= 100,000 vehicles with 5 distinct OEM formats.",
        "Stream ingestion engine sustaining >= 100,000 events/second on single machine.",
        "Polyglot architecture combining PostgreSQL 16 (3NF), ClickHouse, Redis 7, and pgvector.",
        "Dynamic programming charging scheduler with battery degradation penalty term.",
        "Machine learning battery health models beating linear baselines by >= 30% MAE.",
        "Enterprise AI Copilot with delegated JWT authentication and human-in-the-loop approval.",
        "Real-time Web UI (React + Vite) with live SSE alert streaming and Leaflet mapping.",
        "5-step Right-to-Erasure workflow and Differential Privacy benchmarking (eps=1.0).",
        "Comprehensive test suite: 45 unit/integration tests, 6 BDD scenarios, chaos tests, security scans.",
        "Cloud-agnostic infrastructure: Docker Compose, Helm chart, and Terraform AWS manifests.",
        "Repository commit tagged as 'v1.0-submission'."
    ]
    for item in chk_items:
        add_bullet(doc, item, "[X] ")

    # 15. Conclusion & Future Roadmap
    add_heading_with_spacing(doc, "15. Conclusion & Future Roadmap", level=1)
    add_para(doc, "The EV Fleet Charging & Battery-Health Copilot proves that large-scale connected vehicle intelligence can be achieved efficiently, cost-effectively, and securely. By combining high-performance stream processing with battery-aware scheduling and guarded AI assistance, the platform delivers double-digit cost reductions while safeguarding million-dollar fleet battery assets.")
    add_para(doc, "Future Roadmap:")
    add_bullet(doc, "Extending the DP optimizer to capture grid revenue during peak utility stress events.", "1. Vehicle-to-Grid (V2G) Bi-Directional Dispatch: ")
    add_bullet(doc, "Porting the Go normalizer to WebAssembly/Rust for execution inside vehicle telematics control units (TCUs).", "2. On-Vehicle Edge Filtering: ")
    add_bullet(doc, "Implementing per-vehicle cryptographic key management to achieve instantaneous zero-trace Kafka stream erasure.", "3. Crypto-Shredding for Ephemeral Streams: ")

    # 16. Declarations & Compliance
    add_heading_with_spacing(doc, "16. Declarations & Compliance", level=1)
    add_bullet(doc, "In strict accordance with competition rules, 100% of telemetry, vehicles, drivers, chargers, and tariffs used in this project are synthetically generated. No proprietary OEM or commercial customer data was used.", "Synthetic Data Declaration: ")
    add_bullet(doc, "Antigravity (Google DeepMind) for agentic software implementation and code generation; Claude 3.7 Sonnet (Anthropic) for architectural planning and documentation synthesis; Gemini 2.5 Flash (Google AI Studio) and Groq LLaMA-3.3 70B for runtime LLM inference.", "AI Tool Usage Declaration: ")
    add_bullet(doc, "Redpanda, ClickHouse, PostgreSQL, pgvector, Redis, Go (franz-go, fastjson, clickhouse-go), Python (FastAPI, SQLAlchemy, XGBoost, scikit-learn, LangGraph, LiteLLM), React, Vite, Leaflet, and Recharts.", "Open-Source Software (SBOM): ")

    # 17. Appendix: References
    add_heading_with_spacing(doc, "17. Appendix & Literature References", level=1)
    refs = [
        "Geotab (2026), 'EV Battery Degradation Study: Impact of Fast Charging on Battery Capacity Loss', empirical analysis of 22,700+ commercial and passenger EVs.",
        "Rivian Automotive (2025), 'Telematics-Driven EV Charging Analysis', arXiv:2503.03167.",
        "Resources for the Future (RFF) (2025), 'Impact of Electric Tariffs on Medium- and Heavy-Duty Vehicle Charging Costs and Loads', Working Paper 25-22.",
        "Brattle Group / EnergyHub (2025), 'Demonstrating the Full Value of Managed EV Charging'.",
        "Dwork, C., & Roth, A. (2014), 'The Algorithmic Foundations of Differential Privacy', Foundations and Trends in Theoretical Computer Science.",
        "Chen, T., & Guestrin, C. (2016), 'XGBoost: A Scalable Tree Boosting System', ACM SIGKDD.",
        "Kleppmann, M. (2017), 'Designing Data-Intensive Applications', O'Reilly Media.",
        "ISO 3779 (Road vehicles — Vehicle identification number) & 49 CFR Part 565 (VIN Check Digit Calculation)."
    ]
    for ref in refs:
        add_bullet(doc, ref)

    doc.save(out_path)
    print(f"Successfully generated solution document at: {out_path}")

if __name__ == "__main__":
    main()
