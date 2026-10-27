# Historial de señales y tabla de aciertos

El historial vive en `~/.fintube/signals.json` (copia `.bak` en cada escritura). Guarda lo que dijo cada video; la vida de cada señal (apertura, revisiones, cierre) la reconstruye el CLI recorriendo los videos por fecha. Por eso:

- Reprocesar un video **sustituye** lo registrado para ese analista y video: no duplica (`result: "unchanged"` si no cambia nada).
- Se pueden registrar videos antiguos despues y el historial se recalcula en orden de publicacion.
- El historial solo cubre lo registrado. El RSS trae ~15 videos: la primera vez, registra todos los que devuelva `scan-rss` para tener base.

## 1. Registrar un video (`signals --action record`)

Despues de extraer las señales de un video, guarda un JSON y registralo (o pasalo por stdin con `--input -`):

```json
{
  "analyst": "Especulacion en Bolsa",
  "video_id": "t2LKCl8qQFo",
  "published_at": "2026-10-23",
  "title": "TODO EN ROJO...",
  "signals": [
    {"ticker": "SAN.MC", "asset_name": "Banco Santander", "signal": "BUY", "confidence": "explicit",
     "entry_level": 12.50, "stop_loss": 12.10, "target_price": null, "expiry_date": null,
     "timestamp": "[00:14:32]", "quote": "Santander, compra en 12,50 y si pierde 12,10 fuera",
     "person": "Alberto Iturralde"}
  ]
}
```

```bash
uv run scripts/fintube_cli.py signals --action record --input /ruta/video.json
```

Reglas de la entrada (el CLI rechaza con codigo 2 lo que no cumpla):

- **`analyst`** = la fuente, no la persona: `"Especulacion en Bolsa"` para sus videos aunque hablen Iturralde y Mendez. Si esta claro quien lo dice, ponlo en `person`. No distingue mayusculas ni tildes.
- **Una señal por valor y video.** Si se repite, deja la conclusion final del video.
- **`signal`**: `BUY`, `SELL`, `HOLD` o `CLOSE` (el analista dice que sale o deja el valor sin darse la vuelta).
- **Niveles**: soporte o precio de compra → `entry_level`; nivel cuya perdida invalida la idea ("si pierde X, fuera") → `stop_loss`; objetivo → `target_price`. Numeros con punto decimal o `null`. Nunca inventes un nivel: si la cifra es dudosa, `null` y `confidence: "ambiguous"`.
- **Registra tambien los videos sin señales** (`"signals": []`): cuentan para detectar abandonos.
- `benchmark` es opcional: por defecto `^IBEX` para `.MC`, `^STOXX50E` para Europa, `^GSPC` para EE. UU. y ninguno para indices, materias primas, divisas y cripto.

La respuesta trae `events` con lo que ha supuesto el video para cada valor:

| Evento | Significado |
| :-- | :-- |
| `NEW` | Primera aparicion: abre una señal BUY o SELL |
| `CONFIRMED` | Repite la señal sin cambiar niveles (tambien un MANTENER sobre una señal abierta) |
| `REVISED` | Misma señal con niveles cambiados; `changes` dice de cuanto a cuanto |
| `REVERSED` | Se da la vuelta: cierra la señal anterior y abre la contraria |
| `CLOSED` | El analista la cierra (`CLOSE`) |
| `ABANDONED` | El valor lleva `--abandon-after` videos (5) sin mencionarse |
| `EXPIRED` | Paso la fecha de caducidad |
| `NEUTRAL` | MANTENER/NEUTRO sin señal abierta: se guarda, no puntua |

Si el usuario pide corregir un video mal registrado, vuelve a registrarlo con la extraccion corregida. Para quitarlo del todo, pide confirmacion y usa `signals --action delete --analyst "..." --video-id ID`.

## 2. Consultar el historial (`signals --action list`)

```bash
uv run scripts/fintube_cli.py signals --action list --analyst "Especulacion en Bolsa" --ticker SAN.MC
```

