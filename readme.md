
📘 산업용 설비 자동 진단 시스템 상세 설계서
Project: Inspection & Diagnosis System Version: 1.0 (Refined Logic)

1. 개요 (Overview)
본 프로젝트는 산업 현장(데이터센터, 발전실 등)의 설비 사진을 분석하여, **엑셀에 정의된 점검 포인트(Inspection Point)**들의 상태를 자동으로 진단하는 시스템입니다. 이미지 기반의 AI 모델(YOLO, OCR)을 활용하여 아날로그 게이지, 디지털 게이지, 스위치/LED 등의 상태를 판독하고, 정상 범위를 벗어났는지 판단합니다.

1.1 핵심 목표
자동화: 사람이 직접 순찰하는 대신 로봇/CCTV가 촬영한 이미지를 자동 분석.

다양성: 아날로그(바늘), 디지털(숫자), 상태형(On/Off, Open/Close) 등 다양한 설비 대응.

정확성: 단순히 객체를 찾는 것을 넘어, 엑셀 점검표의 순서와 실제 설비 배치를 1:1로 매칭하여 오진단 방지.

2. 시스템 아키텍처 (System Architecture)
2.1 폴더 구조 (Project Structure)
Plaintext

project_root/
├── main.py                     # 시스템 진입점 (DiagnosisSystem 클래스)
├── test/
│   └── test_mixed_inference.py # [Core] 정밀 매칭 로직 검증 및 테스트 코드
├── inspectors/                 # 모듈화된 진단기
│   ├── base.py                 # (Optional) Inspector 추상 클래스
│   ├── ag_inspector.py         # 아날로그 게이지 (YOLO Pose)
│   ├── dg_inspector.py         # 디지털 게이지 (PaddleOCR)
│   └── sw_led_inspector.py     # (Logical) 스위치/LED 및 일반 Compliance Check
├── models/                     # AI 모델 가중치
│   ├── classifier/             # 객체 탐지용 (YOLOv8/v11)
│   └── ag_inspector/           # 바늘/눈금 탐지용 (YOLO Pose)
├── utils/
│   └── geometry.py             # 기하학 계산 (각도, 비율 등)
└── data/
    └── Inspection_point.xlsx   # 점검 기준표 (Excel)
2.2 데이터 흐름 (Data Flow)
Input: Inspection_point.xlsx 로드 (점검 항목, 기준값, 위치 정보 포함).

Image Fetching: 엑셀의 mission_name과 inspection_name을 조합하여 파일 시스템에서 최신 이미지 검색.

Path Rule: BASE_DIR/Inspection_Raw_DATA/{mission}.walk/...

Routing: 점검 포인트 타입(AG*, DG*, SW* 등)에 따라 적절한 Inspector로 분기.

Inference & Logic:

AG: Object Detect -> Keypoint Extract -> Geometry Calc -> Value Conversion.

DG: Object Detect -> Crop -> Rotate/Deskew -> OCR.

Compliance (SW/LED): Object Detect -> Grid Sorting -> Strict Type Matching -> State Check.

Output: 진단 결과(Pass/Fail, Read Value) 및 시각화된 이미지(Bounding Box + Text).

3. 상세 모듈 설계 (Detailed Design)
3.1 Main Controller (DiagnosisSystem in main.py)
역할: 전체 프로세스 오케스트레이션.

주요 기능:

_init_system: 엑셀 로드, YOLO 모델(Classifier) 로드.

run: 엑셀 행을 그룹핑(mission_name + inspection_name)하여 이미지 단위로 처리.

_process_ag_group, _process_dg_group, _process_compliance_group: 타입별 처리 분기.

3.2 아날로그 게이지 진단기 (AGInspector)
Target: AG_* (Analog Gauge)

Algorithm:

Detection: YOLO Pose 모델로 게이지 영역 및 키포인트(Start, Mid, Center, End, Needle_Head) 검출.

Validation: validate_gauge_geometry 함수로 형상 찌그러짐, 크기 미달 확인.

Calculation: calculate_gauge_ratio 함수로 바늘의 각도 비율(0.0 ~ 1.0) 계산.

Conversion: 비율을 물리적 수치로 변환 (min + ratio * (max - min)).

Judgment: 변환된 값이 normal_min ~ normal_max 사이인지 판정.

