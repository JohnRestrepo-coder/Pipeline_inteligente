"""
================================================================================
CONTRATO DE DATOS Y VALIDACIÓN ROBUSTA CON PYDANTIC (procesos/modelos.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB
================================================================================
"""

import os
import re
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


def sanitizar_numero(valor: Any) -> float:
    """
    Convierte celdas de Excel corruptas, vacías, con signos de moneda ($),
    puntos de miles o comas decimales a un flotante seguro (0.0 por defecto).
    """
    if valor is None:
        return 0.0
    
    # Si ya es numérico
    if isinstance(valor, (int, float)):
        import math
        return 0.0 if math.isnan(valor) else float(valor)
    
    texto = str(valor).strip()
    if not texto or texto.lower() in ["nan", "none", "null", "n/a", "-", "--", "sin dato"]:
        return 0.0
    
    # Remover signos de moneda y espacios
    texto = re.sub(r'[\$\s]', '', texto)
    
    # Manejo de formatos tipo 1.500.000 o 1,500,000 o 1500000.50
    try:
        if "." in texto and "," in texto:
            # Caso 1.500.000,50 -> eliminar puntos de miles y coma a punto
            if texto.find(".") < texto.find(","):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                # Caso 1,500,000.50
                texto = texto.replace(",", "")
        elif "," in texto:
            # Caso 1500,50 o 1,500
            partes = texto.split(",")
            if len(partes[-1]) == 3 and len(partes) > 1:
                # Separador de miles
                texto = texto.replace(",", "")
            else:
                # Decimal
                texto = texto.replace(",", ".")
        elif "." in texto:
            partes = texto.split(".")
            # Si tiene múltiples puntos (ej. 1.500.000) son miles
            if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
                texto = texto.replace(".", "")
                
        return float(re.sub(r'[^\d\.-]', '', texto))
    except (ValueError, TypeError):
        return 0.0


class DatosFinancieros(BaseModel):
    """Sub-modelo de validación financiera del emprendimiento."""
    ventas_ultimo_mes: float = Field(default=0.0, description="Ingresos reportados del último mes")
    salidas_ultimo_mes: float = Field(default=0.0, description="Costos y gastos del último mes")
    saldo_caja: float = Field(default=0.0, description="Flujo de caja o saldo disponible")

    @field_validator("ventas_ultimo_mes", "salidas_ultimo_mes", "saldo_caja", mode="before")
    @classmethod
    def validar_cifras(cls, v: Any) -> float:
        return sanitizar_numero(v)

    @property
    def margen_estimado(self) -> float:
        return self.ventas_ultimo_mes - self.salidas_ultimo_mes

    def formato_moneda(self, valor: float) -> str:
        return f"${valor:,.0f}".replace(",", ".")


