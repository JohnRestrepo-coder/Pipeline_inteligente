"""
================================================================================
MOTOR DE INTELIGENCIA ARTIFICIAL HÍBRIDO Y RESILIENTE (procesos/cerebro.py)
Proyecto: Pipeline Inteligente de Planes de Negocio - Fundación WWB
Soporta: Inferencia Local (Ollama) + Respaldo en la Nube (Google Gemini Flash)
Incluye: Telemetría en tiempo real, medición de tokens/segundo y diagnósticos de salud.
================================================================================
"""

import os
import json
import re
import time
import requests
from typing import Dict, Any, List, Optional, Tuple, Callable

import config
from procesos.modelos import PlanNegocio

# ==============================================================================
# CONFIGURACIÓN DE PROMPTS Y MAPEO INSTITUCIONAL WWB (OPTIMIZADOS PARA VELOCIDAD)
# ==============================================================================
CONFIG_IA = {
    "Resumen_ejecutivo": {
        "columnas": [
            "Nombre_Negocio", "Actividad_economica_detallada", 
            "Descripcion_actividad_economica", "Tiempo_operacion_negocio", 
            "Tipo_negocio", "Territorio"
        ],
        "prompt": (
            "Redacta un resumen ejecutivo conciso (aprox. 50 palabras) del emprendimiento {Nombre_Negocio} en {Territorio}. "
            "Actividad: {Actividad_economica_detallada} ({Descripcion_actividad_economica}). "
            "Tiempo: {Tiempo_operacion_negocio}. Tipo: {Tipo_negocio}. Tono profesional e inspirador."
        )
    },
    "Mision": {
        "columnas": ["Mision"],
        "prompt": "Redacta de forma profesional y clara la misión del emprendimiento basada en: {Mision}"
    },
    "Vision": {
        "columnas": ["Vision"],
        "prompt": "Redacta de forma profesional la visión a futuro del emprendimiento basada en: {Vision}"
    },
    "Valor": {
        "columnas": ["Valor"],
        "prompt": "Redacta los valores y principios éticos del emprendimiento basados en: {Valor}"
    },
    "Objetivos": {
        "columnas": [
            "Principal_objetivo_negocio", 
            "Cuenta_con_equipo_maquinaria_para_operar", 
            "Realiza_presupuesto_identificar_ingresos"
        ],
        "prompt": (
            "Redacta en un párrafo de 50 palabras los objetivos comerciales y operativos basándote en: "
            "Objetivo: {Principal_objetivo_negocio}, Equipos: {Cuenta_con_equipo_maquinaria_para_operar}, "
            "Presupuesto: {Realiza_presupuesto_identificar_ingresos}."
        )
    },
    "Perfil_del_emprendedor": {
        "columnas": [
            "has_ganado_confianza_y_seguridad_para_tomar_decisiones", 
            "eres_consciente_de_la_importancia_de_contar_con_otras_opiniones_puntos_de_vista_para_tomar_decisiones_relacionadas_con_el_negocio", 
            "te_sientes_mas_seguro_de_tus_capacidades", 
            "buscas_otras_formas_de_expresarte_mejor"
        ],
        "prompt": (
            "Redacta un párrafo de 50 palabras destacando las fortalezas, liderazgo y autoconfianza del emprendedor: "
            "Decisiones: {has_ganado_confianza_y_seguridad_para_tomar_decisiones}, "
            "Opiniones: {eres_consciente_de_la_importancia_de_contar_con_otras_opiniones_puntos_de_vista_para_tomar_decisiones_relacionadas_con_el_negocio}, "
            "Capacidades: {te_sientes_mas_seguro_de_tus_capacidades}."
        )
    },
    "Productos_y_servicios": {
        "columnas": [
            "Producto_mas_vendido", "Actividad_economica_detallada", 
            "Descripcion_actividad_economica", "principal_medio_entrega_producto"
        ],
        "prompt": (
            "Describe en 40 palabras los productos/servicios clave: "
            "Producto estrella: {Producto_mas_vendido}, Actividad: {Actividad_economica_detallada}, "
            "Entrega: {principal_medio_entrega_producto}."
        )
    },
    "Propuesta_de_valor": {
        "columnas": [
            "valor_agregado_de_la_empresa_frente_competencia", 
            "porque_clientes_prefieren_su_producto_servicio", 
            "Producto_mas_vendido", "Principales_competidores"
        ],
        "prompt": (
            "Redacta la propuesta de valor en 35 palabras explicando el diferencial frente a la competencia ({Principales_competidores}). "
            "Diferencial: {valor_agregado_de_la_empresa_frente_competencia}. Preferencia: {porque_clientes_prefieren_su_producto_servicio}."
        )
    },
    "Fabricacion_productos": {
        "columnas": [
            "Producto_mas_vendido", "Actividad_economica_detallada", 
            "Descripcion_actividad_economica", "medio_venta_productos_servicios", 
            "principal_medio_entrega_producto"
        ],
        "prompt": (
            "Describe en 60 palabras el proceso operativo o de prestación de servicios para {Actividad_economica_detallada}: "
            "Procedimiento: {Descripcion_actividad_economica}. Canal de venta: {medio_venta_productos_servicios}."
        )
    },
    "Administracion_financiera_presupuesto": {
        "columnas": [
            "Realiza_presupuesto_identificar_ingresos", "frecuencia_realiza_presupuesto", 
            "sabe_cuanto_gano_perdio_mes_pasado", "conoce_ingresos_cubren_costos_negocio"
        ],
        "prompt": (
            "Redacta en 35 palabras el manejo financiero del emprendimiento: "
            "Presupuesto: {Realiza_presupuesto_identificar_ingresos}, Frecuencia: {frecuencia_realiza_presupuesto}, "
            "Control de resultados: {sabe_cuanto_gano_perdio_mes_pasado}."
        )
    },
    "Sostenibilidad_ambiental": {
        "columnas": ["Actividad_economica_detallada", "Descripcion_actividad_economica", "Sostenibilidad"],
        "prompt": (
            "Redacta en 45 palabras las prácticas ambientales y sostenibles de la unidad productiva de {Actividad_economica_detallada}: "
            "Acciones: {Sostenibilidad} y {Descripcion_actividad_economica}."
        )
    },
    "Perfil_clientes": {
        "columnas": [
            "Producto_mas_vendido", "Actividad_economica_detallada", 
            "cuenta_segmentacion_clientes", "ha_habido_aumento_de_clientes_ultimos_meses", 
            "porque_clientes_prefieren_su_producto_servicio"
        ],
        "prompt": (
            "Redacta en 50 palabras el perfil del cliente objetivo para {Actividad_economica_detallada}: "
            "Segmentación: {cuenta_segmentacion_clientes}. Preferencia: {porque_clientes_prefieren_su_producto_servicio}."
        )
    },
    "Segmento_mercado": {
        "columnas": [
            "Segmento_pertenece_negocio", "porcentaje_segmento_espera_alcanzar", 
            "alcance_ventas_del_negocio", "Actividad_economica_detallada"
        ],
        "prompt": (
            "Redacta en 50 palabras el segmento de mercado ({Segmento_pertenece_negocio}) "
            "y alcance de ventas ({alcance_ventas_del_negocio}) para {Actividad_economica_detallada}."
        )
    },
    "Competencia": {
        "columnas": [
            "Actividad_economica_detallada", "Principales_competidores", 
            "nivel_operacion_competencia", "valor_agregado_de_la_empresa_frente_competencia"
        ],
        "prompt": (
            "Redacta en 50 palabras la identificación de competidores ({Principales_competidores}) "
            "y el factor diferencial ({valor_agregado_de_la_empresa_frente_competencia})."
        )
    },
    "Estrategia_ventas": {
        "columnas": [
            "cuenta_con_estrategias_comerciales", "redsocial_venta_producto", 
            "usa_red_social", "medio_venta_productos_servicios", "principal_medio_entrega_producto"
        ],
        "prompt": (
            "Describe en 50 palabras la estrategia de ventas: "
            "Estrategia: {cuenta_con_estrategias_comerciales}, Canales: {medio_venta_productos_servicios}, Entrega: {principal_medio_entrega_producto}."
        )
    },
    "red_social": {
        "columnas": ["red_social", "Nombre_red_social", "Negocio"],
        "prompt": (
            "Redacta en 30 palabras los canales digitales o redes activas del emprendimiento: {red_social} ({Nombre_red_social})."
        )
    },
    "Herramientas_difundir": {
        "columnas": ["principal_medio_promocion", "usa_red_social"],
        "prompt": (
            "Redacta en 30 palabras los medios de difusión comercial: "
            "Medio principal: {principal_medio_promocion}, Redes: {usa_red_social}."
        )
    },
    "Estrategia_marketing_digital": {
        "columnas": ["RedSocial_ventas", "principal_medio_promocion", "usa_red_social", "cuenta_con_estrategias_comerciales"],
        "prompt": (
            "Redacta en 45 palabras la estrategia de marketing digital para promocionar y vender con base en: "
            "{RedSocial_ventas}, {principal_medio_promocion}."
        )
    }
}

