"""
================================================================================
CONSTRUCTOR DE DOCUMENTOS WORD INSTITUCIONALES (procesos/redactor.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB
================================================================================
"""

import os
import re
from pathlib import Path
from typing import Optional, Union
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Inches

import config
from procesos.modelos import PlanNegocio


class Redactor:
    """
    Ensambla la plantilla Word institucional de la Fundación WWB
    fusionando los datos tabulares, narrativas de IA y fotografías.
    """

    def __init__(
        self,
        ruta_plantilla: Optional[Union[str, Path]] = None,
        carpeta_salidas: Optional[Union[str, Path]] = None
    ):
        self.ruta_plantilla = Path(ruta_plantilla or config.RUTA_PLANTILLA_DEFAULT)
        self.carpeta_salidas = Path(carpeta_salidas or config.SALIDAS_DIR)
        self.carpeta_salidas.mkdir(parents=True, exist_ok=True)

    def _buscar_imagen(self, folder: str, name: str) -> Optional[str]:
        if not folder or not os.path.exists(folder):
            return None
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG', '.JPEG']:
            p = os.path.join(folder, f"{name}{ext}")
            if os.path.exists(p):
                return p
        return None

    def procesar_plan(self, plan: PlanNegocio) -> Path:
        """
        Renderiza el documento Word final para el plan de negocio y retorna su ruta.
        """
        if not self.ruta_plantilla.exists():
            raise FileNotFoundError(f"No existe la plantilla institucional en: {self.ruta_plantilla}")

        # Cargamos la plantilla institucional con motor Jinja2
        doc = DocxTemplate(str(self.ruta_plantilla))
        
        # Obtenemos el contexto validado desde el modelo Pydantic
        contexto = plan.construir_contexto_word()

        # Inyección dinámica de fotos del emprendimiento
        if plan.ruta_fotos and os.path.exists(plan.ruta_fotos):
            for i in range(1, 4):
                tag_foto = f"foto{i}"
                ruta_img = self._buscar_imagen(plan.ruta_fotos, tag_foto)
                if ruta_img:
                    try:
                        contexto[tag_foto] = InlineImage(doc, ruta_img, width=Inches(3.47))
                    except Exception as e_img:
                        print(f"⚠️ No se pudo incrustar imagen {ruta_img}: {e_img}")
                        contexto[tag_foto] = ""
                else:
                    contexto[tag_foto] = ""
        else:
            for i in range(1, 4):
                contexto[f"foto{i}"] = ""

        # Renderizado único de variables Jinja2
        doc.render(contexto)
        
        # Nombre de archivo normalizado sin caracteres inválidos
        nombre_negocio_limpio = re.sub(r'[\\/*?:"<>|]', "", plan.nombre_negocio).replace(" ", "_")
        nombre_archivo = f"{plan.id_doc}_{nombre_negocio_limpio}.docx"
        ruta_final = self.carpeta_salidas / nombre_archivo
        
        doc.save(str(ruta_final))
        print(f"✅ Word Renderizado: {ruta_final.name}")
        return ruta_final
