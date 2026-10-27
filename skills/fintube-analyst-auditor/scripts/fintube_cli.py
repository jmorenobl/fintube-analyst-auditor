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
import re
import sys
import urllib.request
import warnings
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

PORTFOLIO_PATH = Path.home() / ".fintube" / "portfolio.json"
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
    inc_pattern = re.compile(args.keyword, re.IGNORECASE) if args.keyword else None
    exc_pattern = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None
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

def load_closes(yf, ticker: str, start: datetime, end: datetime):
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    if hist is None or hist.empty:
        return None
    closes = hist["Close"].dropna()
    if closes.index.tz is not None:
        closes.index = closes.index.tz_localize(None)
    return closes


def price_on_or_after(closes, dt: datetime):
    valid = closes[closes.index >= dt]
    if valid.empty:
        return None, None
    return round(float(valid.iloc[0]), 4), str(valid.index[0])[:10]


def price_on_or_before(closes, dt: datetime):
    valid = closes[closes.index < dt + timedelta(days=1)]
    if valid.empty:
        return None, None
    return round(float(valid.iloc[-1]), 4), str(valid.index[-1])[:10]


def measure(yf, ticker: str, signal_dt: datetime, eval_dt: datetime):
    closes = load_closes(yf, ticker, signal_dt - timedelta(days=5), eval_dt + timedelta(days=2))
    if closes is None:
        return None
    p_start, d_start = price_on_or_after(closes, signal_dt)
    p_eval, d_eval = price_on_or_before(closes, eval_dt)
    if not p_start or not p_eval:
        return None
    window = closes[(closes.index >= signal_dt) & (closes.index < eval_dt + timedelta(days=1))]
    return {
        "signal_date_used": d_start,
        "price_at_signal": p_start,
        "eval_date_used": d_eval,
        "eval_price": p_eval,
        "return_pct": round((p_eval - p_start) / p_start * 100.0, 2),
        "max_price_in_window": round(float(window.max()), 4) if not window.empty else None,
        "min_price_in_window": round(float(window.min()), 4) if not window.empty else None,
    }


def cmd_audit(args):
    try:
        import yfinance as yf
    except ImportError:
        fail("Falta yfinance. Ejecuta con `uv run` o instala: pip install yfinance", code=EXIT_DEPENDENCY)
    # yfinance reconfigura los filtros al importarse: silenciar despues para no ensuciar la salida.
    warnings.simplefilter("ignore")
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    signal_dt = parse_date(args.signal_date, "--signal-date")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if signal_dt > today:
        fail("--signal-date esta en el futuro")

    target_dt = parse_date(args.target_date, "--target-date") if args.target_date else None
    # Se evalua en la fecha objetivo si ya ha pasado; si no, a dia de hoy.
    eval_dt = target_dt if target_dt and target_dt <= today else today
    target_reached = bool(target_dt and target_dt <= today)

    benchmark = None
    if args.benchmark:
        benchmark = measure(yf, args.benchmark, signal_dt, eval_dt)

    results = []
    for ticker in tickers:
        data = measure(yf, ticker, signal_dt, eval_dt)
        if data is None:
            results.append({"ticker": ticker, "error": "Sin datos en Yahoo Finance (revisa el ticker)"})
            continue
        bm_ret = benchmark["return_pct"] if benchmark else None
        results.append(
            {
                "ticker": ticker,
                **data,
                "benchmark_ticker": args.benchmark,
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
            "benchmark": {"ticker": args.benchmark, **benchmark} if benchmark else None,
            "audits": results,
            "note": "return_pct es la variacion del precio (ajustado). Para senales VENDER, una caida es un acierto.",
        }
    )


# --------------------------------------------------------------------------- portfolio

