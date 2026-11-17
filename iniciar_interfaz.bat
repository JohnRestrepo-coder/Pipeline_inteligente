@echo off
title Pipeline Inteligente - Fundacion WWB Colombia
echo ===============================================================================
echo       PIPELINE INTELIGENTE DE PLANES DE NEGOCIO - FUNDACION WWB COLOMBIA
echo ===============================================================================
echo.
echo Iniciando entorno virtual y levantando servidor Streamlit...
echo La aplicacion se abrira automaticamente en su navegador web predeterminado.
echo.

if exist .venv\Scripts\streamlit.exe (
    call .venv\Scripts\streamlit.exe run app.py
) else (
    streamlit run app.py
)

pause
