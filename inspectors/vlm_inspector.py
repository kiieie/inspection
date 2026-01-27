# inspectors/vlm_inspector.py
import requests
import base64
import json
import config
from loguru import logger

class VLMInspector:
    def __init__(self):
        self.config = config.VLM_CONFIG
        self.backend = self.config.get("use_backend", "ollama")
        
        if self.backend == "ollama":
            self.api_url = self.config["ollama"]["api_url"]
            self.model = self.config["ollama"]["model"]
        else:
            # TRTLLM 기본 설정
            trt_cfg = self.config["trtllm"]
            default_model = trt_cfg.get("default_model", "8b")
            self.api_url = trt_cfg["model_urls"].get(default_model)
            self.model = f"qwen3-vl-{default_model}" # 로깅용

    def _get_system_role(self, inspection_type):
        """라벨 타입에 따라 시스템 역할을 동적으로 결정"""
        if inspection_type.startswith("DG_"):
            return "You are an expert OCR assistant. Your task is to accurately extract numbers and text from the provided image of a digital display. Strictly follow the output format."
        elif inspection_type.startswith("Class_"):
            return "You are a professional industrial inspector. Your task is to analyze the image for any abnormalities, cleaning states, or damages. Strictly follow the output format."
        return "You are a helpful assistant."

    def _encode_image_from_array(self, image_array):
        """OpenCV 이미지를 Base64 문자열로 인코딩"""
        try:
            import cv2
            _, buffer = cv2.imencode('.jpg', image_array)
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            logger.error(f"메모리 이미지 인코딩 실패: {e}")
            return None

    def _encode_image(self, image_path):
        """파일 경로의 이미지를 Base64 문자열로 인코딩"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"이미지 인코딩 실패 ({image_path}): {e}")
            return None

    def _analyze_ollama(self, b64_image, prompt, timeout=60):
        """Ollama API를 이용한 분석 (타임아웃 20초)"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "options": {"temperature": 0.1}
        }
        response = requests.post(self.api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _analyze_trtllm(self, b64_image, prompt, inspection_type, timeout=40):
        """TRTLLM API를 이용한 분석 (타임아웃 20초)"""
        system_content = self._get_system_role(inspection_type)
        
        payload = {
            "batch_size": 1,
            "temperature": 1.0, # TRTLLM에서 Ollama와 유사한 답변 형도를 위해 조정 가능
            "top_p": 1.0,
            "top_k": 50,
            "max_generate_length": 256,
            "max_new_tokens": 256,
            "max_tokens": 256,
            "max_output_len": 256,
            "requests": [
                {
                    "messages": [
                        {"role": "system", "content": system_content},
                        {
                            "role": "user",
                            "content": [
                                {"type": "image", "image": b64_image},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            answer = ""
            if "responses" in result and len(result["responses"]) > 0:
                answer = result["responses"][0].get("output_text", "").strip()
            
            # [Ollama 스타일 일치화 후처리]
            # 1. 단위 및 특수문자 제거 (Ollama는 보통 순수 숫자/텍스트 위주)
            answer = answer.replace("°C", "").replace("℃", "").replace("%", "")
            
            # 2. 구분자 통일 (Ollama는 세미콜론(;)을 주로 사용함)
            # 만약 공백으로 구분되어 있다면 세미콜론으로 변경 시도 (DG 관련)
            # [Update] 모든 백엔드에 대해 Separator 통일 (Pipe -> Comma)
            answer = answer.replace("|", ", ")

            # [Update] TRT-LLM Semicolon Cleanup
            if self.backend == "trtllm":
                import re
                answer = re.sub(r'[;]', '', answer) # Remove all semicolons
                answer = re.sub(r',\s*,', ',', answer) # Fix double commas

            # [Legacy Fix] 만약 괄호가 없고, 콤마도 없는데 공백만 있다면 (예: 10 20 30) 콤마로 변환
            if inspection_type.startswith("DG_") and "(" not in answer and "," not in answer and " " in answer:
                # 1) 2) 등의 인덱스가 붙어있는 경우 처리
                import re
                answer = re.sub(r'\d+\)\s*', '', answer)
                answer = ", ".join([s.strip() for s in answer.split() if s.strip()])
            
            return answer.strip()
        except requests.exceptions.Timeout:
            logger.error(f"❌ TRTLLM Timeout: {timeout}s exceeded")
            return "Error: Timeout"
        except Exception as e:
            raise e

    def analyze_crop(self, crop_img, prompt="Read the digital number displayed on the screen.", inspection_type="DG_Generic"):
        """크롭된 이미지 영역에 대해 VLM 질의 수행"""
        b64_image = self._encode_image_from_array(crop_img)
        if not b64_image:
            return "Error: Image Encode Failed"

        try:
            logger.info(f"📡 VLM [{self.backend.upper()}] Crop Request -> '{prompt}'")
            
            if self.backend == "trtllm":
                answer = self._analyze_trtllm(b64_image, prompt, inspection_type)
            else:
                answer = self._analyze_ollama(b64_image, prompt, timeout=60)
                
            if not answer.strip():
                logger.warning(f"⚠️ Empty VLM Response from {self.backend}")
            
            # 일관성을 위해 줄바꿈 제거 및 공백 정리
            answer = answer.replace("\n", " ").strip()
            logger.success(f"✅ VLM Crop Response: {answer}")
            return answer

        except Exception as e:
            logger.error(f"❌ VLM Crop Error ({self.backend}): {e}")
            return "Error"

    def analyze(self, image_path, inspection_type):
        """전체 이미지 또는 지정된 타입에 대한 VLM 질의 수행"""
        b64_image = self._encode_image(image_path)
        if not b64_image:
            return "Error: Image Load Failed"

        # 프롬프트 매핑 확인
        prompt = config.VLM_PROMPTS.get(inspection_type)
        if not prompt:
            prompt = next((v for k, v in config.VLM_PROMPTS.items() if inspection_type.startswith(k)), None)
        if not prompt:
            prompt = inspection_type

        if not prompt or len(prompt.strip()) == 0:
            prompt = config.VLM_PROMPTS.get("DEFAULT")

        try:
            logger.info(f"📡 VLM [{self.backend.upper()}] Request ({inspection_type})")
            
            if self.backend == "trtllm":
                answer = self._analyze_trtllm(b64_image, prompt, inspection_type)
            else:
                answer = self._analyze_ollama(b64_image, prompt)

            # [Update] 모든 백엔드에 대해 Separator 통일 (Pipe -> Comma)
            answer = answer.replace("|", ", ")

            if not answer.strip():
                logger.warning(f"⚠️ Empty VLM Response from {self.backend}")

            # 일관성을 위해 줄바꿈 제거 및 공백 정리
            answer = answer.replace("\n", " ").strip()
            logger.success(f"✅ VLM Response: {answer}")
            return answer

        except requests.exceptions.Timeout:
            logger.error(f"❌ VLM Timeout ({self.backend}): Inference took too long.")
            return "Error: Timeout"
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ VLM Connection Error ({self.backend}): Server is down or unreachable.")
            return "Error: Connection Refused"
        except Exception as e:
            logger.error(f"❌ VLM Error ({self.backend}): {e}")
            return f"Error: {str(e)}"