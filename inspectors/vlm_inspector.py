# inspectors/vlm_inspector.py
import requests
import base64
import json
import config
from loguru import logger

class VLMInspector:
    def __init__(self):
        self.api_url = config.VLM_CONFIG["api_url"]
        self.model = config.VLM_CONFIG["model"]
    
    def _encode_image(self, image_path):
        """이미지 파일을 Base64 문자열로 인코딩"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"이미지 인코딩 실패: {e}")
            return None

    def get_prompt_by_type(self, inspection_type):
        """점검 타입에 맞는 프롬프트 로드"""
        for key, prompt in config.VLM_PROMPTS.items():
            if key in inspection_type:
                return prompt
        return config.VLM_PROMPTS["DEFAULT"]

    def analyze(self, image_path, inspection_type):
        b64_image = self._encode_image(image_path)
        if not b64_image:
            return "Error: Image Load Failed"

        prompt = self.get_prompt_by_type(inspection_type)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }

        try:
            logger.info(f"📡 VLM Request ({inspection_type}) -> 모델 로딩 중... (최대 5분 대기)")
            
            # [수정] 타임아웃을 300초(5분)로 설정하여 첫 로딩 대기
            response = requests.post(self.api_url, json=payload, timeout=300)
            
            # HTTP 에러(404 등) 발생 시 예외 발생
            response.raise_for_status()
            
            result = response.json()
            answer = result.get("response", "").strip()
            
            logger.success(f"✅ VLM Response: {answer}")
            return answer

        except requests.exceptions.ConnectTimeout:
            logger.error("❌ VLM Timeout: 모델 로딩이 너무 오래 걸립니다.")
            return "Error: Timeout (Model Loading)"
            
        except requests.exceptions.ConnectionError:
            logger.error("❌ VLM Connection Error: Ollama 서버가 꺼져 있거나 포트가 막혔습니다.")
            return "Error: Connection Refused"
            
        except requests.exceptions.HTTPError as e:
            # 404 Not Found가 뜨면 모델명이 틀린 것입니다.
            logger.error(f"❌ VLM HTTP Error: {e} (모델명 {self.model} 확인 필요)")
            return f"Error: HTTP {response.status_code}"
            
        except Exception as e:
            logger.error(f"❌ VLM Unknown Error: {e}")
            return f"Error: {str(e)}"