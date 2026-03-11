# 프로젝트 핸드오버 문서 (Handover Documentation)

이 문서는 **AI 설비 진단 통합 시스템 (Inspection Project)**의 전반적인 구조, 핵심 로직, AI 모델 활용 방식 및 UI 구성에 대해 상세히 설명합니다.

---

## 1. 프로젝트 개요
본 프로젝트는 산업 현장의 다양한 계측기(아날로그/디지털 게이지), 스위치, LED 상태를 통합적으로 진단하기 위한 시스템입니다. Spot 로봇 또는 고정형 카메라로부터 수집된 이미지를 분석하여 설비의 이상 유무를 판단하고 결과를 대시보드에 시각화합니다.

## 2. 시스템 아키텍처
시스템은 크게 세 가지 레이어로 구성됩니다.

1.  **Main Controller (main.py)**: 전체 프로세스를 관리하는 엔진입니다. DB(SQLite)를 폴링하며 새로운 태스크가 주입되면 각 Inspector를 호출하여 진단을 수행하고 결과를 저장합니다.
2.  **ML Inspectors (inspectors/)**: 특정 설비 유형에 최적화된 분석 로직 모음입니다.
    -   `AGInspector`: 아날로그 게이지 분석 (YOLOv8-Pose 기반).
    -   `DGInspector`: 디지털 게이지 분석 (기울기 보정 및 영역 추출).
    -   `VLMInspector`: 시각 언어 모델(Ollama/TRT-LLM)을 활용한 비정형 데이터 및 텍스트 분석.
    -   `SW_LED_Inspector`: 스위치 및 LED 상태 분석.
3.  **Web Dashboard (web/)**: FastAPI 기반의 웹 서버와 대시보드 UI입니다. 검사 결과를 실시간으로 확인하고 과거 이력을 탐색할 수 있습니다.

---

## 3. 핵심 AI 모델 및 구현 논리

### A. 아날로그 게이지 (AG) 분석
-   **모델**: YOLOv8-Pose (`ag_pose`)
-   **구현 논리**:
    -   키포인트(Start, Mid, Center, End, Needle Head)를 검출합니다.
    -   검출된 키포인트를 기반으로 기하학적 각도를 계산하여 0.0 ~ 1.0 사이의 비율을 산출합니다.
    -   **특이점**: 심한 측면 이미지의 경우 호모그래피 변환(Homography Warping)을 통해 정면 이미지로 보정 후 각도를 계산하여 정확도를 높입니다.

### B. 디지털 게이지 (DG) 분석
-   **모델**: YOLOv11 (`classifier`) + VLM
-   **구현 논리**:
    -   YOLO를 통해 게이지 영역을 검출합니다.
    -   허프 변환(Hough Transform)을 사용하여 이미지의 기울기를 계산하고 수평을 맞춥니다.
    -   보정된 크롭 이미지를 VLM에 전달하여 수치를 읽어옵니다.

### C. 시각 언어 모델 (VLM) 연동
-   **백엔드**: Ollama 또는 NVIDIA TensorRT-LLM (TRT-LLM) 선택 가능.
-   **구현 논리**:
    -   `config.py`의 `VLM_PROMPTS`에 정의된 프롬프트를 사용하여 모델에 질의합니다.
    -   디지털 게이지 숫자 읽기뿐만 아니라 `CLASS_`로 시작하는 항목(오염도, 파손 여부 등)에 대한 판단도 수행합니다.
    -   TRT-LLM 사용 시 `8b` 등의 모델을 원격 API 형태로 호출합니다.

### D. 모델 관리 (ModelManager)
-   `model_manager.py`를 통해 모델의 지연 로딩(Lazy Loading), 메모리 모니터링, LRU 기반 모델 언로딩을 관리하여 리소스 효율성을 극대화합니다.

---

## 4. UI/UX 구성 및 시각화

### A. 웹 대시보드
-   **Frontend**: Vanilla JS (`app.js`), CSS (`style.css`), HTML5.
-   **주요 기능**:
    -   검사 결과 이미지 및 상세 데이터(유형, 수치, 판정 결과) 실시간 표시.
    -   이전/다음 태스크 탐색 및 수동 검사 요청(Push).
    -   검사 결과 위치(Spatial Info)를 기반으로 한 하이라이트 표시.

### B. 진단 결과 시각화 (`utils/visualizer.py`)
-   결과 이미지 상에 바운딩 박스, 상태 텍스트, AG 키포인트를 직접 렌더링합니다.
-   검정색 아웃라인 텍스트 및 배경 박스를 사용하여 다양한 배경에서도 가독성을 확보합니다.
-   우측 상단에 전체 검사 항목의 리스트(POINT STATUS)를 스택 형태로 표시합니다.

---

## 5. 데이터 흐름
1.  **태스크 생성**: 외부 장치 또는 웹 대시보드에서 엑셀 정보를 기반으로 DB(InspectionData)에 태스크 주입.
2.  **분영 수행**: `main.py`가 `QUEUED` 상태의 태스크를 감지하여 실행.
3.  **검색 및 매칭**: YOLO/Pose 모델로 설비를 찾고, 엑셀 마스터 정보(InspectionPoint)와 위치 기반 매칭.
4.  **결과 저장**: 분석 결과(수치, 이미지)를 `test_results/`에 저장하고 DB 업데이터.
5.  **모니터링**: 웹 대시보드에서 `/api/latest_result` API를 통해 결과를 가져와 화면 갱신.

---

## 6. 설치 및 실행 방법
-   **의존성 설치**: `pip install -r requirements.txt`
-   **DB 마이그레이션**: `python migrate_db.py`
-   **엔진 실행**: `python main.py --withfig` (시각화 창 포함)
-   **웹 서버 실행**: `python web/server.py` (포트 38000)

---

이 문서는 2026년 3월 2일 기준으로 작성되었습니다. 추가적인 로직 변경 시 해당 섹션을 업데이트하시기 바랍니다.
