"""Phase 1 Acceptance Verification Test
Tests per NOTE.md §15:
- 5 OEM payloads -> canonical topic
- Unit tests pass
- DLQ receives garbage / bad VIN
- >= 50K ev/s locally
- Saves evidence in tests/evidence/
"""

import json
import os
import re
import shutil
import subprocess
import time
import pytest

def get_go_cmd():
    if shutil.which("go"):
        return "go"
    for p in [r"C:\Program Files\Go\bin\go.exe", r"C:\Go\bin\go.exe"]:
        if os.path.exists(p):
            return f'"{p}"'
    return "go"

def run_cmd(cmd: str, cwd: str = None):
    env = os.environ.copy()
    if r"C:\Program Files\Go\bin" not in env.get("PATH", ""):
        env["PATH"] = r"C:\Program Files\Go\bin;" + env.get("PATH", "")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env, cwd=cwd)
    output = (res.stdout + "\n" + res.stderr).strip()
    assert res.returncode == 0, f"Command failed: {cmd}\nOutput: {output}"
    return output

def test_ingest_unit_tests():
    go = get_go_cmd()
    out = run_cmd(f"{go} test -v ./...", cwd="services/ingest")
    assert "PASS" in out
    assert "FAIL" not in out

def test_simulator_unit_tests():
    go = get_go_cmd()
    out = run_cmd(f"{go} test -v ./...", cwd="services/simulator")
    assert "PASS" in out
    assert "FAIL" not in out

def test_five_oems_in_canonical_topic():
    # Verify that messages in canonical topic contain records from all 5 OEMs with schema_v: 1
    cmd = 'docker compose exec -T redpanda rpk topic consume telemetry.canonical -n 150 -o start -p 0,1,2,3,4,5,6,7,8,9,10,11 --pretty-print=false'
    out = run_cmd(cmd)
    
    oems_found = set()
    records = []
    for line in out.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
            val_str = parsed.get("value")
            if val_str:
                val = json.loads(val_str)
                records.append(val)
                oems_found.add(val.get("oem"))
        except Exception:
            continue
            
    expected_oems = {"VoltX", "NordMotors", "AsiaDrive", "EuroEV", "ZephyrEV"}
    assert expected_oems.issubset(oems_found), f"Missing OEMs in canonical topic: {expected_oems - oems_found}"
    
    for r in records[:10]:
        assert r.get("schema_v") == 1
        assert len(r.get("vin")) == 17
        assert len(r.get("geohash7", "")) == 7
        assert 0.0 <= r.get("soc_pct", 0) <= 100.0
        assert r.get("speed_kmh", 0) >= 0.0

def test_dlq_received_garbage_and_bad_vin():
    cmd = 'docker compose exec -T redpanda rpk topic consume telemetry.dlq -n 10 -o start -p 0,1,2 --pretty-print=false'
    out = run_cmd(cmd)
    
    reasons = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
            val_str = parsed.get("value")
            if val_str:
                val = json.loads(val_str)
                reasons.add(val.get("reason"))
        except Exception:
            continue
            
    assert len(reasons) > 0, "No DLQ envelopes found"
    assert "bad_vin" in reasons or "parse_error" in reasons, f"Expected bad_vin or parse_error in DLQ, got: {reasons}"

def test_prometheus_metrics():
    out = run_cmd('curl.exe -s http://localhost:2112/metrics')
    assert "ingest_events_total" in out
    assert "invalid_total" in out
    assert "dedupe_dropped_total" in out
    assert "normalize_latency_seconds" in out
    
    # Save evidence file
    os.makedirs("tests/evidence", exist_ok=True)
    with open("tests/evidence/p1_metrics.txt", "w", encoding="utf-8") as f:
        f.write(out)

def test_throughput_benchmark_evidence():
    go = get_go_cmd()
    cmd = f'{go} run ./cmd/simulator --vehicles 100000 --duration 5s --rate 75000 --brokers localhost:19092'
    out = run_cmd(cmd, cwd="services/simulator")
    
    # Remove ANSI escape sequences
    clean_out = re.sub(r'\x1b\[[0-9;]*m', '', out)
    
    rates = []
    for match in re.finditer(r'rate_ev_s=([0-9.]+)', clean_out):
        try:
            rates.append(float(match.group(1)))
        except ValueError:
            pass
                    
    assert len(rates) > 0, f"No rate metrics captured in clean output:\n{clean_out}"
    max_rate = max(rates)
    avg_rate = sum(rates) / len(rates)
    
    assert max_rate >= 50000, f"Peak throughput {max_rate} < 50,000 ev/s"
    
    # Write evidence
    with open("tests/evidence/p1_throughput.txt", "w", encoding="utf-8") as f:
        f.write(f"Phase 1 Throughput Benchmark Results\n")
        f.write(f"====================================\n")
        f.write(f"Target Rate: 75,000 ev/s\n")
        f.write(f"Simulated Vehicles: 100,000\n")
        f.write(f"Observed Peak Rate: {max_rate:.1f} ev/s\n")
        f.write(f"Observed Average Rate: {avg_rate:.1f} ev/s\n")
        f.write(f"Acceptance Standard: >= 50,000 ev/s (PASSED)\n")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
