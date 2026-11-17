"""
================================================================================
CONFIGURACIÓN DINÁMICA DEL PIPELINE INTELIGENTE (config.py)
Proyecto: Automatización de Planes de Negocio - Fundación WWB
Soporta rutas relativas dinámicas y variables de entorno (.env)
================================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carga de variables de entorno si existe un archivo .env
load_dotenv()

# Raíz del proyecto (donde reside este archivo de configuración)
PROJECT_ROOT = Path(__file__).resolve().parent

# Directorios de datos y artefactos (por defecto en el proyecto, o sobreescritos vía entorno)
BASE_DIR = Path(os.getenv("PIPELINE_BASE_DIR", PROJECT_ROOT)).resolve()
ENTRADAS_DIR = BASE_DIR / "entradas"
PLANTILLAS_DIR = BASE_DIR / "plantillas"
SALIDAS_DIR = BASE_DIR / "salidas"
PRUEBAS_DIR = BASE_DIR / "pruebas"

# Creación automática de directorios si no existen
for d in [ENTRADAS_DIR, PLANTILLAS_DIR, SALIDAS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Rutas de archivos por defecto
RUTA_PLANTILLA_DEFAULT = PLANTILLAS_DIR / "Formato Plan de negocio AeA script.docx"
RUTA_CONSOLIDADO_DEFAULT = BASE_DIR / "Consolidado_Planes_Negocio.xlsx"
RUTA_DX1_DEFAULT = BASE_DIR / "DX1_Yaru_Virtual_2025_Final_script.xlsx"
RUTA_AUDITORIA = SALIDAS_DIR / "auditoria_ejecucion.json"

# Configuración de Motores de IA
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Motor por defecto: "auto" (prueba Ollama primero, fallback a Gemini), "ollama", o "gemini"
DEFAULT_AI_ENGINE = os.getenv("DEFAULT_AI_ENGINE", "auto")

# Timeout y reintentos
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
