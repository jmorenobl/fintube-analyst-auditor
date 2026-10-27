---
name: fintube-analyst-auditor
description: Extrae recomendaciones de inversion bursatil de videos de YouTube, filtra canales por analista mediante RSS, limpia tertulias no financieras y audita la tasa de acierto de los expertos comparando precios historicos en Yahoo Finance y el estado de la cartera del usuario. Usar cuando el usuario pida resumir videos de bolsa, auditar a un analista financiero de YouTube (p. ej. Alberto Iturralde, Miguel Mendez, Especulacion en Bolsa, Capital Radio, Intereconomia), consultar el semaforo de compra/venta de un experto o cruzar señales de YouTube con su cartera.
license: EUPL-1.2
compatibility: Requiere Python 3.9+ y acceso a internet (youtube.com y finance.yahoo.com). Recomendado uv. En apps de chat con sandbox (Claude.ai, ChatGPT) hay que permitir el acceso de red a esos dominios.
metadata:
  author: jmorenobl
  version: "0.1.0"
  repository: https://github.com/jmorenobl/fintube-analyst-auditor
---

# FinTube Analyst Auditor

El trabajo de red (RSS, subtitulos con marcas de tiempo, cotizaciones historicas) lo hace `scripts/fintube_cli.py`; la extraccion semantica, el filtrado anti-paja y el cruce con la cartera los haces tu.

## Como ejecutar el CLI

Rutas relativas al directorio de esta skill. Todos los subcomandos devuelven JSON por stdout (`"status": "ok"` o `"status": "error"` con `message`). Codigos de salida: 2 entrada invalida, 3 error remoto, 4 falta dependencia.

```bash
uv run scripts/fintube_cli.py <subcomando> ...
```

`uv run` instala solo las dependencias (metadatos PEP 723 del script). Si `uv` no existe, ejecuta `pip install youtube-transcript-api yfinance` una vez y usa `python3 scripts/fintube_cli.py`. Si tampoco hay Python, explica al usuario en lenguaje sencillo que necesita instalarlo; no intentes analizar el video sin transcripcion.

## Flujo

- [ ] 1. Localizar el video (URL directa o RSS)
- [ ] 2. Descargar la transcripcion
- [ ] 3. Extraer señales y separar grano de paja
- [ ] 4. Auditar precios (si hay señales con fecha pasada o el usuario lo pide)
- [ ] 5. Cruzar con la cartera del usuario

### 1. Localizar el video (`resolve-channel` + `scan-rss`)

Si el usuario da una URL, salta al paso 2. Si pregunta *"¿Que ha dicho hoy Iturralde?"*:

1. Si nombra a un analista o programa, lee `references/analysts.md`: tiene los canales comprobados, los horarios, el filtro adecuado y como interpretar cada fuente. Si no aparece, busca en `followed_analysts` (`portfolio --action list`) o resuelve el handle:
   ```bash
   uv run scripts/fintube_cli.py resolve-channel --channel "@especulacionenbolsa"
   ```
   Comprueba que `channel_title` corresponde al canal esperado antes de seguir.
2. Escanea el RSS filtrando por regex en el titulo:
   ```bash
   uv run scripts/fintube_cli.py scan-rss --channel-id UCmU9b04Ym19_OvsSdt7rRYg --keyword "Iturralde|Consultorio" --exclude "#shorts" --since 2026-10-01
   ```
3. Ofrece guardar el canal para la proxima vez: `portfolio --action follow --analyst "Alberto Iturralde" --channel-id UC... --keyword Iturralde`.

### 2. Transcripcion (`transcript`)

```bash
uv run scripts/fintube_cli.py transcript --video "URL_O_VIDEO_ID"
```

Texto en bloques de 30 s con prefijo `[HH:MM:SS]` (`--chunk-seconds` para ajustar, `--languages es,en`).

### 3. Extraccion semantica (tu trabajo)

