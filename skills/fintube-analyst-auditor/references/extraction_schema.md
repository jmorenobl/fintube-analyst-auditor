# Esquema de extraccion y diccionario de tickers (Yahoo Finance)

## 1. Esquema de cada señal

Extrae una señal por activo y video. Campos (usa `null` si el video no lo dice; no lo inventes):

```json
{
  "analyst": "Alberto Iturralde",
  "video_id": "abc123XYZ_0",
  "published_at": "2026-10-09",
  "asset_name": "Banco Santander",
  "ticker": "SAN.MC",
  "benchmark": "^IBEX",
  "signal": "BUY | HOLD | SELL",
  "confidence": "explicit | implicit | ambiguous",
  "entry_level": 10.20,
  "stop_loss": 9.80,
  "target_price": 11.50,
  "expiry_date": "2026-11-29",
  "expiry_reason": "Salir antes de las elecciones del 29 de noviembre",
  "timestamp": "[00:14:32]",
  "timestamp_url": "https://www.youtube.com/watch?v=abc123XYZ_0&t=872s",
  "quote": "Cita literal breve que justifica la señal"
}
```

Correspondencia con el semaforo: `BUY` = 🟢 COMPRAR, `HOLD` = 🟡 MANTENER / NEUTRO, `SELL` = 🔴 VENDER / SALIR / PRECAUCION.

## 2. Tabla de presentacion al usuario

| Semaforo | Activo | Ticker | Entrada | Stop | Objetivo | Caducidad | Momento |
| :-- | :-- | :-- | --: | --: | --: | :-- | :-- |
| 🟢 COMPRAR | Banco Santander | SAN.MC | 10,20 | 9,80 | 11,50 | 2026-11-29 | [00:14:32](url) |

Debajo: `Analisis de mercado: X min de Y min (Z %)` y un resumen de la paja descartada en una linea.

## 3. Diccionario de tickers

Si un activo no aparece aqui, deduce el ticker de Yahoo (sufijo `.MC` para el Mercado Continuo, `.PA` Paris, `.DE` Xetra, `.MI` Milan, `.AS` Amsterdam, sin sufijo EE. UU.) y verificalo con `audit`: si devuelve "Sin datos", el ticker es incorrecto.

### Indices

| Nombre mencionado | Ticker | Benchmark |
| :-- | :-- | :-- |
| IBEX 35 / bolsa española | ^IBEX | ^IBEX |
| Euro Stoxx 50 / bolsa europea | ^STOXX50E | ^STOXX50E |
| CAC 40 / bolsa francesa | ^FCHI | ^STOXX50E |
| DAX / bolsa alemana | ^GDAXI | ^STOXX50E |
| FTSE MIB / bolsa italiana | FTSEMIB.MI | ^STOXX50E |
| S&P 500 / bolsa americana | ^GSPC (ETF: SPY) | ^GSPC |
| Nasdaq 100 / tecnologicas EE. UU. | ^NDX (ETF: QQQ) | ^GSPC |
| Nasdaq Composite | ^IXIC | ^GSPC |
| Dow Jones | ^DJI | ^GSPC |
| VIX / volatilidad | ^VIX | — |

### IBEX 35 (benchmark ^IBEX)

| Empresa | Ticker | Empresa | Ticker |
| :-- | :-- | :-- | :-- |
| Banco Santander | SAN.MC | Iberdrola | IBE.MC |
| BBVA | BBVA.MC | Endesa | ELE.MC |
| CaixaBank | CABK.MC | Naturgy | NTGY.MC |
| Banco Sabadell | SAB.MC | Enagas | ENG.MC |
| Bankinter | BKT.MC | Redeia (Red Electrica) | RED.MC |
| Unicaja | UNI.MC | Acciona | ANA.MC |
| Mapfre | MAP.MC | Acciona Energia | ANE.MC |
| Repsol | REP.MC | Solaria | SLR.MC |
| Inditex | ITX.MC | Telefonica | TEF.MC |
| Puig | PUIG.MC | Cellnex | CLNX.MC |
| Amadeus | AMS.MC | Indra | IDR.MC |
| IAG (Iberia) | IAG.MC | Aena | AENA.MC |
| Melia | MEL.MC | ACS | ACS.MC |
| Ferrovial | FER.MC | Sacyr | SCYR.MC |
| ArcelorMittal | MTS.MC | Acerinox | ACX.MC |
| Grifols | GRF.MC | Laboratorios Rovi | ROVI.MC |
| Merlin Properties | MRL.MC | Inmobiliaria Colonial | COL.MC |
| Logista | LOG.MC | Fluidra | FDR.MC |

### Materias primas, divisas, cripto y bonos

| Nombre mencionado | Ticker |
| :-- | :-- |
| Oro / futuro del oro | GC=F |
| Plata | SI=F |
| Cobre | HG=F |
| Petroleo Brent | BZ=F |
| Petroleo WTI / Texas | CL=F |
| Gas natural (Henry Hub) | NG=F |
| Euro-dolar | EURUSD=X |
| Bitcoin | BTC-USD |
| Ethereum | ETH-USD |
| Bono EE. UU. 10 años (rentabilidad) | ^TNX |

Benchmark para materias primas, divisas y cripto: ninguno (`--benchmark ""`) o el que el usuario indique.
