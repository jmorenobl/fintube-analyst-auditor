# Analistas y canales conocidos

Comprobados el 2026-10-27. Los horarios los aportan usuarios y pueden cambiar: si un video no aparece donde se espera, dilo y pide la URL.

## Especulacion en Bolsa (Alberto Iturralde y Miguel Mendez) — fuente principal

- **Canal:** `UCugd6tlorqt5KTqqB8bKyrg` (`@especulacionenbolsa`)
- **Frecuencia:** un video por dia laborable.
- **Filtro:** todos los videos son suyos; no uses `--keyword` (muchos titulos no los nombran). Usa `--exclude "#shorts"`.
- **Contenido:** situacion general del mercado, indices, materias primas (oro, plata, petroleo), bitcoin y una lista fija de valores de la bolsa española que repasan todos los dias. Responden preguntas de oyentes.
- **Como tratarlo:** dan soportes y resistencias y **los ajustan cada dia**. Trata los videos como una serie:
  - La señal vigente de un valor es la del video mas reciente; las anteriores quedan sustituidas, no son señales nuevas.
  - Si el usuario pregunta por cambios, compara el ultimo video con el anterior y destaca solo lo que cambia (p. ej. "el soporte de SAN.MC sube de 7,80 a 8,10").
  - Al auditar, usa como fecha de señal el primer video en el que aparece cada recomendacion.
  - Registra cada video con `signals --action record` y `analyst: "Especulacion en Bolsa"` (la persona, en `person`, solo si esta claro). El historial calcula la primera aparicion y cada cambio de nivel; con un video por dia laborable, el abandono por defecto (5 videos sin mencion) equivale a una semana.
  - En las preguntas de oyentes, atribuye la respuesta al analista solo si da una opinion propia.

## Capital Radio — intervenciones de Alberto Iturralde

- **Canal:** `UCmU9b04Ym19_OvsSdt7rRYg`
- **Programas:**
  - Lunes 18:00 — Consultorio de Bolsa en *Mercado Abierto*.
  - Viernes 09:30 — Consultorio de Bolsa en *Capital, la Bolsa y la Vida*.
  - Viernes — *Clase Magistral con Alberto Iturralde*, con Laura Blanco: aprendizaje de trading, estrategias y geopolitica. Mas didactico que operativo; extrae señales solo si da niveles concretos.
- **Filtro:** `--keyword "Iturralde|Clase Magistral|Consultorio" --exclude "#shorts"`.
- **Historial:** registra con `analyst: "Capital Radio - Alberto Iturralde"` y consulta con `--abandon-after 0`: los valores dependen de las preguntas de los oyentes, asi que no mencionar uno no significa abandonarlo.
- **Ojo:** el canal sube unos 15 videos al dia, asi que el RSS cubre solo uno o dos dias. Escanea el mismo dia de la emision o pide la URL al usuario.

## Intereconomia — Miguel Mendez

- Interviene en *Capital Intereconomia*, normalmente los miercoles de 11:00 a 12:00 (puede cambiar de dia).
- **Canal no localizado.** `@intereconomia` y `@intereconomiatv` estan abandonados (2010 y 2007). Pide la URL del video o del canal al usuario y resuelvelo con `resolve-channel`.

## Canales descartados

- **Alberto Iturralde (canal personal):** `UC4NCu44AQXnhscxeDrdgvow`. No publica desde 2021.
- **`@CapitalRadio`:** es una radio britanica, no la española.
