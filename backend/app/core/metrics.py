from prometheus_client import Counter, Gauge, Histogram

scan_duration_seconds = Histogram(
    "scanner_scan_duration_seconds",
    "Time taken to complete a full scan",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

scan_findings_total = Counter(
    "scanner_findings_total",
    "Total findings detected, by severity band",
    labelnames=["severity_band"],  # critical / high / medium / low
)

groq_api_calls_total = Counter(
    "scanner_groq_api_calls_total",
    "Total Groq API calls, by stage",
    labelnames=["stage"],  # classify / score / fix
)

groq_api_errors_total = Counter(
    "scanner_groq_api_errors_total",
    "Total Groq API errors",
    labelnames=["stage"],
)

scan_cache_hits_total = Counter(
    "scanner_cache_hits_total",
    "Total scan cache hits (skipped re-scan)",
)

scans_total = Counter(
    "scanner_scans_total",
    "Total scans started",
    labelnames=["status"],  # pending / done / failed
)

active_websocket_connections = Gauge(
    "scanner_active_websocket_connections",
    "Number of currently open WebSocket scan connections",
)
