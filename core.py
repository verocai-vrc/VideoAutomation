from ai_scripting import AIScripter
from audio_engine import AudioEngine
from video_renderer import VideoRenderer

class ParceiroAutomacao:
    """Facade class bridging the GUI to the specialized background engines."""
    def __init__(self, model="llama3", log_cb=print, progress_cb=None):
        self.ai = AIScripter(model, log_cb)
        self.audio = AudioEngine(log_cb)
        self.renderer = VideoRenderer(log_cb, progress_cb)

    def gerar_guiao(self, prompt):
        return self.ai.gerar_guiao(prompt)

    async def gerar_audio_e_legendas(self, texto, base_name):
        return await self.audio.gerar_audio_e_legendas(texto, base_name)

    def transcrever_video(self, video_path, base_name):
        return self.audio.transcrever_video(video_path, base_name)

    def planejar_timeline(self, audio_p, srt_p, imagens_info, transcribe_mode=False):
        return self.renderer.planejar_timeline(audio_p, srt_p, imagens_info, transcribe_mode)

    def criar_video_com_legendas(self, audio_p, srt_p, imagens_info, guiao, output_dir=None, bg_music_path=None, bg_volume=0.1, loop_bg=True, enable_narration=True, transcribe_mode=False, sub_font="Arial Bold", sub_color="yellow", sub_size=60, transition="Cut", sub_y=1300, visual_effect="None", custom_timeline=None):
        from config import OUTPUT_DIR
        if output_dir is None: output_dir = OUTPUT_DIR
        return self.renderer.criar_video_com_legendas(audio_p, srt_p, imagens_info, guiao, output_dir, bg_music_path, bg_volume, loop_bg, enable_narration, transcribe_mode, sub_font, sub_color, sub_size, transition, sub_y, visual_effect, custom_timeline)