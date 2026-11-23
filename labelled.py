"""Audit the assumed sweep constraints with labelled Coinbase Exchange messages."""
import gzip
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from study import SETTINGS, compatible

PRODUCTS = ["ETH-USD", "BTC-USD", "SOL-USD"]
DAYS = ["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]


def get_messages(day, offset):
    params = dict(filters=json.dumps([dict(channel="match", symbols=PRODUCTS)]),
                  offset=offset, sliceSize=10)
    params["from"] = day
    url = "https://api.tardis.dev/v1/data-feeds/coinbase?" + urlencode(params)
    path = Path("cache") / (f"coinbase-{day}.gz" if offset == 0 else f"coinbase-{day}-{offset}.gz")
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".part")
        subprocess.run(["curl", "-fsSL", "-H", "Accept-Encoding: gzip", "--retry", "2", "--max-time", "120", url, "-o", str(tmp)], check=True)
        tmp.replace(path)
    data = path.read_bytes()
    body = gzip.decompress(data) if data.startswith(b"\x1f\x8b") else data
    groups = defaultdict(list)
    for line in body.splitlines():
        if line.strip():
            msg = json.loads(line.split(b" ", 1)[1])
            if msg["type"] == "match":
                groups[msg["product_id"]].append(msg)
    if set(groups) != set(PRODUCTS):
        raise ValueError(f"missing product: {groups.keys()}")
    return groups, hashlib.sha256(data).hexdigest()


def audit(msgs):
    rows = []
    for msg in msgs:
        dt = datetime.fromisoformat(msg["time"])
        t = int(dt.replace(microsecond=0).timestamp()) * 10**6 + dt.microsecond
        row = (1 if msg["side"] == "sell" else -1, Decimal(msg["price"]), t)
        trade = int(msg["trade_id"])
        order = msg["taker_order_id"]
        reset = not rows or trade != last_trade + 1
        if reset or (row, order) != rows[-1][:2]:
            rows.append((row, order, reset))
        last_trade = trade
    counts = Counter(fills=len(msgs), records=len(rows), unique_takers=len({r[1] for r in rows}),
                     first_us=rows[0][0][2], last_us=rows[-1][0][2])
    starts = {}
    exceptions = []
    for i, (row, order, reset) in enumerate(rows):
        if reset:
            counts["segments"] += 1
        if reset or order != prev_order:
            true_start = row[2]
            counts["orders"] += 1
        if not reset:
            counts["switches"] += row[0] != prev[0]
            if row[2] < prev[2]:
                raise ValueError("unordered times")
        for kind in SETTINGS:
            if reset or not compatible(kind, starts[kind], prev, row):
                counts[kind + "_min"] += 1
                starts[kind] = row[2]
            if not reset and order == prev_order and not compatible(kind, true_start, prev, row):
                counts[kind + "_violating_edges"] += 1
                if kind == "native":
                    exceptions.append(dict(side=row[0], previous_price=str(prev[1]), price=str(row[1]),
                                           previous_us=prev[2], stamp_us=row[2], previous_side=prev[0]))
        prev, prev_order = row, order
    return dict(**counts, native_exceptions=exceptions)


def main():
    out = []
    windows = [(day, 0) for day in DAYS]
    windows.extend((f"2025-{m:02}-01", 720) for m in (2, 5, 8, 11))
    for day, offset in windows:
        groups, digest = get_messages(day, offset)
        for symbol, msgs in groups.items():
            out.append(dict(day=day, offset=offset, symbol=symbol, sha256=digest, **audit(msgs)))
    Path("results/labelled.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