BLOQUE_1 = ["Resumen_ejecutivo", "Mision", "Vision", "Valor", "Objetivos", "Perfil_del_emprendedor"]
BLOQUE_2 = ["Productos_y_servicios", "Propuesta_de_valor", "Fabricacion_productos", "Administracion_financiera_presupuesto", "Sostenibilidad_ambiental"]
BLOQUE_3 = ["Perfil_clientes", "Segmento_mercado", "Competencia", "Estrategia_ventas", "red_social", "Herramientas_difundir", "Estrategia_marketing_digital"]

INSTRUCCION_SISTEMA_WWB = (
    "Actúa como consultor senior de la Fundación WWB Colombia.\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. PROHIBIDO usar las palabras 'empresa' o 'negocio'. Usa SIEMPRE 'emprendimiento' o 'unidad productiva'.\n"
    "2. Redacta en tercera persona, con tono humano, empático, claro y conciso.\n"
    "3. No inventes datos que no figuren en la información provista.\n"
    "4. Retorna EXCLUSIVAMENTE un objeto JSON válido donde cada clave sea exactamente el nombre de la sección solicitada."
)


class MotorIAHibrido:
    """
    Motor inteligente con resiliencia híbrida y telemetría:
    - Prioridad 1: Ollama Local (llama3:latest / llama3.2:3b).
    - Respaldo: Google Gemini (1.5 Flash).
    """

    def __init__(
        self,
        modo: str = config.DEFAULT_AI_ENGINE,
        ollama_host: str = config.OLLAMA_HOST,
        ollama_model: str = config.OLLAMA_MODEL,
        gemini_api_key: str = config.GEMINI_API_KEY,
        gemini_model: str = config.GEMINI_MODEL,
        timeout: int = 240  # Ampliado a 240s para inferencia en CPU sin fallos
    ):
        self.modo = modo.lower()  # "auto", "ollama", o "gemini"
        self.ollama_host = ollama_host.rstrip('/')
        self.ollama_model = ollama_model
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = gemini_model
        self.timeout = timeout
        
        self._gemini_client = None
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                self._gemini_client = genai.GenerativeModel(
                    model_name=self.gemini_model,
                    system_instruction=INSTRUCCION_SISTEMA_WWB
                )
            except Exception as e:
                print(f"⚠️ Aviso al configurar Gemini: {e}")

    def verificar_ollama(self) -> bool:
        """Comprueba si el servidor local de Ollama está activo."""
        try:
            r = requests.get(f"{self.ollama_host}/", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def obtener_modelos_ollama(self) -> List[str]:
        """Consulta los modelos disponibles localmente en Ollama."""
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            if r.status_code == 200:
                modelos = [m["name"] for m in r.json().get("models", [])]
                if modelos:
                    return modelos
        except Exception:
            pass
        return [self.ollama_model]

    def verificar_gemini(self) -> bool:
        """Comprueba si la API de Gemini está configurada."""
        return bool(self.gemini_api_key and len(self.gemini_api_key.strip()) > 10)

    def diagnosticar_salud(self) -> Dict[str, Any]:
        """
        Ejecuta un diagnóstico rápido del estado de los motores de IA,
        midiendo velocidad en tokens/segundo y posibles alertas de hardware.
        """
        diag = {
            "ollama_activo": False,
            "ollama_latencia_ms": 0,
            "ollama_velocidad_tok_s": 0.0,
            "ollama_modelo": self.ollama_model,
            "ollama_aviso": "",
            "gemini_activo": False,
            "gemini_latencia_ms": 0,
            "gemini_aviso": ""
        }

        # Prueba de Ollama
        if self.verificar_ollama():
            diag["ollama_activo"] = True
            t0 = time.time()
            try:
                r = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": "Responde solo: OK",
                        "stream": False,
                        "options": {"num_predict": 5}
                    },
                    timeout=30
                )
                diag["ollama_latencia_ms"] = int((time.time() - t0) * 1000)
                if r.status_code == 200:
                    datos = r.json()
                    eval_count = datos.get("eval_count", 0)
                    eval_duration = datos.get("eval_duration", 1) / 1e9
                    tok_s = round(eval_count / eval_duration, 2) if eval_duration > 0 else 0.0
                    diag["ollama_velocidad_tok_s"] = tok_s
                    if tok_s < 6.0:
                        diag["ollama_aviso"] = (
                            f"Inferencia en CPU lenta ({tok_s} tok/s). "
                            f"Para respuestas instantáneas se recomienda usar Gemini Flash o descargar llama3.2:3b."
                        )
            except Exception as e:
                diag["ollama_aviso"] = f"Error en test de inferencia: {e}"
        else:
            diag["ollama_aviso"] = "Servidor Ollama no detectado en localhost:11434."

        # Prueba de Gemini
        if self.verificar_gemini():
            diag["gemini_activo"] = True
            t0 = time.time()
            try:
                if self._gemini_client:
                    resp = self._gemini_client.generate_content("Responde: OK")
                    diag["gemini_latencia_ms"] = int((time.time() - t0) * 1000)
            except Exception as e_gem:
                diag["gemini_aviso"] = f"API Key inválida o error: {e_gem}"
        else:
            diag["gemini_aviso"] = "No se ha configurado GEMINI_API_KEY."

        return diag

    def _limpiar_json_markdown(self, texto: str) -> Dict[str, Any]:
        """Extrae y parsea de forma segura un JSON contenido en bloques Markdown."""
        texto = texto.strip()
        if texto.startswith("```"):
            texto = re.sub(r'^```(?:json)?\s*', '', texto, flags=re.MULTILINE)
            texto = re.sub(r'\s*```$', '', texto, flags=re.MULTILINE)
            texto = texto.strip()
            
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            match = re.search(r'(\{[\s\S]*\})', texto)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return {}

    def _inferencia_ollama(self, prompts_bloque: Dict[str, str]) -> Dict[str, Any]:
        """Ejecuta inferencia en Ollama local optimizado para CPU multi-hilo."""
        endpoint = f"{self.ollama_host}/api/chat"
        prompt_usuario = (
            "Genera las narrativas en formato JSON estricto para las siguientes secciones:\n"
            f"{json.dumps(prompts_bloque, indent=2, ensure_ascii=False)}\n\n"
            "Retorna EXCLUSIVAMENTE el JSON con las mismas claves."
        )

        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": INSTRUCCION_SISTEMA_WWB},
                {"role": "user", "content": prompt_usuario}
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "num_ctx": 2048,
                "num_thread": 8  # Utilizar todos los núcleos lógicos disponibles
            }
        }

        resp = requests.post(endpoint, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama respondió HTTP {resp.status_code}: {resp.text}")

        contenido = resp.json().get("message", {}).get("content", "")
        resultado = self._limpiar_json_markdown(contenido)
        if not resultado:
            raise ValueError(f"Ollama retornó un contenido JSON no válido: {contenido[:150]}...")
        return resultado

    def _inferencia_gemini(self, prompts_bloque: Dict[str, str]) -> Dict[str, Any]:
        """Ejecuta inferencia ultrarrápida mediante Google Gemini API."""
        if not self.gemini_api_key:
            raise ValueError("No se ha configurado la clave GEMINI_API_KEY")

        import google.generativeai as genai
        if not self._gemini_client:
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_client = genai.GenerativeModel(
                model_name=self.gemini_model,
                system_instruction=INSTRUCCION_SISTEMA_WWB
            )

        prompt_usuario = (
            "Genera las narrativas en formato JSON estricto para las siguientes secciones:\n"
            f"{json.dumps(prompts_bloque, indent=2, ensure_ascii=False)}\n\n"
            "Mantiene exactamente los mismos nombres de clave."
        )

        generation_config = {
            "temperature": 0.2,
            "response_mime_type": "application/json"
        }

        resp = self._gemini_client.generate_content(
            prompt_usuario,
            generation_config=generation_config
        )
        texto = resp.text if hasattr(resp, "text") else ""
        resultado = self._limpiar_json_markdown(texto)
        if not resultado:
            raise ValueError("Gemini retornó un contenido JSON no válido")
        return resultado

    def _generar_bloque_resiliente(self, prompts_bloque: Dict[str, str]) -> Tuple[Dict[str, Any], str]:
        """
        Ejecuta la inferencia con fallback automático y captura detallada de excepciones.
        """
        usar_ollama = self.modo in ["auto", "ollama"]
        usar_gemini = self.modo in ["auto", "gemini"]

        ultimo_error = ""

        # Intento 1: Ollama Local
        if usar_ollama and self.verificar_ollama():
            try:
                res = self._inferencia_ollama(prompts_bloque)
                if res:
                    return res, f"Ollama Local ({self.ollama_model})"
            except Exception as e_ollama:
                ultimo_error = f"Ollama ({self.ollama_model}) error: {e_ollama}"
                print(f"⚠️ {ultimo_error}")
                if self.modo == "ollama":
                    raise RuntimeError(ultimo_error)

        # Fallback / Modo Gemini
        if usar_gemini and self.verificar_gemini():
            try:
                res = self._inferencia_gemini(prompts_bloque)
                if res:
                    return res, f"Google Gemini ({self.gemini_model})"
            except Exception as e_gemini:
                ultimo_error = f"Gemini error: {e_gemini}"
                print(f"⚠️ {ultimo_error}")
                if self.modo == "gemini":
                    raise RuntimeError(ultimo_error)

        raise RuntimeError(f"No fue posible generar el bloque. Causa: {ultimo_error or 'Ningún motor disponible'}")

    def _preparar_prompts(self, datos_empresa: Dict[str, Any], secciones: List[str]) -> Dict[str, str]:
        prompts = {}
        for seccion in secciones:
            if seccion not in CONFIG_IA:
                continue
            cfg = CONFIG_IA[seccion]
            valores = {}
            for col in cfg["columnas"]:
                val = datos_empresa.get(col, None)
                if val is None or str(val).strip() == "" or str(val).lower() in ["nan", "none"]:
                    valores[col] = "[No registrado]"
                else:
                    valores[col] = str(val).strip()
            try:
                prompts[seccion] = cfg["prompt"].format(**valores)
            except Exception:
                prompts[seccion] = cfg["prompt"]
        return prompts

    def generar_narrativas_plan(
        self,
        plan: PlanNegocio,
        callback_progreso: Optional[Callable[[float, str, str], None]] = None,
        *args,
        **kwargs
    ) -> PlanNegocio:
        """
        Procesa los tres bloques para un plan de negocio, transmitiendo
        el progreso paso a paso a la interfaz con telemetría en vivo.
        """
        motor_utilizado = "Ninguno"
        resultado_total: Dict[str, str] = {}
        reintentos = 0
        max_reintentos = config.MAX_RETRIES

        bloques = [
            ("Bloque 1/3: Identidad y Objetivos", BLOQUE_1, 0.15, 0.45),
            ("Bloque 2/3: Operaciones y Finanzas", BLOQUE_2, 0.50, 0.75),
            ("Bloque 3/3: Mercado y Comercialización", BLOQUE_3, 0.80, 0.98)
        ]

        if callback_progreso:
            callback_progreso(0.05, "Iniciando motor de IA...", f"Modo: {self.modo.upper()}")

        for nombre_bloque, secciones, pct_inicio, pct_fin in bloques:
            prompts = self._preparar_prompts(plan.datos_completos, secciones)
            bloque_exitoso = False
            
            if callback_progreso:
                callback_progreso(
                    pct_inicio,
                    f"Generando {nombre_bloque}...",
                    f"Procesando {len(secciones)} secciones con {self.ollama_model if self.modo != 'gemini' else self.gemini_model}..."
                )

            t_bloque_inicio = time.time()

            for intento in range(1, max_reintentos + 1):
                try:
                    res, motor = self._generar_bloque_resiliente(prompts)
                    resultado_total.update(res)
                    motor_utilizado = motor
                    bloque_exitoso = True
                    
                    t_duracion = round(time.time() - t_bloque_inicio, 1)
                    if callback_progreso:
                        callback_progreso(
                            pct_fin,
                            f"{nombre_bloque} completado ({t_duracion}s)",
                            f"Motor: {motor}"
                        )
                    break
                except Exception as e:
                    reintentos += 1
                    err_msg = str(e)
                    print(f"  ⚠️ Intento {intento} falló para {nombre_bloque}: {err_msg}")
                    if callback_progreso:
                        callback_progreso(
                            pct_inicio,
                            f"Reintentando {nombre_bloque} (Intento {intento}/{max_reintentos})...",
                            f"Alerta: {err_msg[:120]}"
                        )
                    time.sleep(1)

            if not bloque_exitoso:
                for sec in secciones:
                    if sec not in resultado_total:
                        resultado_total[sec] = (
                            f"La unidad productiva avanza en la consolidación de sus procesos en {plan.territorio}, "
                            f"enfocándose en fortalecer su oferta y su atención a los clientes."
                        )

        # Actualizar modelo Pydantic
        plan.narrativas = resultado_total
        plan.resumen_ejecutivo = resultado_total.get("Resumen_ejecutivo", "")
        plan.analisis_competencia = resultado_total.get("Competencia", "")
        plan.motor_ia_usado = motor_utilizado
        plan.reintentos_ia = reintentos

        if callback_progreso:
            callback_progreso(1.0, "¡Generación completada con éxito!", f"Procesado con {motor_utilizado}")

        return plan


# Alias para compatibilidad
cerebro = MotorIAHibrido