3.3 디지털 게이지 진단기 (DGInspector)
Target: DG_* (Digital Gauge)

Algorithm:

Detection: 메인 YOLO 모델로 게이지 박스 검출.

Preprocessing:

이미지 Crop.

Skew Correction: Hough Transform 또는 PCA를 사용하여 기울어진 LCD 화면을 수평으로 보정 (OCR 인식률 향상 핵심).

OCR: PaddleOCR 엔진을 사용하여 숫자 인식.

Parsing: 정규식(re)을 통해 텍스트에서 숫자만 추출 (float).

Judgment: 추출된 숫자가 정상 범위 내인지 판정.

3.4 컴플라이언스 진단기 (Compliance Check - SW/LED)
Target: SW_*, LED_*, Valve, etc.

핵심 문제 해결: 엑셀에는 같은 이름(LED_on)이 여러 개 있고, 사진에도 여러 개가 있을 때 어떤 것이 어떤 설비인지 매칭하는 문제 해결.

Algorithm (The "Grid Sort & Match" Logic):

Filtering: 해당 미션(SW_LED_inspection)과 관련 없는 객체(AG, DG 등)는 검출 결과에서 배제.

Grid Sorting (공간 정렬):

검출된 객체들을 Y축(상→하) 우선, 같은 높이일 경우 X축(좌→우) 순서로 정렬.

엑셀 데이터는 작성 순서가 실제 설비 배치 순서(좌상→우하)와 동일하다고 가정.

Strict Type Matching (엄격한 타입 매칭):

엑셀 타겟명(target)과 검출 라벨(label) 비교.

Rule 1: label이 target으로 시작해야 함 (startswith).

Rule 2 (Boundary Check): target 뒤에 바로 끝이 나거나, _(언더바), (공백)이 와야 함.

Example: Target LED_red는 Label LED_red-dot과 매칭 불가 (하이픈 구분자).

1:1 Sequential Mapping:

정렬된 엑셀 리스트를 순회하며, 정렬된 검출 리스트에서 "사용되지 않았고(unused) + 타입이 호환되는" 첫 번째 객체를 찾아 매칭 (is_used 플래그 사용).

Judgment: 엑셀의 기대 상태(Target Name에 포함된 상태값)와 검출된 상태(Label) 일치 여부 확인.

4. 데이터 명세 및 규칙 (Data Spec & Rules)
4.1 엑셀 데이터 컬럼
mission_name: 점검 미션 (폴더명 매핑).

inspection_name: 세부 점검명 (파일명 매핑).

facility_1, facility_2: 설비 위치/이름 (시각화 시 라벨링).

inspection_point_type: 점검 대상 타입 (AG_, DG_, LED_, SW_).

min_value, max_value: 게이지 물리적 최소/최대값.

normal_min, normal_max: 정상 범위.

4.2 시각화 및 정보 표시 전략 (Display & Visualization Strategy)
사용자(작업자)가 진단 결과를 직관적으로 확인하고, 시스템의 판단 근거를 명확히 알 수 있도록 아래와 같은 시각화 규칙을 적용합니다.

A. 바운딩 박스 색상 정책 (Color Policy)
검출된 객체의 상태에 따라 박스 테두리 색상을 구분하여 즉각적인 상태 파악을 돕습니다.

🟢 Green (정상/Pass):

엑셀 기준값과 일치하며, 상태가 정상인 경우.

(예: LED_on 기대 -> LED_on 검출)

🔴 Red (비정상/Fail):

엑셀 기준값과 다르거나, 비정상(Abnormal/NOK) 상태가 검출된 경우.

(예: Switch_Close 기대 -> Switch_Open 검출, NOK 라벨 검출)

🟡 Yellow (매칭 실패/Unknown/Extra):

화면에 객체는 있으나 엑셀 리스트와 매칭되지 않는 경우 (잉여 객체).

또는 검출은 되었으나 판독이 불가능한 경우.

B. 텍스트 라벨링 구조 (Text Labeling Structure)
박스 주변에 표시되는 정보는 **"진단 근거"**와 **"위치 정보"**를 포함하여 오진단 시 원인을 파악할 수 있게 합니다.

상단 라벨 (Header Info): [기대값 vs 결과값]

