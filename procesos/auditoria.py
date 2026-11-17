"""
================================================================================
MÓDULO DE TRAZABILIDAD Y AUDITORÍA (procesos/auditoria.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB
================================================================================
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd

import config
from procesos.modelos import PlanNegocio


class GestorAuditoria:
    """Gestiona el registro de auditoría y trazabilidad de generaciones de planes."""

    def __init__(self, ruta_archivo: Path = config.RUTA_AUDITORIA):
        self.ruta_archivo = Path(ruta_archivo)
        self.ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    def _inicializar(self) -> None:
        if not self.ruta_archivo.exists():
            self._guardar([])

    def _cargar(self) -> List[Dict[str, Any]]:
        try:
            if self.ruta_archivo.exists():
                with open(self.ruta_archivo, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _guardar(self, registros: List[Dict[str, Any]]) -> None:
        try:
            with open(self.ruta_archivo, "w", encoding="utf-8") as f:
                json.dump(registros, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando auditoría: {e}")

    def registrar_evento(
        self,
        plan: PlanNegocio,
        archivo_word: str,
        modificado_manualmente: bool = False
    ) -> Dict[str, Any]:
        """Registra una sesión de generación y aprobación de plan."""
        registros = self._cargar()
        
        evento = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "documento": plan.id_doc,
            "emprendedor": plan.nombre_emprendedor,
            "negocio": plan.nombre_negocio,
            "territorio": plan.territorio,
            "motor_ia": plan.motor_ia_usado or "No especificado",
            "reintentos_ia": plan.reintentos_ia,
            "aprobado_humano": plan.aprobado_humano,
            "modificado_manualmente": modificado_manualmente,
            "secciones_generadas": len(plan.narrativas),
            "archivo_word": archivo_word
        }

        # Actualizar si ya existía el mismo documento o añadir nuevo
        actualizado = False
        for i, reg in enumerate(registros):
            if reg.get("documento") == plan.id_doc:
                registros[i] = evento
                actualizado = True
                break
        if not actualizado:
            registros.append(evento)

        self._guardar(registros)
        return evento

    def obtener_historial(self) -> List[Dict[str, Any]]:
        return self._cargar()

    def obtener_dataframe(self) -> pd.DataFrame:
        historial = self.obtener_historial()
        if not historial:
            return pd.DataFrame(columns=[
                "timestamp", "documento", "emprendedor", "negocio", 
                "motor_ia", "reintentos_ia", "aprobado_humano", "modificado_manualmente"
            ])
        return pd.DataFrame(historial)

    def obtener_metricas(self) -> Dict[str, Any]:
        historial = self.obtener_historial()
        if not historial:
            return {
                "total": 0,
                "aprobados": 0,
                "modificados": 0,
                "promedio_reintentos": 0.0,
                "motores": {}
            }

        df = pd.DataFrame(historial)
        motores_dict = df["motor_ia"].value_counts().to_dict() if "motor_ia" in df.columns else {}
        
        return {
            "total": len(df),
            "aprobados": int(df["aprobado_humano"].sum()) if "aprobado_humano" in df.columns else 0,
            "modificados": int(df["modificado_manualmente"].sum()) if "modificado_manualmente" in df.columns else 0,
            "promedio_reintentos": round(float(df["reintentos_ia"].mean()), 2) if "reintentos_ia" in df.columns else 0.0,
            "motores": motores_dict
        }
