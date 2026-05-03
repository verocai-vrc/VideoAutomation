import os

# --- CONFIGURAÇÃO ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OUTPUT_DIR = "output_videos"
ASSETS_DIR = "assets"

for folder in [OUTPUT_DIR, ASSETS_DIR]:
    if not os.path.exists(folder): os.makedirs(folder)