1. **Grano vs. paja**: estima los minutos de analisis de mercado frente a autopromocion, tertulia politica o temas ajenos.
2. **Semaforo** por activo:
   - 🟢 **COMPRAR**: orden clara de entrada (ya o en un soporte concreto).
   - 🟡 **MANTENER / NEUTRO**: sesgo alcista sin entrada inmediata, o pide esperar confirmacion.
   - 🔴 **VENDER / SALIR / PRECAUCION**: aviso de techo, distribucion o recogida de beneficios.
3. **Niveles y caducidad**: entrada, stop loss, objetivo, fecha limite y timestamp con enlace `https://www.youtube.com/watch?v=ID&t=SEGUNDOSs`.
4. Lee `references/extraction_schema.md` para mapear nombres a tickers y para el formato exacto de la señal y de la tabla.

### 4. Auditoria (`audit`)

```bash
uv run scripts/fintube_cli.py audit --tickers "SAN.MC,REP.MC" --signal-date 2026-10-09 --target-date 2026-11-29 --benchmark "^IBEX"
```

- `--signal-date` = fecha de publicacion del video. Si `--target-date` ya paso se evalua ahi; si no, hoy (`target_reached: false` → resultado provisional, dilo).
- COMPRAR acierta si `return_pct > 0` (mejor aun si `alpha_pct > 0`); VENDER acierta si el precio cae. Con stop loss, usa `min_price_in_window` / `max_price_in_window` para ver si habria saltado.
- Con varias señales del mismo analista, resume tasa de acierto (aciertos / evaluadas) y alpha medio.

### 5. Cartera (`portfolio`)

Cartera local en `~/.fintube/portfolio.json`:

```bash
uv run scripts/fintube_cli.py portfolio --action list
uv run scripts/fintube_cli.py portfolio --action add --ticker SAN.MC --shares 500 --buy-price 10.45 --analyst "Alberto Iturralde" --recommendation BUY --target-date 2026-11-29
uv run scripts/fintube_cli.py portfolio --action remove --ticker SAN.MC
```

Señala cualquier contradiccion entre posiciones abiertas y señales nuevas (p. ej. tiene SAN.MC y el analista ahora dice VENDER). Pide confirmacion antes de añadir o borrar posiciones.

## Gotchas

- **Los analistas no siempre publican en su canal.** El canal propio de Alberto Iturralde no sube videos desde 2021; lo actual esta en Especulacion en Bolsa y Capital Radio (ver `references/analysts.md`). Si el RSS devuelve videos antiguos, dilo en vez de presentarlos como recientes.
- **Los handles enganan.** `@CapitalRadio` es una radio britanica, no la española, y `@intereconomia` esta abandonado. Verifica siempre `channel_title` y la fecha del ultimo video.
- **El RSS solo trae los ~15 ultimos videos.** En canales que suben mucho (Capital Radio, ~15 al dia) eso es un solo dia. Para videos mas antiguos pide la URL al usuario.
- **Los subtitulos suelen ser automaticos** (`is_generated: true`) y deforman nombres y cifras (empresas mal transcritas, "1 75" por "1,75 %"). Deduce la empresa por contexto, marca la señal como `ambiguous` si dudas y no inventes niveles de precio.
- **YouTube bloquea a veces la descarga de subtitulos** desde IPs de servidores en la nube (error de tipo `RequestBlocked`/`IpBlocked`). Explicalo y sugiere ejecutar la skill en el ordenador del usuario; no resumas el video sin transcripcion.
- **Yahoo usa tickers con sufijo de mercado** (`.MC` Madrid). Si `audit` responde "Sin datos", el ticker esta mal, no el analista.
- **En apps de chat con sandbox** la cartera de `~/.fintube` puede borrarse al cerrar la sesion. Avisa al usuario de que solo persiste en agentes locales.

## Salida

Tabla semaforo, resumen grano/paja, auditoria si procede y alertas de cartera, en el idioma del usuario. Termina con una linea: es un resumen de opiniones de terceros, no asesoramiento financiero.
