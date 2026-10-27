#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "youtube-transcript-api>=1.0",
#     "yfinance>=0.2.40",
# ]
# ///
# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 Jorge MB
"""
CLI auxiliar para el Agent Skill 'fintube-analyst-auditor'.
Compatible con el estandar Agent Skills (agentskills.io).

Todos los subcomandos imprimen JSON por stdout y salen con codigo != 0 si hay error.
"""

import argparse
import json
import logging
import math
import re
import sys
import unicodedata
import urllib.request
import warnings
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

PORTFOLIO_PATH = Path.home() / ".fintube" / "portfolio.json"
SIGNALS_PATH = Path.home() / ".fintube" / "signals.json"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def emit(payload: dict, indent=2) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=indent))


# Codigos de salida: 2 = entrada invalida, 3 = error remoto (YouTube/Yahoo), 4 = falta dependencia.
EXIT_INVALID, EXIT_REMOTE, EXIT_DEPENDENCY = 2, 3, 4


def fail(message: str, code: int = EXIT_INVALID, **extra) -> None:
    emit({"status": "error", "message": message, **extra})
    sys.exit(code)


def http_get(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_date(value: str, flag: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        fail(f"{flag} debe tener formato YYYY-MM-DD (recibido: {value!r})")


def load_store(path: Path, default: dict) -> dict:
    """Lee un JSON local de ~/.fintube; si esta danado no lo toca y remite a la copia .bak."""
    backup_path = path.with_suffix(".json.bak")
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("se esperaba un objeto JSON")
        return data
    except ValueError as exc:  # incluye json.JSONDecodeError
        fail(
            f"{path} esta danado ({exc}). No se ha modificado.",
            backup=str(backup_path) if backup_path.exists() else None,
            hint="Restaura la copia .bak o corrige el JSON a mano antes de seguir.",
        )


def save_store(path: Path, data: dict) -> None:
    """Guarda con copia .bak de la version anterior y escritura atomica (tmp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.with_suffix(".json.bak").write_bytes(path.read_bytes())
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def extract_video_id(url_or_id: str) -> str:
    patterns = [
        r"(?:v=|/live/|youtu\.be/|/embed/|/shorts/)([0-9A-Za-z_-]{11})",
        r"^([0-9A-Za-z_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id.strip())
        if match:
            return match.group(1)
    return url_or_id.strip()


# --------------------------------------------------------------------------- resolve-channel

def cmd_resolve_channel(args):
    """Convierte @handle o URL de canal en channel_id (UC...) para usar en scan-rss."""
    raw = args.channel.strip()
    if re.fullmatch(r"UC[0-9A-Za-z_-]{22}", raw):
        emit({"status": "ok", "channel_id": raw, "source": "input"})
        return

    if raw.startswith("http"):
        url = raw
    else:
        handle = raw if raw.startswith("@") else f"@{raw}"
        url = f"https://www.youtube.com/{handle}"

    try:
        html = http_get(url).decode("utf-8", errors="replace")
    except Exception as exc:
        fail(f"No se pudo abrir {url}: {exc}", code=EXIT_REMOTE)

    match = (
        re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[0-9A-Za-z_-]{22})"', html)
        or re.search(r'"externalId":"(UC[0-9A-Za-z_-]{22})"', html)
        or re.search(r'"channelId":"(UC[0-9A-Za-z_-]{22})"', html)
    )
    if not match:
        fail(f"No se encontro channel_id en {url}", code=EXIT_REMOTE)

    title_match = re.search(r'<meta property="og:title" content="([^"]*)"', html)
    channel_id = match.group(1)
    emit(
        {
            "status": "ok",
            "channel_id": channel_id,
            "channel_title": title_match.group(1) if title_match else None,
            "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
            "source": url,
        }
    )


# --------------------------------------------------------------------------- scan-rss

def compile_regex(pattern, flag: str):
    if not pattern:
        return None
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        fail(f"Expresion regular invalida en {flag}: {exc}. Escapa los parentesis con \\( o quitalos.")


def cmd_scan_rss(args):
    if args.playlist_id:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={args.playlist_id}"
    else:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={args.channel_id}"

    try:
        root = ET.fromstring(http_get(rss_url))
    except Exception as exc:
        fail(f"Error leyendo RSS: {exc}", code=EXIT_REMOTE, rss_url=rss_url)

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    inc_pattern = compile_regex(args.keyword, "--keyword")
    exc_pattern = compile_regex(args.exclude, "--exclude")
    since = parse_date(args.since, "--since") if args.since else None

    matched_videos = []
    discarded_videos = []
    for entry in root.findall("atom:entry", ns):
        video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
        title = entry.findtext("atom:title", default="", namespaces=ns)
        published = entry.findtext("atom:published", default="", namespaces=ns)
        link_el = entry.find("atom:link", ns)
        url = link_el.attrib.get("href") if link_el is not None else None

        item = {
            "video_id": video_id,
            "title": title,
            "published_at": published[:10],
            "url": url or f"https://www.youtube.com/watch?v={video_id}",
        }

        if since and published[:10] and datetime.strptime(published[:10], "%Y-%m-%d") < since:
            item["reason"] = "Anterior a --since"
            discarded_videos.append(item)
            continue
        if exc_pattern and exc_pattern.search(title):
            item["reason"] = "Excluido por patron negativo"
            discarded_videos.append(item)
            continue
        if inc_pattern and not inc_pattern.search(title):
            item["reason"] = "No contiene palabra clave del analista/seccion"
            discarded_videos.append(item)
            continue
        matched_videos.append(item)

    emit(
        {
            "status": "ok",
            "rss_url": rss_url,
            "feed_title": root.findtext("atom:title", default="", namespaces=ns),
            "note": "El RSS de YouTube solo expone los ~15 videos mas recientes.",
            "matched_count": len(matched_videos),
            "matched_videos": matched_videos[: args.limit],
            "discarded_count": len(discarded_videos),
            "discarded_sample": discarded_videos[:5],
        }
    )


# --------------------------------------------------------------------------- transcript

def format_seconds(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"[{hrs:02d}:{mins:02d}:{secs:02d}]"


def cmd_transcript(args):
    video_id = extract_video_id(args.video)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        fail("Falta youtube-transcript-api. Ejecuta con `uv run` o instala: pip install youtube-transcript-api", code=EXIT_DEPENDENCY)

    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
    except Exception as exc:
        fail(
            f"{type(exc).__name__}: {exc}",
            code=EXIT_REMOTE,
            video_id=video_id,
            hint="Si es un bloqueo de IP de YouTube, reintenta mas tarde o desde otra red.",
        )

    # Agrupa los fragmentos en bloques de N segundos para reducir tokens sin perder la marca de tiempo.
    blocks = []
    block_start = None
    block_text = []
    total_duration = 0.0
    for snippet in fetched:
        start = float(snippet.start)
        total_duration = max(total_duration, start + float(snippet.duration))
        text = snippet.text.replace("\n", " ").strip()
        if not text:
            continue
        if block_start is None:
            block_start = start
        elif start - block_start >= args.chunk_seconds:
            blocks.append(f"{format_seconds(block_start)} {' '.join(block_text)}")
            block_start, block_text = start, []
        block_text.append(text)
    if block_text:
        blocks.append(f"{format_seconds(block_start)} {' '.join(block_text)}")

    emit(
        {
            "status": "ok",
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "language": getattr(fetched, "language_code", None),
            "is_generated": getattr(fetched, "is_generated", None),
            "estimated_duration_minutes": round(total_duration / 60.0, 1),
            "transcript": "\n".join(blocks),
        },
        indent=None,
    )


# --------------------------------------------------------------------------- audit

# Valores del Mercado Continuo cuyo simbolo sin sufijo es otra empresa (o nada) en Yahoo:
# p. ej. "IAG" es IAMGOLD (NYSE) y "SAN" el ADR de Santander en dolares.
SPANISH_TICKERS = {
    "SAN", "BBVA", "CABK", "SAB", "BKT", "UNI", "MAP", "REP", "ITX", "PUIG", "TEF", "CLNX",
    "AMS", "IDR", "IAG", "AENA", "MEL", "ACS", "FER", "SCYR", "MTS", "ACX", "GRF", "ROVI",
    "MRL", "COL", "LOG", "FDR", "IBE", "ELE", "NTGY", "ENG", "RED", "ANA", "ANE", "SLR",
}
INDEX_ALIASES = {
    "IBEX": "^IBEX", "IBEX35": "^IBEX", "IBEX 35": "^IBEX",
    "STOXX50": "^STOXX50E", "EUROSTOXX": "^STOXX50E", "EUROSTOXX50": "^STOXX50E",
    "DAX": "^GDAXI", "CAC": "^FCHI", "CAC40": "^FCHI",
    "SP500": "^GSPC", "S&P500": "^GSPC", "NASDAQ": "^IXIC", "NASDAQ100": "^NDX", "NDX": "^NDX",
}


def normalize_ticker(raw: str, warnings_out: list) -> str:
    ticker = raw.strip().upper()
    if ticker in INDEX_ALIASES:
        fixed = INDEX_ALIASES[ticker]
    elif ticker in SPANISH_TICKERS:
        fixed = f"{ticker}.MC"
    else:
        return ticker
    warnings_out.append(f"{raw} interpretado como {fixed}. Usa --raw-tickers si querias el simbolo literal.")
    return fixed


# Historicos ya descargados por ticker: (inicio, fin, DataFrame o None, metadatos).
# scorecard mide muchas ventanas del mismo valor y asi solo pide una vez cada ticker a Yahoo.
_HISTORY_CACHE = {}


def load_history(yf, ticker: str, start: datetime, end: datetime):
    """Devuelve (DataFrame con precios nominales y 'Adj Close', metadatos) o (None, {})."""
    cached = _HISTORY_CACHE.get(ticker)
    if cached is None or start < cached[0] or end > cached[1]:
        fetch_start, fetch_end = (start, end) if cached is None else (min(start, cached[0]), max(end, cached[1]))
        tk = yf.Ticker(ticker)
        hist = tk.history(start=fetch_start, end=fetch_end, auto_adjust=False)
        meta = {}
        if hist is not None and not hist.empty:
            hist = hist.dropna(subset=["Close"])
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)
            raw_meta = getattr(tk, "history_metadata", None) or {}
            meta = {"currency": raw_meta.get("currency"), "exchange": raw_meta.get("exchangeName")}
        else:
            hist = None
        cached = _HISTORY_CACHE[ticker] = (fetch_start, fetch_end, hist, meta)
    hist, meta = cached[2], cached[3]
    if hist is None:
        return None, {}
    window = hist[(hist.index >= start) & (hist.index < end)]
    return (window, meta) if not window.empty else (None, {})


def first_touch(window, column: str, level: float, above: bool):
    """Primera fecha en que el precio intradia nominal toca el nivel (por arriba o por abajo)."""
    hits = window[window[column] >= level] if above else window[window[column] <= level]
    return str(hits.index[0])[:10] if not hits.empty else None


def measure(yf, ticker: str, signal_dt: datetime, eval_dt: datetime, side="BUY", stop=None, target=None):
    hist, meta = load_history(yf, ticker, signal_dt - timedelta(days=5), eval_dt + timedelta(days=2))
    if hist is None:
        return None
    start_rows = hist[hist.index >= signal_dt]
    eval_rows = hist[hist.index < eval_dt + timedelta(days=1)]
    if start_rows.empty or eval_rows.empty:
        return None
    first, last = start_rows.iloc[0], eval_rows.iloc[-1]
    window = hist[(hist.index >= signal_dt) & (hist.index < eval_dt + timedelta(days=1))]

    # Rentabilidad total con precios ajustados (incluye dividendos); niveles con precios nominales,
    # que son los que ve el inversor en el grafico y donde saltan los stops.
    adj_start, adj_eval = float(first["Adj Close"]), float(last["Adj Close"])
    nom_start, nom_eval = float(first["Close"]), float(last["Close"])
    result = {
        **meta,
        "signal_date_used": str(start_rows.index[0])[:10],
        "price_at_signal": round(nom_start, 4),
        "eval_date_used": str(eval_rows.index[-1])[:10],
        "eval_price": round(nom_eval, 4),
        "return_pct": round((adj_eval - adj_start) / adj_start * 100.0, 2),
        "price_return_pct": round((nom_eval - nom_start) / nom_start * 100.0, 2),
        "max_price_in_window": round(float(window["High"].max()), 4) if not window.empty else None,
        "min_price_in_window": round(float(window["Low"].min()), 4) if not window.empty else None,
    }
    if stop is not None or target is not None:
        buy = side == "BUY"
        stop_date = first_touch(window, "Low" if buy else "High", stop, above=not buy) if stop is not None else None
        target_date = first_touch(window, "High" if buy else "Low", target, above=buy) if target is not None else None
        hits = [(d, name) for d, name in ((stop_date, "stop"), (target_date, "target")) if d]
        result.update(
            {
                "side": side,
                "stop": stop,
                "stop_hit_date": stop_date,
                "target": target,
                "target_hit_date": target_date,
                # Si ambos caen el mismo dia no se sabe cual fue antes sin datos intradia.
                "first_event": (
                    "ambiguous_same_day" if len(hits) == 2 and stop_date == target_date
                    else min(hits)[1] if hits else None
                ),
            }
        )
    return result


def cmd_audit(args):
    try:
        import yfinance as yf
    except ImportError:
        fail("Falta yfinance. Ejecuta con `uv run` o instala: pip install yfinance", code=EXIT_DEPENDENCY)
    # yfinance reconfigura los filtros al importarse: silenciar despues para no ensuciar la salida.
    warnings.simplefilter("ignore")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    ticker_warnings = []
    raw = [t.strip() for t in args.tickers.split(",") if t.strip()]
    tickers = raw if args.raw_tickers else [normalize_ticker(t, ticker_warnings) for t in raw]
    benchmark_ticker = args.benchmark
    if benchmark_ticker and not args.raw_tickers:
        benchmark_ticker = normalize_ticker(benchmark_ticker, ticker_warnings)
    if (args.stop is not None or args.target_price is not None) and len(tickers) != 1:
        fail("--stop y --target-price solo se pueden usar con un unico ticker")
    signal_dt = parse_date(args.signal_date, "--signal-date")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if signal_dt > today:
        fail("--signal-date esta en el futuro")

    target_dt = parse_date(args.target_date, "--target-date") if args.target_date else None
    # Se evalua en la fecha objetivo si ya ha pasado; si no, a dia de hoy.
    eval_dt = target_dt if target_dt and target_dt <= today else today
    target_reached = bool(target_dt and target_dt <= today)

    benchmark = None
    if benchmark_ticker:
        benchmark = measure(yf, benchmark_ticker, signal_dt, eval_dt)
        if benchmark is None:
            ticker_warnings.append(f"Sin datos para el benchmark {benchmark_ticker}; alpha no calculado.")

    results = []
    for ticker in tickers:
        data = measure(yf, ticker, signal_dt, eval_dt, side=args.side, stop=args.stop, target=args.target_price)
        if data is None:
            results.append({"ticker": ticker, "error": "Sin datos en Yahoo Finance (revisa el ticker)"})
            continue
        bm_ret = benchmark["return_pct"] if benchmark else None
        results.append(
            {
                "ticker": ticker,
                **data,
                "benchmark_ticker": benchmark_ticker,
                "benchmark_return_pct": bm_ret,
                "alpha_pct": round(data["return_pct"] - bm_ret, 2) if bm_ret is not None else None,
            }
        )

    emit(
        {
            "status": "ok",
            "signal_date": args.signal_date,
            "target_date": args.target_date,
            "target_reached": target_reached,
            "eval_date": eval_dt.strftime("%Y-%m-%d"),
            "warnings": ticker_warnings,
            "benchmark": {"ticker": benchmark_ticker, **benchmark} if benchmark else None,
            "audits": results,
            "note": (
                "return_pct es rentabilidad total (precios ajustados por dividendos) y es la que se compara con el benchmark; "
                "price_return_pct es solo precio. Precios, max/min (intradia) y stops son nominales. "
                "Para senales VENDER, una caida es un acierto. Comprueba currency/exchange: un valor espanol debe cotizar en EUR."
            ),
        }
    )


# --------------------------------------------------------------------------- portfolio

def summarize_positions(positions: list) -> list:
    """Agrupa los lotes por ticker con acciones totales y precio medio ponderado."""
    summary = {}
    for lot in positions:
        s = summary.setdefault(lot["ticker"], {"ticker": lot["ticker"], "lots": 0, "shares": 0.0, "cost": 0.0})
        s["lots"] += 1
        s["shares"] += lot.get("shares") or 0.0
        s["cost"] += (lot.get("shares") or 0.0) * (lot.get("buy_price") or 0.0)
    return [
        {
            "ticker": s["ticker"],
            "lots": s["lots"],
            "total_shares": round(s["shares"], 6),
            "avg_buy_price": round(s["cost"] / s["shares"], 4) if s["shares"] else None,
        }
        for s in summary.values()
    ]


def cmd_portfolio(args):
    data = load_store(PORTFOLIO_PATH, {"positions": [], "followed_analysts": []})
    data.setdefault("positions", [])
    data.setdefault("followed_analysts", [])

    # Las carteras antiguas guardaban una posicion por ticker sin id: se convierten en lotes.
    next_id = max((p.get("id", 0) for p in data["positions"]), default=0) + 1
    for lot in data["positions"]:
        if "id" not in lot:
            lot["id"], next_id = next_id, next_id + 1

    def save():
        save_store(PORTFOLIO_PATH, data)

    if args.action == "list":
        emit(
            {
                "status": "ok",
                "portfolio_file": str(PORTFOLIO_PATH),
                "summary": summarize_positions(data["positions"]),
                "data": data,
            }
        )
        return

    if args.action in ("add", "remove") and not args.ticker:
        fail(f"--ticker es obligatorio para --action {args.action}")

    if args.action == "add":
        if args.shares <= 0 or args.buy_price <= 0:
            fail("--shares y --buy-price deben ser mayores que 0 (las posiciones cortas no estan soportadas)")
        if args.buy_date:
            parse_date(args.buy_date, "--buy-date")
        lot = {
            "id": next_id,
            "ticker": args.ticker.upper(),
            "shares": args.shares,
            "buy_price": args.buy_price,
            "buy_date": args.buy_date or datetime.now().strftime("%Y-%m-%d"),
            "analyst": args.analyst,
            "recommendation": args.recommendation,
            "target_date": args.target_date,
            "status": "OPEN",
        }
        data["positions"].append(lot)
        save()
        summary = [s for s in summarize_positions(data["positions"]) if s["ticker"] == lot["ticker"]]
        emit({"status": "saved", "lot": lot, "position": summary[0]})
        return

    if args.action == "remove":
        ticker = args.ticker.upper()
        if args.lot_id is None and not args.all_lots:
            fail(
                "Indica --lot-id para borrar un lote o --all-lots para borrar todos los de ese ticker",
                lots=[p for p in data["positions"] if p.get("ticker") == ticker],
            )
        before = len(data["positions"])
        data["positions"] = [
            p for p in data["positions"]
            if not (p.get("ticker") == ticker and (args.all_lots or p.get("id") == args.lot_id))
        ]
        removed = before - len(data["positions"])
        if removed:
            save()
        emit({"status": "removed" if removed else "not_found", "ticker": ticker, "lots_removed": removed})
        return

    if args.action == "follow":
        if not args.analyst:
            fail("--analyst es obligatorio para --action follow")
        follow = {"analyst": args.analyst, "channel_id": args.channel_id, "keyword": args.keyword}
        data["followed_analysts"] = [a for a in data["followed_analysts"] if a.get("analyst") != args.analyst]
        data["followed_analysts"].append(follow)
        save()
        emit({"status": "saved", "followed": follow})


# --------------------------------------------------------------------------- signals (historial)

# Se guarda lo que dijo cada video (una mencion por ticker); la vida de cada senal (apertura,
# revisiones de niveles y cierre) se reconstruye recorriendo los videos por fecha. Asi reprocesar
# un video lo sustituye en vez de duplicarlo y se pueden registrar videos antiguos mas tarde.
SIGNAL_VALUES = ("BUY", "HOLD", "SELL", "CLOSE")
LEVEL_FIELDS = ("entry_level", "stop_loss", "target_price")
REVISABLE_FIELDS = LEVEL_FIELDS + ("expiry_date",)
MENTION_TEXT_FIELDS = ("asset_name", "person", "confidence", "expiry_reason", "timestamp", "quote")
CLOSE_REASONS = ("REVERSED", "CLOSED_BY_ANALYST", "EXPIRED", "ABANDONED")
DEFAULT_ABANDON_AFTER = 5
MIN_SAMPLE = 20
ENTRY_TOLERANCE_PCT = 1.0  # entrada a menos de esta distancia del precio = compra/venta a mercado


def analyst_key(name: str) -> str:
    """'Especulación en  Bolsa' y 'especulacion en bolsa' son el mismo analista."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(plain.lower().split())


def default_benchmark(ticker: str):
    if ticker.startswith("^") or re.search(r"(=F|=X|-USD|-EUR)$", ticker):
        return None  # indices, materias primas, divisas y cripto no tienen indice de referencia obvio
    if ticker.endswith(".MC"):
        return "^IBEX"
    if re.search(r"\.(PA|DE|MI|AS|BR|LS|HE|IR|VI)$", ticker):
        return "^STOXX50E"
    return "^GSPC" if "." not in ticker else None


def timestamp_url(video_id: str, timestamp):
    match = re.fullmatch(r"\[?(?:(\d+):)?(\d{1,2}):(\d{2})\]?", (timestamp or "").strip())
    if not match:
        return None
    hrs, mins, secs = (int(g or 0) for g in match.groups())
    return f"https://www.youtube.com/watch?v={video_id}&t={hrs * 3600 + mins * 60 + secs}s"


def read_json_input(source: str):
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"No se pudo leer --input {source}: {exc}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"--input no es JSON valido: {exc}")


def check_date(value, where: str) -> str:
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        fail(f"{where} debe tener formato YYYY-MM-DD (recibido: {value!r})")
    return str(value)


def parse_level(value, where: str):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        fail(f"{where} debe ser un numero mayor que 0 o null, con punto decimal (recibido: {value!r})")
    return float(value)


def parse_video_record(payload, warnings_out: list) -> dict:
    """Valida la entrada de 'signals --action record' y la deja en el formato guardado."""
    if not isinstance(payload, dict):
        fail("--input debe ser un objeto JSON con analyst, video_id, published_at y signals")
    analyst = str(payload.get("analyst") or "").strip()
    if not analyst:
        fail("Falta analyst (p. ej. \"Especulacion en Bolsa\")")
    video_id = extract_video_id(str(payload.get("video_id") or payload.get("url") or ""))
    if not re.fullmatch(r"[0-9A-Za-z_-]{11}", video_id):
        fail(f"video_id invalido: {video_id!r}")
    published_at = check_date(payload.get("published_at"), "published_at")
    if published_at > datetime.now().strftime("%Y-%m-%d"):
        fail("published_at esta en el futuro")
    raw_signals = payload.get("signals")
    if not isinstance(raw_signals, list):
        fail("Falta la lista signals (usa [] si el video no tiene senales: tambien cuenta para detectar abandonos)")

    mentions, seen = [], {}
    for i, raw in enumerate(raw_signals):
        where = f"signals[{i}]"
        if not isinstance(raw, dict):
            fail(f"{where} debe ser un objeto")
        for field in ("video_id", "published_at"):
            if raw.get(field) not in (None, payload.get(field)):
                fail(f"{where}.{field} no coincide con el del video: registra cada video por separado")
        ticker_raw = str(raw.get("ticker") or "").strip()
        if not ticker_raw or " " in ticker_raw:
            fail(f"{where}.ticker invalido: {ticker_raw!r}")
        ticker = normalize_ticker(ticker_raw, warnings_out)
        if ticker in seen:
            fail(f"{where}: {ticker} ya aparece en signals[{seen[ticker]}]. Deja una sola senal por valor y video (la ultima o la mas clara).")
        seen[ticker] = i
        signal = str(raw.get("signal") or "").strip().upper()
        if signal not in SIGNAL_VALUES:
            fail(f"{where}.signal debe ser uno de {', '.join(SIGNAL_VALUES)} (recibido: {raw.get('signal')!r})")
        if "benchmark" in raw:
            benchmark = normalize_ticker(raw["benchmark"], warnings_out) if raw["benchmark"] else None
        else:
            benchmark = default_benchmark(ticker)
        mention = {"ticker": ticker, "signal": signal, "benchmark": benchmark}
        for field in LEVEL_FIELDS:
            mention[field] = parse_level(raw.get(field), f"{where}.{field}")
        mention["expiry_date"] = check_date(raw["expiry_date"], f"{where}.expiry_date") if raw.get("expiry_date") else None
        for field in MENTION_TEXT_FIELDS:
            if raw.get(field) not in (None, ""):
                mention[field] = str(raw[field])
        mentions.append(mention)

    record = {"analyst": analyst, "video_id": video_id, "published_at": published_at, "mentions": mentions}
    if payload.get("title"):
        record["title"] = str(payload["title"])
    return record


def mention_snapshot(video: dict, mention: dict) -> dict:
    snap = {"date": video["published_at"], "video_id": video["video_id"], "signal": mention["signal"]}
    for field in REVISABLE_FIELDS + ("timestamp", "person", "confidence", "quote"):
        if mention.get(field) is not None:
            snap[field] = mention[field]
    url = timestamp_url(video["video_id"], mention.get("timestamp"))
    if url:
        snap["timestamp_url"] = url
    return snap


def build_history(videos: list, abandon_after: int, today: str) -> dict:
    """Reconstruye las senales de cada analista recorriendo sus videos por fecha de publicacion."""
    threads, events, neutral = [], [], []
    by_analyst = {}
    for video in videos:
        by_analyst.setdefault(analyst_key(video["analyst"]), []).append(video)

    for vids in by_analyst.values():
        vids.sort(key=lambda v: (v["published_at"], v.get("recorded_at", ""), v["video_id"]))
        open_threads, last_neutral = {}, {}

        def event(video, ticker, kind, **extra):
            events.append({"video_id": video["video_id"], "ticker": ticker, "event": kind, **extra})

        def close(thread, reason, date, video=None, mention=None):
            thread["status"] = "CLOSED"
            thread["closed"] = {"reason": reason, "date": date}
            if video is not None:
                thread["closed"].update(mention_snapshot(video, mention) if mention else {"video_id": video["video_id"]})
                thread["closed"]["date"] = date
            del open_threads[thread["ticker"]]

        def open_thread(video, mention):
            thread = {
                "id": f"{mention['ticker']}@{video['video_id']}",
                "analyst": video["analyst"],
                "ticker": mention["ticker"],
                "asset_name": mention.get("asset_name"),
                "benchmark": mention["benchmark"],
                "side": mention["signal"],
                "status": "OPEN",
                "opened": mention_snapshot(video, mention),
                "current": {f: mention.get(f) for f in REVISABLE_FIELDS},
                "mentions": 1,
                "last_mentioned": video["published_at"],
                "revisions": [],
                "closed": None,
                "_set_on": {f: video["published_at"] for f in REVISABLE_FIELDS},
                "_missed": 0,
            }
            open_threads[mention["ticker"]] = thread
            threads.append(thread)
            last_neutral.pop(mention["ticker"], None)
            return thread

        for video in vids:
            date = video["published_at"]
            for thread in list(open_threads.values()):
                expiry = thread["current"]["expiry_date"]
                if expiry and expiry < date:
                    close(thread, "EXPIRED", expiry)
                    event(video, thread["ticker"], "EXPIRED", signal_id=thread["id"], expiry_date=expiry)

            mentioned = set()
            for mention in video["mentions"]:
                ticker, signal = mention["ticker"], mention["signal"]
                mentioned.add(ticker)
                thread = open_threads.get(ticker)
                if thread is None:
                    if signal in ("BUY", "SELL"):
                        new = open_thread(video, mention)
                        event(video, ticker, "NEW", signal_id=new["id"], side=signal)
                    elif signal == "HOLD":
                        last_neutral[ticker] = {"analyst": video["analyst"], "ticker": ticker, **mention_snapshot(video, mention)}
                        event(video, ticker, "NEUTRAL", note="MANTENER/NEUTRO sin senal abierta: se guarda pero no puntua")
                    else:
                        event(video, ticker, "IGNORED", note="CLOSE sin senal abierta de ese valor")
                    continue

                thread["_missed"] = 0
                if signal == "CLOSE":
                    close(thread, "CLOSED_BY_ANALYST", date, video, mention)
                    event(video, ticker, "CLOSED", signal_id=thread["id"])
                elif signal in ("BUY", "SELL") and signal != thread["side"]:
                    close(thread, "REVERSED", date, video, mention)
                    new = open_thread(video, mention)
                    event(video, ticker, "REVERSED", closed_signal_id=thread["id"], signal_id=new["id"], side=signal)
                else:
                    # Misma direccion o MANTENER: sigue la misma senal; solo cuentan los niveles que cambian.
                    thread["mentions"] += 1
                    thread["last_mentioned"] = date
                    thread["asset_name"] = thread["asset_name"] or mention.get("asset_name")
                    changes = []
                    for field in REVISABLE_FIELDS:
                        new_value, old_value = mention.get(field), thread["current"][field]
                        if new_value is None or new_value == old_value:
                            continue
                        changes.append(
                            {
                                "field": field,
                                "from": old_value,
                                "to": new_value,
                                "kind": "set" if old_value is None else "moved",
                                "previous_set_on": thread["_set_on"][field],
                                "date": date,
                                "video_id": video["video_id"],
                                "timestamp": mention.get("timestamp"),
                                "timestamp_url": timestamp_url(video["video_id"], mention.get("timestamp")),
                            }
                        )
                        thread["current"][field] = new_value
                        thread["_set_on"][field] = date
                    thread["revisions"].extend(changes)
                    event(
                        video, ticker, "REVISED" if changes else "CONFIRMED", signal_id=thread["id"], signal=signal,
                        changes=[{k: c[k] for k in ("field", "from", "to")} for c in changes],
                    )

            for thread in list(open_threads.values()):
                if thread["ticker"] in mentioned:
                    continue
                thread["_missed"] += 1
                if abandon_after and thread["_missed"] >= abandon_after:
                    close(thread, "ABANDONED", date)
                    event(video, thread["ticker"], "ABANDONED", signal_id=thread["id"], videos_without_mention=thread["_missed"])

        for thread in list(open_threads.values()):
            expiry = thread["current"]["expiry_date"]
            if expiry and expiry < today:
                close(thread, "EXPIRED", expiry)
        neutral.extend(last_neutral.values())

    for thread in threads:
        thread.pop("_set_on")
        thread.pop("_missed")
    threads.sort(key=lambda t: (t["opened"]["date"], t["analyst"], t["ticker"]))
    return {"threads": threads, "events": events, "neutral": neutral}


def summarize_analysts(videos: list) -> list:
    summary = {}
    for video in videos:
        s = summary.setdefault(analyst_key(video["analyst"]), {"analyst": video["analyst"], "videos_recorded": 0, "dates": []})
        s["videos_recorded"] += 1
        s["dates"].append(video["published_at"])
    return [
        {"analyst": s["analyst"], "videos_recorded": s["videos_recorded"], "first_video": min(s["dates"]), "last_video": max(s["dates"])}
        for s in summary.values()
    ]


def filter_videos(data: dict, analyst) -> list:
    if not analyst:
        return data["videos"]
    key = analyst_key(analyst)
    return [v for v in data["videos"] if analyst_key(v["analyst"]) == key]


def cmd_signals(args):
    data = load_store(SIGNALS_PATH, {"version": 1, "videos": []})
    data.setdefault("videos", [])
    today = datetime.now().strftime("%Y-%m-%d")

    if args.action == "record":
        if not args.input:
            fail("--input es obligatorio para --action record (ruta a un JSON o - para stdin)")
        warnings_out = []
        record = parse_video_record(read_json_input(args.input), warnings_out)
        key = analyst_key(record["analyst"])
        same_analyst = [v for v in data["videos"] if analyst_key(v["analyst"]) == key]
        if same_analyst:
            record["analyst"] = same_analyst[0]["analyst"]  # mismo nombre visible para todo el historial
        existing = next((v for v in same_analyst if v["video_id"] == record["video_id"]), None)
        if existing is not None and {k: v for k, v in existing.items() if k != "recorded_at"} == record:
            result = "unchanged"
        else:
            # Al reprocesar se conserva recorded_at para no alterar el orden de videos del mismo dia.
            record["recorded_at"] = existing["recorded_at"] if existing else datetime.now().isoformat(timespec="seconds")
            if existing is not None:
                data["videos"][data["videos"].index(existing)] = record
            else:
                data["videos"].append(record)
            save_store(SIGNALS_PATH, data)
            result = "replaced" if existing else "created"

        history = build_history(filter_videos(data, record["analyst"]), args.abandon_after, today)
        emit(
            {
                "status": "ok",
                "result": result,
                "signals_file": str(SIGNALS_PATH),
                "analyst": record["analyst"],
                "video_id": record["video_id"],
                "published_at": record["published_at"],
                "warnings": warnings_out,
                "events": [e for e in history["events"] if e["video_id"] == record["video_id"]],
                "open_signals": sum(1 for t in history["threads"] if t["status"] == "OPEN"),
            }
        )
        return

    if args.action == "delete":
        if not args.analyst or not args.video_id:
            fail("--analyst y --video-id son obligatorios para --action delete")
        key, video_id = analyst_key(args.analyst), extract_video_id(args.video_id)
        before = len(data["videos"])
        data["videos"] = [v for v in data["videos"] if not (analyst_key(v["analyst"]) == key and v["video_id"] == video_id)]
        removed = before - len(data["videos"])
        if removed:
            save_store(SIGNALS_PATH, data)
        emit({"status": "ok", "result": "removed" if removed else "not_found", "video_id": video_id, "videos_removed": removed})
        return

    # list
    videos = filter_videos(data, args.analyst)
    history = build_history(videos, args.abandon_after, today)
    threads, neutral = history["threads"], history["neutral"]
    if args.ticker:
        ticker = normalize_ticker(args.ticker, [])
        threads = [t for t in threads if t["ticker"] == ticker]
        neutral = [n for n in neutral if n["ticker"] == ticker]
    if args.status != "all":
        threads = [t for t in threads if t["status"] == args.status.upper()]
    emit(
        {
            "status": "ok",
            "signals_file": str(SIGNALS_PATH),
            "abandon_after": args.abandon_after,
            "analysts": summarize_analysts(videos),
            "count": len(threads),
            "signals": threads,
            "neutral": neutral,
        }
    )


# --------------------------------------------------------------------------- scorecard

def wilson_interval(hits: int, n: int, z: float = 1.96):
    """Intervalo de confianza del 95 % de una proporcion; con pocas senales sale muy ancho."""
    if n == 0:
        return None
    p = hits / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (centre - margin) / denom) * 100, 1), round(min(1.0, (centre + margin) / denom) * 100, 1)]


