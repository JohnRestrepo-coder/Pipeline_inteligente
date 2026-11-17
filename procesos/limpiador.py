"""
================================================================================
MÓDULO ETL Y CONSOLIDACIÓN DE DATOS (procesos/limpiador.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB
================================================================================
"""

import os
import re
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
import pandas as pd
from openpyxl import load_workbook

import config
from procesos.modelos import sanitizar_numero

class DataCleaner:
    """Utilidades de normalización y limpieza de tipos para el ETL."""

    @staticmethod
    def limpiar_documento(valor: Any) -> str:
        """Extrae dígitos limpios del documento sin decimales de float."""
        if valor is None or pd.isna(valor):
            return "0"
        texto = str(valor).strip()
        if texto.endswith(".0"):
            texto = texto[:-2]
        match = re.search(r'(\d[\d\.\s-]{4,})', texto)
        if match:
            return re.sub(r'\D', '', match.group(0))
        return re.sub(r'\D', '', texto) or "0"

    @staticmethod
    def normalizar_texto(texto: Any, tipo: str) -> str:
        """Normaliza mayúsculas, minúsculas y espacios en blanco."""
        if not texto or not isinstance(texto, str) or pd.isna(texto):
            return ""
        texto = " ".join(texto.strip().split())
        if tipo == "nombre_propio":
            return texto.title()
        elif tipo == "frase":
            return texto.capitalize()
        return texto


