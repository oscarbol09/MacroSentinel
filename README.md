# MacroSentinel 🦅📡

> **Radar Autónomo de Inteligencia Macroeconómica y Señales de Política Monetaria**

MacroSentinel es un sistema automatizado de inteligencia financiera que ingesta indicadores macroeconómicos oficiales (FRED API), extrae y analiza comunicados de bancos centrales (Fed FOMC, BCE, etc.), evalúa el tono de política monetaria (*Hawkish* vs *Dovish*) con LLMs y genera reportes ejecutivos periódicos (**Macro Pulse**) con alertas de cambio de ciclo económico.

---

## 🧭 ¿Por qué existe este proyecto?

Los analistas, tesoreros e inversores se enfrentan a dos problemas constantes:
1. **Sobrecarga de texto no estructurado:** Los discursos y minutas de los bancos centrales contienen decenas de páginas con lenguaje burocrático y cambios semánticos sutiles pero críticos.
2. **Desconexión entre el dato duro y el discurso:** Los datos macroeconómicos (inflación, curva de rendimientos, desempleo, masa monetaria M2) se publican en calendarios dispersos y requieren cruzarse manualmente con la postura monetaria oficial.

**MacroSentinel** automatiza este pipeline mediante un patrón *Scanner $\rightarrow$ Filter $\rightarrow$ Reasoner $\rightarrow$ Dispatcher*, eliminando el ruido y entregando síntesis de alta convicción.

---

## 🏗️ Arquitectura del Sistema

```
[ Scheduled Worker / APScheduler ]
               │
               ├──> 1. FRED API Client ───> [ Tasas, Curva 10Y-2Y, CPI, M2, Desempleo ]
               │
               └──> 2. Central Bank Feeds ─> [ FOMC Statements, Minutas BCE, Discursos ]
                               │
                               ▼
               [ Filtro de Novedades & Cache SQLite ]
                               │
                               ▼
               [ LLM Reasoning Engine (Structured Outputs) ]
                 - Puntuación Hawkish / Dovish (-1.0 a +1.0)
                 - Diff semántico vs. reunión previa
                 - Detección de anomalías macro (inversión de curva, shock CPI)
                               │
                               ▼
               [ Report Generator & Chart Engine ] ──> "Macro Pulse Report"
                               │
                               ├──> 📱 Telegram Bot
                               ├──> ✉️ Email (Resend / SMTP)
                               └──> 💻 Rich Terminal CLI
```

---

## 📦 Módulos del Proyecto

* **`macro_sentinel/config/`**: Registro de series temporales de FRED (`T10Y2Y`, `CPIAUCSL`, `FEDFUNDS`, etc.) y configuración centralizada (`pydantic-settings`).
* **`macro_sentinel/extractors/`**: Clientes asíncronos y tipados para FRED y extractores de comunicados de la Reserva Federal (FOMC) y Banco Central Europeo (BCE).
* **`macro_sentinel/analyzer/`**: Esquemas estructurados (`Pydantic`) y motor de inferencia LLM para análisis de tono monetario y correlación cuantitativa.
* **`macro_sentinel/scheduler/`**: Motor de tareas programadas con soporte para cron jobs periódicos y ejecuciones bajo demanda.
* **`macro_sentinel/reports/`**: Generador del reporte semanal/diario *Macro Pulse* con gráficos de curvas macro.
* **`macro_sentinel/dispatchers/`**: Canales de entrega (Telegram, Email, consola interactiva).

---

## 🚀 Inicio Rápido

### 1. Clonar e Instalar Dependencias

```bash
# Con uv (recomendado)
uv venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
uv pip install -e .

# O con pip
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Copia el archivo `.env.example` a `.env` y añade tus claves:

```bash
cp .env.example .env
```

Variables clave:
* `FRED_API_KEY`: Clave gratuita de [Federal Reserve Economic Data](https://fred.stlouisfed.org/docs/api/api_key.html).
* `GEMINI_API_KEY` o `OPENAI_API_KEY`: Proveedor de LLM.
* `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (opcional).

### 3. Comandos de Ejecución

```bash
# Ejecutar un escaneo y reporte inmediato en consola
macro-sentinel scan --now

# Iniciar el demonio de tareas programadas (Scheduler)
macro-sentinel daemon

# Probar la conexión con las APIs externas
macro-sentinel test-apis
```

---

## ⚠️ Limitaciones Conocidas & Trade-offs

1. **Latencia de FRED API:** Los datos macroeconómicos tienen revisiones retroactivas por parte de las agencias oficiales (BEA/BLS); el sistema utiliza datos de serie continua pero documenta si hubo revisiones.
2. **Rate Limits:** Las llamadas a FRED están limitadas a 120 peticiones por minuto. El cliente incluye un mecanismo interno de rate-limiting con retroceso exponencial (*exponential backoff*).
3. **Dependencia de Scraping en Bancos Centrales:** Las URLs de los portales de bancos centrales pueden cambiar de estructura; se recomienda usar feeds RSS oficiales como canal primario.

---

## 📄 Licencia

MIT License — Creado por Dario.
