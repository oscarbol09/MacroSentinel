"""Generates formatted executive Markdown briefs for Macro Pulse."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

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
        chart_path: Optional[Path] = None,
    ) -> Path:
        """Render and save a complete Markdown brief to disk."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_name = f"MacroPulse_{date_str}_{report_data.report_id}.md"
        output_path = self.settings.data_storage_dir / "reports" / file_name

        score = report_data.tone_assessment.score
        normalized_pos = int((score + 1.0) * 10)  # Maps [-1.0, 1.0] to [0, 20]
        gauge = ["—"] * 21
        clamped_pos = min(max(normalized_pos, 0), 20)
        gauge[clamped_pos] = "🎯"
        gauge_str = f"DOVISH [-1.0] [{' '.join(gauge)}] [+1.0] HAWKISH"

        table_rows = []
        for dp in macro_points:
            if dp.delta_bps is not None:
                delta_str = f"{dp.delta:+.2f} ({dp.delta_bps:+.1f} bps)"
            elif dp.delta is not None and dp.delta_percentage is not None:
                delta_str = f"{dp.delta:+.2f} ({dp.delta_percentage:+.1f}%)"
            else:
                delta_str = "—"

            table_rows.append(
                f"| **{dp.meta.name}** (`{dp.meta.series_id}`) | `{dp.latest_value:.2f} {dp.meta.unit}` | `{delta_str}` | `{dp.latest_date}` |"
            )
        table_body = "\n".join(table_rows)

        anomalies_block = []
        for a in report_data.anomalies:
            prec_line = f"\n  *Precedente Histórico:* {a.historical_precedent}" if a.historical_precedent else ""
            anomalies_block.append(
                f"- **[{a.severity}] {a.title}** ({a.indicator}):\n  _{a.description}_{prec_line}"
            )
        anomalies_text = "\n".join(anomalies_block) if anomalies_block else "_No critical anomalies flagged._"

        cross_asset_text = "\n".join(f"- {item}" for item in report_data.cross_asset_implications)
        watchpoints_text = "\n".join(f"- ⏱️ {item}" for item in report_data.actionable_watchpoints)

        hawkish_quotes = "\n".join(f"  * \"{q}\"" for q in report_data.tone_assessment.key_phrases_hawkish)
        if not hawkish_quotes:
            hawkish_quotes = "  * _Ninguna destacada_"

        dovish_quotes = "\n".join(f"  * \"{q}\"" for q in report_data.tone_assessment.key_phrases_dovish)
        if not dovish_quotes:
            dovish_quotes = "  * _Ninguna destacada_"

        chart_section = ""
        if chart_path and chart_path.exists():
            chart_rel = chart_path.as_posix()
            chart_section = f"\n## 📊 Curva de Rendimientos y Estructura Temporal\n\n![Treasury Yield Curve]({chart_rel})\n\n---\n"

        dialectic_block = []
        if report_data.dialectical_debate:
            for d in report_data.dialectical_debate:
                icon = "🦅" if d.stance == "Hawkish" else "🕊️"
                evidence_items = "\n".join(f"    - {e}" for e in d.key_evidence)
                dialectic_block.append(
                    f"- **{icon} Argumento {d.stance}:**\n{evidence_items}\n    - *Conclusión:* {d.conclusion}"
                )
        dialectic_text = "\n".join(dialectic_block) if dialectic_block else ""
        dialectic_section = (
            f"\n## ⚖️ Debate Dialéctico de Política Monetaria (Halcón vs. Paloma)\n\n{dialectic_text}\n\n---\n"
            if dialectic_text
            else ""
        )

        regime_badge = (
            f"**Cuadrante Investment Clock:** `{report_data.regime_classification.value}`\n"
            if report_data.regime_classification
            else ""
        )

        content = f"""# 🦅 MacroSentinel: Macro Pulse Report
**ID del Reporte:** `{report_data.report_id}`
**Fecha de Generación:** `{report_data.generated_at}`
**Régimen Dominante:** **{report_data.primary_regime}**
{regime_badge}
---

## 🎯 Postura de Política Monetaria (Central Bank Tone)

* **Postura Oficial:** `{report_data.tone_assessment.stance.value}` (Puntaje: `{report_data.tone_assessment.score:+.2f}` / Confianza: `{report_data.tone_assessment.confidence * 100:.0f}%`)
* **Termómetro de Tono:**
  `{gauge_str}`

### Justificación del Tono
{report_data.tone_assessment.rationale}

* **Frases Hawkish Clave:**
{hawkish_quotes}

* **Frases Dovish Clave:**
{dovish_quotes}
{dialectic_section}
---

## 📝 Resumen Ejecutivo
{report_data.executive_summary}

---

## 📈 Tablero de Inteligencia Macroeconómica Multi-Fuente

| Indicador / Serie | Última Lectura | Variación Reciente | Fecha Oficial |
| :--- | :--- | :--- | :--- |
{table_body}
{chart_section}
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
_Generado automáticamente por MacroSentinel Engine. Fuentes oficiales: Federal Reserve FRED, U.S. Treasury, BLS, CFTC y Bancos Centrales._
"""
        output_path.write_text(content, encoding="utf-8")
        return output_path
