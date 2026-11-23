"""Independent label-only replay of the hour and state-level target from cached match messages."""
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from earlier_days import DAYS as EARLIER
from full_days import DAYS, OUT, PRODUCTS


def check():
    checks = {}
    prior_id = {}
    for day in [*DAYS,*EARLIER]:
        for hour in range(24):
            info = json.loads((OUT/f"{day}-{hour:02}.json").read_bytes())
            stream = defaultdict(dict)
            for off, digest in info["slice_sha256"].items():
                suffix = "" if int(off)==0 else "-"+off
                data = (Path("cache")/f"coinbase-{day}{suffix}.gz").read_bytes()
                if hashlib.sha256(data).hexdigest()!=digest:
                    raise ValueError(f"archive changed: {day} {off}")
                for line in gzip.decompress(data).splitlines():
                    if line.strip():
                        stamp, body = line.split(b" ",1)
                        if stamp[:13].decode() != f"{day}T{hour:02}":
                            raise ValueError("slice outside assigned capture hour")
                        m = json.loads(body)
                        if m["type"] == "match":
                            stream[m["product_id"]][int(m["trade_id"])]=(m["taker_order_id"],m["side"])
            for symbol in PRODUCTS:
                expected = info["products"][symbol]
                n = pairs = agreements = cross_missing = 0
                prev = None
                for tid,(oid,side) in sorted(stream[symbol].items()):
                    if prev is None:
                        last = prior_id.get((day,symbol),tid-1)
                        cross_missing = tid-last-1
                        if cross_missing<0:
                            raise ValueError("overlapping capture hours")
                    if prev is None or tid!=prev+1:
                        n += 1
                    elif oid != old_oid:
                        n += 1
                        pairs += 1
                        agreements += side==old_side
                    elif old_side != side:
                        raise ValueError("inconsistent side within a labelled episode")
                    prev,old_oid,old_side = tid,oid,side
                prior_id[day,symbol] = prev
                if (n,pairs,agreements)!=(expected["orders"],n-expected["segments"],pairs-expected["switches"]):
                    raise ValueError((day,hour,symbol,n,pairs,agreements))
                checks[day,hour,symbol] = (len(stream[symbol]),pairs,agreements,cross_missing)
    summary = []
    with Path("results/coinbase_full.csv").open() as f:
        for r in csv.DictReader(f):
            if r["rule"]!="native":
                continue
            day,symbol = r["day"],r["symbol"]
            hours = sorted(range(24),key=lambda h:(checks[day,h,symbol][0],h))
            def rate(hs):
                return sum(checks[day,h,symbol][2] for h in hs)/sum(checks[day,h,symbol][1] for h in hs)
            value = rate(hours[-6:])-rate(hours[:6])
            if abs(value-float(r["truth"]))>1e-12:
                raise ValueError("state contrast mismatch")
            summary.append(dict(day=day,symbol=symbol,direct_high_minus_low=value,
                                cross_hour_missing_ids=sum(checks[day,h,symbol][3] for h in hours)))
    Path("results/replay_check.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(len(checks),"hours and",len(summary),"state comparisons reproduced directly from labelled fills")


if __name__ == "__main__":
    check()
