import requests
import base64
import json
import os
import cv2
import time

class VLLM_SW_LED_Tester:
    def __init__(self, qwen_url="http://localhost:8001/v1"):
        self.qwen_url = qwen_url

    def encode_image(self, image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def test_status_check(self, image_array, component_type="Switch"):
        print(f"Testing Status Check (Qwen3.5) for {component_type}")
        _, buffer = cv2.imencode('.jpg', image_array)
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        
        prompt = f"Analyze this {component_type}. 1) Status: (On/Off or Open/Closed), 2) Abnormality: (Normal/Abnormal), 3) Description: (Briefly describe)."
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
        
        try:
            response = requests.post(f"{self.qwen_url}/chat/completions", json=payload, timeout=30)
            result = response.json()
            answer = result['choices'][0]['message']['content']
            return {"status": "success", "answer": answer}
        except Exception as e:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    tester = VLLM_SW_LED_Tester()
    # Sample Test
    img_path = "/home/kiie/projects/python/inspection/test_vlm.jpg"
    if os.path.exists(img_path):
        img = cv2.imread(img_path)
        print("--- SW Status Test ---")
        print(tester.test_status_check(img, "Switch"))
        print("--- LED Status Test ---")
        print(tester.test_status_check(img, "LED Indicator"))
    else:
        print("Test image not found.")
