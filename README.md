# MacroSentinel

Radar autónomo de inteligencia macroeconómica y señales de política monetaria. Ingesta indicadores cuantitativos oficiales de múltiples fuentes (St. Louis Fed FRED, U.S. Treasury Fiscal Data, Bureau of Labor Statistics BLS, CFTC Commitment of Traders), extrae comunicados de bancos centrales (Fed FOMC, BCE), evalúa el tono monetario (*Hawkish* vs *Dovish*) con modelos de razonamiento estructurado (**Financial Chain-of-Thought & Debate Dialéctico**) y genera informes periódicos (**Macro Pulse**) con visualizaciones de curvas de rendimiento y despacho multicanal (Consola, Telegram, Email Digest).

---

## Motivación

El análisis macroeconómico tradicional sufre tres fricciones recurrentes:
1. **Sobrecarga de lenguaje burocrático:** Los comunicados y minutas de los bancos centrales acumulan decenas de páginas donde los cambios sutiles de sintaxis definen giros de política monetaria multimillonarios.
2. **Desconexión y fragmentación multi-fuente:** Los indicadores de inflación (CPI, PCE), estructura temporal de rendimientos (curva 10Y-2Y), deuda fiscal del Tesoro, empleo y posicionamiento en futuros (COT) se publican en calendarios disjuntos y requieren cruce manual.
3. **Fragilidad de pipelines analíticos:** Si una API externa sufre caídas de red o cuotas de tasa, los pipelines tradicionales colapsan por completo.

MacroSentinel unifica este flujo mediante un pipeline asíncrono **Scatter-Gather** con disyuntores (*circuit breakers*), cola de cuarentena (*Dead Letter Queue*), deduplicación local, debate dialéctico (Halcón vs. Paloma) y despacho multicanal.

---

## Arquitectura

```
[ APScheduler Worker / CLI ]
             │
             ├──> Scatter-Gather Ingestion (Concurrente con Circuit Breaker)
             │    ├── 1. FRED Client ─────────> [ T10Y2Y, FEDFUNDS, DGS10, CPI, PCE, UNRATE, PAYEMS, M2, SAHM, DXY, HY Spread ]
             │    ├── 2. U.S. Treasury Client > [ Tipos Medios de Deuda, Deuda Federal Diaria ]
             │    ├── 3. BLS Client (v2) ─────> [ CPI-U Desglosado, Core CPI, Total Nonfarm CES ]
             │    ├── 4. CFTC COT Client ─────> [ Posicionamiento Neto Leveraged Funds en UST y S&P ]
             │    └── 5. Central Bank Feeds ──> [ FOMC Statements, ECB Press Releases ]
             │                    │
             │                    ▼ (Si falla 3x consecutivo)
             │          [ Tabla de Cuarentena (DLQ) ]
             │                    │
             │                    ▼
             ├──> [ Filtro de Novedades & Cache SQLite WAL ]
             │                    │
             │                    ▼
             ├──> [ Motor de Inferencia LLM (LiteLLM / Gemini / OpenAI) ]
             │      - Financial Chain-of-Thought (FinCoT en 4 fases)
             │      - Debate Dialéctico obligatorio (Agente Halcón vs Agente Paloma)
             │      - Clasificación en Cuadrantes Investment Clock (Goldilocks, Reflation, Stagflation, Disinflation)
             │      - Fallback determinista rule-based ante indisponibilidad de API
             │                    │
             │                    ▼
             ├──> [ Generador de Gráficos (Matplotlib Agg) ]
             │      - Visualización de la Curva de Rendimientos (10Y - 2Y Spread)
             │                    │
             │                    ▼
             └──> [ Generador de Reportes & Despacho Multicanal ]
                    ├── Markdown Brief (`data/reports/MacroPulse_*.md`)
                    ├── Rich Terminal Dashboard
                    ├── Alertas HTML a Telegram Bot
                    └── Email Digest Responsive vía Resend API
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
| `BLS_API_KEY` | No | Clave opcional para [BLS API v2](https://data.bls.gov/registrationEngine/) (aumenta cuota diaria). |
| `CFTC_APP_TOKEN` | No | Token de aplicación para la API SODA2 de la CFTC. |
| `GEMINI_API_KEY` o `OPENAI_API_KEY` | No (usa fallback) | Clave para el motor de inferencia LLM. |
| `LLM_MODEL` | No | Modelo destino (ej. `gemini/gemini-1.5-flash` o `openai/gpt-4o-mini`). |
| `TELEGRAM_BOT_TOKEN` / `CHAT_ID` | No | Credenciales para alertas push automáticas a Telegram. |
| `RESEND_API_KEY` / `ALERT_EMAIL_RECIPIENT` | No | Credenciales para el envío de Email Digest matutino. |
| `SCAN_CRON_SCHEDULE` | No | Expresión cron para el daemon (por defecto: `0 8 * * 1-5`). |

### 3. Comandos de la CLI

```bash
# Ejecutar un escaneo completo inmediato y renderizar en consola
macro-sentinel scan --now

# Iniciar el daemon de escaneos programados en segundo plano
macro-sentinel daemon

# Listar todas las series temporales, endpoints y fuentes registradas
macro-sentinel list-series

# Probar la conectividad de red con todas las APIs y feeds externos
macro-sentinel test-apis

# Inspeccionar errores y llamadas aisladas en la cola de cuarentena
macro-sentinel quarantine
```

---

## Verificación y Pruebas

La suite de pruebas ejecuta 16 validaciones herméticas con mocks automáticos:

```bash
# Ejecutar linter y formateador
ruff check .

# Ejecutar suite de pruebas
pytest -v
```

---

## Decisiones Técnicas Clave

1. **Puntos Básicos (bps) en Tasas:** Las variaciones en series de tipo de interés (`unit == "Percent"`) se computan estrictamente en **Puntos Básicos (bps)** ($\Delta \times 100$) para evitar distorsiones matemáticas porcentuales en lecturas cercanas a cero.
2. **Scatter-Gather con Aislamiento:** Si la API del Tesoro o de la CFTC experimenta indisponibilidad, el pipeline no aborta: aísla la falla en la tabla `pipeline_quarantine` y continúa la síntesis con los datos supervivientes de FRED y BLS.
3. **Debate Dialéctico en LLMs:** Para neutralizar el sesgo alcista/complaciente común en modelos de lenguaje, el prompt obliga a presentar una tesis antagónica explícita (Halcón vigilante de inflación vs. Paloma defensora del empleo) antes de formular la síntesis final.

---

## Licencia

MIT License — Oscar Madera (@oscarbol09).

