"""Temporal replication of the frozen full-day label audit in a separate year."""
from concurrent.futures import ThreadPoolExecutor

from full_days import OUT, collect_hour

DAYS = [f"2024-{month:02}-01" for month in (3,6,9,12)]


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True, parents=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(collect_hour, [(d,h) for d in DAYS for h in range(24)]))
