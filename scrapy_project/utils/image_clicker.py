import cv2
import numpy as np
from typing import Tuple, Optional, List
import os

class ImageClicker:
    def __init__(self, template_dir: str = './templates', threshold: float = 0.8):
        self.template_dir = template_dir
        self.threshold = threshold
        self.templates = {}
    
    def load_template(self, name: str, path: str = None) -> bool:
        if path is None:
            path = os.path.join(self.template_dir, name)
        
        if not os.path.exists(path):
            return False
        
        template = cv2.imread(path, cv2.IMREAD_COLOR)
        if template is None:
            return False
        
        self.templates[name] = template
        return True
    
    def load_templates_from_dir(self, dir_path: str = None) -> int:
        if dir_path is None:
            dir_path = self.template_dir
        
        if not os.path.exists(dir_path):
            return 0
        
        count = 0
        for filename in os.listdir(dir_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                if self.load_template(filename):
                    count += 1
        return count
    
    async def click_by_image(self, page, template_name: str) -> Optional[Tuple[int, int]]:
        screenshot_bytes = await page.screenshot()
        
        screenshot = cv2.imdecode(
            np.frombuffer(screenshot_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )
        
        if template_name not in self.templates:
            if not self.load_template(template_name):
                return None
        
        template = self.templates[template_name]
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= self.threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y)
        
        return None
    
    async def find_all_matches(
        self,
        page,
        template_name: str,
        max_matches: int = 10
    ) -> List[Tuple[int, int]]:
        screenshot_bytes = await page.screenshot()
        
        screenshot = cv2.imdecode(
            np.frombuffer(screenshot_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )
        
        if template_name not in self.templates:
            if not self.load_template(template_name):
                return []
        
        template = self.templates[template_name]
        
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        
        locations = np.where(result >= self.threshold)
        
        matches = []
        h, w = template.shape[:2]
        
        for y, x in zip(locations[0], locations[1]):
            center_x = x + w // 2
            center_y = y + h // 2
            matches.append((center_x, center_y))
            
            if len(matches) >= max_matches:
                break
        
        return matches
    
    def set_threshold(self, threshold: float):
        self.threshold = max(0.0, min(1.0, threshold))
    
    async def compare_screenshots(
        self,
        screenshot1: bytes,
        screenshot2: bytes,
        method: str = 'ssim'
    ) -> float:
        img1 = cv2.imdecode(
            np.frombuffer(screenshot1, np.uint8),
            cv2.IMREAD_COLOR
        )
        img2 = cv2.imdecode(
            np.frombuffer(screenshot2, np.uint8),
            cv2.IMREAD_COLOR
        )
        
        if img1 is None or img2 is None:
            return 0.0
        
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        if method == 'mse':
            diff = cv2.absdiff(img1, img2)
            return float(np.mean(diff))
        
        elif method == 'ssim':
            from skimage.metrics import structural_similarity
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            score = structural_similarity(gray1, gray2, full=True)
            return float(score[0])
        
        return 0.0

clicker = ImageClicker()

async def click_by_image(page, template_path: str) -> Optional[Tuple[int, int]]:
    return await clicker.click_by_image(page, template_path)
