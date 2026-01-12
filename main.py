"""
프로그램명: AI 설비 진단 통합 컨트롤러 (main.py)
버전: v1.9 (2026-01-05)
변경 사항:
- [Error Fix] AGInspector 임포트 확인으로 AttributeError/NameError 해결
- [요구사항 반영] Classifier가 탐지한 모든 객체(Conf 0.1+)를 터미널 출력 및 화면 강제 표시
- [시각화 강화] 진단 정보 2줄 표시 및 [OK]/[NG] 상태 명시
"""

import os
import cv2
import pandas as pd
import numpy as np
from loguru import logger
from ultralytics import YOLO

# 설정 및 유틸리티
import config
from utils.matching import sort_by_grid_position, is_type_compatible, evaluate_gauge_reading, sort_by_x_priority
from utils.visualizer import draw_diagnosis_box, draw_summary_table, draw_outline_text

# 인스펙터 (파일 존재 및 경로 확인 필수)
from inspectors.ag_inspector import AGInspector
from inspectors.dg_inspector import DGInspector
from inspectors.sw_led_inspector import SW_LED_Inspector
from inspectors.vlm_inspector import VLMInspector

class DiagnosisSystem:
    def __init__(self):
        self.base_path = config.BASE_DIR
        self.excel_path = config.EXCEL_FILE
        try:
            # 엑셀 시트명 'inspection_point' 확인
            self.df = pd.read_excel(self.excel_path, sheet_name='inspection_point')
            self.detector = YOLO(config.MODEL_CONFIG["classifier"])
            self.ag_inspector = AGInspector(config.MODEL_CONFIG["ag_pose"])
            self.dg_inspector = DGInspector()
            self.sw_led_inspector = SW_LED_Inspector()
            self.vlm_inspector = VLMInspector()
            logger.info("✅ 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 초기화 중 에러 발생: {e}")

    def _process_group(self, img_path, group_df, results_map):
        """
        [v1.9 Debug 버전]
        - D(다음), A(이전), Q(종료) 키 지원
        - 각 단계별 상세 로그 출력으로 실행 여부 확인 가능
        """
        # [Step 1] 진입 로그 출력
        logger.info(f"▶ [DEBUG] _process_group 진입 완료 (이미지: {os.path.basename(img_path)})")
        
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"❌ [DEBUG] 이미지 파일을 읽을 수 없습니다: {img_path}")
            return 'next'

        final_img = img.copy()

        # [Step 2] 창 이름 및 그룹 정보 설정
        row_sample = group_df.iloc[0]
        sight = row_sample.get('sight', 'Unknown')
        mission = row_sample['mission_name']
        insp = row_sample['inspection_name']
        window_name = f"{sight}/{mission}/{insp}"
        
        logger.info(f"🔍 [DEBUG] 탐지 시작 (모델: {config.MODEL_CONFIG['classifier']})")

        # [Step 3] 탐지 및 정렬 수행
        results = self.detector.predict(img, conf=0.1, verbose=False)
        ag_details = self.ag_inspector.inspect_all(img_path)
        
        detections = []
        if results and len(results[0].boxes) > 0:
            logger.info(f"✅ [DEBUG] Classifier가 {len(results[0].boxes)}개의 객체를 탐지했습니다.")
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append({
                    "box": [x1, y1, x2, y2], 
                    "label": results[0].names[int(box.cls[0])],
                    "matched": False, 
                    "center_x": (x1+x2)/2, 
                    "center_y": (y1+y2)/2
                })
        else:
            logger.warning("⚠️ [DEBUG] 탐지된 객체가 없습니다. Confidence 설정을 확인하세요.")

        # [Step 4] 매칭 및 시각화
        sorted_dets = sort_by_x_priority(detections)
        summary_list = []
        
        for idx, row in group_df.iterrows():
            target = str(row['inspection_point_type'])
            matched = None
            for obj in sorted_dets:
                if not obj['matched'] and is_type_compatible(target, obj['label']):
                    matched = obj
                    obj['matched'] = True
                    break
            
            summary_list.append({"type": target, "found": matched is not None})
            
            if matched:
                val, status = None, "PASS"
                if target.startswith("AG"):
                    for ag in ag_details:
                        if abs(ag['center_x'] - matched['center_x']) < 50:
                            val, _, is_norm = evaluate_gauge_reading(ag, row)
                            status = "PASS" if is_norm else "FAIL"
                            break
                # [요구사항 반영] 2줄 정보 표시
                draw_diagnosis_box(final_img, matched['box'], row, matched['label'], status, value=val)

        # 매칭 안 된 나머지 객체 표시 (Classifier 결과 전수 노출)
        for obj in sorted_dets:
            if not obj['matched']:
                x1, y1, x2, y2 = obj['box']
                cv2.rectangle(final_img, (x1, y1), (x2, y2), config.COLORS["UNKNOWN"], 1)

        draw_summary_table(final_img, summary_list)
        
        # [Step 5] 화면 출력 및 사용자 입력 대기
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, final_img)
        logger.info(f"⌨️ [WAIT] '{window_name}' 창에서 키 입력을 대기합니다 (D:다음, A:이전, Q:종료)")
        
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord('q') or key == ord('Q'):
                logger.info("🛑 [QUIT] 프로그램을 종료합니다.")
                os._exit(0)
            elif key == ord('a') or key == ord('A'):
                cv2.destroyWindow(window_name)
                return 'prev'
            elif key == ord('d') or key == ord('D'):
                cv2.destroyWindow(window_name)
                return 'next'

    @staticmethod
    def get_latest_image(base_dir, mission, insp_name):
        import glob
        path = os.path.join(base_dir, f"{mission}.walk", f"{mission}.walk_{insp_name}")
        files = glob.glob(os.path.join(path, "*.[jJ][pP][gG]"))
        return max(files, key=os.path.getmtime) if files else None

    def run(self):
        # 엑셀 그룹화 및 이미지 탐색 후 _process_group 호출 (기존과 동일)
        pass

if __name__ == "__main__":
    DiagnosisSystem().run()