class MultiSourceETL:
    """
    Extractor, Transformador y Consolidador de datos multiorigen
    (Encuesta DX1 Maestro + Asesorías individuales de estructura de costos).
    """

    def __init__(
        self,
        ruta_dx1_maestro: Optional[Union[str, Path]] = None,
        ruta_entradas: Optional[Union[str, Path]] = None,
        ruta_salida: Optional[Union[str, Path]] = None,
        nombre_consolidado: str = "Consolidado_Planes_Negocio.xlsx"
    ):
        self.ruta_dx1_maestro = Path(ruta_dx1_maestro or config.RUTA_DX1_DEFAULT)
        self.ruta_entradas = Path(ruta_entradas or config.ENTRADAS_DIR)
        self.ruta_salida = Path(ruta_salida or config.BASE_DIR)
        self.nombre_consolidado = nombre_consolidado
        
        self.hoja_objetivo_asesoria = "As1 Estructura de Costos"
        self.mapeo_campos_asesoria = {
            "Documento": "D2",
            "Nombre": "D3",
            "Nombre_negocio": "D4",
            "Direccion_negocio": "D5",
            "Horas_dedicadas_negocio": "D6",
            "Horario_de_atencion": "D7",
            "Producto_servicio_ofertado": "D8",
            "Numero_empleados": "D9",
            "Fecha_creación_negocio": "D10",
            "ventas_ultimo_mes": "E18",
            "Salidas_ultimo_mes": "E19",
            "Saldo_caja": "E20"
        }
        
        self.columnas_dx1 = [
            "Documento", "Tipo_documento", "Nacionalidad", "Nombre", "Apellido", 
            "año_nacimiento", "fecha_nacimiento", "Territorio", "Direccion", "Cel", 
            "Cel_alternativo", "Correo", "Negocio", "Ingresos_negocio", "Objetivo_negocio", 
            "Tiempo_operacion", "Tipo_empresa", "ACTIVIDAD_ECONOMICA", "Ubicacion_negocio", 
            "HORAS_DIARIAS", "RUT", "Medio_ventas", "Promocion", "principal_medio_entrega_producto", 
            "Usa_redes_sociales", "Nombre_red_social", "Producto_mas_vendido", 
            "has_ganado_confianza_y_seguridad_para_tomar_decisiones", 
            "eres_consciente_de_la_importancia_de_contar_con_otras_opiniones_puntos_de_vista_para_tomar_decisiones_relacionadas_con_el_negocio", 
            "has_mejorado_en_el_manejo_adecuado_de_tu_tiempo", "respetas_los_horarios_que_has_establecido", 
            "te_sientes_mas_seguro_de_tus_capacidades", "buscas_otras_formas_de_expresarte_mejor", 
            "valor_agregado_de_la_empresa_frente_competencia", "porque_clientes_prefieren_su_producto_servicio", 
            "Principales_competidores", "nivel_operacion_competencia", "Mision2", "Vision2", "Valor2", 
            "Nombre_Negocio", "Principal_objetivo_negocio", "Tipo_negocio", "Actividad_economica_detallada", 
            "Descripcion_actividad_economica", "Tiempo_operacion_negocio", "Cuenta_con_equipo_maquinaria_para_operar", 
            "billeteras_electronicas", "transferencias_cuenta_ahorros", "plataformas_tarjeta_credito", "datofono", 
            "medio_venta_productos_servicios", "principal_medio_promocion", "usa_red_social", "redsocial_venta_producto", 
            "red_social", "cuenta_con_estrategias_comerciales", "cuenta_segmentacion_clientes", "Segmento_pertenece_negocio", 
            "porcentaje_segmento_espera_alcanzar", "alcance_ventas_del_negocio", "ha_habido_aumento_de_clientes_ultimos_meses", 
            "participacion_ventas_empresariales", "Realiza_presupuesto_identificar_ingresos", "frecuencia_realiza_presupuesto", 
            "sabe_cuanto_gano_perdio_ultimos_tres_meses", "sabe_cuanto_gano_perdio_mes_pasado", "conoce_ingresos_cubren_costos_negocio", 
            "registro_cuentas_por_pagar_proveedores", "pago_a_proveedores", "socio_estrategico", "Aliados", 
            "registro_camara_comercio", "registro_rut", "facturacion_electronica", "plazo_pago_proveedores", 
            "Sostenibilidad", "numero_clientes_3_meses", "Arriendo-", "Servicios_publicos-", "Salario_emprendedor-"
        ]
        
        self.mapa_dx1: Dict[str, Dict[str, Any]] = {}
        self.datos_asesorias: List[Dict[str, Any]] = []

    def cargar_maestro_dx1(self) -> int:
        """Carga y procesa la información del archivo Maestro DX1."""
        if not self.ruta_dx1_maestro.exists():
            print(f"⚠️ No se encontró el archivo maestro DX1 en {self.ruta_dx1_maestro}")
            return 0

        print(f"📖 Leyendo Archivo Maestro DX1: {self.ruta_dx1_maestro.name}...")
        try:
            df_dx1 = pd.read_excel(self.ruta_dx1_maestro)
            df_dx1.columns = [str(col).strip() for col in df_dx1.columns]
            cols_disponibles = [col for col in self.columnas_dx1 if col in df_dx1.columns]

            for _, fila in df_dx1.iterrows():
                doc_raw = fila.get("Documento", None)
                doc_limpio = DataCleaner.limpiar_documento(doc_raw)
                if doc_limpio == "0":
                    continue

                registro = {col: ("" if pd.isna(fila[col]) else str(fila[col]).strip()) for col in cols_disponibles}
                registro["Documento"] = doc_limpio
                self.mapa_dx1[doc_limpio] = registro

            print(f"✅ Se indexaron {len(self.mapa_dx1)} emprendedores desde el DX1.")
            return len(self.mapa_dx1)
        except Exception as e:
            print(f"❌ Error al procesar el archivo DX1 Maestro: {e}")
            return 0

    def extraer_datos_asesoria_individual(self, ruta_archivo: Path) -> Optional[Dict[str, Any]]:
        """Extrae celdas financieras de las hojas de asesoría de los consultores."""
        try:
            wb = load_workbook(str(ruta_archivo), data_only=True, read_only=True)
            if self.hoja_objetivo_asesoria not in wb.sheetnames:
                wb.close()
                return None

            ws = wb[self.hoja_objetivo_asesoria]
            registro: Dict[str, Any] = {}

            campos_titulo = ["Nombre"]
            campos_frase = [
                "Nombre_negocio", "Direccion_negocio", "Horas_dedicadas_negocio", 
                "Horario_de_atencion", "Producto_servicio_ofertado", "Fecha_creación_negocio"
            ]

            for campo, celda in self.mapeo_campos_asesoria.items():
                valor = ws[celda].value
                if campo == "Documento":
                    registro[campo] = DataCleaner.limpiar_documento(valor)
                elif campo in campos_titulo:
                    registro[campo] = DataCleaner.normalizar_texto(valor, "nombre_propio")
                elif campo in campos_frase:
                    registro[campo] = DataCleaner.normalizar_texto(valor, "frase")
                elif campo in ["ventas_ultimo_mes", "Salidas_ultimo_mes", "Saldo_caja"]:
                    registro[campo] = sanitizar_numero(valor)
                else:
                    registro[campo] = valor.strip() if isinstance(valor, str) else valor

            wb.close()
            return registro
        except Exception as e:
            print(f"❌ Error procesando {ruta_archivo.name}: {e}")
            return None

    def ejecutar_pipeline(self) -> Path:
        """Ejecuta la consolidación y exporta el Excel resultante."""
        self.cargar_maestro_dx1()

        if self.ruta_entradas.exists():
            print(f"🔍 Escaneando archivos de asesorías en: {self.ruta_entradas}")
            for root, _, files in os.walk(self.ruta_entradas):
                for f in files:
                    if f.endswith('.xlsx') and not f.startswith('~$') and "DX1_Yaru" not in f:
                        ruta_file = Path(root) / f
                        datos = self.extraer_datos_asesoria_individual(ruta_file)
                        if datos:
                            datos['Carpeta_Asesor'] = Path(root).name
                            self.datos_asesorias.append(datos)

        consolidado_final = []
        if self.datos_asesorias:
            for datos_as in self.datos_asesorias:
                doc = datos_as.get("Documento", "0")
                registro_unificado = {}
                if doc in self.mapa_dx1:
                    registro_unificado.update(self.mapa_dx1[doc])
                registro_unificado.update(datos_as)
                consolidado_final.append(registro_unificado)
        else:
            consolidado_final = list(self.mapa_dx1.values())

        if not consolidado_final:
            raise ValueError("No se encontraron registros válidos para consolidar.")

        df_final = pd.DataFrame(consolidado_final)
        self.ruta_salida.mkdir(parents=True, exist_ok=True)
        ruta_archivo_final = self.ruta_salida / self.nombre_consolidado
        df_final.to_excel(str(ruta_archivo_final), index=False)
        print(f"✅ ETL EXITOSO: {len(df_final)} registros guardados en: {ruta_archivo_final}")
        return ruta_archivo_final
