# Pipeline Inteligente de Planes de Negocio - Fundación WWB Colombia

Sistema de automatización para la generación de informes y planes de negocio institucionales para microempresarios de la Fundación WWB Colombia (Programas Yarú y Asesorías Especializadas). Integra Inteligencia Artificial con supervisión humana en el bucle (**Human-in-the-Loop**), validación formal de esquemas con **Pydantic** y generación de documentos Word institucionales con **docxtpl**.

---

## 🚀 Inicio Rápido (Presentación / Producción)

### Opción 1: Ejecución Directa (Doble Clic en Windows)
Haga doble clic en el archivo:
```text
iniciar_interfaz.bat
```
El sistema activará el entorno virtual y abrirá automáticamente la aplicación en su navegador web (`http://localhost:8501`).

### Opción 2: Desde la Terminal
```bash
# 1. Activar el entorno virtual
.\.venv\Scripts\activate

# 2. Iniciar la aplicación web
streamlit run app.py
```

---

## 🏛️ Arquitectura Modular del Sistema

```text
├── app.py                     # Interfaz Gráfica Web Interactiva (Streamlit)
├── config.py                  # Configuración dinámica y gestión de rutas (pathlib)
├── main.py                    # Orquestador del pipeline para consola o procesos batch
├── iniciar_interfaz.bat       # Script ejecutable de un clic para asesores
├── requirements.txt           # Dependencias del proyecto
├── .env.example               # Plantilla de variables de entorno (Gemini API Key, Ollama Host)
│
├── procesos/
│   ├── modelos.py             # Ficha técnica y validación robusta con Pydantic
│   ├── cerebro.py             # Motor de IA Híbrido (Ollama Local + Fallback Gemini)
│   ├── redactor.py            # Ensamblador de documentos Word institucionales (docxtpl)
│   ├── limpiador.py           # Pipeline ETL multiorigen (DX1 Maestro + Hojas de costos)
│   └── auditoria.py           # Trazabilidad, métricas de reintentos e insumos de tesis
│
├── plantillas/
│   └── Formato Plan de negocio AeA script.docx   # Plantilla institucional WWB
├── entradas/                  # Archivos maestros DX1, asesorías y carpetas de fotos
└── salidas/                   # Documentos Word generados y registro de auditoría JSON
```

---

## ✨ Características Principales

1. **Interfaz Web Interactiva (Sin Terminales):**
   * Panel visual para asesores de la Fundación WWB.
   * Carga de archivos por arrastrar y soltar (*drag & drop* de Excel y carpetas de fotos en ZIP).
   * **Editor en pantalla:** El asesor visualiza las narrativas propuestas por la IA y puede corregir o enriquecer cualquier texto antes de generar el documento final.
   * Descarga inmediata del archivo `.docx` terminado con un solo clic.

2. **Rutas Dinámicas y Portabilidad:**
   * Eliminación total de rutas fijas (`C:\Plan_IA`). El sistema resuelve dinámicamente sus rutas relativas y respeta variables de entorno mediante `config.py`.

3. **Validación Robusta con Pydantic:**
   * Conversión y limpieza automática de números corruptos, formatos de moneda colombiana (`$ 1.500.000`), cadenas nulas y eliminación de decimales `.0` de los documentos de identidad.

4. **Motor de IA Híbrido y Resiliente:**
   * **Prioridad 1 (Local):** Inferencia con **Ollama** (`llama3.2:3b`), garantizando costo cero y soberanía de datos personales (Ley 1581 de Habeas Data).
   * **Fallback / Nube:** Si la máquina no tiene GPU o Ollama está inactivo, conmuta automáticamente a **Google Gemini 1.5 Flash**.

5. **Trazabilidad y Auditoría (Aporte Académico para Tesis):**
   * Registro sistemático de cada documento: número de reintentos de IA, motor utilizado, intervenciones y modificaciones del asesor humano, exportable a Excel como insumo experimental para la tesis de maestría.
