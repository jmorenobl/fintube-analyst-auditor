---
name: fintube-analyst-auditor
description: Extrae recomendaciones de inversion bursatil de videos de YouTube, filtra canales por analista mediante RSS, limpia tertulias no financieras y audita la tasa de acierto de los expertos comparando precios historicos en Yahoo Finance y el estado de la cartera del usuario. Usar cuando el usuario pida resumir videos de bolsa, auditar a un analista financiero de YouTube (p. ej. Alberto Iturralde, Miguel Mendez, Especulacion en Bolsa, Capital Radio, Intereconomia), consultar el semaforo de compra/venta de un experto, ver si un analista ha movido sus soportes o stops, pedir su historial o tabla de aciertos, o cruzar señales de YouTube con su cartera.
license: EUPL-1.2
compatibility: Requiere Python 3.9+ y acceso a internet (youtube.com y finance.yahoo.com). Recomendado uv. En apps de chat con sandbox (Claude.ai, ChatGPT) hay que permitir el acceso de red a esos dominios.
metadata:
  author: jmorenobl
  version: "0.3.0"
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
- [ ] 4. Registrar las señales en el historial
- [ ] 5. Auditar precios (si hay señales con fecha pasada o el usuario lo pide)
- [ ] 6. Cruzar con la cartera del usuario

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

### 4. Historial de señales (`signals`, `scorecard`)

Tras extraer las señales de cada video, **registralas siempre**, tambien si el video no tiene ninguna (cuenta para detectar abandonos):

```bash
uv run scripts/fintube_cli.py signals --action record --input /ruta/video.json
```

El JSON lleva `analyst` (la fuente, p. ej. `"Especulacion en Bolsa"`), `video_id`, `published_at` y `signals` con los campos de `extraction_schema.md`. Reintentar es seguro: el mismo video se sustituye, no se duplica. La respuesta (`events`) dice si cada valor es una señal nueva, confirmada, revisada (con los niveles antes y despues), invertida, cerrada, abandonada o caducada: usala para contar al usuario que ha cambiado.

Antes de responder sobre un analista o un valor, consulta lo ya registrado:

```bash
uv run scripts/fintube_cli.py signals --action list --analyst "Especulacion en Bolsa" --ticker SAN.MC
uv run scripts/fintube_cli.py scorecard --analyst "Especulacion en Bolsa" --detail
```

- `list` da la primera aparicion de cada señal, cada cambio de nivel con fecha y enlace, y el cierre. Cita siempre el nivel original y despues los cambios.
- `scorecard` da tasa de acierto con intervalo de confianza, alpha medio, compras frente a ventas, niveles movidos (`moved_after_breach`: movidos despues de romperse) y señales abandonadas. Si trae `sample_warning`, dilo antes que la tasa.
- La tabla de aciertos es informacion, no una recomendacion: nunca digas que conviene seguir o dejar de seguir a un analista.

Lee `references/signal_history.md` para el formato de entrada, las reglas de cierre y como presentar la tabla.

### 5. Auditoria (`audit`)

```bash
uv run scripts/fintube_cli.py audit --tickers "SAN.MC,REP.MC" --signal-date 2026-10-09 --target-date 2026-11-29 --benchmark "^IBEX"
```

- `--signal-date` = fecha de publicacion del video. Si `--target-date` ya paso se evalua ahi; si no, hoy (`target_reached: false` → resultado provisional, dilo).
- COMPRAR acierta si `return_pct > 0` (mejor aun si `alpha_pct > 0`); VENDER acierta si el precio cae. `return_pct` incluye dividendos; `price_return_pct` es solo precio.
- Si el analista dio stop u objetivo, audita cada valor por separado con sus niveles: `--tickers SAN.MC --side BUY --stop 9.80 --target-price 11.50`. `first_event` dice que se toco antes (`stop`, `target` o `ambiguous_same_day`). Los niveles se comparan con maximos y minimos intradia nominales, como en el grafico del inversor.
- Lee `warnings` y comprueba `currency`/`exchange`: un valor español debe cotizar en EUR en `MCE`. El CLI corrige `SAN` → `SAN.MC` e `IBEX` → `^IBEX`; si el usuario quiere de verdad el ADR de Nueva York, usa `--raw-tickers`.
- Para analistas que ajustan niveles a diario, audita desde el **primer** video en que dieron la señal, no desde el ultimo nivel corregido: `signals --action list` te da esa fecha y niveles. Si el nivel se ha movido, di cuando y cuanto ("soporte fijado en 11,80 € el 15/10 y rebajado a 11,15 € el 22/10").
- Para la tasa de acierto de un analista usa `scorecard`, no sumes audits a mano: aplica las mismas reglas a todas las señales y compara con el indice (comparar solo contra cero oculta el coste de oportunidad).