def as_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def breach_date(yf, ticker: str, side: str, field: str, level: float, set_on: str, moved_on: str):
    """Primera fecha, entre que se fijo el nivel y el dia en que se movio, en que el precio lo rompio (o None).

    Stop: basta con tocarlo intradia (ahi salta la orden). Entrada: un soporte (compra) o una
    resistencia (venta) falla si el cierre lo pierde; un nivel de ruptura no se puede fallar asi.
    Si devuelve el propio `moved_on`, el video pudo publicarse antes o despues de la ruptura.
    """
    start, end = as_date(set_on), as_date(moved_on)
    if end < start:
        return None
    hist, _ = load_history(yf, ticker, start, end + timedelta(days=1))
    if hist is None:
        return None
    buy = side == "BUY"
    if field == "stop_loss":
        return first_touch(hist, "Low" if buy else "High", level, above=not buy)
    reference = float(hist["Close"].iloc[0])
    if (buy and level >= reference) or (not buy and level <= reference):
        return None
    return first_touch(hist, "Close", level, above=not buy)


def evaluate_thread(yf, thread: dict, today: datetime) -> dict:
    opened, closed = thread["opened"], thread["closed"]
    start = as_date(opened["date"])
    end = max(start, as_date(closed["date"]) if closed else today)
    side = thread["side"]
    row = {
        "id": thread["id"], "ticker": thread["ticker"], "side": side, "status": thread["status"],
        "opened_on": opened["date"], "closed_on": closed["date"] if closed else None,
        "close_reason": closed["reason"] if closed else None,
    }

    data = measure(yf, thread["ticker"], start, end)
    if data is None:
        return {**row, "outcome": "NOT_EVALUATED", "reason": "Sin datos en Yahoo Finance (revisa el ticker)"}
    if data["signal_date_used"] > data["eval_date_used"]:
        if closed:
            return {**row, "outcome": "NOT_EVALUATED", "reason": "La senal se cerro sin ninguna sesion de bolsa por medio"}
        return {**row, "outcome": "PROVISIONAL", "reason": "Aun no hay sesiones de bolsa desde la senal"}

    # Una entrada lejos del precio ("compro si cae a 10,85", "si supera 13") es una orden condicionada:
    # la senal no empieza hasta que el precio la toca y, si nunca la toca, no es ni acierto ni fallo.
    price, buy = data["price_at_signal"], side == "BUY"
    entry = opened.get("entry_level")
    if entry is not None and abs(entry - price) / price * 100 > ENTRY_TOLERANCE_PCT:
        hist, _ = load_history(yf, thread["ticker"], start, end + timedelta(days=1))
        triggered = first_touch(hist, "High" if entry > price else "Low", entry, above=entry > price) if hist is not None else None
        row.update({"entry_level": entry, "entry_triggered_on": triggered})
        if triggered is None:
            if closed:
                return {**row, "outcome": "NOT_TRIGGERED", "reason": "El precio no llego a la entrada antes de cerrarse la senal"}
            return {**row, "outcome": "PROVISIONAL", "reason": "Pendiente: el precio aun no ha llegado a la entrada"}
        start = as_date(triggered)
        data = measure(yf, thread["ticker"], start, end) or data
        price = entry

    # Un stop por encima de la entrada en una compra (o un objetivo por debajo) daria un "acierto" o "fallo"
    # instantaneo: suele ser una cifra mal transcrita o de otro instrumento. Se descarta y se avisa.
    stop, target, level_warnings = opened.get("stop_loss"), opened.get("target_price"), []
    if stop is not None and (stop >= price if buy else stop <= price):
        level_warnings.append(f"stop_loss {stop} incoherente con el precio {price} en la senal {side}; ignorado")
        stop = None
    if target is not None and (target <= price if buy else target >= price):
        level_warnings.append(f"target_price {target} incoherente con el precio {price} en la senal {side}; ignorado")
        target = None
    if stop is not None or target is not None:
        data = measure(yf, thread["ticker"], start, end, side=side, stop=stop, target=target) or data
    if level_warnings:
        row["level_warnings"] = level_warnings

    first_event = data.get("first_event")
    if first_event == "target":
        outcome, decided_by = "HIT", "target"
    elif first_event == "stop":
        outcome, decided_by = "MISS", "stop"
    elif first_event == "ambiguous_same_day":
        outcome, decided_by = "NOT_EVALUATED", "ambiguous_same_day"
    elif closed:
        won = data["return_pct"] > 0 if side == "BUY" else data["return_pct"] < 0
        outcome, decided_by = ("HIT" if won else "MISS"), "return"
    else:
        outcome, decided_by = "PROVISIONAL", None

    bench = measure(yf, thread["benchmark"], start, end) if thread["benchmark"] else None
    signal_alpha = None
    if bench is not None:
        # Alpha en la direccion de la senal: en una venta, quedarse por debajo del indice es acertar.
        signal_alpha = round((data["return_pct"] - bench["return_pct"]) * (1 if side == "BUY" else -1), 2)

    revisions = []
    for rev in thread["revisions"]:
        item = {k: rev[k] for k in ("field", "from", "to", "kind", "date", "timestamp_url")}
        if rev["kind"] == "moved" and rev["field"] in ("stop_loss", "entry_level"):
            broken = breach_date(yf, thread["ticker"], side, rev["field"], rev["from"], rev["previous_set_on"], rev["date"])
            # El dia del cambio no cuenta como "despues": no sabemos si el video salio antes o despues del cierre.
            item["after_breach"] = broken if broken and broken < rev["date"] else None
            if broken == rev["date"]:
                item["after_breach_same_day"] = broken
        revisions.append(item)

    return {
        **row,
        "outcome": outcome,
        "decided_by": decided_by,
        "eval_date_used": data["eval_date_used"],
        "price_at_signal": data["price_at_signal"],
        "eval_price": data["eval_price"],
        "currency": data.get("currency"),
        "first_event": first_event,
        "return_pct": data["return_pct"],
        "benchmark": thread["benchmark"],
        "benchmark_return_pct": bench["return_pct"] if bench else None,
        "signal_alpha_pct": signal_alpha,
        "revisions": revisions,
    }


