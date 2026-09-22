"""Generates formatted executive Markdown and HTML briefs for Macro Pulse."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List
from ..analyzer.schemas import MacroPulseReportData
from ..config.settings import get_settings
from ..extractors.fred_client import MacroDataPoint


class ReportGenerator:
    """Renders structured macroeconomic reports into professional Markdown artifacts."""

    def __init__(self):
        self.settings = get_settings()

    def generate_markdown_report(
        self,
        report_data: MacroPulseReportData,
        macro_points: List[MacroDataPoint],
    ) -> Path:
        """Render and save a complete Markdown brief to disk."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_name = f"MacroPulse_{date_str}_{report_data.report_id}.md"
        output_path = self.settings.data_storage_dir / "reports" / file_name

        # Score bar visualizer
        score = report_data.tone_assessment.score
        # score ranges from -1.0 to 1.0
        normalized_pos = int((score + 1.0) * 10)  # 0 to 20
        gauge = ["—"] * 21
        gauge[min(max(normalized_pos, 0), 20)] = "🎯"
        gauge_str = f"DOVISH [-1.0] [{' '.join(gauge)}] [+1.0] HAWKISH"

        # Build table of macro readings
        table_rows = []
        for dp in macro_points:
            delta_str = f"{dp.delta:+.2f} ({dp.delta_percentage:+.1f}%)" if dp.delta is not None else "—"
            table_rows.append(
                f"| **{dp.meta.name}** (`{dp.meta.series_id}`) | `{dp.latest_value:.2f} {dp.meta.unit}` | `{delta_str}` | `{dp.latest_date}` |"
            )
        table_body = "\n".join(table_rows)

        # Build anomalies block
        anomalies_block = []
        for a in report_data.anomalies:
            anomalies_block.append(
                f"- **[{a.severity}] {a.title}** ({a.indicator}):\n  _{a.description}_\n"
                + (f"  *Precedente Histórico:* {a.historical_precedent}\n" if a.historical_precedent else "")
            )
        anomalies_text = "\n".join(anomalies_block) if anomalies_block else "_No critical anomalies flagged._"

        # Build cross-asset block
        cross_asset_text = "\n".join(f"- {item}" for item in report_data.cross_asset_implications)
        watchpoints_text = "\n".join(f"- ⏱️ {item}" for item in report_data.actionable_watchpoints)

        content = f"""# 🦅 MacroSentinel: Macro Pulse Report
**ID del Reporte:** `{report_data.report_id}`  
**Fecha de Generación:** `{report_data.generated_at}`  
**Régimen Dominante:** **{report_data.primary_regime}**

---

## 🎯 Postura de Política Monetaria (Central Bank Tone)

* **Postura Oficial:** `{report_data.tone_assessment.stance.value}` (Puntaje: `{report_data.tone_assessment.score:+.2f}` / Confianza: `{report_data.tone_assessment.confidence * 100:.0f}%`)
* **Termómetro de Tono:**
  `{gauge_str}`

### Justificación del Tono
{report_data.tone_assessment.rationale}

* **Frases Hawkish Clave:**
{chr(10).join(f"  * \"{q}\"" for q in report_data.tone_assessment.key_phrases_hawkish) or "  * _Ninguna destacada_"}

* **Frases Dovish Clave:**
{chr(10).join(f"  * \"{q}\"" for q in report_data.tone_assessment.key_phrases_dovish) or "  * _Ninguna destacada_"}

---

## 📝 Resumen Ejecutivo
{report_data.executive_summary}

---

## 📈 Tablero de Indicadores Macroeconómicos (FRED Data)

| Indicador | Última Lectura | Variación Reciente | Fecha Oficial |
| :--- | :--- | :--- | :--- |
{table_body}

---

## 🚨 Señales de Alerta & Anomalías Detectadas
{anomalies_text}

---

## 💼 Implicaciones por Clase de Activo (Cross-Asset Allocation)
{cross_asset_text}

---

## 🔭 Puntos de Control y Próximos Catalizadores (Watchpoints)
{watchpoints_text}

---
_Generado automáticamente por MacroSentinel Engine. Datos oficiales extraídos de St. Louis Fed FRED y Bancos Centrales._
"""
        output_path.write_text(content, encoding="utf-8")
        return output_path
