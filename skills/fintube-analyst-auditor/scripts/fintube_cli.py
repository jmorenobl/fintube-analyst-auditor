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


def load_history(yf, ticker: str, start: datetime, end: datetime):
    """Devuelve (DataFrame con precios nominales y 'Adj Close', metadatos) o (None, {})."""
    tk = yf.Ticker(ticker)
    hist = tk.history(start=start, end=end, auto_adjust=False)
    if hist is None or hist.empty:
        return None, {}
    hist = hist.dropna(subset=["Close"])
    if hist.index.tz is not None:
        hist.index = hist.index.tz_localize(None)
    meta = getattr(tk, "history_metadata", None) or {}
    return hist, {"currency": meta.get("currency"), "exchange": meta.get("exchangeName")}


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
    PORTFOLIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    backup_path = PORTFOLIO_PATH.with_suffix(".json.bak")
    if PORTFOLIO_PATH.exists():
        try:
            data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(
                f"{PORTFOLIO_PATH} esta danado ({exc}). No se ha modificado.",
                backup=str(backup_path) if backup_path.exists() else None,
                hint="Restaura la copia .bak o corrige el JSON a mano antes de seguir.",
            )
    else:
        data = {"positions": [], "followed_analysts": []}
    data.setdefault("positions", [])
    data.setdefault("followed_analysts", [])

    # Las carteras antiguas guardaban una posicion por ticker sin id: se convierten en lotes.
    next_id = max((p.get("id", 0) for p in data["positions"]), default=0) + 1
    for lot in data["positions"]:
        if "id" not in lot:
            lot["id"], next_id = next_id, next_id + 1

    def save():
        if PORTFOLIO_PATH.exists():
            backup_path.write_bytes(PORTFOLIO_PATH.read_bytes())
        tmp = PORTFOLIO_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(PORTFOLIO_PATH)

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


# --------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(
        description="FinTube Analyst Auditor CLI: RSS y subtitulos de YouTube, precios de Yahoo Finance y cartera local. Salida JSON por stdout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  fintube_cli.py resolve-channel --channel @especulacionenbolsa
  fintube_cli.py scan-rss --channel-id UCugd6tlorqt5KTqqB8bKyrg --exclude "#shorts" --since 2026-10-01
  fintube_cli.py transcript --video https://youtu.be/VIDEO_ID
  fintube_cli.py audit --tickers SAN.MC,REP.MC --signal-date 2026-10-09 --benchmark ^IBEX
  fintube_cli.py audit --tickers SAN.MC --signal-date 2026-10-09 --side BUY --stop 9.80 --target-price 11.50
  fintube_cli.py portfolio --action add --ticker SAN.MC --shares 500 --buy-price 10.45 --buy-date 2026-10-10
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
