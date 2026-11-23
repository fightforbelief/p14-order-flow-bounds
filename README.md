# Order-flow persistence under uncertain execution grouping

Guo and Yang study whether the sign of a high- versus low-activity comparison of successive taker directions survives the ambiguity of order reconstruction. [Read the manuscript](paper/manuscript.pdf) or inspect the [state contrasts and integer witnesses](results/contrasts.csv).

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
