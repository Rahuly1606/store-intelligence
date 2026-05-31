#!/usr/bin/env python3
"""
Live Terminal Dashboard

Polls GET /stores/{store_id}/metrics and displays real‑time metrics
using the Rich library. Press Ctrl+C to exit.
"""

import time
import sys
import requests
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

API_BASE = "http://localhost:8000"
STORE_ID = "STORE_BLR_002"
POLL_INTERVAL = 2  # seconds

console = Console()

def fetch_metrics():
    """Fetch current metrics from the API."""
    try:
        resp = requests.get(f"{API_BASE}/stores/{STORE_ID}/metrics")
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        return None
    return None

def build_table(metrics):
    """Create a Rich table from metrics dict."""
    table = Table(title=f"Store Intelligence – {STORE_ID}", title_style="bold white on blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    if metrics is None:
        table.add_row("Status", "[red]API unavailable")
        return table

    table.add_row("Unique Visitors", str(metrics.get("unique_visitors", 0)))
    table.add_row("Conversion Rate", f"{metrics.get('conversion_rate', 0):.2%}")
    table.add_row("Queue Depth", str(metrics.get("queue_depth", 0)))
    table.add_row("Abandonment Rate", f"{metrics.get('abandonment_rate', 0):.2%}")

    # Show average dwell per zone
    for zone, dwell in metrics.get("avg_dwell_per_zone_ms", {}).items():
        table.add_row(f"Dwell [{zone}]", f"{dwell:,} ms")

    return table

def main():
    console.print(Panel("Live Store Dashboard", style="bold green"))
    console.print("Connecting to API...")

    try:
        with Live(build_table(None), refresh_per_second=0.5) as live:
            while True:
                metrics = fetch_metrics()
                live.update(build_table(metrics))
                time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        console.print("\n[bold red]Dashboard stopped.[/bold red]")
        sys.exit(0)

if __name__ == "__main__":
    main()