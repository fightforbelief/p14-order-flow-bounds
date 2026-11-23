"""Run the unchanged primary estimator on twelve previously unexamined dates."""
import json
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

from study import SYMBOLS, analyze, archive, file_hash

DAYS = [f"2025-{month:02}-01" for month in range(1,13)]
OUT = Path("results/monthly")


def collect(job):
    symbol, day = job
    p = OUT / f"{symbol}-{day}.json"
    script = file_hash(Path("study.py"))
    if p.exists() and json.loads(p.read_bytes())["script"] == script:
        return
    path, digest = archive(symbol, day)
    info = dict(symbol=symbol, day=day, sha256=digest, script=script, hours=analyze(path, day))
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(info, indent=2)+"\n")
    tmp.replace(p)
    print(symbol, day, "complete", flush=True)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True, parents=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(collect, product(SYMBOLS, DAYS)))
