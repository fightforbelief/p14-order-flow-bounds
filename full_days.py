"""Rebuild 24-hour labelled tapes from adjacent archive slices and retain hourly evidence."""
import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from labelled import PRODUCTS, get_messages
from study import compatible

DAYS = [f"2025-{month:02}-01" for month in (3, 6, 9, 12)]
RULES = ("native", "millisecond")
OUT = Path("results/full_days")


def audit_hour(messages, day, hour):
    unique = {}
    for m in messages:
        trade = int(m["trade_id"])
        record = (m["side"], Decimal(m["price"]), m["time"], m["taker_order_id"])
        if trade in unique and unique[trade] != record:
            raise ValueError("conflicting copies of a trade")
        unique[trade] = record
    if not unique:
        raise ValueError("empty product-hour")
    c = Counter(fills=len(unique), duplicates=len(messages)-len(unique))
    ids = sorted(unique)
    c.update(first_id=ids[0], last_id=ids[-1])
    prev = prev_id = order = None
    for trade in ids:
        maker, price, stamp, taker = unique[trade]
        dt = datetime.fromisoformat(stamp)
        if dt.strftime("%Y-%m-%d") != day or dt.hour != hour:
            c["outside_exchange_hour"] += 1
        us = int(dt.replace(microsecond=0).timestamp()) * 10**6 + dt.microsecond
        if maker not in ("buy", "sell"):
            raise ValueError(maker)
        row = (1 if maker == "sell" else -1, price, us)
        reset = prev_id is None or trade != prev_id+1
        prev_id = trade
        if not reset and prev == row and taker == order:
            continue
        same = not reset and taker == order
        flip = not reset and row[0] != prev[0]
        if flip and same:
            raise ValueError("taker changed sign")
        c["records"] += 1
        c["segments"] += reset
        c["switches"] += flip
        c["orders"] += not same
        for kind in RULES:
            eligible = not reset and compatible(kind, prev[2], prev, row)
            c[kind+"_eligible"] += eligible
            c[kind+"_false_join"] += eligible and not same
            c[kind+"_missed_join"] += same and not eligible
        prev, order = row, taker
    for kind in RULES:
        assert c["orders"] == c["records"] - c[kind+"_eligible"] + c[kind+"_false_join"] - c[kind+"_missed_join"]
    return c


def collect_hour(job):
    day, hour = job
    dest = OUT / f"{day}-{hour:02}.json"
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if dest.exists() and json.loads(dest.read_bytes())["code"] == sha:
        return
    msgs = {symbol: [] for symbol in PRODUCTS}
    digests = {}
    for offset in range(60*hour, 60*(hour+1), 10):
        groups, digest = get_messages(day, offset)
        digests[offset] = digest
        for symbol in PRODUCTS:
            msgs[symbol].extend(groups[symbol])
    info = dict(code=sha, day=day, hour=hour, slice_sha256=digests,
                products={s: audit_hour(ms, day, hour) for s, ms in msgs.items()})
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(info, indent=2)+"\n")
    tmp.replace(dest)
    print(day, hour, "complete", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True, parents=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(collect_hour, [(d,h) for d in DAYS for h in range(24)]))