def side_stats(rows: list) -> dict:
    decided = [r for r in rows if r["outcome"] in ("HIT", "MISS")]
    hits = sum(1 for r in decided if r["outcome"] == "HIT")
    alphas = [r["signal_alpha_pct"] for r in decided if r.get("signal_alpha_pct") is not None]
    return {
        "evaluated": len(decided),
        "hits": hits,
        "hit_rate_pct": round(hits / len(decided) * 100, 1) if decided else None,
        "hit_rate_ci95_pct": wilson_interval(hits, len(decided)),
        "avg_signal_alpha_pct": round(sum(alphas) / len(alphas), 2) if alphas else None,
        "alpha_sample": len(alphas),
    }


def build_scorecard(analyst: dict, threads: list, rows: list) -> dict:
    overall = side_stats(rows)
    # Los cambios salen del historial (no dependen de Yahoo); la ruptura previa, de la evaluacion.
    moved = [(t, r) for t in threads for r in t["revisions"] if r["kind"] == "moved"]
    level_moves = [(t, r) for t, r in moved if r["field"] in LEVEL_FIELDS]
    breached = sum(1 for row in rows for r in row.get("revisions", []) if r.get("after_breach"))
    same_day = sum(1 for row in rows for r in row.get("revisions", []) if r.get("after_breach_same_day"))
    closures = {reason: sum(1 for t in threads if t["closed"] and t["closed"]["reason"] == reason) for reason in CLOSE_REASONS}
    n = overall["evaluated"]
    return {
        **analyst,
        "signals_total": len(threads),
        "open": sum(1 for t in threads if t["status"] == "OPEN"),
        **overall,
        "by_side": {side: side_stats([r for r in rows if r["side"] == side]) for side in ("BUY", "SELL")},
        "provisional": sum(1 for r in rows if r["outcome"] == "PROVISIONAL"),
        "not_evaluated": sum(1 for r in rows if r["outcome"] == "NOT_EVALUATED"),
        "not_triggered": sum(1 for r in rows if r["outcome"] == "NOT_TRIGGERED"),
        "level_moves": {
            "total": len(level_moves),
            "signals_with_moves": len({t["id"] for t, _ in level_moves}),
            "stop_loosened": sum(
                1 for t, r in level_moves
                if r["field"] == "stop_loss" and ((r["to"] < r["from"]) if t["side"] == "BUY" else (r["to"] > r["from"]))
            ),
            "moved_after_breach": breached,
            "moved_same_day_as_breach": same_day,
            "expiry_changes": sum(1 for _, r in moved if r["field"] == "expiry_date"),
        },
        "closures": closures,
        "abandoned_without_close": closures["ABANDONED"],
        # Respuestas sueltas (p. ej. a oyentes) que no se vuelven a mencionar: no son lo mismo que
        # dejar caer una senal que se venia siguiendo.
        "abandoned_after_single_mention": sum(
            1 for t in threads if t["closed"] and t["closed"]["reason"] == "ABANDONED" and t["mentions"] == 1
        ),
        "sample_warning": (
            f"Solo {n} senales evaluadas (minimo orientativo: {MIN_SAMPLE}). La muestra no es significativa: "
            "la tasa de acierto puede deberse al azar."
            if n < MIN_SAMPLE else None
        ),
    }


