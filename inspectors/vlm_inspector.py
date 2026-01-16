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
    
    def _encode_image_from_array(self, image_array):
        """[New] OpenCV 이미지를 Base64 문자열로 인코딩 (메모리 처리)"""
        try:
            import cv2
            _, buffer = cv2.imencode('.jpg', image_array)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            logger.error(f"메모리 이미지 인코딩 실패: {e}")
            return None

    def analyze_crop(self, crop_img, prompt="Read the digital number displayed on the screen."):
        """[New] 크롭된 이미지 영역에 대해 직접 VLM 질의 수행 (DG 전용)"""
        b64_image = self._encode_image_from_array(crop_img)
        if not b64_image:
            return "Error: Image Encode Failed"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "options": {
                "temperature": 0.0, # 확정적 답변 유도
                # "num_predict": 100   # 짧은 답변 유도 (Increased from 20 to 100)
            }
        }

        try:
            logger.info(f"📡 VLM Crop Request -> '{prompt}' (ImgLen: {len(b64_image)})")
            # 타임아웃 10초 (부분 질의이므로 전체보다 짧게 설정) -> VLM 특성상 30초로 넉넉히
            response = requests.post(self.api_url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            # Debug: Log full response if answer is empty
            if not result.get("response", "").strip():
                logger.warning(f"⚠️ Empty VLM Response. Raw JSON: {result}")
                
            answer = result.get("response", "").strip()
            
            # 줄바꿈 및 불필요 공백 제거
            answer = answer.replace("\n", " ").strip()
            
            logger.success(f"✅ VLM Crop Response: {answer}")
            return answer

        except Exception as e:
            logger.error(f"❌ VLM Crop Error: {e}")
            return "Error"

    def analyze(self, image_path, inspection_type):
        b64_image = self._encode_image(image_path)
        if not b64_image:
            return "Error: Image Load Failed"

        # [수정] 2026-01-13: 입력값이 VLM_PROMPTS 키가 아니면 직접 프롬프트로 인식
        prompt = config.VLM_PROMPTS.get(inspection_type)
        if not prompt:
            # 부분 일치 확인
            prompt = next((v for k, v in config.VLM_PROMPTS.items() if inspection_type.startswith(k)), None)
        if not prompt:
            # 키가 아니면 입력된 텍스트 자체를 프롬프트로 사용 (자유 질문 허용)
            prompt = inspection_type

        # prompt가 여전히 비어있다면 DEFAULT 사용
        if not prompt or len(prompt.strip()) == 0:
            prompt = config.VLM_PROMPTS.get("DEFAULT")
        
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