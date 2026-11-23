"""Build held-out comparisons from hourly counts, without market data access."""
import csv
import json
import math
from collections import Counter
from pathlib import Path
from fractions import Fraction

from boundary_audit import audit_size, log_miss, reversal_radius
from full_days import DAYS, PRODUCTS, RULES, OUT
from monthly import DAYS as MONTHS, OUT as MONTHLY
from earlier_days import DAYS as EARLIER
from study import SETTINGS, SYMBOLS
from summarize import join_asymmetry


def states(hours):
    ordered = sorted(hours, key=lambda h: (h["fills"],h["hour"]))
    return [sum(map(Counter, group), Counter()) for group in (ordered[-6:], ordered[:6])]


def freq(c, n):
    return 1-Fraction(c["switches"], n-c["segments"])


def compare(hi, lo, rule, labelled):
    def minimum(c):
        return c["records"]-c[rule+"_eligible"]
    def difference(n):
        return freq(hi,n(hi))-freq(lo,n(lo))
    record = difference(lambda c:c["records"])
    greedy = difference(minimum)
    w,l = (hi,lo) if greedy >= 0 else (lo,hi)
    dw,dl = minimum(w)-w["segments"],minimum(l)-l["segments"]
    sw,sl = w["switches"],l["switches"]
    harm_pool = dw-sw+l[rule+"_eligible"]
    all_pool = sum(c["records"]-c["segments"]-c["switches"] for c in (hi,lo))
    row = dict(records=float(record), greedy=float(greedy), fills=float(difference(lambda c:c["fills"])),
               lower=float(freq(hi,minimum(hi))-freq(lo,lo["records"])),
               upper=float(freq(hi,hi["records"])-freq(lo,minimum(lo))),
               high_fills=hi["fills"],low_fills=lo["fills"],high_records=hi["records"],low_records=lo["records"],
               harm_pool=harm_pool, all_pool=all_pool)
    rad = reversal_radius(dw,sw,dl,sl,l[rule+"_eligible"])
    if rad:
        row.update(radius=rad, audit_n=audit_size(harm_pool,rad), all_n=audit_size(all_pool,rad),
                   family_n=audit_size(harm_pool,rad,0.05/12))
    a,b = (hi,lo) if record>=0 else (lo,hi)
    def fraction_input(c):
        # join_asymmetry requires only the total minimum order count.
        return dict(records=c["records"], switches=c["switches"], segments=c["segments"],
                    **{rule+"_buy":minimum(c), rule+"_sell":0})
    row["threshold"] = join_asymmetry(fraction_input(a),fraction_input(b),rule)[0]
    if labelled:
        err = w[rule+"_missed_join"]+l[rule+"_false_join"]
        truth = difference(lambda c:c["orders"])
        row.update(truth=float(truth), high_orders=hi["orders"],low_orders=lo["orders"],
                   harmful_errors=err,total_errors=sum(c[rule+"_missed_join"]+c[rule+"_false_join"] for c in (w,l)))
        for name,c in (("high",hi),("low",lo)):
            u = c[rule+"_eligible"]
            row[name+"_fraction"] = (u-c[rule+"_false_join"])/u
            row[name+"_off_rule_joins"] = c[rule+"_missed_join"]
            row[name+"_false_joins"] = c[rule+"_false_join"]
        if rad:
            row["cert_prob"]=math.exp(log_miss(harm_pool,err,row["audit_n"]))
            row["family_prob"]=math.exp(log_miss(harm_pool,err,row["family_n"]))
            assert (err >= rad or greedy*truth > 0)
    return row


def weighting_checks(hours, rule):
    clean = [h for h in hours if h["segments"] == 1]
    result = {"gapfree_hours":len(clean)}
    if len(clean) >= 12:
        a,b = states(clean)
        for key in ("records","orders"):
            result["gapfree_"+key] = float(freq(a,a[key])-freq(b,b[key]))
        result["gapfree_greedy"] = float(freq(a,a["records"]-a[rule+"_eligible"])
                                         -freq(b,b["records"]-b[rule+"_eligible"]))
    ordered = sorted(hours, key=lambda h:(h["fills"],h["hour"]))
    for key in ("orders","records","greedy"):
        def hourly(h):
            n = h["records"]-h[rule+"_eligible"] if key=="greedy" else h[key]
            return freq(h,n)
        result["equal_hour_"+key] = float((sum(map(hourly,ordered[-6:]))-sum(map(hourly,ordered[:6])))/6)
    by_orders = sorted(hours, key=lambda h:(h["orders"],h["hour"]))
    high,low = [sum(map(Counter,g),Counter()) for g in (by_orders[-6:],by_orders[:6])]
    for key in ("orders","records"):
        result["order_activity_"+key] = float(freq(high,high[key])-freq(low,low[key]))
    result["order_activity_greedy"] = float(freq(high, high["records"]-high[rule+"_eligible"])
                                            -freq(low,low["records"]-low[rule+"_eligible"]))
    result["overlap_high_hours"] = len({h["hour"] for h in by_orders[-6:]} & {h["hour"] for h in ordered[-6:]})
    result["overlap_low_hours"] = len({h["hour"] for h in by_orders[:6]} & {h["hour"] for h in ordered[:6]})
    return result


def write(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w",newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main():
    cb, bn = [],[]
    for day in [*DAYS,*EARLIER]:
        info = [json.loads((OUT/f"{day}-{h:02}.json").read_bytes()) for h in range(24)]
        for symbol in PRODUCTS:
            hours = [dict(hour=t["hour"],**t["products"][symbol]) for t in info]
            if any(a["last_id"]>=b["first_id"] for a,b in zip(hours,hours[1:])):
                raise ValueError("overlapping capture-hour trade ranges")
            hi,lo = states(hours)
            for rule in RULES:
                cb.append(dict(day=day,symbol=symbol,rule=rule,**compare(hi,lo,rule,True),
                               **weighting_checks(hours,rule)))
    for day in MONTHS:
        for symbol in SYMBOLS:
            info = json.loads((MONTHLY/f"{symbol}-{day}.json").read_bytes())
            for rule in SETTINGS:
                hi,lo = states(info["hours"])
                for c in (hi,lo):
                    c[rule+"_eligible"] = c["records"]-c[rule+"_buy"]-c[rule+"_sell"]
                bn.append(dict(day=day,symbol=symbol,rule=rule,**compare(hi,lo,rule,False)))
    write(Path("results/coinbase_full.csv"), cb)
    write(Path("results/binance_monthly.csv"), bn)
    print(f"Produced {len(cb)} labelled and {len(bn)} anonymous comparisons.")

if __name__ == "__main__":
    main()