def cmd_scorecard(args):
    try:
        import yfinance as yf
    except ImportError:
        fail("Falta yfinance. Ejecuta con `uv run` o instala: pip install yfinance", code=EXIT_DEPENDENCY)
    warnings.simplefilter("ignore")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    since = check_date(args.since, "--since") if args.since else None
    data = load_store(SIGNALS_PATH, {"version": 1, "videos": []})
    videos = filter_videos(data, args.analyst)
    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    history = build_history(videos, args.abandon_after, today_dt.strftime("%Y-%m-%d"))
    threads = [t for t in history["threads"] if not since or t["opened"]["date"] >= since]
    if not threads:
        emit(
            {
                "status": "ok",
                "signals_file": str(SIGNALS_PATH),
                "scorecards": [],
                "message": "No hay senales registradas para ese filtro. Registra videos con `signals --action record`.",
            }
        )
        return

    # Una descarga por ticker para todo el periodo; measure() recorta despues cada ventana.
    earliest = {}
    for t in threads:
        for ticker in filter(None, (t["ticker"], t["benchmark"])):
            earliest[ticker] = min(earliest.get(ticker, t["opened"]["date"]), t["opened"]["date"])
    try:
        for ticker, first in earliest.items():
            load_history(yf, ticker, as_date(first) - timedelta(days=5), today_dt + timedelta(days=2))
        rows = [evaluate_thread(yf, t, today_dt) for t in threads]
    except Exception as exc:
        fail(f"Error consultando Yahoo Finance: {type(exc).__name__}: {exc}", code=EXIT_REMOTE)

    scorecards = []
    for analyst in summarize_analysts(videos):
        key = analyst_key(analyst["analyst"])
        pairs = [(t, r) for t, r in zip(threads, rows) if analyst_key(t["analyst"]) == key]
        if not pairs:
            continue
        card = build_scorecard(analyst, [t for t, _ in pairs], [r for _, r in pairs])
        if args.detail:
            card["signals"] = [r for _, r in pairs]
        scorecards.append(card)

    emit(
        {
            "status": "ok",
            "signals_file": str(SIGNALS_PATH),
            "since": since,
            "eval_date": today_dt.strftime("%Y-%m-%d"),
            "abandon_after": args.abandon_after,
            "scorecards": scorecards,
            "note": (
                "Informacion sobre senales pasadas, no una recomendacion de seguir a ningun analista. "
                "Cada senal se audita desde su primera aparicion y con sus niveles originales. Si la entrada estaba a mas de "
                f"un {ENTRY_TOLERANCE_PCT:g} % del precio, la senal empieza el dia en que el precio la toca (cierre de ese dia) y, "
                "si no la toca, queda NOT_TRIGGERED y no cuenta. Si el precio toca antes el "
                "objetivo es acierto, si toca antes el stop es fallo; sin niveles decide el signo de return_pct al cierre "
                "(una caida es acierto en VENDER). Las senales abiertas sin stop ni objetivo tocados son provisionales y "
                "no cuentan. signal_alpha_pct es la rentabilidad frente al indice en la direccion de la senal."
            ),
        }
    )


