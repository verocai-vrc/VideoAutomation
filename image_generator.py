import requests
import base64
import os
import time
import asyncio
from config import GEMINI_API_KEY, ASSETS_DIR
import usage_tracker

class AIImageGenerator:
    def __init__(self, log_cb=print):
        self.log = log_cb

    async def generate_images(self, prompts, num_to_generate, assets_dir):
        """
        Generates images using an AI API and saves them locally.
        """
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
            raise ValueError("Gemini API Key is not configured in config.py")

        if not usage_tracker.can_generate(num_to_generate):
            remaining = usage_tracker.get_remaining_today()
            raise RuntimeError(f"Daily API limit reached. Requested: {num_to_generate}, Remaining: {remaining}. Please try again tomorrow.")

        self.log(f"[*] Starting AI image generation for {num_to_generate} prompts...")
        
        generated_images = []
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={GEMINI_API_KEY}"

        for i, prompt in enumerate(prompts[:num_to_generate]):
            self.log(f"  - Generating image {i+1}/{num_to_generate}: '{prompt[:50]}...'")
            
            if not usage_tracker.can_generate(1):
                self.log(f"[!] Warning: Daily API limit hit during generation. Stopping.")
                break

            try:
                payload = {
                    "instances": [{"prompt": prompt}],
                    "parameters": {
                        "sampleCount": 1,
                        "aspectRatio": "9:16"
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=payload, headers=headers, timeout=120)
                response.raise_for_status()
                
                output = response.json()
                predictions = output.get("predictions", [])
                
                if not predictions or "bytesBase64" not in predictions[0]:
                    self.log(f"[!] API call succeeded but no image data was returned for prompt: {prompt}")
                    continue

                image_b64 = predictions[0]["bytesBase64"]
                img_data = base64.b64decode(image_b64)
                
                timestamp = int(time.time() * 1000)
                img_filename = f"ai_generated_{timestamp}_{i}.png"
                img_path = os.path.join(assets_dir, img_filename)
                
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                    
                generated_images.append({'path': img_path, 'keyword': prompt})
                usage_tracker.record_usage(1)
                await asyncio.sleep(1)

            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    error_msg += f" - {e.response.text}"
                self.log(f"[!] API Error for prompt '{prompt}': {error_msg}")
                continue
                
        self.log(f"[*] AI Generation complete. Successfully generated {len(generated_images)} images.")
        return generated_images