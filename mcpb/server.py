# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 Jorge MB
"""
Servidor MCP local de 'fintube-analyst-auditor' para Claude Desktop (extension .mcpb).

Cada herramienta ejecuta el mismo subcomando de scripts/fintube_cli.py y devuelve su JSON
tal cual, asi que el contrato es el del CLI. La herramienta `guia` sirve SKILL.md y las
referencias para que el modelo tenga las instrucciones aunque no tenga la skill instalada.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, Optional, Union

from mcp.server.mcpserver import MCPServer

HERE = Path(__file__).resolve().parent
# Dentro del .mcpb la skill va en ./skill; en el repo, en ../skills/fintube-analyst-auditor.
SKILL_DIR = next(
    d for d in (HERE / "skill", HERE.parent / "skills" / "fintube-analyst-auditor") if (d / "SKILL.md").exists()
)
CLI = SKILL_DIR / "scripts" / "fintube_cli.py"
DOCS = {
    "skill": SKILL_DIR / "SKILL.md",
    "analysts": SKILL_DIR / "references" / "analysts.md",
    "extraction_schema": SKILL_DIR / "references" / "extraction_schema.md",
    "signal_history": SKILL_DIR / "references" / "signal_history.md",
}
TIMEOUT = 300

mcp = MCPServer(
    "fintube",
    instructions=(
        "Herramientas de la skill fintube-analyst-auditor (videos de bolsa de YouTube, semaforo de "
        "compra/venta, auditoria con Yahoo Finance, historial de señales y cartera). Antes de usarlas, "
        "llama a `guia` sin argumentos y sigue esas instrucciones: donde digan `uv run "
        "scripts/fintube_cli.py <subcomando> --opcion valor`, llama a la herramienta del mismo nombre "
        "(con guiones bajos) con esos argumentos."
    ),
)


def error(message: str, **extra) -> str:
    return json.dumps({"status": "error", "message": message, **extra}, ensure_ascii=False)


def run_cli(args: list, stdin: Optional[str] = None) -> str:
    """Ejecuta el CLI con el mismo Python (y dependencias) del servidor y devuelve su JSON."""
    try:
        proc = subprocess.run(
            [sys.executable, str(CLI), *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return error(f"El CLI no respondio en {TIMEOUT} s")
    out = proc.stdout.strip()
    if out:
        return out
    return error("El CLI no devolvio JSON", stderr=proc.stderr.strip()[-2000:])


def opts(**kwargs) -> list:
    """Convierte argumentos de la herramienta en opciones del CLI (None se omite, True es un flag)."""
    out = []
    for key, value in kwargs.items():
        if value is None or value is False:
            continue
        flag = "--" + key.replace("_", "-")
        out += [flag] if value is True else [flag, str(value)]
    return out


@mcp.tool()
def guia(
    documento: Literal["skill", "analysts", "extraction_schema", "signal_history"] = "skill",
) -> str:
    """Instrucciones de la skill (SKILL.md) y sus referencias. Llamala primero, sin argumentos.

    'analysts': canales comprobados y como interpretar cada fuente; 'extraction_schema': nombres a
    tickers y formato de señal y tabla; 'signal_history': formato de `signals record` y reglas del historial.
    """
    return DOCS[documento].read_text(encoding="utf-8")


@mcp.tool()
def resolve_channel(channel: str) -> str:
    """Obtiene el channel_id (UC...) de un @handle o URL de canal de YouTube."""
    return run_cli(["resolve-channel", *opts(channel=channel)])


@mcp.tool()
def scan_rss(
    channel_id: Optional[str] = None,
    playlist_id: Optional[str] = None,
    keyword: Optional[str] = None,
    exclude: Optional[str] = None,
    since: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """Lista los ultimos videos (~15) de un canal o playlist, filtrando el titulo por regex.

    Da channel_id o playlist_id. since: YYYY-MM-DD.
    """
    return run_cli(
        ["scan-rss", *opts(channel_id=channel_id, playlist_id=playlist_id, keyword=keyword, exclude=exclude, since=since, limit=limit)]
    )


@mcp.tool()
def transcript(video: str, languages: Optional[str] = None, chunk_seconds: Optional[int] = None) -> str:
    """Descarga los subtitulos de un video (URL o id) en bloques con marca [HH:MM:SS]."""
    return run_cli(["transcript", *opts(video=video, languages=languages, chunk_seconds=chunk_seconds)])


@mcp.tool()
def audit(
    tickers: str,
    signal_date: str,
    target_date: Optional[str] = None,
    benchmark: Optional[str] = None,
    side: Optional[Literal["BUY", "SELL"]] = None,
    stop: Optional[float] = None,
    target_price: Optional[float] = None,
    raw_tickers: bool = False,
) -> str:
    """Rentabilidad y alpha de tickers de Yahoo Finance desde la fecha de la señal (YYYY-MM-DD).

    tickers separados por comas. stop y target_price solo con un ticker.
    """
    return run_cli(
        [
            "audit",
            *opts(
                tickers=tickers,
                signal_date=signal_date,
                target_date=target_date,
                benchmark=benchmark,
                side=side,
                stop=stop,
                target_price=target_price,
                raw_tickers=raw_tickers,
            ),
        ]
    )


@mcp.tool()
def portfolio(
    action: Literal["list", "add", "remove", "follow"],
    ticker: Optional[str] = None,
    shares: Optional[float] = None,
    buy_price: Optional[float] = None,
    buy_date: Optional[str] = None,
    analyst: Optional[str] = None,
    recommendation: Optional[Literal["BUY", "HOLD", "SELL"]] = None,
    target_date: Optional[str] = None,
    lot_id: Optional[int] = None,
    all_lots: bool = False,
    channel_id: Optional[str] = None,
    keyword: Optional[str] = None,
) -> str:
    """Cartera local del usuario (~/.fintube/portfolio.json) y analistas seguidos.

    Pide confirmacion al usuario antes de add o remove.
    """
    return run_cli(
        [
            "portfolio",
            *opts(
                action=action,
                ticker=ticker,
                shares=shares,
                buy_price=buy_price,
                buy_date=buy_date,
                analyst=analyst,
                recommendation=recommendation,
                target_date=target_date,
                lot_id=lot_id,
                all_lots=all_lots,
                channel_id=channel_id,
                keyword=keyword,
            ),
        ]
    )


@mcp.tool()
def signals(
    action: Literal["record", "list", "delete"],
    record: Optional[Union[dict[str, Any], str]] = None,
    analyst: Optional[str] = None,
    ticker: Optional[str] = None,
    status: Optional[Literal["open", "closed", "all"]] = None,
    video_id: Optional[str] = None,
    abandon_after: Optional[int] = None,
) -> str:
    """Historial de señales por analista (~/.fintube/signals.json).

    Para action='record', pasa en `record` el objeto JSON del video (formato en guia('signal_history')),
    en lugar del fichero de --input.
    """
    if action == "record" and not record:
        return error("record es obligatorio para action=record (JSON del video)")
    args = opts(action=action, analyst=analyst, ticker=ticker, status=status, video_id=video_id, abandon_after=abandon_after)
    if action == "record":
        text = record if isinstance(record, str) else json.dumps(record, ensure_ascii=False)
        return run_cli(["signals", *args, "--input", "-"], stdin=text)
    return run_cli(["signals", *args])


@mcp.tool()
def scorecard(
    analyst: Optional[str] = None,
    since: Optional[str] = None,
    abandon_after: Optional[int] = None,
    detail: bool = False,
) -> str:
    """Tabla de aciertos por analista a partir del historial de señales."""
    return run_cli(["scorecard", *opts(analyst=analyst, since=since, abandon_after=abandon_after, detail=detail)])


if __name__ == "__main__":
    mcp.run()
