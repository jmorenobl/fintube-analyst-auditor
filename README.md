<div align="center">

<img src=".github/assets/banner.svg" alt="FinTube Analyst Auditor: lo que dicen los analistas de YouTube, resumido en un semáforo y auditado con precios reales" width="100%">

<br>

**Pregúntale a tu asistente de IA qué recomienda un analista de bolsa en YouTube,<br>sin ver el vídeo entero, y comprueba si acertó.**

<br>

[![Versión](https://img.shields.io/badge/versión-0.3.0-34d399?style=for-the-badge)](CHANGELOG.md)
[![Licencia EUPL 1.2](https://img.shields.io/badge/licencia-EUPL_1.2-0f2e2a?style=for-the-badge)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/estándar-Agent_Skills-0b1626?style=for-the-badge)](https://agentskills.io)
[![Gratis](https://img.shields.io/badge/sin_API_de_pago-gratis-fbbf24?style=for-the-badge)](#-requisitos)

![Claude](https://img.shields.io/badge/Claude-D97757?style=flat-square&logo=anthropic&logoColor=white)
![ChatGPT](https://img.shields.io/badge/ChatGPT-10A37F?style=flat-square&logo=openai&logoColor=white)
![Gemini CLI](https://img.shields.io/badge/Gemini_CLI-4285F4?style=flat-square&logo=googlegemini&logoColor=white)
![Antigravity](https://img.shields.io/badge/Antigravity-4285F4?style=flat-square&logo=google&logoColor=white)
![Codex](https://img.shields.io/badge/Codex-000000?style=flat-square&logo=openai&logoColor=white)
![Cursor](https://img.shields.io/badge/Cursor-000000?style=flat-square)
![Copilot](https://img.shields.io/badge/Copilot-24292F?style=flat-square&logo=githubcopilot&logoColor=white)
![+ más](https://img.shields.io/badge/+_más-555555?style=flat-square)

[**Instalar**](#-instalación) · [**Qué hace**](#-qué-hace) · [**Ejemplos**](#-ejemplos-de-preguntas) · [**Analistas**](#-analistas-que-ya-conoce) · [**Preguntas frecuentes**](#-lo-que-conviene-saber)

</div>

<br>

> [!WARNING]
> **No es asesoramiento financiero.** La skill resume opiniones de terceros y las compara con precios históricos. Las decisiones de inversión son tuyas.

<br>

## ✨ Qué hace

Una *skill* es un "superpoder" que instalas en tu asistente de IA. Esta le enseña a hacer tres cosas:

<table>
<tr>
<td width="33%" align="center" valign="top">

### 📺
**Ve el vídeo por ti**

Descarga los subtítulos y separa el análisis de bolsa de la tertulia y la autopromoción.

</td>
<td width="33%" align="center" valign="top">

### 🚦
**Te da un semáforo**

Comprar, mantener o vender, con precios de entrada, stop y el minuto exacto del vídeo.

</td>
<td width="33%" align="center" valign="top">

### 📊
**Comprueba si acertó**

Compara cada recomendación con precios reales de Yahoo Finance y con el IBEX 35.

</td>
</tr>
</table>

Además **guarda un historial de cada señal**: sabe cuándo apareció por primera vez, te enseña cada vez que el analista movió un soporte o un stop y calcula su tabla de aciertos frente al IBEX 35.

Y si le cuentas qué acciones tienes, **te avisa cuando un analista cambia de opinión sobre ellas.**

<br>

## 💬 Ejemplos de preguntas

> 🗣️ *"Resúmeme este vídeo y dime qué recomienda comprar: https://youtu.be/..."*
>
> 🗣️ *"¿Qué ha dicho últimamente Alberto Iturralde?"*
>
> 🗣️ *"En septiembre dijeron que vendiera Santander. ¿Acertaron?"*
>
> 🗣️ *"Tengo 500 acciones de Repsol. ¿Algún analista ha cambiado de opinión?"*
>
> 🗣️ *"¿Han movido el soporte de Santander? ¿Qué tasa de acierto tiene Especulación en Bolsa?"*

**Así responde:**

| Semáforo | Activo | Ticker | Entrada | Stop | Caducidad | Momento del vídeo |
| :-- | :-- | :-- | --: | --: | :-- | :-- |
| 🟢 **COMPRAR** | Banco Santander | `SAN.MC` | 10,20 € | 9,80 € | 29-nov | ▶️ 00:14:32 |
| 🟡 **MANTENER** | Iberdrola | `IBE.MC` | — | — | — | ▶️ 00:21:05 |
| 🔴 **VENDER** | Solaria | `SLR.MC` | — | — | — | ▶️ 00:03:10 |

> ⏱️ **Análisis de mercado: 18 de 52 minutos (35 %).** El resto, tertulia política y autopromoción.

<br>

## 📺 Analistas que ya conoce

La skill viene con estos canales comprobados, así que basta con decir el nombre:

| Analista | Dónde | Cuándo |
| :-- | :-- | :-- |
| **Alberto Iturralde y Miguel Méndez** | [Especulación en Bolsa](https://www.youtube.com/@especulacionenbolsa) | Cada día laborable. Mercado general, índices, oro, plata, petróleo, bitcoin y los mismos valores españoles con soportes y resistencias actualizados a diario. |
| **Alberto Iturralde** | [Capital Radio](https://www.youtube.com/channel/UCmU9b04Ym19_OvsSdt7rRYg) | Lunes 18:00 (*Mercado Abierto*), viernes 09:30 (*Capital, la Bolsa y la Vida*) y *Clase Magistral* con Laura Blanco los viernes. |
| **Miguel Méndez** | *Capital Intereconomía* | Miércoles de 11:00 a 12:00. Pásale el enlace del vídeo a tu asistente. |

> [!TIP]
> Como en Especulación en Bolsa repasan los mismos valores cada día, puedes preguntar *"¿qué ha cambiado respecto a ayer?"* y la skill te dirá solo qué soportes o recomendaciones se han movido.

¿Sigues a otro analista? Pásale a tu asistente el enlace de su canal. Y si quieres que lo incluyamos para todos, [abre una propuesta](https://github.com/jmorenobl/fintube-analyst-auditor/issues).

<br>

## 📥 Instalación

### ¿Qué app usas?

| Si usas… | Ve a… | Dificultad |
| :-- | :-- | :-: |
| Claude Code, Codex, Gemini CLI, Antigravity, Cursor, Windsurf, OpenCode, Copilot | [Opción 1 · Pídeselo a tu asistente](#opcion-1) | ⭐ |
| Claude en la web o en la app de escritorio | [Opción 2 · Claude](#opcion-2) | ⭐⭐ |
| ChatGPT | [Opción 3 · ChatGPT](#opcion-3) | ⭐⭐ |
| La terminal (ya sabes lo que es) | [Opción 4 · Comandos](#opcion-4) | ⭐⭐⭐ |

<br>

<a id="opcion-1"></a>
### 1️⃣ Pídeselo a tu asistente &nbsp;<sub>⭐ la más fácil</sub>

Para cualquier asistente que trabaje **en tu ordenador**. Copia este mensaje y pégalo tal cual:

```text
Instala la skill de https://github.com/jmorenobl/fintube-analyst-auditor
para que esté disponible en todos mis proyectos. Si tengo Node.js, usa
"npx skills add jmorenobl/fintube-analyst-auditor -g". Si no, descarga la
carpeta skills/fintube-analyst-auditor en tu carpeta global de skills.
Comprueba también que tengo Python 3 y uv, y si no, explícame en
lenguaje sencillo cómo instalarlos. Al terminar, dime cómo usarla.
```

> [!TIP]
> El asistente hará el resto y te pedirá permiso antes de cada paso. Solo tienes que ir diciendo que sí.

<br>

<a id="opcion-2"></a>
### 2️⃣ Claude &nbsp;<sub>claude.ai o la app de escritorio</sub>

| Paso | Qué hacer |
| :-: | :-- |
| **1** | Descarga **`fintube-analyst-auditor.zip`** desde la [página de versiones](https://github.com/jmorenobl/fintube-analyst-auditor/releases/latest). **No lo descomprimas.** |
| **2** | En Claude, ve a **Configuración → Capacidades** y activa **Ejecución de código y creación de archivos**. |
| **3** | En esa misma sección, añade estos dominios a la lista de permitidos:<br>`youtube.com` · `www.youtube.com` · `finance.yahoo.com` · `query1.finance.yahoo.com` · `query2.finance.yahoo.com` |
| **4** | Ve a **Personalizar → Skills**, pulsa **+ Crear skill → Subir una skill** y elige el ZIP. |

> [!IMPORTANT]
> Sin el paso 3 la skill no puede descargar ni vídeos ni precios.

<br>

<a id="opcion-3"></a>
### 3️⃣ ChatGPT &nbsp;<sub>planes Business, Enterprise y Edu</sub>

| Paso | Qué hacer |
| :-: | :-- |
| **1** | Descarga **`fintube-analyst-auditor.zip`** desde la [página de versiones](https://github.com/jmorenobl/fintube-analyst-auditor/releases/latest). |
| **2** | En ChatGPT, abre **Skills → Crear → Subir desde tu ordenador** y elige el ZIP. |

> [!NOTE]
> Los nombres de los menús de Claude y ChatGPT cambian a menudo. Si no los encuentras, pregúntale a la propia app: *"¿Cómo subo una skill en formato ZIP?"*

<br>

<a id="opcion-4"></a>
### 4️⃣ Comandos directos &nbsp;<sub>si ya usas la terminal</sub>

<details>
<summary><b>Ver los comandos</b></summary>

<br>

**Cualquier app** (detecta las que tienes y te deja elegir):

```bash
npx skills add jmorenobl/fintube-analyst-auditor
```

**Claude Code** (como plugin, con actualizaciones):

```text
/plugin marketplace add jmorenobl/fintube-analyst-auditor
/plugin install fintube-analyst-auditor@fintube
```

**Gemini CLI:**

```bash
gemini skills install https://github.com/jmorenobl/fintube-analyst-auditor --path skills/fintube-analyst-auditor
```

**Manual:** copia la carpeta `skills/fintube-analyst-auditor/` en la carpeta de skills de tu app:

| App | Carpeta |
| :-- | :-- |
| Claude Code | `~/.claude/skills/` |
| Codex, Cursor, OpenCode y otros | `~/.agents/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Antigravity | `~/.gemini/antigravity/skills/` |

</details>

<br>

## ✅ Requisitos

| | Qué necesitas | ¿Por qué? |
| :-: | :-- | :-- |
| 🐍 | **Python 3.9 o superior** | Ejecuta las herramientas que descargan los datos. |
| ⚡ | **[uv](https://docs.astral.sh/uv/getting-started/installation/)** *(recomendado)* | Instala las librerías solo, sin que tengas que hacer nada. |
| 🌐 | **Conexión a internet** | Para leer YouTube y Yahoo Finance. |
| 💸 | ~~Cuentas o claves de pago~~ | **No hacen falta.** Todo es gratis. |

<br>

## 💡 Lo que conviene saber

<details>
<summary><b>🏠 ¿Por qué funciona mejor en mi ordenador que en la web?</b></summary>
<br>
YouTube a veces bloquea la descarga de subtítulos desde los servidores de las apps en la nube (Claude.ai, ChatGPT). Si te pasa, usa la <a href="#opcion-1">opción 1</a> con un asistente que trabaje en tu ordenador.
</details>

<details>
<summary><b>🎙️ ¿Me puedo fiar de lo que entiende del vídeo?</b></summary>
<br>
Los subtítulos automáticos de YouTube se equivocan con nombres y cifras. La skill marca como dudosas las señales poco claras y te da el minuto exacto del vídeo: escucha esos segundos antes de actuar.
</details>

<details>
<summary><b>🔒 ¿Dónde se guarda mi cartera?</b></summary>
<br>
Solo en tu ordenador, en <code>~/.fintube/portfolio.json</code> (y el historial de señales en <code>~/.fintube/signals.json</code>). No se envía a ningún sitio. En las apps de chat en la nube puede perderse al cerrar la conversación.
</details>

<details>
<summary><b>📈 ¿Me puedo fiar de la tabla de aciertos?</b></summary>
<br>
Solo cuenta los vídeos que tu asistente ha registrado: el historial empieza el día que empiezas a usarlo (con los ~15 últimos vídeos del canal). Con menos de 20 señales evaluadas el resultado puede deberse al azar, y la skill te lo dirá. Es información sobre lo que pasó, no una recomendación para seguir a nadie.
</details>

<details>
<summary><b>📡 Le pregunto por un analista y me enseña vídeos antiguos</b></summary>
<br>
Muchos analistas no publican en su propio canal: el canal personal de Alberto Iturralde, por ejemplo, no sube vídeos desde 2021. Los canales de la tabla de <a href="#-analistas-que-ya-conoce">analistas</a> ya están comprobados. Para otros, dile a tu asistente qué canal quieres que revise.
</details>

<br>

## 🛠️ Para desarrolladores

<details>
<summary><b>Estructura del repositorio, pruebas y publicación</b></summary>

<br>

```
.
├── .claude-plugin/             # Marketplace y plugin de Claude Code
├── .github/
│   ├── assets/                 # Imágenes del README
│   └── workflows/              # CI (validación) y release (genera el ZIP)
└── skills/fintube-analyst-auditor/
    ├── SKILL.md                # Instrucciones para el agente
    ├── scripts/fintube_cli.py  # CLI: resolve-channel, scan-rss, transcript, audit, portfolio, signals, scorecard
    ├── references/             # Esquema de señales, tickers y analistas conocidos
    └── evals/evals.json        # Casos de prueba (formato agentskills.io)
```

**Probar el CLI:**

```bash
uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py --help
```

**Validar la skill** con [`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref), el validador oficial del estándar:

```bash
uvx --from "git+https://github.com/agentskills/agentskills#subdirectory=skills-ref" skills-ref validate skills/fintube-analyst-auditor
```

**Publicar una versión:** actualiza la versión en `SKILL.md`, `.claude-plugin/plugin.json` y `CHANGELOG.md`, y crea la etiqueta:

```bash
git tag vX.Y.Z && git push --tags
```

GitHub Actions genera el ZIP y la release.

**Contribuir:** las mejoras son bienvenidas, sobre todo nuevos analistas en `references/analysts.md`, tickers en `references/extraction_schema.md` y *gotchas* detectados al usar la skill. Al contribuir aceptas que tu aportación se publique bajo la EUPL v1.2.

</details>

<br>

<details>
<summary>🇬🇧 <b>English</b></summary>
<br>
Agent Skill that turns YouTube stock-market videos (mainly Spanish) into a buy/hold/sell table with timestamps, and audits past calls against Yahoo Finance prices and a benchmark. Install with <code>npx skills add jmorenobl/fintube-analyst-auditor</code>, as a Claude Code plugin, or upload the release ZIP to Claude.ai or ChatGPT. Not financial advice. Licensed under the EUPL v1.2.
</details>

<br>

<div align="center">
<sub>Hecho con ☕ y 📈 · <a href="LICENSE">Licencia EUPL v1.2</a> · No es asesoramiento financiero</sub>
</div>
