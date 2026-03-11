import requests
import base64
import json
import os
import cv2
import time

class VLLMTester:
    def __init__(self, ocr_url="http://localhost:8000/v1", qwen_url="http://localhost:8001/v1"):
        self.ocr_url = ocr_url
        self.qwen_url = qwen_url

    def encode_image(self, image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def test_ocr(self, image_path, prompt="Extract the numbers from this digital gauge."):
        print(f"Testing OCR (GLM-OCR) with: {image_path}")
        image_b64 = self.encode_image(image_path)
        payload = {
            "model": "unsloth/GLM-OCR",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            "temperature": 0.0
        }
        start_time = time.time()
        try:
            response = requests.post(f"{self.ocr_url}/chat/completions", json=payload, timeout=30)
            elapsed = time.time() - start_time
            result = response.json()
            answer = result['choices'][0]['message']['content']
            return {"status": "success", "answer": answer, "time": elapsed}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def test_classification(self, image_path):
        print(f"Testing Classification (Qwen3.5) with: {image_path}")
        image_b64 = self.encode_image(image_path)
        prompt = "Analyze this industrial component. 1) Type: (Analog Gauge/Digital Gauge/LED/Switch/ETC), 2) Status: (Normal/Abnormal), 3) Value or Detail: (e.g. 25.5 or on/off)."
        payload = {
            "model": "Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-GGUF",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }
            ],
            "temperature": 0.0
        }
        start_time = time.time()
        try:
            response = requests.post(f"{self.qwen_url}/chat/completions", json=payload, timeout=30)
            elapsed = time.time() - start_time
            result = response.json()
            answer = result['choices'][0]['message']['content']
            return {"status": "success", "answer": answer, "time": elapsed}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    tester = VLLMTester()
    # 예시 테스트 (파일이 있을 경우 실행)
    test_img = "/home/kiie/projects/python/inspection/test_vlm.jpg"
    if os.path.exists(test_img):
        print("--- OCR Test ---")
        print(tester.test_ocr(test_img))
        print("--- Classification Test ---")
        print(tester.test_classification(test_img))
    else:
        print(f"Test image not found at {test_img}. Please provide a sample image.")
