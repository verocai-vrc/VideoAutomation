import os

# --- CONFIGURAÇÃO ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OUTPUT_DIR = "output_videos"
ASSETS_DIR = "assets"

# --- GOOGLE AI STUDIO (Imagen Generation) ---
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

for folder in [OUTPUT_DIR, ASSETS_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)