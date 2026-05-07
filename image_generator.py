import requests
import base64
import os
import time
import asyncio
from config import BANANA_API_KEY, BANANA_MODEL_KEY, BANANA_API_URL, ASSETS_DIR
import usage_tracker

class AIImageGenerator:
    def __init__(self, log_cb=print):
        self.log = log_cb

    async def generate_images(self, prompts, num_to_generate, assets_dir):
        """
        Generates images using an AI API and saves them locally.
        """
        if not BANANA_API_KEY or not BANANA_MODEL_KEY or not BANANA_API_URL:
            raise ValueError("Banana API Key, Model Key, or URL is not configured in config.py")

        if not usage_tracker.can_generate(num_to_generate):
            remaining = usage_tracker.get_remaining_today()
            raise RuntimeError(f"Daily API limit reached. Requested: {num_to_generate}, Remaining: {remaining}. Please try again tomorrow.")

        self.log(f"[*] Starting AI image generation for {num_to_generate} prompts...")
        
        generated_images = []
        
        payload = {
            "apiKey": BANANA_API_KEY,
            "modelKey": BANANA_MODEL_KEY,
        }

        for i, prompt in enumerate(prompts[:num_to_generate]):
            self.log(f"  - Generating image {i+1}/{num_to_generate}: '{prompt[:50]}...'")
            
            if not usage_tracker.can_generate(1):
                self.log(f"[!] Warning: Daily API limit hit during generation. Stopping.")
                break

            try:
                # Forcing a 9:16 aspect ratio.
                model_inputs = {
                    "prompt": prompt,
                    "negative_prompt": "blurry, low quality, text, watermark, signature, deformed",
                    "height": 1920,
                    "width": 1080,
                    "num_inference_steps": 28,
                    "guidance_scale": 7.5
                }
                
                response = requests.post(BANANA_API_URL, json={"modelInputs": model_inputs, **payload}, timeout=120)
                response.raise_for_status()
                
                output = response.json()
                image_b64 = output.get("modelOutputs", [{}])[0].get("image_base64")

                if not image_b64:
                    self.log(f"[!] API call succeeded but no image data was returned for prompt: {prompt}")
                    continue

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
                self.log(f"[!] API Error for prompt '{prompt}': {e}")
                continue
                
        self.log(f"[*] AI Generation complete. Successfully generated {len(generated_images)} images.")
        return generated_images