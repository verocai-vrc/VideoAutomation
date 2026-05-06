import os
import asyncio
import datetime
import edge_tts
from config import ASSETS_DIR

class AudioEngine:
    def __init__(self, log_cb=print):
        self.log = log_cb

    async def gerar_audio_e_legendas(self, texto, base_name):
        """
        Gera o áudio e o ficheiro de legendas .srt de forma manual e robusta.
        """
        self.log("[*] A gerar voz e calculando tempos das legendas...")
        audio_path = os.path.join(ASSETS_DIR, f"{base_name}.mp3")
        subs_path = os.path.join(ASSETS_DIR, f"{base_name}.srt")
        
        communicate = edge_tts.Communicate(texto, "en-US-AndrewNeural") # Voz premium-like
        subs_data = []
        
        # 1. Transmitir o áudio e capturar limites com tentativas (Retries)
        for attempt in range(3):
            try:
                subs_data.clear()
                with open(audio_path, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            # Guardamos o tempo e o texto da palavra
                            subs_data.append({
                                "start": chunk["offset"],
                                "duration": chunk["duration"],
                                "text": chunk["text"]
                            })
                break  # Sucesso, sair do loop
            except Exception as e:
                if attempt < 2:
                    self.log(f"[!] Erro TTS (503 ou Rate Limit). A aguardar 5s (tentativa {attempt+1}/3)...")
                    await asyncio.sleep(5)
                else:
                    raise RuntimeError(f"Falha contínua no TTS. Tente rodar 'pip install --upgrade edge-tts' no terminal. Erro original: {str(e)}")

        # 2. Função interna para formatar o tempo para o padrão SRT (00:00:00,000)
        def format_srt_time(microseconds):
            td = datetime.timedelta(microseconds=microseconds / 10)
            total_seconds = int(td.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            millis = int(td.microseconds / 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        # 3. Escrever o arquivo SRT manualmente
        with open(subs_path, "w", encoding="utf-8") as f:
            if not subs_data:
                # Fallback to prevent pysubs2 "No suitable formats" crash on empty files
                f.write("1\n00:00:00,000 --> 00:00:01,000\n \n\n")
                self.log("[!] Aviso: O TTS não retornou limites de palavras. Legendas poderão faltar.")
            else:
                for i, word in enumerate(subs_data):
                    start_time = format_srt_time(word["start"])
                    # O fim é o início + a duração da palavra
                    end_time = format_srt_time(word["start"] + word["duration"])
                    
                    f.write(f"{i + 1}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{word['text']}\n\n")
        
        self.log(f"[V] Áudio e Legendas gerados com sucesso em {ASSETS_DIR}")
        return audio_path, subs_path

    def transcrever_video(self, video_path, base_name):
        try:
            import whisper
        except ImportError:
            raise RuntimeError("A biblioteca Whisper não está instalada. Abra o terminal e corra: pip install openai-whisper")
            
        self.log("[*] A analisar o áudio do vídeo local com Whisper (isto pode demorar alguns minutos)...")
        model = whisper.load_model("base")
        result = model.transcribe(video_path, word_timestamps=True)
        
        subs_path = os.path.join(ASSETS_DIR, f"{base_name}.srt")
        
        def format_srt_time(seconds):
            td = datetime.timedelta(seconds=seconds)
            total_seconds = int(td.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            millis = int(td.microseconds / 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        with open(subs_path, "w", encoding="utf-8") as f:
            idx = 1
            for segment in result.get("segments", []):
                words = segment.get("words", [])
                items_to_write = words if words else [segment]
                for item in items_to_write:
                    start_time = format_srt_time(item["start"])
                    end_time = format_srt_time(item["end"])
                    text = item.get("word", item.get("text", "")).strip()
                    if text:
                        f.write(f"{idx}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")
                        idx += 1
                        
        self.log(f"[V] Transcrição concluída com sucesso em {ASSETS_DIR}")
        return subs_path