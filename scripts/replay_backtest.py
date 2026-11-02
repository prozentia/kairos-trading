"""Replay historical 1m candles through the real TradingRunner (dry-run).

Unlike a separate backtest implementation, this drives the production engine
(aggregation, indicators, filters, risk gate, position manager, simulated
fees) candle by candle, so results reflect what the bot would really do.

Warmup mirrors production: 500 candles of the strategy timeframe are fed to
``_warm_up_indicators()`` before trading starts.

Data: Binance public monthly 1m klines (data.binance.vision), stored as the
original zip files in ``--data``. Use ``--download`` to fetch missing months.

Examples::

    python scripts/replay_backtest.py --list
    python scripts/replay_backtest.py "EMA Cross Trend" --data data/klines \\
        --start 2025-11 --end 2026-10 --download
    python scripts/replay_backtest.py my_strategy.json --data data/klines \\
        --set risk.stop_loss_pct=2 --out result.json
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import csv
import glob
import heapq
import io
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.indicators.registry import get_registry  # noqa: E402
from core.models import Candle  # noqa: E402
from core.timeframe.aggregator import TimeframeAggregator  # noqa: E402
from engine.config import EngineConfig  # noqa: E402
from engine.runner import TradingRunner  # noqa: E402

BINANCE_URL = "https://data.binance.vision/data/spot/{period}/klines/{pair}/1m/{pair}-1m-{date}.zip"
TF_MINUTES = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
WARMUP_CANDLES = 500


# ----------------------------------------------------------------------
# Strategies
# ----------------------------------------------------------------------

def seed_strategies() -> dict[str, dict[str, Any]]:
    """Read STRATEGIES from seed_strategies.py without importing it (no DB deps)."""
    src = (REPO / "scripts" / "seed_strategies.py").read_text(encoding="utf-8")
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "STRATEGIES":
            return {s["name"]: s["definition"] for s in ast.literal_eval(node.value)}
    raise RuntimeError("STRATEGIES not found in seed_strategies.py")


def load_strategy(ref: str) -> dict[str, Any]:
    """Load a strategy from a JSON file path or a seed template name."""
    if ref.endswith(".json") and os.path.isfile(ref):
        with open(ref, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("definition", data)
    seeds = seed_strategies()
    if ref not in seeds:
        raise SystemExit(f"Unknown strategy {ref!r}. Seeds: {', '.join(seeds)}")
    return json.loads(json.dumps(seeds[ref]))


def apply_overrides(defn: dict[str, Any], overrides: list[str]) -> None:
    """Apply ``dotted.path=value`` overrides (value parsed as JSON when possible)."""
    for item in overrides:
        path, _, raw = item.partition("=")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        node = defn
        keys = path.split(".")
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------

def month_range(start: str, end: str) -> list[str]:
    year, month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))
    months = []
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def _fetch(data_dir: str, pair: str, period: str, date: str) -> bool:
    path = os.path.join(data_dir, f"{pair}-1m-{date}.zip")
    if os.path.exists(path):
        return True
    url = BINANCE_URL.format(period=period, pair=pair, date=date)
    try:
        urllib.request.urlretrieve(url, path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    print(f"downloaded {url}", file=sys.stderr)
    return True


def download(data_dir: str, pairs: list[str], months: list[str]) -> None:
    """Fetch monthly files; the current month only exists as daily files."""
    os.makedirs(data_dir, exist_ok=True)
    for pair in pairs:
        for month in months:
            if glob.glob(os.path.join(data_dir, f"{pair}-1m-{month}*.zip")):
                continue
            if _fetch(data_dir, pair, "monthly", month):
                continue
            day = datetime.strptime(month, "%Y-%m")
            while day.strftime("%Y-%m") == month and day < datetime.utcnow():
                _fetch(data_dir, pair, "daily", day.strftime("%Y-%m-%d"))
                day += timedelta(days=1)


def candle_stream(data_dir: str, pair: str, months: list[str] | None) -> Iterator[tuple[float, str, Candle]]:
    files = sorted(glob.glob(os.path.join(data_dir, f"{pair}-1m-*.zip")))
    if months:
        # Matches monthly (PAIR-1m-YYYY-MM.zip) and daily (PAIR-1m-YYYY-MM-DD.zip) files.
        prefixes = tuple(f"{pair}-1m-{m}" for m in months)
        files = [f for f in files if os.path.basename(f).startswith(prefixes)]
    if not files:
        raise SystemExit(f"No data for {pair} in {data_dir} (use --download)")
    for path in files:
        with zipfile.ZipFile(path) as zf, zf.open(zf.namelist()[0]) as fh:
            for row in csv.reader(io.TextIOWrapper(fh, encoding="ascii")):
                if not row[0].isdigit():
                    continue
                ts = int(row[0])
                # Binance switched spot timestamps to microseconds in 2025.
                ts_s = ts / 1_000_000 if ts > 10**14 else ts / 1000
                yield ts_s, pair, Candle(
                    timestamp=datetime.fromtimestamp(ts_s, tz=timezone.utc).replace(tzinfo=None),
                    open=float(row[1]), high=float(row[2]), low=float(row[3]),
                    close=float(row[4]), volume=float(row[5]),
                    pair=pair, timeframe="1m", is_closed=True,
                )


# ----------------------------------------------------------------------
# Replay
# ----------------------------------------------------------------------

async def replay(defn: dict[str, Any], data_dir: str, months: list[str] | None,
                 capital: float, fee_pct: float) -> dict[str, Any]:
    get_registry().discover()
    pairs = defn["pairs"]
    config = EngineConfig(pairs=pairs, dry_run=True, capital_per_pair=capital / len(pairs),
                          dry_run_fee_pct=fee_pct)
    runner = TradingRunner(config=config)
    runner._strategy_config = runner._strategy_loader.load_from_dict(json.loads(json.dumps(defn)))
    runner._setup_timeframe_aggregator()
    tf = runner._effective_strategy_tf
    runner._running = True
    start_balance = runner._balance

    # _daily_trades is cleared at each UTC day change: archive it just before.
    archive: list = []
    original_roll = runner._roll_daily_stats

    async def roll(ts: Any) -> None:
        before = runner._daily_trades
        await original_roll(ts)
        if runner._daily_trades is not before:
            archive.extend(before)

    runner._roll_daily_stats = roll

    warm_agg = TimeframeAggregator([tf]) if tf != "1m" else None
    warm: dict[str, list[Candle]] | None = {p: [] for p in pairs}
    warm_until = None
    first_px: dict[str, float] = {}
    last_px: dict[str, float] = {}
    peak, max_dd, count = start_balance, 0.0, 0

    def equity() -> float:
        return runner._balance + sum(pos.quantity * last_px[pos.pair]
                                     for pos in runner._open_positions.values())

    streams = (candle_stream(data_dir, p, months) for p in pairs)
    for _, pair, candle in heapq.merge(*streams, key=lambda x: (x[0], x[1])):
        count += 1
        first_px.setdefault(pair, candle.close)
        last_px[pair] = candle.close
        if warm_until is None:
            warm_until = candle.timestamp + timedelta(minutes=WARMUP_CANDLES * TF_MINUTES[tf])
        if candle.timestamp < warm_until:
            htf = warm_agg.on_candle(candle) if warm_agg else [candle]
            warm[pair].extend(c for c in htf if c.timeframe == tf)
            continue
        if warm is not None:
            # End of warmup: same path as _initialize_pair() in production.
            for p, history in warm.items():
                runner._warm_up_indicators(p, history)
            warm = None
        await runner.on_candle({
            "pair": pair, "timeframe": "1m", "timestamp": candle.timestamp.isoformat() + "+00:00",
            "open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close,
            "volume": candle.volume, "is_closed": True,
        })
        if count % 60 == 0:
            eq = equity()
            peak = max(peak, eq)
            max_dd = max(max_dd, (peak - eq) / peak * 100)

    trades = archive + list(runner._daily_trades)
    wins = [t for t in trades if t.pnl_usdt > 0]
    gross_win = sum(t.pnl_usdt for t in wins)
    gross_loss = -sum(t.pnl_usdt for t in trades if t.pnl_usdt <= 0)
    reasons: dict[str, int] = {}
    for t in trades:
        key = (t.exit_reason or "").split(" ")[0]
        reasons[key] = reasons.get(key, 0) + 1
    return {
        "strategy": defn.get("name"), "pairs": pairs, "timeframe": tf, "candles_1m": count,
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "return_pct": round((equity() - start_balance) / start_balance * 100, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "fees_usdt": round(sum(t.fees for t in trades), 2),
        "exit_reasons": reasons,
        "open_at_end": len(runner._open_positions),
        "buy_hold_pct": {p: round((last_px[p] / first_px[p] - 1) * 100, 2) for p in first_px},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("strategy", nargs="?", help="Seed template name or strategy JSON file")
    parser.add_argument("--list", action="store_true", help="List seed templates and exit")
    parser.add_argument("--data", default="data/klines", help="Directory of Binance 1m zip files")
    parser.add_argument("--start", help="First month YYYY-MM (default: all files)")
    parser.add_argument("--end", help="Last month YYYY-MM")
    parser.add_argument("--download", action="store_true", help="Fetch missing months first")
    parser.add_argument("--pairs", help="Comma-separated pairs overriding the strategy's")
    parser.add_argument("--set", action="append", default=[], metavar="PATH=VALUE",
                        help="Override a definition field, e.g. risk.stop_loss_pct=2")
    parser.add_argument("--capital", type=float, default=1000.0)
    parser.add_argument("--fee-pct", type=float, default=0.1, help="Fee per side in percent")
    parser.add_argument("--out", help="Write the JSON result to this file")
    args = parser.parse_args()

    if args.list:
        print("\n".join(seed_strategies()))
        return
    if not args.strategy:
        parser.error("strategy is required")

    defn = load_strategy(args.strategy)
    if args.pairs:
        defn["pairs"] = args.pairs.split(",")
    apply_overrides(defn, args.set)

    months = None
    if args.start:
        months = month_range(args.start, args.end or args.start)
        if args.download:
            download(args.data, defn["pairs"], months)

    logging.disable(logging.CRITICAL)
    t0 = time.time()
    result = asyncio.run(replay(defn, args.data, months, args.capital, args.fee_pct))
    result["runtime_s"] = round(time.time() - t0, 1)
    text = json.dumps(result, indent=1, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
