"""
================================================================================
ORQUESTADOR PRINCIPAL DEL PIPELINE INTELIGENTE (main.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB
Soporta configuración dinámica, modelo Pydantic y trazabilidad de auditoría.
================================================================================
"""

import os
import sys
from pathlib import Path
from typing import List
import pandas as pd

import config
from procesos.modelos import PlanNegocio
from procesos.cerebro import MotorIAHibrido
from procesos.redactor import Redactor
from procesos.auditoria import GestorAuditoria


def cargar_datos(ruta_excel: Path, carpeta_fotos: Path = config.ENTRADAS_DIR / "Fotos") -> List[PlanNegocio]:
    """
    Carga y valida los registros desde el Excel consolidado usando Pydantic.
    """
    if not ruta_excel.exists():
        print(f"❌ ERROR: No se encontró el archivo consolidado en {ruta_excel}")
        return []

    print(f"📊 Leyendo registros desde: {ruta_excel.name}...")
    try:
        df = pd.read_excel(ruta_excel)
    except Exception as e:
        print(f"❌ Error al abrir la hoja de cálculo: {e}")
        return []

    df.columns = [str(c).strip() for c in df.columns]
    lista_planes: List[PlanNegocio] = []

    for _, fila in df.iterrows():
        try:
            plan = PlanNegocio.desde_diccionario(
                fila=fila.to_dict(),
                carpeta_fotos_base=str(carpeta_fotos) if carpeta_fotos.exists() else None
            )
            lista_planes.append(plan)
        except Exception as e_val:
            print(f"⚠️ Error validando registro con Pydantic: {e_val}")

    return lista_planes


def ejecutar_pipeline(modo_ia: str = config.DEFAULT_AI_ENGINE):
    """
    Ejecuta el pipeline con supervisión humana en consola (HITL).
    """
    print("\n" + "=" * 75)
    print("🚀 PIPELINE AUTOMATIZADO DE PLANES DE NEGOCIO - FUNDACIÓN WWB")
    print("=" * 75 + "\n")

    if not config.RUTA_PLANTILLA_DEFAULT.exists():
        print(f"❌ ERROR CRÍTICO: La plantilla institucional no existe en:\n   {config.RUTA_PLANTILLA_DEFAULT}")
        return

    planes = cargar_datos(config.RUTA_CONSOLIDADO_DEFAULT)
    if not planes:
        print("⚠️ No existen registros para procesar. Abortando.")
        return

    print(f"✅ Se cargaron y validaron {len(planes)} registros con Pydantic.\n")

    motor_ia = MotorIAHibrido(modo=modo_ia)
    redactor = Redactor()
    auditor = GestorAuditoria()

    total = len(planes)
    for i, plan in enumerate(planes, 1):
        print("\n" + "-" * 75)
        print(f"📋 REGISTRO [{i}/{total}]: {plan.nombre_emprendedor}")
        print(f"🏢 Emprendimiento: {plan.nombre_negocio} | ID: {plan.id_doc} | Territorio: {plan.territorio}")
        print("-" * 75)

        aprobado = False
        intentos = 0
        max_intentos = config.MAX_RETRIES

        while not aprobado and intentos < max_intentos:
            intentos += 1
            print(f"  🧠 Generando narrativas con IA ({motor_ia.modo}) - Intento {intentos}...")
            plan = motor_ia.generar_narrativas_plan(plan)

            print(f"\n  🔍 [VISTA PREVIA - RESUMEN EJECUTIVO]:")
            resumen_prev = plan.resumen_ejecutivo[:250] + "..." if len(plan.resumen_ejecutivo) > 250 else plan.resumen_ejecutivo
            print(f"  \"{resumen_prev}\"\n")

            confirmacion = input("  👉 ¿Desea aprobar esta versión para generar el documento Word? (s/n): ").strip().lower()
            if confirmacion in ['s', 'si', 'y', 'yes', '']:
                aprobado = True
                plan.aprobado_humano = True
                print("  ✅ Narrativas aprobadas por el asesor.")
            else:
                if intentos < max_intentos:
                    print("  🔄 Reintentando generación...")
                else:
                    print("  ⚠️ Límite de intentos alcanzado. Se ensamblará con la última versión.")

        try:
            ruta_word = redactor.procesar_plan(plan)
            auditor.registrar_evento(plan, archivo_word=ruta_word.name)
            print(f"  📝 Documento listo en: {ruta_word}")
        except Exception as e_word:
            print(f"  ❌ Error generando Word: {e_word}")

    print("\n" + "=" * 75)
    print("✨ PIPELINE FINALIZADO CON ÉXITO")
    print(f"📁 Salidas guardadas en: {config.SALIDAS_DIR}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    ejecutar_pipeline()
