# Changelog

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