# --------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(
        description="FinTube Analyst Auditor CLI: RSS y subtitulos de YouTube, precios de Yahoo Finance, cartera local e historial de senales. Salida JSON por stdout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  fintube_cli.py resolve-channel --channel @especulacionenbolsa
  fintube_cli.py scan-rss --channel-id UCugd6tlorqt5KTqqB8bKyrg --exclude "#shorts" --since 2026-10-01
  fintube_cli.py transcript --video https://youtu.be/VIDEO_ID
  fintube_cli.py audit --tickers SAN.MC,REP.MC --signal-date 2026-10-09 --benchmark ^IBEX
  fintube_cli.py audit --tickers SAN.MC --signal-date 2026-10-09 --side BUY --stop 9.80 --target-price 11.50
  fintube_cli.py portfolio --action add --ticker SAN.MC --shares 500 --buy-price 10.45 --buy-date 2026-10-10
  fintube_cli.py portfolio --action list
  fintube_cli.py signals --action record --input video.json
  fintube_cli.py signals --action list --analyst "Especulacion en Bolsa" --ticker SAN.MC
  fintube_cli.py scorecard --analyst "Especulacion en Bolsa" --detail

Codigos de salida: 0 ok, 2 entrada invalida, 3 error remoto (YouTube/Yahoo), 4 falta dependencia.""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_res = sub.add_parser("resolve-channel", help="Obtiene el channel_id (UC...) a partir de @handle o URL")
    p_res.add_argument("--channel", required=True, help="@handle, URL del canal o channel_id")

    p_rss = sub.add_parser("scan-rss", help="Filtra el RSS de un canal o playlist de YouTube")
    src = p_rss.add_mutually_exclusive_group(required=True)
    src.add_argument("--channel-id")
    src.add_argument("--playlist-id")
    p_rss.add_argument("--keyword", default=None, help="Regex que debe aparecer en el titulo")
    p_rss.add_argument("--exclude", default=None, help="Regex que descarta el video si aparece en el titulo")
    p_rss.add_argument("--since", default=None, help="Solo videos publicados desde YYYY-MM-DD")
    p_rss.add_argument("--limit", type=int, default=15, help="Maximo de videos devueltos (el RSS trae ~15)")

    p_tr = sub.add_parser("transcript", help="Descarga subtitulos con marcas de tiempo")
    p_tr.add_argument("--video", required=True, help="URL o video_id")
    p_tr.add_argument("--languages", default="es,en", help="Idiomas por orden de preferencia")
    p_tr.add_argument("--chunk-seconds", type=int, default=30, help="Agrupa el texto en bloques de N segundos")

    p_aud = sub.add_parser("audit", help="Audita rentabilidad y Alpha en Yahoo Finance")
    p_aud.add_argument("--tickers", required=True, help="Tickers Yahoo separados por comas (SAN se corrige a SAN.MC)")
    p_aud.add_argument("--signal-date", required=True, help="Fecha de la senal (publicacion del video) YYYY-MM-DD")
    p_aud.add_argument("--target-date", default=None, help="Fecha objetivo/caducidad YYYY-MM-DD")
    p_aud.add_argument("--benchmark", default="^IBEX", help="Indice de referencia; vacio para omitir")
    p_aud.add_argument("--side", type=str.upper, choices=["BUY", "SELL"], default="BUY", help="Direccion de la senal")
    p_aud.add_argument("--stop", type=float, default=None, help="Stop loss nominal (solo con un ticker)")
    p_aud.add_argument("--target-price", type=float, default=None, help="Precio objetivo nominal (solo con un ticker)")
    p_aud.add_argument("--raw-tickers", action="store_true", help="No corregir tickers (p. ej. para el ADR SAN en NYSE)")

    p_port = sub.add_parser("portfolio", help=f"Gestiona la cartera local en {PORTFOLIO_PATH}")
    p_port.add_argument("--action", choices=["list", "add", "remove", "follow"], required=True)
    p_port.add_argument("--ticker", default="")
    p_port.add_argument("--shares", type=float, default=0.0)
    p_port.add_argument("--buy-price", type=float, default=0.0)
    p_port.add_argument("--buy-date", default=None, help="Fecha de compra YYYY-MM-DD (por defecto hoy)")
    p_port.add_argument("--analyst", default="")
    p_port.add_argument("--recommendation", type=str.upper, choices=["BUY", "HOLD", "SELL"], default="BUY")
    p_port.add_argument("--target-date", default=None)
    p_port.add_argument("--lot-id", type=int, default=None, help="Lote a borrar con --action remove")
    p_port.add_argument("--all-lots", action="store_true", help="Borra todos los lotes del ticker con --action remove")
    p_port.add_argument("--channel-id", default=None, help="Para --action follow")
    p_port.add_argument("--keyword", default=None, help="Para --action follow")

    abandon_help = f"Videos seguidos sin mencionar un valor para dar su senal por abandonada (0 = nunca; por defecto {DEFAULT_ABANDON_AFTER})"

    p_sig = sub.add_parser("signals", help=f"Historial de senales por analista en {SIGNALS_PATH}")
    p_sig.add_argument("--action", choices=["record", "list", "delete"], required=True)
    p_sig.add_argument("--input", default=None, help="Para record: JSON del video con sus senales (ruta o - para stdin)")
    p_sig.add_argument("--analyst", default=None, help="Filtra por analista (sin distinguir mayusculas ni tildes)")
    p_sig.add_argument("--ticker", default=None, help="Para list: filtra por ticker")
    p_sig.add_argument("--status", choices=["open", "closed", "all"], default="all", help="Para list")
    p_sig.add_argument("--video-id", default=None, help="Para delete: URL o video_id")
    p_sig.add_argument("--abandon-after", type=int, default=DEFAULT_ABANDON_AFTER, help=abandon_help)

    p_sc = sub.add_parser("scorecard", help="Tabla de aciertos por analista a partir del historial de senales")
    p_sc.add_argument("--analyst", default=None, help="Solo este analista (por defecto, todos)")
    p_sc.add_argument("--since", default=None, help="Solo senales abiertas desde YYYY-MM-DD")
    p_sc.add_argument("--abandon-after", type=int, default=DEFAULT_ABANDON_AFTER, help=abandon_help)
    p_sc.add_argument("--detail", action="store_true", help="Incluye la evaluacion de cada senal")

    args = parser.parse_args()
    if getattr(args, "abandon_after", 0) < 0:
        fail("--abandon-after no puede ser negativo")
    handlers = {
        "resolve-channel": cmd_resolve_channel,
        "scan-rss": cmd_scan_rss,
        "transcript": cmd_transcript,
        "audit": cmd_audit,
        "portfolio": cmd_portfolio,
        "signals": cmd_signals,
        "scorecard": cmd_scorecard,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