def cmd_portfolio(args):
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PORTFOLIO_PATH.exists():
        data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
    else:
        data = {"positions": [], "followed_analysts": []}
    data.setdefault("positions", [])
    data.setdefault("followed_analysts", [])

    def save():
        PORTFOLIO_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.action == "list":
        emit({"status": "ok", "portfolio_file": str(PORTFOLIO_PATH), "data": data})
        return

    if args.action in ("add", "remove") and not args.ticker:
        fail(f"--ticker es obligatorio para --action {args.action}")

    if args.action == "add":
        entry = {
            "ticker": args.ticker.upper(),
            "shares": args.shares,
            "buy_price": args.buy_price,
            "analyst": args.analyst,
            "recommendation": args.recommendation.upper(),
            "target_date": args.target_date,
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "status": "OPEN",
        }
        data["positions"] = [p for p in data["positions"] if p.get("ticker") != entry["ticker"]]
        data["positions"].append(entry)
        save()
        emit({"status": "saved", "entry": entry})
        return

    if args.action == "remove":
        ticker = args.ticker.upper()
        before = len(data["positions"])
        data["positions"] = [p for p in data["positions"] if p.get("ticker") != ticker]
        save()
        emit({"status": "removed" if len(data["positions"]) < before else "not_found", "ticker": ticker})
        return

    if args.action == "follow":
        if not args.analyst:
            fail("--analyst es obligatorio para --action follow")
        follow = {"analyst": args.analyst, "channel_id": args.channel_id, "keyword": args.keyword}
        data["followed_analysts"] = [a for a in data["followed_analysts"] if a.get("analyst") != args.analyst]
        data["followed_analysts"].append(follow)
        save()
        emit({"status": "saved", "followed": follow})


# --------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(
        description="FinTube Analyst Auditor CLI: RSS y subtitulos de YouTube, precios de Yahoo Finance y cartera local. Salida JSON por stdout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  fintube_cli.py resolve-channel --channel @AlbertoIturralde
  fintube_cli.py scan-rss --channel-id UC4NCu44AQXnhscxeDrdgvow --keyword Iturralde --since 2026-10-01
  fintube_cli.py transcript --video https://youtu.be/VIDEO_ID
  fintube_cli.py audit --tickers SAN.MC,REP.MC --signal-date 2026-10-09 --benchmark ^IBEX
  fintube_cli.py portfolio --action list

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
    p_rss.add_argument("--limit", type=int, default=10)

    p_tr = sub.add_parser("transcript", help="Descarga subtitulos con marcas de tiempo")
    p_tr.add_argument("--video", required=True, help="URL o video_id")
    p_tr.add_argument("--languages", default="es,en", help="Idiomas por orden de preferencia")
    p_tr.add_argument("--chunk-seconds", type=int, default=30, help="Agrupa el texto en bloques de N segundos")

    p_aud = sub.add_parser("audit", help="Audita rentabilidad y Alpha en Yahoo Finance")
    p_aud.add_argument("--tickers", required=True, help="Tickers Yahoo separados por comas")
    p_aud.add_argument("--signal-date", required=True, help="Fecha de la senal (publicacion del video) YYYY-MM-DD")
    p_aud.add_argument("--target-date", default=None, help="Fecha objetivo/caducidad YYYY-MM-DD")
    p_aud.add_argument("--benchmark", default="^IBEX", help="Indice de referencia; vacio para omitir")

    p_port = sub.add_parser("portfolio", help=f"Gestiona la cartera local en {PORTFOLIO_PATH}")
    p_port.add_argument("--action", choices=["list", "add", "remove", "follow"], required=True)
    p_port.add_argument("--ticker", default="")
    p_port.add_argument("--shares", type=float, default=0.0)
    p_port.add_argument("--buy-price", type=float, default=0.0)
    p_port.add_argument("--analyst", default="")
    p_port.add_argument("--recommendation", default="BUY", help="BUY | HOLD | SELL")
    p_port.add_argument("--target-date", default=None)
    p_port.add_argument("--channel-id", default=None, help="Para --action follow")
    p_port.add_argument("--keyword", default=None, help="Para --action follow")

    args = parser.parse_args()
    handlers = {
        "resolve-channel": cmd_resolve_channel,
        "scan-rss": cmd_scan_rss,
        "transcript": cmd_transcript,
        "audit": cmd_audit,
        "portfolio": cmd_portfolio,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