class PlanNegocio(BaseModel):
    """
    Ficha Técnica validada con Pydantic.
    Garantiza integridad ante celdas corruptas de Excel y audita el proceso de IA.
    """
    id_doc: str = Field(..., description="Número de identificación sin decimales")
    nombre_emprendedor: str = Field(..., description="Nombre completo del emprendedor")
    nombre_negocio: str = Field(default="Unidad Productiva", description="Nombre de la unidad productiva")
    territorio: str = Field(default="No registrado")
    actividad_economica: str = Field(default="Comercio / Servicios")
    descripcion_actividad: str = Field(default="")
    
    # Datos financieros estructurados y validados
    datos_financieros: DatosFinancieros = Field(default_factory=DatosFinancieros)
    
    # Diccionario completo de todas las columnas del Excel consolidado
    datos_completos: Dict[str, Any] = Field(default_factory=dict)
    
    # Narrativas generadas por la IA
    narrativas: Dict[str, str] = Field(default_factory=dict)
    resumen_ejecutivo: str = Field(default="")
    analisis_competencia: str = Field(default="")
    
    # Ruta de carpeta o archivo de fotos
    ruta_fotos: Optional[str] = Field(default=None)
    
    # Trazabilidad y Auditoría (Requisito Maestría y WWB)
    reintentos_ia: int = Field(default=0, description="Número de intentos de generación IA")
    motor_ia_usado: str = Field(default="", description="Motor que generó el texto (Ollama / Gemini)")
    aprobado_humano: bool = Field(default=False, description="Validación del asesor HITL")
    fecha_procesamiento: Optional[str] = Field(default=None)

    @field_validator("id_doc", mode="before")
    @classmethod
    def normalizar_documento(cls, v: Any) -> str:
        if v is None:
            return "REG_000"
        texto = str(v).strip()
        if texto.endswith(".0"):
            texto = texto[:-2]
        # Conservar solo caracteres numéricos o alfanuméricos limpios
        limpio = re.sub(r'[^\w\-]', '', texto)
        return limpio if limpio else "REG_000"

    @field_validator("nombre_emprendedor", mode="before")
    @classmethod
    def normalizar_nombre(cls, v: Any) -> str:
        if not v or str(v).lower() in ["nan", "none"]:
            return "EMPRENDEDOR SIN NOMBRE"
        return " ".join(str(v).strip().split()).upper()

    @field_validator("nombre_negocio", mode="before")
    @classmethod
    def normalizar_negocio(cls, v: Any) -> str:
        if not v or str(v).lower() in ["nan", "none"]:
            return "Unidad Productiva"
        return " ".join(str(v).strip().split())

    @model_validator(mode="after")
    def sincronizar_atributos(self) -> "PlanNegocio":
        # Sincroniza campos directos si vienen en las narrativas
        if "Resumen_ejecutivo" in self.narrativas and not self.resumen_ejecutivo:
            self.resumen_ejecutivo = self.narrativas["Resumen_ejecutivo"]
        if "Competencia" in self.narrativas and not self.analisis_competencia:
            self.analisis_competencia = self.narrativas["Competencia"]
        return self

    def construir_contexto_word(self) -> Dict[str, Any]:
        """
        Construye el diccionario de contexto para Jinja2 / docxtpl,
        inyectando variables de Excel, narrativas IA y datos financieros formateados.
        """
        contexto: Dict[str, Any] = {
            "Documento": self.id_doc,
            "Nombre": self.nombre_emprendedor,
            "Negocio": self.nombre_negocio,
            "Territorio": self.territorio,
            "Resumen_ejecutivo": self.resumen_ejecutivo or self.narrativas.get("Resumen_ejecutivo", ""),
            "analisis_competencia": self.analisis_competencia or self.narrativas.get("Competencia", ""),
            
            # Formatos de moneda legibles
            "ventas_ultimo_mes_formato": self.datos_financieros.formato_moneda(self.datos_financieros.ventas_ultimo_mes),
            "Salidas_ultimo_mes_formato": self.datos_financieros.formato_moneda(self.datos_financieros.salidas_ultimo_mes),
            "Saldo_caja_formato": self.datos_financieros.formato_moneda(self.datos_financieros.saldo_caja),
            "Margen_formato": self.datos_financieros.formato_moneda(self.datos_financieros.margen_estimado),
        }

        # Inyectar todos los datos del Excel
        for k, v in self.datos_completos.items():
            clave_limpia = str(k).strip()
            if clave_limpia not in contexto:
                contexto[clave_limpia] = "" if (v is None or str(v).lower() in ["nan", "none"]) else str(v)

        # Inyectar todas las narrativas generadas por la IA
        for k, v in self.narrativas.items():
            contexto[k] = v

        return contexto

    @classmethod
    def desde_diccionario(cls, fila: Dict[str, Any], carpeta_fotos_base: Optional[str] = None) -> "PlanNegocio":
        """
        Factory method que crea y valida una instancia desde una fila de Excel / DataFrame.
        """
        doc_id = str(fila.get("Documento", fila.get("DOCUMENTO", "0"))).strip()
        
        # Extracción de nombres
        nombre_raw = fila.get("Nombre", fila.get("NOMBRE", ""))
        apellido_raw = fila.get("Apellido", fila.get("APELLIDO", ""))
        nombre_completo = f"{nombre_raw} {apellido_raw}".strip()
        if not nombre_completo:
            nombre_completo = "Emprendedor Sin Nombre"

        negocio_raw = fila.get("Negocio", fila.get("Nombre_negocio", fila.get("Nombre_Negocio", "Unidad Productiva")))

        # Datos financieros
        finanzas = DatosFinancieros(
            ventas_ultimo_mes=fila.get("ventas_ultimo_mes", 0.0),
            salidas_ultimo_mes=fila.get("Salidas_ultimo_mes", 0.0),
            saldo_caja=fila.get("Saldo_caja", 0.0)
        )

        plan = cls(
            id_doc=doc_id,
            nombre_emprendedor=nombre_completo,
            nombre_negocio=str(negocio_raw),
            territorio=str(fila.get("Territorio", fila.get("TERRITORIO", "No registrado"))),
            actividad_economica=str(fila.get("Actividad_economica_detallada", fila.get("ACTIVIDAD_ECONOMICA", ""))),
            descripcion_actividad=str(fila.get("Descripcion_actividad_economica", "")),
            datos_financieros=finanzas,
            datos_completos={str(k).strip(): v for k, v in fila.items()},
            fecha_procesamiento=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Buscar carpeta de fotos asociada al ID del documento
        if carpeta_fotos_base and os.path.exists(carpeta_fotos_base):
            for carpeta in os.listdir(carpeta_fotos_base):
                if plan.id_doc in carpeta:
                    plan.ruta_fotos = os.path.join(carpeta_fotos_base, carpeta)
                    break

        return plan
