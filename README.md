# Order-flow persistence under uncertain execution grouping

Guo and Yang study whether the sign of a high- versus low-activity comparison of successive taker directions survives the ambiguity of order reconstruction. [Read the manuscript](paper/manuscript.pdf) or inspect the [state contrasts and integer witnesses](results/contrasts.csv).

## Main results

Across 24 complete Coinbase asset-days, six record-level activity rankings reverse against public taker episode labels. Three occur in each year's panel. Greedy native-time grouping recovers 23 directions. The exact minimum boundary-error count gives a finite-population audit for the ranking. Median 5% targeted zero-hit budgets are 66 boundary checks in 2025 and 68 in 2024. The budgets concern a uniform random check of a fixed tape. The primary venue without labels, Binance, has 24 robust native-time rankings in 36 additional monthly asset-days. See the [full-day label results](results/coinbase_full.csv) and [monthly extension](results/binance_monthly.csv).

## Reproduction

The archived analysis used CPython 3.12.10 on Windows. From the project root, initialize one environment with `py -3.12 -m venv .venv`. Run the following in PowerShell. Python uses only the standard library in these steps. Provide curl on PATH and outbound HTTPS for the two archive readers.

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -m unittest -v
& $py study.py
& $py labelled.py
& $py summarize.py
& $py paper/tables.py
```

The Binance reader checks each daily ZIP against its publisher's SHA-256, caches the original files in `cache/`, and emits one compact JSON file per symbol-day. The Coinbase reader uses Tardis's free first-of-month raw match endpoint, saves response digests and compares reconstructions with the taker identifiers. Full URLs are constructed in the scripts. Each day's three products share the same Coinbase response digest. Timestamps are in UTC. Use the digests to check for upstream revisions before comparing new output. The numeric output of repeated runs is deterministic on identical inputs. Process IDs vary.

For a data-free rebuild, start with the committed results and run the last two commands. Compile from `paper/` with `tectonic manuscript.tex`. See [protocol and amendments](protocol.md) for sampling choices, timing assumptions and the switch from a live capture to archived messages. The initial live capture script is optional and requires websocket-client 1.8.0. All reported Coinbase results use the replay script.

## Reading the results

Each hour contributes counts of flips, elementary fills, aggregate records, contiguous segments and minimum buy/sell order counts under each timing rule. The published comparison uses the six busiest and six quietest hours per symbol-day. In the contrast CSV, frequencies and differences use units of one. The paper reports percentage points. An empty excess field denotes an unreachable reversal. Witness counts apply first to the higher record-level persistence group and then to the other group. The bounds range over partitions satisfying explicit sweep restrictions. The Binance archives contain no hidden taker identifiers for checking which partition occurred.

## Full-day replication and boundary audit

The independent extension uses the [sampling and verification design](full_days_protocol.md). From the same Windows project environment, run:

```powershell
& $py full_days.py
& $py earlier_days.py
& $py monthly.py
& $py full_summary.py
& $py verify_labels.py
& $py paper/full_tables.py
```

The two Coinbase runs retrieve a total of 1,152 ten-minute slices. The monthly run retrieves 36 Binance daily archives. All three readers resume completed output units. On Coinbase the three products share each capture slice. Each hour contains its six response digests, source program digest, deduplication count, segment count, label episode count and counts of both kinds of boundary error. The label-only replay verifies the digests and reconstructs agreements independently from consecutive taker IDs and sides.

[Coinbase full-day results](results/coinbase_full.csv) compare the true episode-level activity contrast with the proposed reconstruction and the sharp bounds. [Binance monthly results](results/binance_monthly.csv) contain the corresponding anonymous-tape diagnostics. In the CSVs `radius` is the fewest harmful boundary errors capable of eliminating the greedy ranking, `audit_n` the per-comparison zero-hit budget, and `family_n` uses 0.05/12 as a sensitivity for a family of twelve. `cert_prob` is the probability that uniform sampling without replacement returns a zero-hit certificate on the fully labelled population. It is calculated from the label census. For an offline rebuild use the committed hourly results, then run `full_summary.py` and both paper table scripts. The full-day replay check requires the cached raw slices. For the manuscript figure run `python paper/plot_ranks.py` with matplotlib (the archived figure used 3.10.8). The figure PDF is also committed for TeX-only builds.