형식: Exp: {Excel_Target} / Fnd: {Detected_Label}

목적: 시스템이 '무엇을 찾아야 했는지(Exp)'와 '실제 무엇을 보았는지(Fnd)'를 비교 표시.

예시: Exp: A_Heater_LED / Fnd: LED_Red_On

하단 라벨 (Detail Info): [설비 위치 정보]

형식:

Line 1: {facility_1} (대분류)

Line 2: {facility_2} (중분류/상세명)

목적: 동일한 부품(예: LED)이 여러 개 있을 때, 해당 부품이 어떤 설비의 것인지 명시.

예시:

Generator_Panel_1

Main_Breaker_Switch

C. 화면 오버레이 (Screen Overlay)
이미지 전체에 대한 요약 정보를 좌측 상단에 고정 표시합니다.

타이틀 (Title): [{Mission_Name}] {File_Name}

현재 보고 있는 이미지가 어떤 미션의 어떤 파일인지 식별.

종합 결과 (Global Status): Result: {ALL PASS} / {FAIL (count)}

ALL PASS (초록색): 모든 점검 항목이 정상일 때.

FAIL (3) (빨간색): 하나라도 비정상이 있을 경우, 실패한 항목 수 표시.

D. 가독성 강화 (Readability Enhancement)
현장 이미지는 배경이 복잡하거나 어두울 수 있으므로 텍스트 가독성을 최우선으로 합니다.

아웃라인(Outline) 적용: 모든 텍스트에 검은색 또는 흰색의 두꺼운 외곽선을 적용하여 배경색과 관계없이 글자가 뚜렷하게 보이도록 처리.

스마트 위치 조정: 박스가 이미지 최상단에 있어 텍스트를 위에 적을 수 없는 경우, 자동으로 박스 안쪽이나 아래쪽으로 라벨 위치를 이동.

5. 향후 확장 계획 (Future Scope)
5.1 VLM (Vision Language Model) 통합
대상: ETC_* 타입 (비정형 점검 항목).

계획:

이미지와 엑셀의 질의(Query) 내용을 프롬프트로 구성.

네트워크(Tor/OpenWebUI)를 통해 외부 VLM(GPT-4o, Gemini, Claude 등)에 전송.

"전선이 정돈되어 있는가?", "녹이 슬었는가?" 등의 질의 수행 후 결과 텍스트 파싱.

5.2 UI/UX
현재 cv2.imshow 기반의 디버깅 뷰를 웹 기반 대시보드(Streamlit 등)로 전환 고려.

최종 결과를 엑셀 파일로 다시 저장(Export)하는 기능 활성화.

6. 개발자 가이드 (For Gemini CLI / Developers)
6.1 핵심 로직 파일
현재 가장 고도화된 매칭 로직은 main.py의 구버전 로직이 아니라, test/test_mixed_inference.py 내의 test_sw_led_inference_grouped 함수에 구현되어 있습니다.

Action Item: main.py를 리팩토링할 때, test_mixed_inference.py의 Grid Sorting & Strict Matching 로직을 DiagnosisSystem 클래스로 이식해야 합니다.

6.2 디버깅 팁
이미지 미검출 시: 경로(Inspection_Raw_DATA/{mission}.walk/...)가 실제 파일 시스템과 일치하는지 로그 확인.

매칭 꼬임 발생 시: 엑셀의 행 순서와 실제 이미지 상의 설비 배치 순서(좌상→우하)가 일치하는지 확인. 불필요한 객체(AG/DG)가 필터링되지 않고 있는지 확인.


네, 앞서 작성해드린 **[4.2 시각화 및 정보 표시 전략]**의 상세함과 톤앤매너를 유지하여, 전체 프로젝트 설계서를 처음부터 끝까지 **"거시적(아키텍처)에서 미시적(알고리즘)"** 흐름으로 완벽하게 재작성했습니다.

이 문서는 개발자(또는 AI)가 코드를 보지 않고도 시스템의 작동 원리와 구현 요구사항을 명확히 파악할 수 있도록 작성되었습니다.

---

# 📘 산업용 설비 자동 진단 시스템 상세 설계서

**Project Name:** Vision-based Facility Inspection System
**Document Version:** 2.0 (Final Architecture)

---

## 1. 프로젝트 개요 (Project Overview)

