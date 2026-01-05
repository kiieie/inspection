# debug_paddle.py
print("🚀 PaddleOCR 디버깅 시작...")

try:
    from paddleocr import PaddleOCR
    print("✅ 라이브러리 임포트 성공")
    
    print("🛠 OCR 객체 생성 시도 (CPU 모드)...")
    # 여기서 에러가 나면 정확한 traceback이 뜹니다.
    ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=True)
    
    print("✅ OCR 객체 생성 완료! 테스트 이미지 분석 시도...")
    # 더미 이미지로 테스트
    import numpy as np
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = ocr.ocr(dummy_img, cls=True)
    print("✅ 분석 완료. 결과:", result)
    
except Exception as e:
    print("\n❌ [치명적 에러 발생] ❌")
    import traceback
    traceback.print_exc()

print("🚀 디버깅 종료")