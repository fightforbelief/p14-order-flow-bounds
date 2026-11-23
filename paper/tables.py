"""Typeset the primary outcomes, sensitivity and external validation from recovered outputs."""
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median

root = Path(__file__).resolve().parent.parent
out = root / "paper"
results = root / "results"
with (results / "contrasts.csv").open() as source:
    contrasts = list(csv.DictReader(source))
labels = json.loads((results / "labelled.json").read_text())


def save(name, rows):
    (out / (name + ".tex")).write_text("\n".join(" & ".join(r) + r" \\" for r in rows) + "\n")


def pp(x):
    v = 100 * float(x)
    return f"{v:.3f}" if 0 < abs(v) < 0.01 else f"{v:.2f}"


save("primary", [
    [r["symbol"][:-4], r["date"][5:7], *(pp(r[k]) for k in ("at_fills", "at_records", "greedy", "lower", "upper")),
     pp(r["excess"]) if r["excess"] else "--"]
    for r in contrasts if r["model"] == "native"
])
sensitivity = []
for kind in ["native", "millisecond", "span20ms"]:
    rows = [r for r in contrasts if r["model"] == kind]
    widths = [float(r["upper"]) - float(r["lower"]) for r in rows]
    sensitivity.append([{"native":"Native stamp","millisecond":"Millisecond","span20ms":"20 ms span"}[kind],
                        pp(min(widths)), pp(median(widths)), pp(max(widths)),
                        str(sum(float(r["lower"]) < 0 < float(r["upper"]) for r in rows))])
save("timing", sensitivity)
validation = []
for offset in [0, 720]:
    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        data = [r for r in labels if r["offset"] == offset and r["symbol"] == symbol]
        assert len(data) == 4
        counts = Counter()
        for row in data:
            counts.update({k:v for k,v in row.items() if isinstance(v,int)})
        validation.append(["00:00" if offset == 0 else "12:00", symbol,
                           *(f"{counts[k]:,}" for k in ("fills", "records", "orders", "native_min",
                                                        "millisecond_min", "span20ms_min"))])
save("validation", validation)
