# Inspection System v2 — 설계 문서

> 작성일: 2026-05-16  
> 목적: 기존 inspection 시스템의 전면 구조 개편을 위한 설계 기준 문서  
> 브랜치: `v2-restructure` (origin/main 기준)

---

## 1. 개편 목표 요약

| 영역 | 현재 문제 | v2 목표 |
|------|-----------|---------|
| Inspector 로직 | AG 분석에 불필요한 평형화/사상(Homography) 포함 | 핵심 로직만 유지, Homography 제거 |
| 폴더/모듈 구조 | 임시 실행 파일 난립, 흐름 분산 | 단일 진입점, 역할별 명확한 모듈 분리 |
| Web 대시보드 | FastAPI 설정이 두 곳에 분산 (root + web/) | 단일 web/ 모듈로 통합 |
| 설정 관리 | 환경 설정과 기타 설정이 config.py에 혼재 | 환경/도메인/모델 설정 파일 분리 |

---

## 2. v2 폴더 구조

> **결정 (2026-05-16):** 실행 구조(main.py, push_task.py, web_server.py)는 현행 유지.  
> 설정/로직 분리만 진행. core/에는 matching.py만 존재.

```
inspection/
│
├── main.py                   # 진단 엔진 실행 (현행 유지)
├── push_task.py              # 태스크 푸셔 (현행 유지)
├── web_server.py             # 웹 대시보드 (현행 유지)
├── CLAUDE.md
├── DESIGN_v2.md              # 이 문서
├── requirements.txt
├── .env                      # 환경 변수 (배포 환경별 설정) — gitignore
├── .env.example              # 환경 변수 예시 템플릿
│
├── config/
│   ├── __init__.py
│   ├── env.py                # .env 로드 (BASE_DIR, DB_PATH, RESULT_DIR 등)
│   ├── model.py              # 모델 경로, VLM 백엔드 설정
│   └── domain.py             # LABEL_MAP, VLM_PROMPTS, 임계값 등 도메인 규칙
│
├── core/
│   ├── __init__.py
│   └── matching.py           # 2단계 레이블 매칭 로직 (LABEL_MAP + prefix match)
│
├── inspectors/
│   ├── __init__.py
│   ├── base.py               # BaseInspector 추상 클래스
│   ├── ag_inspector.py       # 아날로그 게이지 (YOLO Pose, Homography 제거됨)
│   ├── dg_inspector.py       # 디지털 게이지 (VLM/OCR)
│   ├── sw_led_inspector.py   # 스위치/LED 상태 판별
│   └── vlm_inspector.py      # CLASS_ 타입 VLM 분석
│
├── database/
│   ├── __init__.py
│   ├── session.py            # SQLAlchemy 엔진 + SessionLocal
│   └── robot-control-system-db/   # 기존 유지 (공유 DB, 동적 import)
│       └── models.py
│
├── web/
│   ├── server.py             # FastAPI 앱 (port 38000)
│   └── controller.py         # 태스크 네비게이션 상태 관리
│
└── tests/
    ├── test_ag_inspector.py
    ├── test_matching.py
    └── test_dg_inspector.py
```

---

## 3. 설정 관리 분리 전략

### 3.1 `.env` — 배포 환경별 설정 (gitignore)

```env
BASE_DIR=/data/inspection
RESULT_BASE_DIR=/data/results
DB_PATH=/data/robot-control-system.db
EXCEL_FILE=/data/checklist.xlsx
VLM_BACKEND=ollama        # ollama | trtllm
```

### 3.2 `config/env.py` — 환경 변수 로드

```python
# 역할: .env를 읽어서 경로/환경 설정만 담당
BASE_DIR: Path
RESULT_BASE_DIR: Path
DB_PATH: Path
VLM_BACKEND: str  # "ollama" | "trtllm"
```

### 3.3 `config/model.py` — 모델 경로 및 VLM 설정

```python
# 역할: AI 모델 파일 경로, VLM 연결 설정
AG_MODEL_PATH: Path
DG_MODEL_PATH: Path
VLM_CONFIG: dict  # host, port, model_name 등
```

### 3.4 `config/domain.py` — 도메인 규칙

```python
# 역할: 검사 로직에 관한 비즈니스 규칙
LABEL_MAP: dict        # inspection_point_type → detection labels
VLM_PROMPTS: dict      # 각 분석 타입별 프롬프트
THRESHOLDS: dict       # 판정 임계값
```

---

