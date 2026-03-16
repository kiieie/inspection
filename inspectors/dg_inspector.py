"""
프로그램명: 디지털 게이지 인스펙터 (dg_inspector.py) - VLM 통합 버전
버전: v3.0.0 (2026-03-13)
변경 사항:
- [Refactoring] Skew Correction(기울기 보정) 로직 전면 제거
- [Feature] DG 전용 VLM 설정(DG_VLM_CONFIG)을 이용한 분석 로직 통합
- [Logic] analyze_dg 메서드 추가 (main.py에서 호출 예정)
"""
import cv2
import numpy as np
import base64
import requests
from loguru import logger
import config

class DGInspector:
    """
    디지털 게이지(Digital Gauge)의 이미지를 분석하는 클래스입니다.
    VLM을 사용하여 게이지의 숫자를 읽어옵니다.
    """
    def __init__(self):
        self.config = getattr(config, "DG_VLM_CONFIG", config.VLM_CONFIG)
        self.backend = self.config.get("use_backend", "ollama")
        
        if self.backend == "ollama":
            self.api_url = self.config["ollama"]["api_url"]
            self.model = self.config["ollama"]["model"]
        else:
            trt_cfg = self.config["trtllm"]
            default_model = trt_cfg.get("default_model", "8b")
            self.api_url = trt_cfg["model_urls"].get(default_model)
            self.model = f"qwen3-vl-{default_model}"

        logger.info(f"✅ DGInspector 초기화 완료 (Backend: {self.backend}, Model: {self.model})")

    def analyze_dg(self, crop_img, prompt, target_type):
        """
        디지털 게이지 크롭 이미지에 대해 VLM 분석을 수행합니다.
        
        Args:
            crop_img (np.ndarray): 게이지 영역 이미지
            prompt (str): VLM에 전달할 프롬프트
            target_type (str): 인스펙션 포인트 타입 (예: DG_Air-Conditioner)
            
        Returns:
            str: VLM 응답 결과
        """
        if crop_img is None or crop_img.size == 0:
            return "Error: Image Crop Failed"

        return self.query_vlm(crop_img, prompt, target_type)

    def query_vlm(self, image, prompt, target_type):
        """VLM 백엔드에 따라 질의 수행 (4배 업스케일링 적용)"""
        if image is None or image.size == 0:
            return "Error: Image is empty"

        try:
            # [User Request] 4배 업스케일링 적용
            h, w = image.shape[:2]
            upscaled = cv2.resize(image, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
            logger.info(f"🚀 DG Image Upscaled: ({w}x{h}) -> ({w*4}x{h*4})")
            
            b64_image = self._encode_image(upscaled)
            if not b64_image:
                return "Error: Encode Failed"

            if self.backend == "trtllm":
                return self._analyze_trtllm(b64_image, prompt, target_type)
            else:
                return self._analyze_ollama(b64_image, prompt)
        except Exception as e:
            logger.error(f"❌ DG VLM 분석 오류: {e}")
            return "Error"

    def _encode_image(self, image_array):
        """OpenCV 이미지를 Base64로 인코딩"""
        _, buffer = cv2.imencode('.jpg', image_array)
        return base64.b64encode(buffer).decode('utf-8')

    def _analyze_ollama(self, b64_image, prompt, timeout=60):
        """Ollama API를 이용한 분석"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [b64_image],
            "stream": False,
            "options": {"temperature": self.config["ollama"].get("temperature", 0.0)}
        }
        response = requests.post(self.api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _analyze_trtllm(self, b64_image, prompt, target_type, timeout=40):
        """TRTLLM API를 이용한 분석 (VLMInspector 로직과 유사하게 유지)"""
        system_content = "You are an expert OCR assistant for digital gauges."
        
        payload = {
            "batch_size": 1,
            "temperature": 0.1,
            "max_new_tokens": 128,
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
        
        response = requests.post(self.api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        
        answer = ""
        if "responses" in result and len(result["responses"]) > 0:
            answer = result["responses"][0].get("output_text", "").strip()
        
        # 후처리 로직 (쉼표 등 정리)
        answer = answer.replace("|", ", ").replace("\n", " ").strip()
        return answer

    def analyze_crop(self, crop_img):
        """이전 버전과의 하환성을 위해 유지 (필요 시)"""
        # 현재는 M 행렬 등이 필요 없으므로 기본값 가공하여 반환
        return None, "N/A", [], crop_img, np.eye(2, 3, dtype=np.float32)