### 1.1 배경 및 목적

본 시스템은 산업 현장(데이터센터, 발전기실 등)의 순찰 로봇이나 CCTV가 촬영한 이미지를 분석하여 설비의 정상 작동 여부를 자동 판독하는 것을 목적으로 합니다.
단순한 객체 탐지를 넘어, **엑셀 점검표(Checklist)에 정의된 순서와 설비의 물리적 배치 순서를 동기화(Sync)**하여 오진단 없는 정밀한 상태 점검을 수행합니다.

### 1.2 핵심 워크플로우 (Macro Workflow)

1. **Input:** 점검 기준이 담긴 `Excel` 파일 + 현장 촬영 `Image` 폴더.
2. **Process:**
* 엑셀 데이터를 미션(Mission) 단위로 그룹핑.
* 이미지 내 객체 검출 (Detection).
* **공간 정렬(Spatial Sorting)** 및 **엄격한 타입 매칭(Strict Type Matching)**.
* 설비별 전용 진단 알고리즘 수행 (AG/DG/SW).


3. **Output:** 진단 결과(`Pass`/`Fail`)가 시각화된 이미지 및 데이터.

---

## 2. 시스템 아키텍처 및 데이터 파이프라인 (System Architecture)

### 2.1 디렉토리 및 데이터 구조

시스템은 상대 경로를 기반으로 유동적으로 작동해야 합니다.

* **Root Structure:**
* `/Inspection_Raw_DATA/{Mission}.walk/...` : 이미지 원본 데이터 저장소.
* `/models/...` : YOLO, OCR 등 학습된 모델 가중치.
* `Inspection_point.xlsx` : 진단 기준 메타데이터.


* **Excel Schema (Key Columns):**
* `mission_name`: 점검 구역 대분류 (폴더 매핑용).
* `inspection_name`: 점검 포인트 이름 (파일명 매핑용).
* `inspection_point_type`: 설비 타입 (로직 분기용 Key - 예: `AG_pressure`, `DG_volt`, `LED_run`).
* `facility_1` / `facility_2`: 설비 위치 및 상세 명칭 (표시용).
* `min/max/normal_min/normal_max`: 아날로그/디지털 값 판단 기준.



### 2.2 처리 파이프라인 (Processing Pipeline)

시스템은 다음 순서로 데이터를 처리합니다.

1. **Data Loading:** 엑셀 파일을 로드하고 `unique_key` (`mission` + `inspection`)로 그룹화.
2. **Image Fetching:** 각 그룹에 매핑되는 최신 이미지 파일(`*.jpg`, `*.png`) 탐색.
3. **Detection & Routing:**
* 이미지 전체에 대해 YOLO Detector 수행.
* `inspection_point_type` 접두어에 따라 전용 검사 모듈(Inspector)로 라우팅.
* `AG*` → **AGInspector**
* `DG*` → **DGInspector**
* `SW*`, `LED*`, `Valve` → **SW_LED_Inspector (Compliance Check)**





---

## 3. 모듈별 상세 로직 명세 (Micro Logic Specification)

### 3.1 아날로그 게이지 진단기 (AG Inspector)

바늘이 있는 게이지(압력계, 온도계 등)의 값을 판독합니다.

* **Target:** `AG_pressure`, `AG_temperature`, `Ammeter` 등.
* **Core Logic:** `YOLO Pose` 기반 키포인트 분석.
1. **Keypoint Extraction:** 5개의 키포인트 추출 (0:Start, 1:Mid, 2:Center, 3:End, 4:Needle_Head).
2. **Geometry Validation:**
* 최소 크기 검사: 반지름이 너무 작으면 노이즈로 간주 (`radius < 15px`).
* 왜곡 검사: 타원율(`min_r / max_r`)이 0.4 미만이면 측면 촬영 등으로 판단하여 기각.


3. **Value Calculation:**
* 각도법(Degree)을 사용하여 Start-End 사이의 각도(Span)와 Start-Needle 사이의 각도(Progression) 계산.
* `Ratio = Progression / Span` (0.0 ~ 1.0).
* **Physical Value:** `Min + Ratio * (Max - Min)`.


4. **Result:** 계산된 값이 `normal_min ~ normal_max` 범위 내인지 판정.



