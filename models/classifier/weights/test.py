from ultralytics import YOLO
import pandas as pd
import sys

# Pandas 출력 제한 해제 (모든 행과 열을 보여줌)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def run_full_analysis(model_path, source_img, img_size=1920):
    # 1. 모델 로드
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"❌ 모델을 로드할 수 없습니다: {e}")
        return None

    print(f"🚀 모델: {model_path} | 이미지: {source_img} | 해상도: {img_size}")

    # 2. 추론 실행
    # conf: 신뢰도 임계값 (0.0 ~ 1.0)
    # 예: conf=0.5 (50% 이상만 탐지), conf=0.001 (거의 모든 후보 박스 표시 - 분석용)
    results = model.predict(
        source=source_img, 
        imgsz=img_size, 
        conf=0.25,        # <--- 여기에 추가하시면 됩니다!
        save=False, 
        verbose=False
    )    
    result = results[0]

    detections = []

    # 3. 데이터 추출 (모든 객체 순회)
    if result.boxes:
        for box in result.boxes:
            # Class 정보
            cls_id = int(box.cls[0].item())
            class_name = model.names[cls_id]
            
            # Confidence (신뢰도) - 소수점 4자리까지
            conf = float(box.conf[0].item())
            
            # 좌표 정보 (Int로 변환하여 보기 좋게)
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            detections.append({
                "Class_ID": cls_id,
                "Class_Name": class_name,
                "Confidence": round(conf, 4), # 요청하신 신뢰도 값
                "X1": x1, "Y1": y1, 
                "X2": x2, "Y2": y2
            })
    else:
        print("⚠️ 탐지된 객체가 없습니다.")
        return None

    # 4. DataFrame 생성
    df = pd.DataFrame(detections)
    
    # 신뢰도(Confidence) 높은 순서대로 정렬
    df = df.sort_values(by='Confidence', ascending=False).reset_index(drop=True)

    return df

# --- 실행 설정 ---
MODEL_PATH = 'best.pt'   # 모델 경로
IMAGE_PATH = 'test.jpg'  # 이미지 경로
IMG_SIZE = 1920          # 해상도 설정

# --- 메인 실행 ---
if __name__ == "__main__":
    df_result = run_full_analysis(MODEL_PATH, IMAGE_PATH, IMG_SIZE)

    if df_result is not None:
        print("\n📊 [모든 탐지 데이터 목록 (All Data Classes)]")
        print("=" * 80)
        print(df_result) # 모든 데이터 출력
        print("=" * 80)
        
        print(f"\n✅ 총 탐지된 객체 수: {len(df_result)} 개")
        
        # (선택) CSV 파일로 저장하고 싶다면 아래 주석 해제
        # df_result.to_csv("analysis_result.csv", index=False, encoding='utf-8-sig')
        # print("💾 analysis_result.csv 파일로 저장되었습니다.")