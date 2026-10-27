# Changelog

## 0.3.0 - 2026-10-27

- Historial de señales en `~/.fintube/signals.json` (subcomando `signals`): registra lo que dice cada video y reconstruye cada señal desde su primera aparicion, con cada cambio de entrada, stop, objetivo o caducidad y su cierre (inversion, cierre del analista, caducidad o abandono tras 5 videos sin mencion).
- Reprocesar un video lo sustituye en vez de duplicarlo, y los videos se pueden registrar en cualquier orden.
- Nuevo subcomando `scorecard`: tasa de acierto por analista con intervalo de confianza del 95 %, alpha medio frente al indice, compras frente a ventas, niveles movidos (y cuantos despues de que el precio los rompiera) y señales abandonadas. Avisa cuando hay menos de 20 señales evaluadas.
- Las señales se auditan desde su primera aparicion y con sus niveles originales; los niveles incoherentes con el precio se ignoran y se avisa.
- Las entradas condicionadas ("compraria si cae a 10,85") empiezan a contar cuando el precio las toca; si no llega, la señal queda `NOT_TRIGGERED` y no cuenta como fallo.
- Los abandonos distinguen las señales mencionadas una sola vez (respuestas sueltas a oyentes) de las que se venian siguiendo.
- `audit` y `scorecard` comparten una cache de cotizaciones: una descarga por ticker.
- `portfolio` y `signals` comparten la copia `.bak` y la escritura atomica.
- SKILL.md: registrar las señales tras cada video y consultar el historial antes de responder. Nueva referencia `references/signal_history.md`.
- Evals: cuatro casos nuevos (reintentos sin duplicados, tabla de aciertos con muestra pequeña, niveles movidos y no recomendar analistas).

## 0.2.0 - 2026-10-27

- `audit`: rentabilidad total con precios ajustados por dividendos y niveles con precios nominales intradia.
- `audit`: nuevas opciones `--side`, `--stop` y `--target-price`, que indican cuando se toco cada nivel y cual fue primero.
- `audit`: corrige tickers españoles sin sufijo (`IAG` → `IAG.MC`, `IBEX` → `^IBEX`) y devuelve divisa y mercado para comprobarlos.
- `portfolio`: cada compra es un lote (antes una segunda compra borraba la primera), con precio medio ponderado, copia `.bak`, escritura atomica y validacion de valores.
- `scan-rss`: una expresion regular invalida devuelve un error claro en vez de un traceback.
- SKILL.md: las alertas de cartera se redactan como cruce de datos, nunca como recomendacion personal (criterio CNMV).
- Evals con aserciones sobre resultados observables y dos casos nuevos.

## 0.1.0 - 2026-10-27

- Primera version publica.
- CLI con `resolve-channel`, `scan-rss`, `transcript`, `audit` y `portfolio`.
- Analistas conocidos: Especulacion en Bolsa (Iturralde y Mendez), Capital Radio e Intereconomia.
- Licencia EUPL v1.2.
- Instalable con `npx skills add`, como plugin de Claude Code y como ZIP para Claude.ai y ChatGPT.