## 4. Inspector 개편 — AG Inspector Homography 제거

### 현재 구조 (제거 대상)
```
ag_inspector.py
  ├── detect_keypoints()         # YOLO Pose → 5 keypoints
  ├── apply_homography_warp()    # ← 제거: 측면 각도 보정
  ├── normalize_keypoints()      # ← 제거: 평형화/사상
  └── calculate_angle_ratio()    # 각도 비율 → 물리값 변환
```

### v2 구조 (단순화)
```
ag_inspector.py
  ├── detect_keypoints()         # YOLO Pose → 5 keypoints (유지)
  └── calculate_value()          # 각도 비율 → 물리값 변환 (유지)
```

**제거 이유:**
- Homography는 측면 촬영 보정용인데, 운용 환경에서 로봇이 정면 촬영을 보장함
- 평형화 단계가 오히려 keypoint 정확도에 노이즈 추가
- 코드 복잡도 대비 실제 정확도 향상 미미

---

## 5. 실행 구조 (현행 유지)

실행 파일 통합 없음. 기존 방식대로 각각 실행:

```bash
# 진단 엔진
python main.py

# 태스크 푸셔
python push_task.py

# 웹 대시보드 (port 38000)
python web_server.py
```

---

## 6. Web 대시보드

현행 `web_server.py` + `web/server.py` 구조 유지. 통합 작업 없음.

---

## 7. 개편 작업 순서

### Phase 1: 기반 정리 ✅
- [x] 불필요한 파일 목록 정리 (임시 스크립트, 중복 실행 파일)
- [x] `config/` 구조 생성 및 기존 `config.py` 분리
- [x] `.env.example` 작성

### Phase 2: 핵심 로직 ✅
- [x] `database/session.py` 분리 (기존 database.py 이전)
- [x] `core/matching.py` 이전 (기존 utils/matching.py)
- [x] `inspectors/base.py` 확인
- [x] `ag_inspector.py` Homography 제거 후 단순화
- [x] 나머지 inspector import 업데이트 (dg, sw_led, vlm)

### Phase 3: 실행 구조 — 생략 (현행 유지)
- 실행 파일(main.py, push_task.py, web_server.py) 통합하지 않음
- main.py에서 `config.py` → `config/` 패키지로 import 교체만 수행

### Phase 4: 검증
- [x] 실행 파일 import 교체 (main.py, push_task.py, web_server.py → `config/`, `database.session`, `core.matching`)
- [ ] `tests/` 핵심 테스트 작성
- [ ] 기존 DB + 결과 파일 연동 확인
- [ ] CLAUDE.md 최종 업데이트

---

## 8. 기존 파일 → v2 파일 매핑

| 기존 파일 | v2 파일 | 상태 |
|-----------|---------|------|
| `config.py` | `config/env.py` + `config/model.py` + `config/domain.py` | ✅ 분리 완료 (config.py는 호환용 유지) |
| `database.py` | `database/session.py` | ✅ 완료 (database.py는 호환용 유지) |
| `database/robot-control-system-db/models.py` | 동일 위치 유지 | ✅ 변경 없음 |
| `main.py` | `main.py` | 현행 유지, import만 교체 예정 |
| `push_task.py` | `push_task.py` | 현행 유지 |
| `web_server.py` | `web_server.py` | 현행 유지 |
| `web/server.py` | `web/server.py` | 현행 유지 |
| `inspectors/ag_inspector.py` | `inspectors/ag_inspector.py` | ✅ Homography 제거 완료 |
| `inspectors/dg_inspector.py` | `inspectors/dg_inspector.py` | ✅ import 업데이트 완료 |
| `inspectors/sw_led_inspector.py` | `inspectors/sw_led_inspector.py` | ✅ import 정리 완료 |
| `inspectors/vlm_inspector.py` | `inspectors/vlm_inspector.py` | ✅ import 업데이트 완료 |
| `utils/matching.py` | `core/matching.py` | ✅ 이전 완료 (utils/matching.py는 호환용 유지) |

---

## 9. 유지되는 것 (변경 없음)

- `database/robot-control-system-db/models.py` — 로봇 제어 시스템과 공유, 동적 import 패턴 유지
- AG/DG/SW_LED/VLM Inspector 핵심 판정 알고리즘
- DB 스키마 (`InspectionPoint`, `InspectionData`, `InspectionResult`)
- FastAPI 포트 38000
- RESULT_BASE_DIR 결과 저장 구조