### 6. Cartera (`portfolio`)

Cartera local en `~/.fintube/portfolio.json`:

```bash
uv run scripts/fintube_cli.py portfolio --action list
uv run scripts/fintube_cli.py portfolio --action add --ticker SAN.MC --shares 500 --buy-price 10.45 --buy-date 2026-10-10 --analyst "Alberto Iturralde" --recommendation BUY
uv run scripts/fintube_cli.py portfolio --action remove --ticker SAN.MC --lot-id 3
```

Cada `add` es un lote nuevo; `list` devuelve en `summary` las acciones totales y el precio medio ponderado por ticker. Para borrar, `remove` exige `--lot-id` (o `--all-lots`); sin el, devuelve los lotes para que preguntes cual. Pide confirmacion antes de añadir o borrar.

**Alertas de cartera: datos, nunca consejos.** Recomendar a una persona concreta que compre o venda lo que tiene es asesoramiento financiero, reservado en España a entidades autorizadas por la CNMV, y un descargo final no lo cambia. Presenta las coincidencias como un cruce de hechos:

- Bien: "Tienes 700 acciones de SAN.MC (precio medio 10,66 €). En el video del 26/10 el analista da señal de VENTA por debajo de 11,20 € [00:14:32]."
- Mal: "Te recomiendo vender tus Santander" / "Deberias proteger beneficios".

No uses imperativos ni valoraciones sobre lo que el usuario deberia hacer, aunque te lo pida; si insiste, explica que la skill solo informa de lo que dicen los analistas y de los precios.

## Gotchas

- **Los analistas no siempre publican en su canal.** El canal propio de Alberto Iturralde no sube videos desde 2021; lo actual esta en Especulacion en Bolsa y Capital Radio (ver `references/analysts.md`). Si el RSS devuelve videos antiguos, dilo en vez de presentarlos como recientes.
- **Los handles enganan.** `@CapitalRadio` es una radio britanica, no la española, y `@intereconomia` esta abandonado. Verifica siempre `channel_title` y la fecha del ultimo video.
- **El RSS solo trae los ~15 ultimos videos.** En canales que suben mucho (Capital Radio, ~15 al dia) eso es un solo dia. Para videos mas antiguos pide la URL al usuario.
- **El historial empieza cuando empiezas a registrar.** Si `signals --action list` no tiene videos de un analista, registra los que devuelva `scan-rss` antes de hablar de "primera señal" o de tasa de acierto, y di desde que fecha cubre el historial.
- **Los subtitulos suelen ser automaticos** (`is_generated: true`) y deforman nombres y cifras (empresas mal transcritas, "1 75" por "1,75 %"). Deduce la empresa por contexto, marca la señal como `ambiguous` si dudas y no inventes niveles de precio.
- **YouTube bloquea a veces la descarga de subtitulos** desde IPs de servidores en la nube (error de tipo `RequestBlocked`/`IpBlocked`). Explicalo y sugiere ejecutar la skill en el ordenador del usuario; no resumas el video sin transcripcion.
- **Yahoo usa tickers con sufijo de mercado** (`.MC` Madrid). Sin sufijo, `IAG` es una minera de oro canadiense y `SAN` el ADR en dolares. Si `audit` responde "Sin datos" o la divisa no es EUR, el ticker esta mal, no el analista.
- **En apps de chat con sandbox** la cartera y el historial de `~/.fintube` pueden borrarse al cerrar la sesion. Avisa al usuario de que solo persisten en agentes locales.

## Salida

Tabla semaforo, resumen grano/paja, cambios frente a lo registrado, auditoria o tabla de aciertos si procede y alertas de cartera, en el idioma del usuario. Termina con una linea: es un resumen de opiniones de terceros, no asesoramiento financiero.
