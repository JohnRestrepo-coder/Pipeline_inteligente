"""
================================================================================
INTERFAZ WEB EJECUTIVA - PIPELINE INTELIGENTE FUNDACIÓN WWB (app.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB Colombia
Arquitectura: Streamlit + Pydantic + Motor Híbrido (Ollama / Gemini) + HITL
================================================================================
"""

import os
import io
import time
import zipfile
import shutil
import importlib
from pathlib import Path
import pandas as pd
import streamlit as st

import config
import procesos.modelos
import procesos.cerebro
import procesos.redactor
import procesos.auditoria
import procesos.limpiador

# Forzar recarga de módulos para evitar caching de clases en memoria de Streamlit
importlib.reload(procesos.modelos)
importlib.reload(procesos.cerebro)
importlib.reload(procesos.redactor)
importlib.reload(procesos.auditoria)
importlib.reload(procesos.limpiador)

from procesos.modelos import PlanNegocio
from procesos.cerebro import MotorIAHibrido, CONFIG_IA
from procesos.redactor import Redactor
from procesos.auditoria import GestorAuditoria
from procesos.limpiador import MultiSourceETL

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO INSTITUCIONAL
# ==============================================================================
st.set_page_config(
    page_title="Pipeline Inteligente | Fundación WWB",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual moderno y limpio
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #5B2C6F;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .card-metric {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #5B2C6F;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-success { background-color: #D4EDDA; color: #155724; }
    .badge-warning { background-color: #FFF3CD; color: #856404; }
    .badge-info { background-color: #D1ECF1; color: #0C5460; }
</style>
""", unsafe_allow_html=True)

# Inicialización de estado de sesión
if "planes" not in st.session_state:
    st.session_state.planes = []
if "plan_seleccionado_idx" not in st.session_state:
    st.session_state.plan_seleccionado_idx = 0
if "auditor" not in st.session_state:
    st.session_state.auditor = GestorAuditoria()
if "ultimo_word_path" not in st.session_state:
    st.session_state.ultimo_word_path = None


# ==============================================================================
# BARRA LATERAL (CONFIGURACIÓN Y ESTADO DEL SISTEMA)
# ==============================================================================
st.sidebar.image("https://fundacionwwbcolombia.org/wp-content/uploads/2023/07/logo-fundacion-wwb-colombia.png", width=220)
st.sidebar.markdown("### ⚙️ Centro de Control")

# 1. Selector de Motor IA
modo_ia_opcion = st.sidebar.selectbox(
    "Modo de Operación IA",
    [
        "Híbrido Automático (Ollama -> Gemini)",
        "Ollama Local (Inferencia Local)",
        "Google Gemini Flash (Nube)"
    ],
    index=0,
    help="El modo híbrido prioriza Ollama local con privacidad y costo cero; si falla o no está activo, conmuta a Gemini."
)

mapa_modos = {
    "Híbrido Automático (Ollama -> Gemini)": "auto",
    "Ollama Local (Inferencia Local)": "ollama",
    "Google Gemini Flash (Nube)": "gemini"
}
modo_ia = mapa_modos[modo_ia_opcion]

# 2. Clave de API de Gemini
gemini_key_input = st.sidebar.text_input(
    "Gemini API Key (Nube / Fallback)",
    value=config.GEMINI_API_KEY,
    type="password",
    help="Opcional si usa solo Ollama local. Necesario para el modo nube o respaldo."
)
if gemini_key_input:
    os.environ["GEMINI_API_KEY"] = gemini_key_input

# 3. Estado de conexión y selección de modelo Ollama
motor_temp = MotorIAHibrido(modo=modo_ia, gemini_api_key=gemini_key_input)
ollama_online = motor_temp.verificar_ollama()
gemini_online = motor_temp.verificar_gemini()

def _listar_modelos_ollama(host: str) -> list:
    try:
        import requests
        r = requests.get(f"{host.rstrip('/')}/api/tags", timeout=2)
        if r.status_code == 200:
            mods = [m["name"] for m in r.json().get("models", [])]
            if mods:
                return mods
    except Exception:
        pass
    return [config.OLLAMA_MODEL]

modelos_ollama_disp = _listar_modelos_ollama(config.OLLAMA_HOST) if ollama_online else [config.OLLAMA_MODEL]
modelo_ollama_sel = st.sidebar.selectbox(
    "Modelo Local Ollama",
    modelos_ollama_disp,
    index=0,
    help="Modelos detectados en el servidor local de Ollama."
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 📡 Estado de Motores")
col_est1, col_est2 = st.sidebar.columns(2)
with col_est1:
    if ollama_online:
        st.markdown("**Ollama Local**<br><span class='status-badge badge-success'>🟢 Conectado</span>", unsafe_allow_html=True)
    else:
        st.markdown("**Ollama Local**<br><span class='status-badge badge-warning'>🟡 Inactivo</span>", unsafe_allow_html=True)

with col_est2:
    if gemini_online:
        st.markdown("**Gemini Flash**<br><span class='status-badge badge-success'>🟢 Lista</span>", unsafe_allow_html=True)
    else:
        st.markdown("**Gemini Flash**<br><span class='status-badge badge-info'>⚪ Sin API Key</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")
with st.sidebar.expander("🩺 Diagnóstico de Salud y Rendimiento"):
    st.caption("Verifica la velocidad en tokens/segundo y posibles alertas de hardware.")
    if st.button("🧪 Ejecutar Test de Salud"):
        with st.spinner("Midiendo latencia y velocidad..."):
            diag_motor = MotorIAHibrido(
                modo=modo_ia,
                ollama_model=modelo_ollama_sel,
                gemini_api_key=gemini_key_input
            )
            res_diag = diag_motor.diagnosticar_salud()
            if res_diag["ollama_activo"]:
                st.success(f"Ollama: {res_diag['ollama_latencia_ms']}ms | {res_diag['ollama_velocidad_tok_s']} tok/s")
                if res_diag["ollama_aviso"]:
                    st.warning(res_diag["ollama_aviso"])
            else:
                st.error("Ollama: Inactivo")

            if res_diag["gemini_activo"]:
                st.success(f"Gemini: {res_diag['gemini_latencia_ms']}ms de respuesta")
            elif gemini_key_input:
                st.error(f"Gemini: {res_diag['gemini_aviso']}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Plantilla Word:** `{config.RUTA_PLANTILLA_DEFAULT.name}`")
if config.RUTA_PLANTILLA_DEFAULT.exists():
    st.sidebar.caption("✅ Plantilla institucional cargada.")
else:
    st.sidebar.error("❌ Plantilla no encontrada.")


# ==============================================================================
# ENCABEZADO PRINCIPAL
# ==============================================================================
st.markdown('<div class="main-header">💼 Pipeline Inteligente de Planes de Negocio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Fundación WWB Colombia • Generación Automatizada con Supervisión Humana (Human-in-the-Loop)</div>', unsafe_allow_html=True)

# Pestañas principales
tab_datos, tab_editor, tab_auditoria = st.tabs([
    "📂 1. Carga y Consolidación de Datos",
    "✍️ 2. Generador y Editor Interactivo (HITL)",
    "📊 3. Trazabilidad y Auditoría (Tesis)"
])


# ==============================================================================
# PESTAÑA 1: CARGA Y EXPLORACIÓN DE DATOS
# ==============================================================================
with tab_datos:
    st.markdown("### 📋 Ingesta y Validación de Datos")
    
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.markdown("#### Fuente de Datos")
        origen_datos = st.radio(
            "Seleccione el origen de información:",
            [
                "Utilizar archivo Consolidado existente",
                "Subir nuevo archivo Excel consolidado (.xlsx)",
                "Ejecutar ETL desde DX1 Maestro"
            ]
        )

        archivo_subido = None
        if origen_datos == "Subir nuevo archivo Excel consolidado (.xlsx)":
            archivo_subido = st.file_uploader("Arrastre o suba el archivo consolidado", type=["xlsx"])
        elif origen_datos == "Ejecutar ETL desde DX1 Maestro":
            dx1_subido = st.file_uploader("Subir DX1 Maestro (.xlsx)", type=["xlsx"])
            if dx1_subido:
                ruta_temp = config.ENTRADAS_DIR / dx1_subido.name
                with open(ruta_temp, "wb") as f:
                    f.write(dx1_subido.getbuffer())
                if st.button("🚀 Ejecutar Proceso ETL"):
                    with st.spinner("Procesando y normalizando información..."):
                        etl = MultiSourceETL(ruta_dx1_maestro=ruta_temp)
                        ruta_res = etl.ejecutar_pipeline()
                        st.success(f"ETL completado. Consolidado guardado en: {ruta_res.name}")

    with col_der:
        st.markdown("#### Evidencias Fotográficas (Opcional)")
        fotos_zip = st.file_uploader(
            "Cargar archivo ZIP con carpetas de fotos por Cédula",
            type=["zip"],
            help="Estructura sugerida: ZIP conteniendo carpetas nombradas con el número de documento de cada emprendedor."
        )
        if fotos_zip:
            destino_fotos = config.ENTRADAS_DIR / "Fotos"
            destino_fotos.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(fotos_zip.read())) as z:
                z.extractall(destino_fotos)
            st.success(f"✅ Fotos extraídas correctamente en `{destino_fotos.name}`.")

    st.markdown("---")
    
    # Botón para cargar registros
    if st.button("🔄 Cargar y Validar Registros con Pydantic", type="primary"):
        ruta_a_cargar = config.RUTA_CONSOLIDADO_DEFAULT
        if archivo_subido is not None:
            ruta_a_cargar = config.ENTRADAS_DIR / archivo_subido.name
            with open(ruta_a_cargar, "wb") as f:
                f.write(archivo_subido.getbuffer())

        if not ruta_a_cargar.exists():
            st.error(f"No se encontró el archivo en: {ruta_a_cargar}")
        else:
            with st.spinner("Validando integridad de datos..."):
                try:
                    df = pd.read_excel(ruta_a_cargar)
                    df.columns = [str(c).strip() for c in df.columns]
                    
                    planes_validados = []
                    carpeta_fotos = config.ENTRADAS_DIR / "Fotos"

                    for _, fila in df.iterrows():
                        plan = PlanNegocio.desde_diccionario(
                            fila=fila.to_dict(),
                            carpeta_fotos_base=str(carpeta_fotos) if carpeta_fotos.exists() else None
                        )
                        planes_validados.append(plan)

                    st.session_state.planes = planes_validados
                    st.success(f"🎉 Se cargaron y validaron exitosamente **{len(planes_validados)} emprendedores**.")
                except Exception as e:
                    st.error(f"Error procesando el archivo: {e}")

    # Tabla resumen de registros cargados
    if st.session_state.planes:
        st.markdown("#### Emprendedores Listos para Procesamiento")
        
        datos_tabla = []
        for p in st.session_state.planes:
            datos_tabla.append({
                "Documento": p.id_doc,
                "Emprendedor": p.nombre_emprendedor,
                "Unidad Productiva": p.nombre_negocio,
                "Territorio": p.territorio,
                "Ventas Últ. Mes": p.datos_financieros.formato_moneda(p.datos_financieros.ventas_ultimo_mes),
                "Estado IA": "✅ Generado" if p.narrativas else "⏳ Pendiente",
                "Aprobado Asesor": "✅ Sí" if p.aprobado_humano else "⚪ No"
            })
        
        df_mostrar = pd.DataFrame(datos_tabla)
        st.dataframe(df_mostrar, use_container_width=True)


# ==============================================================================
# PESTAÑA 2: GENERADOR Y EDITOR INTERACTIVO (HITL)
# ==============================================================================
with tab_editor:
    st.markdown("### ✍️ Supervisión y Generación Asistida (Human-in-the-Loop)")

    if not st.session_state.planes:
        st.info("👉 Por favor cargue los datos en la **Pestaña 1** para comenzar la supervisión.")
    else:
        # Selección de emprendedor
        opciones_emprendedores = [
            f"{i+1}. {p.nombre_emprendedor} ({p.nombre_negocio}) - ID: {p.id_doc}"
            for i, p in enumerate(st.session_state.planes)
        ]
        
        idx_seleccionado = st.selectbox(
            "Seleccione el emprendedor a revisar:",
            range(len(opciones_emprendedores)),
            format_func=lambda x: opciones_emprendedores[x],
            index=st.session_state.plan_seleccionado_idx
        )
        st.session_state.plan_seleccionado_idx = idx_seleccionado
        plan_actual: PlanNegocio = st.session_state.planes[idx_seleccionado]

        # Ficha Resumen del Emprendedor
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            st.metric("Cédula / ID", plan_actual.id_doc)
        with col_f2:
            st.metric("Ventas Mes", plan_actual.datos_financieros.formato_moneda(plan_actual.datos_financieros.ventas_ultimo_mes))
        with col_f3:
            st.metric("Costos / Salidas", plan_actual.datos_financieros.formato_moneda(plan_actual.datos_financieros.salidas_ultimo_mes))
        with col_f4:
            st.metric("Margen Estimado", plan_actual.datos_financieros.formato_moneda(plan_actual.datos_financieros.margen_estimado))

        st.markdown("---")

        # Barra de acciones de IA
        col_acc1, col_acc2, col_acc3 = st.columns([1.5, 1, 1.5])
        
        with col_acc1:
            if st.button("🧠 Generar / Regenerar Narrativas con IA", type="primary", use_container_width=True):
                barra_progreso = st.progress(0.0)
                status_container = st.status("🚀 Iniciando motor de IA...", expanded=True)
                
                def actualizar_progreso(pct: float, etapa: str, detalle: str = ""):
                    barra_progreso.progress(min(pct, 1.0))
                    status_container.update(label=f"⏳ {etapa}")
                    if detalle:
                        status_container.write(f"• **{etapa}**: {detalle}")

                motor = MotorIAHibrido(
                    modo=modo_ia,
                    ollama_model=modelo_ollama_sel,
                    gemini_api_key=gemini_key_input
                )

                t_inicio_total = time.time()
                try:
                    if modo_ia in ["auto", "ollama"] and "llama3" in modelo_ollama_sel.lower():
                        status_container.info(
                            "💡 Nota: `llama3` (8B) se ejecuta sobre CPU. Cada bloque puede tomar entre 1 y 2 minutos. "
                            "Para respuestas en 3 segundos puede usar el modo Gemini Flash."
                        )

                    plan_actual = motor.generar_narrativas_plan(
                        plan=plan_actual,
                        callback_progreso=actualizar_progreso
                    )
                    t_total = round(time.time() - t_inicio_total, 1)
                    
                    st.session_state.planes[idx_seleccionado] = plan_actual
                    barra_progreso.progress(1.0)
                    status_container.update(
                        label=f"✅ Narrativas generadas exitosamente en {t_total}s con {plan_actual.motor_ia_usado}!",
                        state="complete",
                        expanded=False
                    )
                    st.success(f"✨ ¡Generación completada! Motor: **{plan_actual.motor_ia_usado}** ({t_total}s)")
                    st.rerun()
                except Exception as e_gen:
                    barra_progreso.progress(0.0)
                    status_container.update(label="❌ Error durante la generación", state="error", expanded=True)
                    st.error(f"**Detalle del error en el modelo:**\n\n`{str(e_gen)}`")
                    st.info("💡 **Consejo:** Si Ollama está tardando demasiado o arrojó timeout en CPU, puede seleccionar en la barra lateral el modo **Google Gemini Flash** para una generación instantánea.")

        with col_acc2:
            estado_texto = "✅ Aprobado" if plan_actual.aprobado_humano else "⏳ Pendiente de Aprobación"
            st.markdown(f"**Estado Asesor:**<br>`{estado_texto}`", unsafe_allow_html=True)

        with col_acc3:
            if plan_actual.motor_ia_usado:
                st.caption(f"🤖 Motor: **{plan_actual.motor_ia_usado}** | Reintentos: **{plan_actual.reintentos_ia}**")

        st.markdown("#### 📝 Editor de Secciones (Ajuste Humano)")
        st.caption("Usted como asesor de la Fundación WWB puede editar cualquier texto antes de generar el documento final.")

        # Edición por bloques temáticos
        subtab_identidad, subtab_operaciones, subtab_mercado = st.tabs([
            "1. Identidad y Objetivos",
            "2. Operaciones y Producto",
            "3. Mercado y Comercialización"
        ])

        cambios_realizados = False

        with subtab_identidad:
            sec_resumen = st.text_area(
                "Resumen Ejecutivo",
                value=plan_actual.narrativas.get("Resumen_ejecutivo", plan_actual.resumen_ejecutivo),
                height=130
            )
            col_m, col_v = st.columns(2)
            with col_m:
                sec_mision = st.text_area("Misión", value=plan_actual.narrativas.get("Mision", ""), height=100)
            with col_v:
                sec_vision = st.text_area("Visión", value=plan_actual.narrativas.get("Vision", ""), height=100)

            col_val, col_obj = st.columns(2)
            with col_val:
                sec_valor = st.text_area("Valores del Emprendimiento", value=plan_actual.narrativas.get("Valor", ""), height=100)
            with col_obj:
                sec_objetivos = st.text_area("Objetivos Comerciales y Operativos", value=plan_actual.narrativas.get("Objetivos", ""), height=100)

            sec_perfil = st.text_area("Perfil y Liderazgo del Emprendedor", value=plan_actual.narrativas.get("Perfil_del_emprendedor", ""), height=100)

        with subtab_operaciones:
            col_prod, col_val_agregado = st.columns(2)
            with col_prod:
                sec_prod = st.text_area("Productos y Servicios", value=plan_actual.narrativas.get("Productos_y_servicios", ""), height=110)
            with col_val_agregado:
                sec_propuesta = st.text_area("Propuesta de Valor (Diferencial)", value=plan_actual.narrativas.get("Propuesta_de_valor", ""), height=110)

            sec_fab = st.text_area("Proceso de Fabricación / Prestación de Servicios", value=plan_actual.narrativas.get("Fabricacion_productos", ""), height=110)

            col_fin, col_sost = st.columns(2)
            with col_fin:
                sec_admin_fin = st.text_area("Administración Financiera", value=plan_actual.narrativas.get("Administracion_financiera_presupuesto", ""), height=100)
            with col_sost:
                sec_sost = st.text_area("Sostenibilidad Ambiental", value=plan_actual.narrativas.get("Sostenibilidad_ambiental", ""), height=100)

        with subtab_mercado:
            col_cli, col_seg = st.columns(2)
            with col_cli:
                sec_clientes = st.text_area("Perfil del Cliente Objetivo", value=plan_actual.narrativas.get("Perfil_clientes", ""), height=110)
            with col_seg:
                sec_segmento = st.text_area("Segmento de Mercado y Alcance", value=plan_actual.narrativas.get("Segmento_mercado", ""), height=110)

            sec_competencia = st.text_area("Análisis de Competencia", value=plan_actual.narrativas.get("Competencia", plan_actual.analisis_competencia), height=100)
            
            col_est, col_red = st.columns(2)
            with col_est:
                sec_ventas = st.text_area("Estrategia Comercial y de Ventas", value=plan_actual.narrativas.get("Estrategia_ventas", ""), height=100)
            with col_red:
                sec_redes = st.text_area("Presencia en Redes Sociales", value=plan_actual.narrativas.get("red_social", ""), height=100)

            sec_mkt = st.text_area("Estrategia de Marketing Digital", value=plan_actual.narrativas.get("Estrategia_marketing_digital", ""), height=100)

        st.markdown("---")

        # Botones de Aprobación y Ensamblaje
        col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 2])

        with col_b1:
            if st.button("💾 Guardar y Aprobar como Asesor", use_container_width=True):
                # Actualizar narrativas en memoria con lo editado por el asesor
                nuevas_narrativas = {
                    "Resumen_ejecutivo": sec_resumen,
                    "Mision": sec_mision,
                    "Vision": sec_vision,
                    "Valor": sec_valor,
                    "Objetivos": sec_objetivos,
                    "Perfil_del_emprendedor": sec_perfil,
                    "Productos_y_servicios": sec_prod,
                    "Propuesta_de_valor": sec_propuesta,
                    "Fabricacion_productos": sec_fab,
                    "Administracion_financiera_presupuesto": sec_admin_fin,
                    "Sostenibilidad_ambiental": sec_sost,
                    "Perfil_clientes": sec_clientes,
                    "Segmento_mercado": sec_segmento,
                    "Competencia": sec_competencia,
                    "Estrategia_ventas": sec_ventas,
                    "red_social": sec_redes,
                    "Estrategia_marketing_digital": sec_mkt
                }
                plan_actual.narrativas = nuevas_narrativas
                plan_actual.resumen_ejecutivo = sec_resumen
                plan_actual.analisis_competencia = sec_competencia
                plan_actual.aprobado_humano = True
                st.session_state.planes[idx_seleccionado] = plan_actual
                st.success("✅ Cambios guardados y plan aprobado formalmente por el asesor.")
                st.rerun()

        with col_b2:
            if st.button("📄 Ensamblar Documento Word", type="primary", use_container_width=True):
                with st.spinner("Ensamblando documento con imágenes y tablas..."):
                    try:
                        redactor = Redactor()
                        ruta_word = redactor.procesar_plan(plan_actual)
                        st.session_state.ultimo_word_path = ruta_word
                        
                        # Registro en auditoría
                        st.session_state.auditor.registrar_evento(
                            plan=plan_actual,
                            archivo_word=ruta_word.name,
                            modificado_manualmente=True
                        )
                        st.success(f"🎉 Documento Word generado: `{ruta_word.name}`")
                    except Exception as e_word:
                        st.error(f"Error generando Word: {e_word}")

        with col_b3:
            if st.session_state.ultimo_word_path and os.path.exists(st.session_state.ultimo_word_path):
                with open(st.session_state.ultimo_word_path, "rb") as f_word:
                    st.download_button(
                        label="⬇️ Descargar Documento Word (.docx)",
                        data=f_word.read(),
                        file_name=os.path.basename(st.session_state.ultimo_word_path),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )


# ==============================================================================
# PESTAÑA 3: TRAZABILIDAD, AUDITORÍA Y RESULTADOS DE TESIS
# ==============================================================================
with tab_auditoria:
    st.markdown("### 📊 Trazabilidad y Métricas para Evaluación de Tesis")
    st.markdown("Registro continuo de eventos de generación de IA, intervenciones humanas y tiempos de respuesta.")

    metricas = st.session_state.auditor.obtener_metricas()
    df_audit = st.session_state.auditor.obtener_dataframe()

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Planes Generados", metricas["total"])
    with col_m2:
        st.metric("Aprobados por Asesor", metricas["aprobados"])
    with col_m3:
        st.metric("Modificados Manualmente", metricas["modificados"])
    with col_m4:
        st.metric("Promedio Reintentos IA", f"{metricas['promedio_reintentos']} / doc")

    st.markdown("---")
    
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        st.markdown("#### Historial Detallado de Auditoría")
        if not df_audit.empty:
            st.dataframe(df_audit, use_container_width=True)
        else:
            st.info("Aún no hay registros de auditoría generados en esta sesión.")

    with col_g2:
        st.markdown("#### Distribución de Motores")
        if metricas["motores"]:
            df_motores = pd.DataFrame(list(metricas["motores"].items()), columns=["Motor", "Planes"])
            st.bar_chart(df_motores.set_index("Motor"))
        else:
            st.caption("Sin datos de distribución todavía.")

    if not df_audit.empty:
        buffer_audit = io.BytesIO()
        df_audit.to_excel(buffer_audit, index=False)
        st.download_button(
            label="📥 Exportar Auditoría a Excel (Insumo Tesis)",
            data=buffer_audit.getvalue(),
            file_name="auditoria_planes_negocio_wwb.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