### 3.2 디지털 게이지 진단기 (DG Inspector)

7-Segment 등의 디지털 숫자를 판독합니다.

* **Target:** `DG_volt`, `Digital_meter` 등.
* **Core Logic:** `OCR` + `Skew Correction`.
1. **Crop & Preprocess:** 검출된 박스 영역을 잘라냄(Crop).
2. **Skew Correction (기울기 보정):**
* OCR 인식률 향상을 위해 필수적.
* Hough Transform 또는 Blue Line Detection을 통해 LCD 패널의 기울기를 계산하고 역회전(Rotate)하여 수평 정렬.


3. **OCR Inference:** PaddleOCR 엔진을 사용하여 텍스트 추출.
4. **Parsing:** 정규식(`re`)으로 숫자(`float`)만 필터링.
5. **Result:** 엑셀 기준값 비교 판정.



### 3.3 상태/컴플라이언스 진단기 (Compliance Inspector)

스위치, LED, 밸브 등 상태(State)를 점검하며, **엑셀 목록과 검출 객체의 1:1 정밀 매칭**이 핵심입니다.

* **Target:** `SW_*`, `LED_*`, `Valve_*`.
* **Core Algorithm: Grid Sorting & Strict Prefix Matching**
1. **Spatial Sorting (공간 정렬):**
* 검출된 객체들을 화면상의 **[위 → 아래]**, 같은 높이면 **[좌 → 우]** 순서로 정렬합니다.
* *전제 조건:* 엑셀 데이터의 입력 순서가 실제 설비의 물리적 배치 순서(좌상→우하)와 일치해야 합니다.


2. **Filtering:**
* 현재 점검 미션과 무관한 객체(예: LED 점검 중 AG/DG 박스)는 매칭 후보군에서 사전 배제하여 인덱스 밀림 방지.


3. **Strict Prefix Matching (엄격한 접두어 매칭):**
* 단순 포함(`in`) 관계가 아닌, 명확한 타입 구분을 수행합니다.
* **규칙:** `Detected_Label`이 `Excel_Target`으로 시작(`startswith`)해야 하며, 그 뒤에 **구분자(_, 공백)나 문장의 끝**이 와야 합니다.
* *Case O:* Target=`LED_Run` vs Label=`LED_Run_on` (매칭 성공)
* *Case X:* Target=`LED_Run` vs Label=`LED_Run-Dot_on` (매칭 실패 - 파생형 구분)




4. **Sequential Binding:**
* 정렬된 엑셀 리스트를 순회하며, 정렬된 검출 리스트에서 **"아직 사용되지 않았고(Unused) + 타입이 호환되는"** 첫 번째 객체를 찾아 바인딩(Binding)합니다.





---

## 4. 시각화 및 정보 표시 전략 (Display Strategy)

사용자(작업자)가 진단 결과를 직관적으로 확인하고, 시스템의 판단 근거를 명확히 알 수 있도록 아래 규칙을 엄수합니다.

### 4.1 바운딩 박스 색상 정책 (Color Code)

* **🟢 Green (Pass):** 정상. 엑셀 기준과 일치하며 상태 양호.
* **🔴 Red (Fail):** 비정상. 엑셀 기준 불일치, 수치 이탈, 또는 NOK 라벨 검출.
* **🟡 Yellow (Unknown/Extra):** 매칭 대상 없음, 잉여 객체, 또는 판독 불가.

### 4.2 텍스트 라벨링 (On-Screen Display)

박스 주변 텍스트는 **배경 박스(Background Rect)** 또는 **진한 아웃라인(Outline)**을 적용하여 어떤 배경에서도 가독성을 확보해야 합니다.

* **박스 상단 (Header):** 판단 근거 표시
* Format: `Exp: {Excel_Target} / Fnd: {Detected_Label}`
* *예시: Exp: Heater_LED / Fnd: LED_Red_On*


* **박스 하단 (Detail):** 설비 위치 정보 (2줄 표시)
* Line 1: `{facility_1}`
* Line 2: `{facility_2}`
* *목적: 동일하게 생긴 LED가 여러 개일 때, 이것이 "어떤 설비"의 LED인지 식별.*



### 4.3 화면 오버레이 (Global Status)

이미지 좌측 상단에 고정된 헤드업 디스플레이(HUD) 정보를 출력합니다.

