"""Draw the record-level and labelled activity contrasts from the full-day census."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parent
with (ROOT.parent/"results/coinbase_full.csv").open() as source:
    rows = [r for r in csv.DictReader(source) if r["rule"]=="native"]
fig, axes = plt.subplots(1,2,sharex=True,sharey=True,figsize=(7.8,4.3))
for ax, year, title in zip(axes, ["2025","2024"], ["2025 independent panel", "2024 temporal replication"]):
    panel = sorted((r for r in rows if r["day"].startswith(year)),key=lambda r:(r["day"],r["symbol"]))
    if len(panel)!=12:
        raise ValueError(year)
    labels = []
    for i,r in enumerate(panel):
        a,b = [100*float(r[k]) for k in ("records","truth")]
        labels.append(r["day"][5:7]+" / "+r["symbol"][:3])
        ax.plot([a,b],[i,i],color="#8a959f",lw=1.4,zorder=2)
        ax.scatter(a,i,marker="s",s=28,facecolors="white",edgecolors="#9a4b10",zorder=3)
        ax.scatter(b,i,marker="o",s=17,color="#145366",zorder=4)
    ax.axvline(0,color="#454545",lw=.85,ls="--",zorder=1)
    for y in (2.5,5.5,8.5):
        ax.axhline(y,color="#e2e5e8",lw=.7,zorder=0)
    ax.set_yticks(range(12),labels,fontsize=8)
    ax.set_title(title,fontsize=10,loc="left")
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5,integer=True))
    ax.tick_params(length=2,labelsize=8)
    ax.spines[["top","right","left"]].set_visible(False)
axes[0].invert_yaxis()
fig.supxlabel("Same-side frequency in the busiest minus quietest hours (percentage points)",fontsize=9,y=.09)
fig.legend(handles=[Line2D([],[],marker="s",mfc="white",mec="#9a4b10",ls="",label="Aggregate records"),
                    Line2D([],[],marker="o",color="#145366",ls="",label="Labelled episodes")],
           loc="lower center",ncols=2,frameon=False,fontsize=8,bbox_to_anchor=(.5,-.008))
fig.subplots_adjust(left=.12,right=.98,bottom=.20,top=.91,wspace=.12)
fig.savefig(ROOT/"full-day-ranks.pdf",metadata={"CreationDate":None,"ModDate":None})
