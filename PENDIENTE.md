# Pendiente: iteración 2 de las evals de la 0.3.0

Estado a 27/10/2026. La 0.3.0 (historial de señales y `scorecard`) está publicada. Las evals 6-9 se pasaron con skill-creator: la 0.3.0 cumple el 100 % de las aserciones (16/16) y la 0.2.0, el 49 %. Hubo 1 ejecución por configuración.

## Antes de seguir: bloqueo de YouTube

YouTube bloqueó la descarga de subtítulos (`IpBlocked`) tras muchas descargas seguidas. Antes de nada, comprueba que se ha levantado:

```bash
uv run skills/fintube-analyst-auditor/scripts/fintube_cli.py transcript --video g60ppt9frmw | head -c 300
```

Si sigue bloqueado, espera unas horas o usa otra red. Las mejoras 1 a 4 se pueden hacer sin YouTube; solo las evals que descargan transcripciones lo necesitan.

## Mejoras a aplicar

1. **No registrar un vídeo sin transcripción.** Si `transcript` falla, el agente no debe registrar el vídeo con `"signals": []`: el historial creería que no mencionó ningún valor y daría señales por abandonadas sin motivo. En la eval 6 el agente lo hizo bien por su cuenta, pero SKILL.md no lo dice.
   - Dónde: SKILL.md, paso 4, y `references/signal_history.md`, sección 1, junto a "Registra tambien los videos sin señales".

2. **Niveles rotos el mismo día del vídeo.** `breach_date()` excluye a propósito el día del cambio, porque el vídeo pudo publicarse antes del cierre. Caso real: el WTI cerró por encima de su resistencia de 96,8 $ el 15/10, el mismo día en que la subieron a 100 $, y no cuenta como `after_breach`.
   - Propuesta: comprobar también el día del cambio y devolver `after_breach_same_day` aparte. En `level_moves`, añadir `moved_same_day_as_breach` sin sumarlo a `moved_after_breach`.
   - Dónde: `scripts/fintube_cli.py` (`breach_date`, `evaluate_thread`, `build_scorecard`) y la tabla de campos de `signal_history.md`.

3. **Aclarar dos cosas en `references/signal_history.md`:**
   - Una señal puede contar como acierto aunque luego pierda dinero, si tocó antes su objetivo original. Ejemplo: PANW tocó 425 $ y después cayó un 15,6 %. Al presentarla hay que decirlo: "acierto por tocar el objetivo; después cayó".
   - `open` no es lo mismo que `provisional`: una señal abierta que ya tocó su stop o su objetivo está decidida y cuenta en la tasa (45 abiertas frente a 44 provisionales).

4. **Nueva eval con historial pequeño.** Hoy las aserciones del aviso de muestra (eval 7 #2 y eval 9 #3) pasan siempre, porque el historial de prueba tiene 80 señales evaluadas y `sample_warning` no salta.
   - Propuesta: eval 10 con un `signals.json` de 3-4 vídeos (menos de 20 señales evaluadas), que compruebe que la respuesta avisa de la muestra antes de dar la tasa.
   - Prepararlo: copiar los primeros vídeos de `~/.fintube/signals.json` a un fichero de entrada en `evals/files/`.

5. **Otras observaciones de los agentes** (menor prioridad):
   - En el historial no hay ningún `stop_loss`: Especulación en Bolsa da soportes y objetivos, no stops. Revisar si la extracción guarda como `entry_level` niveles del tipo "si pierde X, fuera". La regla está en `signal_history.md`; quizá haga falta un ejemplo con su transcripción.
   - `scorecard` no cuenta como "mover la portería" alejar un objetivo mientras el precio va en contra (Moderna: 236 → 270 $ con el precio cayendo) ni hacer un objetivo de venta menos ambicioso (oro: 3.780 → 4.000 $). Valorar si se añade un `target_moved_away`.
   - `scan-rss` devuelve `matched_count: 15` pero lista 10 (`--limit 10` por defecto). Documentar el límite en SKILL.md o subir el valor por defecto.

## Cómo retomar las evals

- Resultados de la iteración 1: `skills/fintube-analyst-auditor-workspace/iteration-1/` (git lo ignora). Contiene `benchmark.json`, `benchmark.md` y, por eval, `eval_metadata.json`, las respuestas en `*/run-1/outputs/` y `grading.json`.
- La versión 0.2.0 de referencia está en `skills/fintube-analyst-auditor-workspace/skill-snapshot/`. Para la iteración 2, la referencia debería ser la 0.3.0 actual: haz otra copia antes de editar.
- Script para escribir las calificaciones: `skills/fintube-analyst-auditor-workspace/write_grading.py`.
- Abrir el visor de nuevo:
  ```bash
  cd skills/fintube-analyst-auditor-workspace
  python ~/.claude/skills/skill-creator/eval-viewer/generate_review.py iteration-1 --skill-name fintube-analyst-auditor --benchmark iteration-1/benchmark.json
  ```
  Al pulsar "Submit All Reviews" se guarda `feedback.json` en el workspace: léelo al empezar la iteración 2.
- Aislamiento: cada ejecución usa su propio `HOME` con `UV_CACHE_DIR=~/.cache/uv`, y las evals 7-9 parten de una copia de `~/.fintube/signals.json`. Comprueba al final que el real no ha cambiado: `shasum -c skills/fintube-analyst-auditor-workspace/real_fintube.sha`. Esa suma corresponde a los 15 vídeos del 02/10 al 26/10; si registras vídeos nuevos, genérala otra vez.

## Al terminar

Si los cambios afectan al CLI o a SKILL.md, prepara la 0.3.1: SKILL.md, plugin.json, CHANGELOG e insignia del README. Borra este fichero en ese commit.