* **Title:** `[{Mission_Name}] {File_Name}`
* **Summary:** `Result: {ALL PASS} / {FAIL (Count)}` (색상 코딩 적용)

---

## 5. 기술 스택 및 환경 (Tech Stack)

* **Language:** Python 3.10+
* **Vision Core:** Ultralytics YOLO (v8/v11), PaddleOCR, OpenCV
* **Data Analysis:** Pandas, NumPy
* **Logging:** Loguru (구조적 로깅)
* **Testing:** Pytest (단위 테스트 및 시각적 검증)

---

## 6. 향후 확장성 (Future Roadmap)

1. **VLM Integration:**
* `ETC_` 로 시작하는 비정형 항목(예: "전선 정리가 잘 되어 있는가?")은 OpenAI GPT-4o 또는 Local LLM(OpenWebUI 연동)으로 이미지를 전송하여 텍스트 질의응답 수행.


2. **Web Dashboard:**
* 현재의 `cv2.imshow` 디버깅 환경을 Streamlit 또는 React 기반의 웹 대시보드로 이관하여 원격 관제 기능 확보.

제공해주신 **상세 설계서(v2.0)**와 실제 **Python 소스 코드**를 비교 분석하여, 현재 시스템의 구현 현황과 설계서 대비 정합성을 정리해 드립니다.

이 보고서는 설계서의 요구사항이 코드에 어떻게 반영되어 있는지, 그리고 향후 리팩토링 시 주의해야 할 핵심 포인트를 짚어줍니다.

---

## 1. 시스템 아키텍처 및 데이터 흐름 검토

설계서의 **거시적 아키텍처**는 현재 코드 구조와 매우 높은 일치도를 보입니다.

* **구현 현황**: `main.py`가 컨트롤 타워 역할을 수행하며, `inspectors/` 폴더 내의 각 모듈(AG, DG, SW_LED)로 진단 로직을 위임하고 있습니다.
* **데이터 파이프라인**: 엑셀의 `mission_name`과 `inspection_name`을 사용하여 이미지 경로를 동적으로 생성하는 규칙(`get_latest_image`)이 설계서대로 구현되어 있습니다.

---

## 2. 모듈별 상세 구현 분석 (Code vs Design)

### 2.1 아날로그 게이지 (AG Inspector)

가장 완성도가 높은 모듈로, 설계서의 기하학적 분석 단계가 코드로 구현되어 있습니다.

* **키포인트 매핑**: 설계서의 5개 핵심 포인트가 `KP_IDX` 상수로 정의되어 동작합니다.
* **수치 변환 로직**: 바늘의 위치를 로 계산하여 수치화하는 공식이 적용되었습니다.


* **시각화**: 설계서에서 요구한 'YOLO 라벨'과 '수치/상태'를 포함한 **3줄 정보 표시**가 구현되어 있습니다.

### 2.2 디지털 게이지 (DG Inspector)

OCR 인식률 향상을 위한 전처리 로직이 핵심입니다.

* **기울기 보정 (Skew Correction)**: 허프 변환(`_estimate_angle_hough`)과 블루 라인 검출을 통해 LCD의 수평을 맞추는 로직이 설계서와 일치합니다.
* **OCR & 파싱**: PaddleOCR을 사용하여 텍스트를 읽고, 정규표현식으로 숫자만 추출하는 과정이 구현되었습니다.

### 2.3 상태 및 컴플라이언스 (Compliance Check)

설계서에서 가장 강조된 **"Grid Sorting & Strict Matching"** 로직입니다.

* **공간 정렬 (Grid Sorting)**: `test_mixed_inference.py`에 구현된 `sort_by_grid_position` 함수가 Y축 우선, X축 차선 정렬을 수행하여 엑셀 순서와의 동기화를 보장합니다.
* **엄격한 타입 매칭**: `is_type_compatible` 함수가 설계서의 규칙(startswith + 구분자 체크)을 충실히 따르고 있어, `LED_red`와 `LED_red-dot`을 명확히 구분합니다.

---

## 3. 시각화 및 정보 표시 전략 준수 현황

설계서 4.2절의 시각화 전략이 코드의 여러 곳에 분산되어 적용되어 있습니다.