Cada señal trae `opened` (fecha, video, niveles originales y enlace al minuto), `current` (niveles vigentes), `revisions` (cada cambio con fecha y enlace) y `closed` (motivo y fecha). `neutral` lista los MANTENER sin señal abierta. Usalo para responder "¿que dice de X?" o "¿ha cambiado el soporte?" sin volver a descargar videos:

- Bien: "Señal de compra desde el 15/10 (soporte 11,80 €). El 22/10 bajo el soporte a 11,15 €, un dia despues de que el precio cerrara por debajo de 11,80 €."
- Cita siempre la **primera** fecha y nivel, y despues cada cambio.

## 3. Tabla de aciertos (`scorecard`)

```bash
uv run scripts/fintube_cli.py scorecard --analyst "Especulacion en Bolsa" [--since 2026-10-01] [--detail]
```

Como se evalua cada señal (lo hace el CLI con los mismos precios que `audit`):

- Desde la **primera aparicion** hasta su cierre (inversion, cierre, caducidad o abandono), o hasta hoy si sigue abierta.
- Con los **niveles originales**: si el precio toca antes el objetivo es acierto; si toca antes el stop, fallo, aunque luego el analista moviera el stop. Sin niveles, decide el signo de la rentabilidad al cierre (en VENDER, una caida es acierto).
- **Entradas condicionadas**: si la entrada original esta a mas de un 1 % del precio ("compraria si cae a 10,85", "si supera 13"), la señal empieza el dia en que el precio la toca (`entry_triggered_on`) y el stop y el objetivo se comparan con esa entrada. Si se cierra sin tocarla → `NOT_TRIGGERED`: no es acierto ni fallo; dilo asi ("la compra en 10,85 nunca se activo").
- Abierta y sin stop ni objetivo tocados (o con la entrada aun sin tocar) → `PROVISIONAL`, fuera de la tasa.
- Niveles incoherentes con el precio de ese dia (stop por encima del precio en una compra, etc.) se ignoran y salen en `level_warnings`: suelen ser cifras mal transcritas. Revisa esas señales.
- `signal_alpha_pct`: rentabilidad frente al indice en la direccion de la señal (en VENDER, quedarse por debajo del indice suma).

Campos clave de cada analista:

| Campo | Que es |
| :-- | :-- |
| `hit_rate_pct`, `hit_rate_ci95_pct` | Aciertos / evaluadas y su intervalo de confianza del 95 % |
| `avg_signal_alpha_pct` | Alpha medio frente al indice |
| `by_side` | Lo mismo separado en BUY y SELL |
| `level_moves.total` | Veces que movio entrada, stop u objetivo |
| `level_moves.stop_loosened` | Stops alejados (bajados en compras, subidos en ventas) |
| `level_moves.moved_after_breach` | Niveles movidos despues de que el precio los rompiera ("mover la porteria") |
| `abandoned_without_close` | Señales que dejo de mencionar sin cerrarlas |
| `abandoned_after_single_mention` | De ellas, las mencionadas una sola vez (respuestas sueltas a oyentes, valores de paso). Distinguelas de las que siguio varios dias y dejo caer |
| `sample_warning` | Presente si hay menos de 20 señales evaluadas |

### Como presentarla

Tabla con analista, señales evaluadas, tasa de acierto con su intervalo, alpha medio, compras frente a ventas, niveles movidos (y cuantos tras romperse) y abandonadas. Debajo:

1. **Si hay `sample_warning`, dilo antes que la tasa**: "Con 8 señales el resultado no es significativo: el intervalo va del 25 % al 85 %".
2. Periodo cubierto (`first_video` a `last_video`) y cuantas siguen abiertas o provisionales.
3. Es informacion sobre señales pasadas. **No** digas "sigue a este analista", "es fiable", "hazle caso" ni lo contrario, y no ordenes analistas como recomendacion. Rentabilidades pasadas no garantizan las futuras.
