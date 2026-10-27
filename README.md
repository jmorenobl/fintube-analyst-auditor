# FinTube Analyst Auditor

**Pregúntale a tu asistente de IA qué recomienda un analista de bolsa en YouTube, sin ver el vídeo entero, y comprueba si acertó.**

Es una *skill* (un "superpoder" que se instala en tu asistente) compatible con el estándar abierto [Agent Skills](https://agentskills.io). Funciona con Claude, ChatGPT, Gemini CLI, Antigravity, Codex, Cursor y otros.

> ⚠️ **No es asesoramiento financiero.** La skill resume opiniones de terceros y las compara con precios históricos. Las decisiones de inversión son tuyas.

## Qué hace

Le escribes cosas como:

- *"Resúmeme este vídeo y dime qué recomienda comprar: https://youtu.be/..."*
- *"¿Qué ha dicho últimamente Alberto Iturralde?"*
- *"En septiembre dijeron que vendiera Santander. ¿Acertaron?"*
- *"Tengo 500 acciones de Repsol. ¿Algún analista ha cambiado de opinión?"*

Y te responde con algo así:

| Semáforo | Activo | Ticker | Entrada | Stop | Caducidad | Momento del vídeo |
| :-- | :-- | :-- | --: | --: | :-- | :-- |
| 🟢 COMPRAR | Banco Santander | SAN.MC | 10,20 | 9,80 | 29-nov | [00:14:32] |
| 🔴 VENDER | Solaria | SLR.MC | — | — | — | [00:03:10] |

*Análisis de mercado: 18 de 52 minutos (35 %). El resto, tertulia política y autopromoción.*

Además, puede comprobar con precios reales de Yahoo Finance si cada recomendación ganó o perdió dinero, compararla con el IBEX 35 y avisarte si contradice tu cartera.

## Instalación

Elige la app que usas. Si dudas, empieza por la primera opción.

### Opción 1 · Pídeselo a tu asistente (la más fácil)

Sirve para cualquier asistente que trabaje en tu ordenador: **Claude Code, Claude Desktop (modo Code), Codex, Gemini CLI, Antigravity, Cursor, Windsurf, OpenCode, GitHub Copilot…**

Copia este mensaje y pégalo en tu asistente:

```text
Instala la skill de https://github.com/jmorenobl/fintube-analyst-auditor
para que esté disponible en todos mis proyectos. Si tengo Node.js, usa
"npx skills add jmorenobl/fintube-analyst-auditor -g". Si no, descarga la
carpeta skills/fintube-analyst-auditor en tu carpeta global de skills.
Comprueba también que tengo Python 3 y uv, y si no, explícame en
lenguaje sencillo cómo instalarlos. Al terminar, dime cómo usarla.
```

El asistente hará el resto y te pedirá permiso antes de cada paso.

### Opción 2 · Claude (claude.ai o la app de escritorio)

1. Descarga **`fintube-analyst-auditor.zip`** desde la [página de versiones](https://github.com/jmorenobl/fintube-analyst-auditor/releases/latest). No lo descomprimas.
2. En Claude, ve a **Configuración → Capacidades** y activa **Ejecución de código y creación de archivos**.
3. En esa misma sección, en los dominios permitidos, añade `youtube.com`, `www.youtube.com` y `finance.yahoo.com`, `query1.finance.yahoo.com` y `query2.finance.yahoo.com`. Sin esto la skill no puede descargar datos.
4. Ve a **Personalizar → Skills**, pulsa **+ Crear skill → Subir una skill** y elige el ZIP.

### Opción 3 · ChatGPT

Disponible en los planes que incluyen Skills (de momento Business, Enterprise y Edu).

1. Descarga **`fintube-analyst-auditor.zip`** desde la [página de versiones](https://github.com/jmorenobl/fintube-analyst-auditor/releases/latest).
2. En ChatGPT, abre **Skills → Crear → Subir desde tu ordenador** y elige el ZIP.

> Los nombres de los menús de Claude y ChatGPT cambian a menudo. Si no los encuentras, pregúntale a la propia app: *"¿Cómo subo una skill en formato ZIP?"*

### Opción 4 · Comandos directos (si ya usas la terminal)

| App | Comando |
| :-- | :-- |
| Cualquiera (detecta tus apps y te deja elegir) | `npx skills add jmorenobl/fintube-analyst-auditor` |
| Claude Code (como plugin, con actualizaciones) | `/plugin marketplace add jmorenobl/fintube-analyst-auditor` y luego `/plugin install fintube-analyst-auditor@fintube` |
| Gemini CLI | `gemini skills install https://github.com/jmorenobl/fintube-analyst-auditor --path skills/fintube-analyst-auditor` |

Instalación manual: copia la carpeta `skills/fintube-analyst-auditor/` en la carpeta de skills de tu app (`~/.claude/skills/`, `~/.agents/skills/`, `~/.gemini/antigravity/skills/`…).

### Requisitos

- **Python 3.9 o superior.** Recomendado: [uv](https://docs.astral.sh/uv/getting-started/installation/), que instala las librerías solo.
- **Conexión a internet** para YouTube y Yahoo Finance.

No necesitas cuentas ni claves de API de pago.

## Lo que conviene saber

- **Funciona mejor en asistentes que se ejecutan en tu ordenador.** YouTube a veces bloquea la descarga de subtítulos desde los servidores de las apps en la nube (Claude.ai, ChatGPT). Si te pasa, usa la opción 1.
- **Los subtítulos automáticos se equivocan** con nombres y cifras. La skill marca como dudosas las señales poco claras, pero revisa el momento del vídeo antes de actuar.
- **Tu cartera se guarda solo en tu ordenador**, en `~/.fintube/portfolio.json`. No se envía a ningún sitio. En las apps de chat en la nube puede perderse al cerrar la conversación.
- **Muchos analistas no publican en su propio canal.** Alberto Iturralde, por ejemplo, sale sobre todo en canales de terceros. Dile a tu asistente qué canal quieres que revise.

## Para desarrolladores

```
.
├── .claude-plugin/             # Marketplace y plugin de Claude Code
├── .github/workflows/          # CI (validación) y release (genera el ZIP)
└── skills/fintube-analyst-auditor/
    ├── SKILL.md                # Instrucciones para el agente
    ├── scripts/fintube_cli.py  # CLI: resolve-channel, scan-rss, transcript, audit, portfolio
    ├── references/             # Esquema de señales y diccionario de tickers
    └── evals/evals.json        # Casos de prueba (formato agentskills.io)
```

Probar el CLI:

```bash
uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py --help
```

Publicar una versión: actualiza la versión en `SKILL.md`, `.claude-plugin/plugin.json` y `CHANGELOG.md`, y crea la etiqueta (`git tag v0.1.0 && git push --tags`). GitHub Actions genera el ZIP y la release.

Las mejoras son bienvenidas, sobre todo nuevos tickers en `references/extraction_schema.md` y *gotchas* detectados al usar la skill.

## English

Agent Skill that turns YouTube stock-market videos (mainly Spanish) into a buy/hold/sell table with timestamps, and audits past calls against Yahoo Finance prices and a benchmark. Install with `npx skills add jmorenobl/fintube-analyst-auditor`, as a Claude Code plugin, or upload the release ZIP to Claude.ai or ChatGPT. Not financial advice. MIT licensed.
