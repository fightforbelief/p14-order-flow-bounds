"""Capture ten minutes of public Coinbase matches, encoding taker IDs as local integers."""
import csv
import gzip
import json
import time
from pathlib import Path

import websocket

PRODUCTS = ["BTC-USD", "ETH-USD", "SOL-USD"]


def main():
    path = Path("data/coinbase.csv.gz")
    path.parent.mkdir(exist_ok=True)
    with gzip.open(path, "xt", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["product", "trade_id", "time", "price", "maker_side", "taker"])
        ids = {}
        ws = websocket.create_connection("wss://ws-feed.exchange.coinbase.com", timeout=20)
        ws.send(json.dumps(dict(type="subscribe", product_ids=PRODUCTS, channels=["matches", "heartbeat"])))
        end = time.monotonic() + 600
        while time.monotonic() < end:
            msg = json.loads(ws.recv())
            if msg["type"] == "error":
                raise RuntimeError(msg)
            if msg["type"] == "match":
                writer.writerow([msg["product_id"], msg["trade_id"], msg["time"], msg["price"],
                                 msg["side"], ids.setdefault(msg["taker_order_id"], len(ids))])
        ws.close()


if __name__ == "__main__":
    main()
