import os
import asyncio
import requests
from PIL import Image
from duckduckgo_search import DDGS

class WebScraper:
    def __init__(self, log_cb=print):
        self.log = log_cb

    def fallback_image_search(self, term, limit=5):
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6, # File namespace
                "gsrsearch": term,
                "gsrlimit": limit,
                "prop": "imageinfo",
                "iiprop": "url"
            }
            headers = {"User-Agent": "VideoMaekar/1.0"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            results = []
            for page_id, page_info in pages.items():
                imageinfo = page_info.get("imageinfo", [])
                if imageinfo and "url" in imageinfo[0]:
                    img_url = imageinfo[0]["url"]
                    if img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        results.append({"image": img_url})
            return results
        except Exception as e:
            self.log(f"  [!] Fallback Wikimedia falhou: {e}")
            return []

    async def scrape_images(self, terms, target_total, current_count, assets_dir):
        imagens_info = []
        local_image_count = current_count
        self.log("[*] A descarregar imagens do DuckDuckGo...")
        
        with DDGS() as ddgs:
            for i, t in enumerate(terms):
                if local_image_count >= target_total:
                    break
                    
                remaining_terms = len(terms) - i
                remaining_images = target_total - local_image_count
                target_for_term = (remaining_images + remaining_terms - 1) // remaining_terms
                
                self.log(f"  -> A pesquisar: {t} (A tentar descarregar {target_for_term} imagens)")
                if i > 0: await asyncio.sleep(2)
                
                res = []
                for attempt in range(3):
                    try:
                        res = list(ddgs.images(t, max_results=target_for_term * 3, safesearch="on"))
                        break
                    except Exception as e:
                        if "403" in str(e) or "Ratelimit" in str(e):
                            if attempt < 2:
                                wait_t = 5 * (attempt + 1)
                                self.log(f"  [!] Rate limit. A aguardar {wait_t}s (tentativa {attempt+1}/3)...")
                                await asyncio.sleep(wait_t)
                            else:
                                self.log(f"  [!] Falha contínua no DuckDuckGo para '{t}'. A usar alternativa (Wikimedia)...")
                                res = self.fallback_image_search(t, target_for_term * 5)
                                break
                        else:
                            self.log(f"  [!] Erro na pesquisa '{t}': {str(e)}. A usar alternativa (Wikimedia)...")
                            res = self.fallback_image_search(t, target_for_term * 5)
                            break
                            
                if res:
                    downloaded_for_term = 0
                    for img_data in res:
                        if local_image_count >= target_total or downloaded_for_term >= target_for_term:
                            break
                        try:
                            path = os.path.join(assets_dir, f"img_ddg_{local_image_count}.jpg")
                            response = requests.get(img_data['image'], timeout=10)
                            response.raise_for_status() # Check for 403 or 404 HTTP errors
                            
                            with open(path, 'wb') as f: f.write(response.content)
                            
                            # Verify if the downloaded file is a valid image
                            with Image.open(path) as img:
                                img.verify()
                                
                            # Reopen to ensure it is in a standard RGB format (fixes WEBP/RGBA issues)
                            with Image.open(path) as img:
                                img.load() # Force load pixel data
                                if img.mode != 'RGB':
                                    rgb_img = img.convert('RGB')
                                else:
                                    rgb_img = img.copy()
                                    
                            # Force save as JPEG unconditionally to correct fake .jpg extensions
                            rgb_img.save(path, 'JPEG')
                                    
                            imagens_info.append({'path': path, 'keyword': t})
                            downloaded_for_term += 1
                            local_image_count += 1
                        except Exception as e:
                            self.log(f"  [!] Link falhou ({str(e)[:30]}...). A tentar outra...")
                            
        return imagens_info, local_image_count