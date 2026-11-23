"""Regenerate manuscript tables from per-hour counts. Run at the project root."""
import csv
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from study import DATES, SETTINGS, SYMBOLS


def persist(c, count):
    return 1 - Fraction(c["switches"], count - c["segments"])


def state(c, kind):
    n_min = c[kind + "_buy"] + c[kind + "_sell"]
    return persist(c, n_min), persist(c, c["records"]), persist(c, c["fills"])


def balanced(c, prefix):
    # Average of the two within-side continuation rates, weighting sides equally.
    def flip_rate(side):
        ends = c["rows_" + side] - c["out_" + side]
        return Fraction(c["flip_" + side], c[prefix + "_" + side] - ends)
    return 1 - (flip_rate("buy") + flip_rate("sell")) / 2


def erase_fraction(larger, smaller, kind):
    # Keep the lower-persistence state's entire record count. All merges
    # on that side only widen the original difference.
    available = larger["records"] - larger[kind + "_buy"] - larger[kind + "_sell"]
    numerator = larger["records"] - larger["segments"] - Fraction(
        larger["switches"] * (smaller["records"] - smaller["segments"]), smaller["switches"])
    minimum = -(-numerator.numerator // numerator.denominator)
    return minimum, available


def join_asymmetry(winner, loser, kind):
    """Smallest positive-part excess of winner's join rate that permits a tie or reversal."""
    def data(c):
        return (c["records"] - c["segments"], c["switches"],
                c["records"] - c[kind + "_buy"] - c[kind + "_sell"])
    dw, sw, aw = data(winner)
    dl, sl, al = data(loser)
    if min(aw, al, sw, sl) <= 0:
        raise ValueError("requires positive switch counts and merge capacities in both groups")
    c = dw * sl - dl * sw
    best = None
    for joins_l in range(al + 1):
        joins_w = max(0, (c + sw * joins_l + sl - 1) // sl)
        if joins_w > aw:
            break
        excess = max(0, joins_w * al - joins_l * aw)
        if best is None or excess < best[0]:
            best = (excess, joins_w, joins_l)
            if not excess:
                break
    if best is None:
        return None, None, None
    return best[0] / (aw * al), best[1], best[2]


def main():
    folder = Path("results")
    rows = []
    totals = Counter()
    for symbol in SYMBOLS:
        for date in DATES:
            info = json.loads((folder / f"{symbol}-aggTrades-{date}.json").read_text())
            hours = sorted(info["hours"], key=lambda h: (h["fills"], h["hour"]))
            lo, hi = [sum(map(Counter, group), Counter()) for group in (hours[:6], hours[-6:])]
            totals.update(sum(map(Counter, hours), Counter()))
            for kind in SETTINGS:
                a, b, f = state(hi, kind)
                x, y, g = state(lo, kind)
                larger, smaller = (hi, lo) if b >= y else (lo, hi)
                need, possible = erase_fraction(larger, smaller, kind)
                excess, jw, jl = join_asymmetry(larger, smaller, kind)
                rows.append(dict(bal_lower=float(balanced(hi,kind)-balanced(lo,"rows")),
                                 bal_upper=float(balanced(hi,"rows")-balanced(lo,kind)),
                                 bal_records=float(balanced(hi,"rows")-balanced(lo,"rows")),
                                 excess=excess, witness_w=jw, witness_l=jl, greedy=float(a-x), symbol=symbol, date=date, model=kind, high_min=float(a),
                                 high_max=float(b), low_min=float(x), low_max=float(y),
                                 lower=float(a-y), upper=float(b-x), at_records=float(b-y),
                                 at_fills=float(f-g), merges_required=need, merges_available=possible))
    with (folder / "contrasts.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print({k: totals[k] for k in ("records", "fills", "segments", "gaps")})
    for r in rows[::3]:
        print(r["symbol"], r["date"], *[round(r[k]*100, 3) for k in ("at_fills","at_records","lower","upper")], r["merges_required"], r["merges_available"])


if __name__ == "__main__":
    main()
