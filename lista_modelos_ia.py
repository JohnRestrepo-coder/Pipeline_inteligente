import os
import requests
import config

API_KEY = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

if not API_KEY:
    print("Por favor configure la variable GEMINI_API_KEY en su archivo .env")
    exit(0)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
response = requests.get(url)
data = response.json()

for model in data.get("models", []):
    print(model.get("name"))
