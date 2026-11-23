"""Stream verified Binance Spot archives. Each UTC hour is a separate observation window."""
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import zipfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from itertools import product
from pathlib import Path

SYMBOLS = ["ETHUSDT", "SOLUSDT", "LTCUSDT"]
DATES = ["2025-01-15", "2025-04-15", "2025-07-15", "2025-10-15"]
SETTINGS = ["native", "millisecond", "span20ms"]


def file_hash(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def archive(symbol, day):
    base = f"{symbol}-aggTrades-{day}.zip"
    url = f"https://data.binance.vision/data/spot/daily/aggTrades/{symbol}/{base}"
    path = Path("cache") / base
    path.parent.mkdir(exist_ok=True)
    opts = ["curl", "-fsSL", "--retry", "3", "--connect-timeout", "20", "--max-time", "600"]
    digest = subprocess.check_output(opts + [url + ".CHECKSUM"]).decode().split()[0]
    if not path.exists() or file_hash(path) != digest:
        tmp = path.with_suffix(".part")
        subprocess.run(opts + [url, "-o", str(tmp)], check=True)
        if file_hash(tmp) != digest:
            raise ValueError(f"hash mismatch {path}")
        tmp.replace(path)
    return path, digest


def compatible(kind, start, prev, now):
    s, p, t = now
    old_s, old_p, old_t = prev
    if s != old_s:
        return False
    move = (p - old_p) * s
    if kind == "native":
        return t == old_t and move > 0
    if kind == "millisecond":
        return t // 1000 == old_t // 1000 and move > 0
    # A same-price fill at a different native stamp can be in a different aggregate.
    return t - start <= 20000 and (move > 0 or (move == 0 and t != old_t))


def analyze(path, day):
    hours = [Counter() for _ in range(24)]
    midnight = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()) * 10**6
    last = None
    starts = {}
    with zipfile.ZipFile(path) as z, z.open(path.stem + ".csv") as f:
        for row in csv.reader(io.TextIOWrapper(f, encoding="ascii")):
            aid, price, _, first, end, stamp, maker = row[:7]
            aid, first, end, stamp = map(int, (aid, first, end, stamp))
            if maker.lower() not in ("true", "false") or end < first:
                raise ValueError(row)
            side = -1 if maker.lower() == "true" else 1
            key = "buy" if side == 1 else "sell"
            now = (side, Decimal(price), stamp)
            hour = (stamp - midnight) // 3600000000
            if not 0 <= hour < 24:
                raise ValueError(row)
            h = hours[hour]
            if last and (aid <= last_a or first <= last_end or stamp < last[2]):
                raise ValueError(f"out of order: {row}")
            gap = last and (aid != last_a + 1 or first != last_end + 1)
            reset = last is None or hour != last_hour or gap
            h["gaps"] += int(bool(gap))
            h["records"] += 1
            h["fills"] += end - first + 1
            h["rows_" + key] += 1
            if reset:
                h["segments"] += 1
            else:
                prev_key = "buy" if last[0] == 1 else "sell"
                h["out_" + prev_key] += 1
                h["flip_" + prev_key] += side != last[0]
                h["switches"] += side != last[0]
            for kind in SETTINGS:
                if reset or not compatible(kind, starts[kind], last, now):
                    starts[kind] = stamp
                    h[kind + "_" + key] += 1
            last, last_a, last_end, last_hour = now, aid, end, hour
    if any(not h for h in hours):
        raise ValueError("empty hour")
    return [dict(hour=i, **h) for i, h in enumerate(hours)]


def main():
    dest = Path("results")
    dest.mkdir(exist_ok=True)
    for symbol, day in product(SYMBOLS, DATES):
        path, digest = archive(symbol, day)
        out = dest / (path.stem + ".json")
        info = dict(symbol=symbol, day=day, sha256=digest, script=file_hash(Path(__file__)),
                    python=platform.python_version(), pid=os.getpid(), hours=analyze(path, day))
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(info, indent=2) + "\n")
        tmp.replace(out)
        print(symbol, day, "complete", flush=True)


if __name__ == "__main__":
    main()
