"""Generate the complete-day manuscript tables from the two summary CSVs."""
import csv
from pathlib import Path
from statistics import median

PAPER = Path(__file__).resolve().parent
RESULTS = PAPER.parent/"results"


def load(name):
    with (RESULTS/name).open() as f:
        return list(csv.DictReader(f))


def write(name, rows):
    (PAPER/name).write_text("".join(" & ".join(row)+r" \\"+"\n" for row in rows))


def main():
    cb = load("coinbase_full.csv")
    rows = []
    for year in ("2025","2024"):
        for rule in ("native","millisecond"):
            group = [r for r in cb if r["day"].startswith(year) and r["rule"] == rule]
            matches = sum(float(r["greedy"])*float(r["truth"])>0 for r in group)
            certified = sum(int(r["harmful_errors"])<int(r["radius"]) for r in group)
            rows.append([year,rule,str(matches),str(certified),
                         f'{median(int(r["audit_n"]) for r in group):g}',
                         f'{median(int(r["all_n"]) for r in group):g}',
                         f'{100*median(float(r["cert_prob"]) for r in group):.1f}'+r"\%"])
    write("audit-performance.tex",rows)
    bn = load("binance_monthly.csv")
    rows = []
    for s in sorted({r["symbol"] for r in bn}):
        group = [r for r in bn if r["symbol"]==s and r["rule"]=="native"]
        n = len(group)
        strict = sum(float(r["lower"])>0 or float(r["upper"])<0 for r in group)
        under_ten = sum(not r["threshold"] or float(r["threshold"])>0.1 for r in group)
        rows.append([s[:-4],str(n),str(sum(float(r["records"])>0 for r in group)),
                     str(sum(float(r["greedy"])>0 for r in group)),str(strict),str(under_ten),
                     f'{median(int(r["audit_n"]) for r in group):g}'])
    write("complete-monthly.tex",rows)


if __name__=="__main__":
    main()
