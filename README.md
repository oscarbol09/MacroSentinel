# MacroSentinel

Radar autónomo de inteligencia macroeconómica y señales de política monetaria. Ingesta indicadores cuantitativos oficiales de la Reserva Federal (FRED API), extrae comunicados de bancos centrales (Fed FOMC, BCE), evalúa el tono monetario (*Hawkish* vs *Dovish*) con modelos de razonamiento estructurado y genera informes periódicos (**Macro Pulse**) con visualizaciones de curvas de rendimiento.

---

## Motivación

El análisis macroeconómico tradicional sufre dos fricciones recurrentes:
1. **Sobrecarga de lenguaje burocrático:** Los comunicados y minutas de los bancos centrales acumulan decenas de páginas donde los cambios sutiles de sintaxis definen giros de política monetaria multimillonarios.
2. **Desconexión entre datos duros y narrativa oficial:** Los indicadores de inflación (CPI, PCE), estructura temporal de rendimientos (curva 10Y-2Y) y empleo se publican en calendarios disjuntos y requieren cruce manual contra el discurso de los comités.

MacroSentinel unifica este flujo mediante un pipeline automatizado de ingesta, deduplicación local, razonamiento estructurado y despacho multicanal.

---

## Arquitectura

```
[ APScheduler Worker / CLI ]
             │
             ├──> 1. FRED Client ─────────> [ T10Y2Y, FEDFUNDS, DGS10, CPI, UNRATE, PAYEMS, M2 ]
             │
             └──> 2. Central Bank Feeds ──> [ FOMC Statements, ECB Press Releases ]
                             │
                             ▼
             [ Filtro de Novedades & Cache SQLite WAL ]
                             │
                             ▼
             [ Motor de Inferencia LLM (LiteLLM / Gemini / OpenAI) ]
               - Evaluación continua de tono (-1.0 a +1.0)
               - Detección de anomalías cuantitativas (inversión de curva, Sahm rule)
               - Fallback determinista rule-based ante indisponibilidad de API
                             │
                             ▼
             [ Generador de Gráficos (Matplotlib Agg) ]
               - Visualización de la Curva de Rendimientos (10Y - 2Y Spread)
                             │
                             ▼
             [ Generador de Reportes & Despacho ]
               ├── Markdown Brief (`data/reports/MacroPulse_*.md`)
               ├── Rich Terminal Dashboard
               └── Alertas HTML a Telegram Bot
```

---

## Inicio Rápido

### 1. Instalación

```bash
# Con uv (recomendado)
uv venv
source .venv/bin/activate  # En Windows: .\.venv\Scripts\activate
uv pip install -e .

# O con pip tradicional
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 2. Configuración

Copia `.env.example` a `.env` y configura tus credenciales:

```bash
cp .env.example .env
```

| Variable | Requerido | Propósito |
| :--- | :---: | :--- |
| `FRED_API_KEY` | No (usa baseline) | Clave de acceso a [St. Louis Fed FRED](https://fred.stlouisfed.org/docs/api/api_key.html). |
| `GEMINI_API_KEY` o `OPENAI_API_KEY` | No (usa fallback) | Clave para el motor de inferencia LLM. |
| `LLM_MODEL` | No | Modelo destino (ej. `gemini/gemini-1.5-flash` o `openai/gpt-4o-mini`). |
| `TELEGRAM_BOT_TOKEN` / `CHAT_ID` | No | Credenciales para alertas push automáticas. |
| `SCAN_CRON_SCHEDULE` | No | Expresión cron para el daemon (por defecto: `0 8 * * 1-5`). |

### 3. Comandos de la CLI

```bash
# Ejecutar un escaneo completo inmediato y renderizar en consola
macro-sentinel scan --now

# Iniciar el daemon de escaneos programados en segundo plano
macro-sentinel daemon

# Listar las series temporales e instituciones registradas
macro-sentinel list-series

# Probar la conectividad de red con las APIs y feeds externos
macro-sentinel test-apis
```

---

## Verificación y Pruebas

La suite de pruebas ejecuta validaciones herméticas sin dependencias externas:

```bash
# Ejecutar linter
ruff check .

# Ejecutar tests unitarios e integrados
pytest -v
```

---

## Limitaciones Conocidas & Trade-offs

1. **Revisiones de Datos FRED:** Series como Nonfarm Payrolls (`PAYEMS`) sufren revisiones retroactivas mensuales por parte de la BLS. El sistema lee el valor de serie continua más reciente disponible en la fecha de consulta.
2. **Cálculo de Spreads en Tasas:** Las variaciones en tasas de interés (`unit == "Percent"`) se computan en **Puntos Básicos (bps)** en lugar de porcentaje relativo para evitar distorsiones matemáticas ante lecturas cercanas a cero.
3. **Estructura de Feeds Centrales:** El parser RSS/Atom incluye soporte para etiquetas estándar de la Reserva Federal y el Banco Central Europeo. Cambios estructurales drásticos en las webs emisoras activan el generador de comunicados baseline sin detener el pipeline.

---

## Licencia

MIT License — Oscar Madera (@oscarbol09).
