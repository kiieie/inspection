import requests
import base64
from loguru import logger
from .base import BaseInspector

class VLMInspector(BaseInspector):
    def __init__(self, api_url, model_name):
        self.api_url = api_url
        self.model_name = model_name

    def inspect(self, image_path, prompt):
        """이미지를 Base64로 인코딩하여 VLM API에 전송 후 결과 파싱"""
        try:
            with open(image_path, "rb") as f:
                img_str = base64.b64encode(f.read()).decode('utf-8')

            payload = {
                "model": self.model_name,
                "prompt": f"Analyze this facility image. Question: {prompt}",
                "images": [img_str],
                "stream": False
            }
            response = requests.post(self.api_url, json=payload, timeout=30)
            result_text = response.json().get("response", "No response")
            
            logger.info(f"VLM Analysis Result: {result_text}")
            return {"status": "Success", "analysis": result_text}
        except Exception as e:
            logger.error(f"VLM API Error: {e}")
            return {"status": "Error", "reason": str(e)}