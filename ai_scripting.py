import re
import requests
from config import OLLAMA_API_URL

class AIScripter:
    def __init__(self, model="llama3", log_cb=print):
        self.model = model
        self.log = log_cb

    def gerar_guiao(self, prompt):
        """Gera o guião usando o prompt fornecido."""
        self.log("[*] A criar guião...")
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        texto = response.json()['response'].strip()
        
        # Remover timestamps (ex: 00:00, 00:00:00) e descrições indesejadas
        texto = re.sub(r'\[?\b\d{1,2}:\d{2}(:\d{2})?\b\]?', '', texto)
        # Remover marcações de cena tipo (Visuals: ...) ou [Scene: ...]
        texto = re.sub(r'\(.*?\)', '', texto)
        texto = re.sub(r'\[.*?\]', '', texto)
        # Remover labels de speaker
        texto = re.sub(r'\b(Speaker\s*\d+|Narrator|Host|Voiceover|AI):\s*', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'\n+', '\n', texto)
        
        return re.sub(r'[ \t]+', ' ', texto).strip()