| 항목 | 설계 요구사항 | 코드 구현 현황 (Status) |
| --- | --- | --- |
| **박스 색상** | Green(정상), Red(이상), Yellow(잉여) | **준수**: `match_details`와 연동되어 색상 분기 처리됨. |
| **텍스트 라벨** | `Exp` vs `Fnd` 표시 | **준수**: `_process_compliance_group`에서 기대값과 검출값 동시 표기. |
| **하단 정보** | `facility_1/2` (위치 정보) 표시 | **준수**: `ag_inspector` 및 `test_mixed_inference` 시각화 로직에 반영. |
| **가독성** | 아웃라인(Outline) 및 스마트 위치 조정 | **준수**: `sw_led_inspector.py`에 아웃라인 텍스트 로직 구현 완료. |

---

## 4. 시스템 수행 방법 및 최적 플로우 제안

설계서의 의도를 가장 잘 반영할 수 있는 시스템 수행 플로우 3가지를 제안합니다.

### **[Flow 1] 알고리즘 중심의 확정적 진단 (현재 권장)**

AG, DG, SW 로직을 순차적으로 실행하여 물리적 수치를 확정합니다.

* **장점**: 판정 근거가 명확하며 오진단 시 원인 파악이 쉬움.
* **단점**: 새로운 형태의 기기가 추가될 때마다 전용 Inspector 개발 필요.

### **[Flow 2] 공간 인식형 하이브리드 진단 (Refined Logic)**

Grid Sorting을 먼저 수행하여 이미지 내 모든 객체의 인덱스를 확정한 후 진단합니다.

* **장점**: 동일 기기가 여러 개 있는 복잡한 패널에서 매칭 정확도가 가장 높음.
* **단점**: 엑셀의 작성 순서가 실제 배치와 다를 경우 오류 발생 가능.

### **[Flow 3] VLM 보조형 유연 진단 (Future Scope)**

정형 기기는 알고리즘으로, 비정형(부식, 전선 등)은 VLM으로 처리합니다.

* **장점**: 설계서 5.1절의 확장성을 확보하여 점검 범위를 무한히 넓힐 수 있음.
* **단점**: 외부 API 연동 시 응답 속도 및 네트워크 의존성 문제 발생.

### **[최선의 방법 선정]**

현 시점에서는 **Flow 2(공간 인식형)**를 주축으로 하되, `test_mixed_inference.py`에 있는 고도화된 매칭 로직을 `main.py`로 통합하는 것이 설계서의 목표를 달성하는 가장 확실한 방법입니다.

---

## 5. 리팩토링 및 통합 가이드 (Action Items)

설계서와 코드의 미세한 간극을 메우기 위한 다음 단계를 권장합니다.

1. **로직 통합**: `test_mixed_inference.py`에만 존재하는 `is_type_compatible` 및 `sort_by_grid_position` 함수를 `utils/` 또는 `main.py`로 옮겨 시스템 전체에서 공통으로 사용하게 하십시오.
2. **시각화 통일**: `ag_inspector`의 3줄 표시 방식과 `sw_led_inspector`의 아웃라인 텍스트 방식을 병합하여 모든 모듈에서 동일한 퀄리티의 결과물을 생성하도록 하십시오.
3. **VLM 인터페이스 준비**: `vlm_inspector.py`의 Mockup 코드를 실제 API 호출 로직으로 교체할 준비를 하십시오.

**이제 이 설계서 내용을 바탕으로 `main.py`에 `test_mixed_inference.py`의 고급 매칭 로직을 통합하는 작업을 시작해볼까요?** 원하시는 경우 해당 통합 코드를 작성해 드릴 수 있습니다.

************************************************************************************************************************************

flow 2에서는 객체가 큰 순서대로 앞에 있어. 뒤에 있는 것은 

엑셀에서는 같은 mission_name, inspection_name, inspection_point_type 으로 이루어 지는 검사 항목에 대해서 위쪽에 기술되어 있는 객체가 사람이(진단시) 앞쪽 왼쪽에 있는 객체야. 그런데 사람이(진단시) 뒤쪽에 있는 객체는 엑셀의 facility_2가 (rear)를 포함해 (rear)를 포함한 항목도 엑셀에서 위쪽에 있는 항목이 사람이 진단시 왼쪽에 있는 항목이야. 


