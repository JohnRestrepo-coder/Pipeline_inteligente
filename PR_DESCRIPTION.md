# Pull Request: Modernización del Pipeline a Web App (Streamlit + Pydantic + Motor Híbrido + HITL)

## 📌 Resumen de Cambios

Este Pull Request transforma el pipeline original basado en consola y scripts locales en una **aplicación web interactiva y modular**, diseñada para consultoría en la **Fundación WWB Colombia** y como caso de estudio riguroso para **tesis de maestría**.

---

## 🚀 Principales Funcionalidades Agregadas

### 1. Interfaz Gráfica Web Interactiva (`app.py`)
* **Sustitución de consola:** Elimina los `input()` por terminal y ofrece un panel visual completo en Streamlit.
* **Carga de datos:** Arrastrar y soltar (*drag & drop*) de hojas Excel consolidadas y carpetas de fotos comprimidas en `.zip`.
* **Editor Humano en el Bucle (HITL):** Los asesores pueden revisar y modificar en pantalla las 18 secciones del plan de negocio antes de generar el Word final.
* **Telemetría y barra de progreso:** Visualización porcentual y tiempos de respuesta por bloque temático.
* **Descarga en 1 clic:** Botón directo para descargar el `.docx` oficial ensamblado.

### 2. Eliminación de Rutas Quemadas (`config.py`)
* Desacoplamiento de rutas estáticas (`C:\Plan_IA`).
* Manejo dinámico con `pathlib.Path` y variables de entorno (`.env` con `python-dotenv`).

### 3. Validación Formal con Pydantic v2 (`procesos/modelos.py`)
* Sanitización automática de formatos de moneda colombianos (`$ 1.500.000`, `1.500.000,00`).
* Normalización de identificadores (remueve el `.0` de floats generados por Excel).
* Prevención de caídas silenciosas en procesamiento por lotes.

### 4. Motor de IA Híbrido y Resiliente (`procesos/cerebro.py`)
* **Prioridad 1 (Local):** Inferencia local con Ollama (`llama3:latest` / `llama3.2:3b`) para soberanía de datos y costo cero.
* **Fallback (Nube):** Conmutación automática a Google Gemini 1.5 Flash si Ollama está inactivo o en equipos sin GPU.
* Paralelización a 8 hilos en CPU y timeouts ampliados a 240s.

### 5. Trazabilidad y Auditoría para Tesis (`procesos/auditoria.py`)
* Registro histórico de generaciones, reintentos de IA, motores utilizados e intervenciones humanas.
* Exportación directa a Excel como insumo experimental para la tesis de maestría.

---

## 🛠️ Instrucciones de Prueba
1. Ejecutar `iniciar_interfaz.bat` o `streamlit run app.py`.
2. En la Pestaña 1, cargar el archivo consolidado.
3. En la Pestaña 2, generar narrativas con IA y editar en pantalla.
4. Ensamblar y descargar el documento Word resultante.
