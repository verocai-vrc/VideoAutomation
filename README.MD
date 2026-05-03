# 🤖 AI Social Media Video Generator (Self-Hosted)

Este projeto é um ecossistema de automação inteligente para criação de conteúdo de vídeo (Reels, TikTok, Shorts). O sistema orquestra modelos de IA locais e APIs gratuitas para gerar guiões, narração, visuais e legendas sincronizadas, resultando num vídeo final pronto para publicação.

---

## 🚀 Panorama Geral
O programa funciona como um pipeline de produção:
1.  **Brainstorming & Scripting:** O Ollama (Llama 3) gera um guião educativo de +60 segundos.
2.  **Voice Generation:** O Edge-TTS converte o texto em áudio e gera timestamps precisos.
3.  **Visual Sourcing:** O sistema procura imagens na internet (DuckDuckGo) ou gera imagens únicas via Stable Diffusion.
4.  **Video Editing:** O MoviePy une todos os elementos e "queima" as legendas sincronizadas no vídeo.

---

## 🛠️ Requisitos Técnicos e Stack
*   **Linguagem:** Python 3.10+
*   **IA de Texto:** [Ollama](https://ollama.com/) (Modelo Llama 3)
*   **IA de Imagem:** [Stable Diffusion (Automatic1111)](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
*   **Voz & Subs:** Edge-TTS (Microsoft) & Pysubs2
*   **Edição de Vídeo:** MoviePy & ImageMagick
*   **Busca de Assets:** DuckDuckGo Search API

---

## 📋 Funcionalidades (Requisitos Funcionais)

### Atuais (Implementadas):
- [x] **Geração de Guiões Longos:** Criação de textos com mais de 180 palavras para garantir vídeos com mais de 1 minuto.
- [x] **Narração Profissional:** TTS em inglês de alta fidelidade com vozes neurais.
- [x] **Legendas Automáticas:** Sincronização fiel palavra-por-palavra extraída dos metadados do áudio.
- [x] **Busca Híbrida de Imagens:** Algoritmo que decide entre buscar imagens reais ou gerar ilustrações por IA.
- [x] **Composição Vertical:** Exportação automática em formato 9:16 (1080x1920).

---

## ⚙️ Como Instalar e Usar

1. **Clonar e Preparar Ambiente:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate no Windows
   pip install requests moviepy edge-tts pysubs2 duckduckgo_search
   ```

2. **Dependências Externas:**
   - Instalar **ImageMagick** e configurar o caminho no MoviePy.
   - Ter o **Ollama** a correr com o comando `ollama run llama3`.
   - (Opcional) Ter o **Automatic1111** aberto com `--api` ativo.

3. **Execução:**
   ```bash
   python video_automator.py
   ```

---

## 🎯 Próximos Objetivos de Desenvolvimento
- [ ] **Melhoria Estética:** Adição de transições suaves e zoom-in / zoom-out para a imagem não parecer tão estatica na tela