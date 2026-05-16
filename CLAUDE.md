# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

> **현재 브랜치: `v2-restructure`**  
> 설계 기준: `DESIGN_v2.md`  
> 기존 코드 참고: `git show origin/main:<파일경로>`

---

## Project Overview

Vision-based industrial facility AI inspection system.  
로봇/CCTV 이미지를 분석해 산업 시설(데이터센터, 전력실)의 계기 및 상태를 자동 판독.

**3가지 검사 모달리티:**
- **AG** — 아날로그 게이지 (YOLO Pose, keypoint 기반 각도 계산)
- **DG** — 디지털 게이지 (VLM/OCR)
- **SW/LED/Valve** — 상태 컴플라이언스 판별

---

## Commands

```bash
# 진단 엔진
python main.py [--withfig]

# 태스크 푸셔
python push_task.py [search_keyword]

# 웹 대시보드 (port 38000)
python web_server.py
# 또는
python web/server.py

# 테스트
pytest tests/
pytest tests/test_matching.py -v
```

---

## Project Structure

```
inspection/
├── main.py                  # 진단 엔진 (DiagnosisSystem, DB 폴링 루프)
├── push_task.py             # 태스크 푸셔 (DB QUEUED 삽입)
├── web_server.py            # 웹 대시보드 진입점
├── DESIGN_v2.md             # 설계 문서 (필독)
├── .env                     # 배포 환경 설정 (gitignore)
├── .env.example             # 환경 변수 템플릿
│
├── config/
│   ├── env.py               # 경로/환경 변수 (.env 로드)
│   ├── model.py             # AI 모델 경로, VLM 연결 설정
│   └── domain.py            # LABEL_MAP, VLM_PROMPTS, 임계값
│
├── core/
│   └── matching.py          # 2단계 레이블 매칭
│
├── inspectors/
│   ├── base.py              # BaseInspector 추상 클래스
│   ├── ag_inspector.py      # 아날로그 게이지 (Homography 없음)
│   ├── dg_inspector.py      # 디지털 게이지
│   ├── sw_led_inspector.py  # 상태 판별
│   └── vlm_inspector.py     # CLASS_ VLM 분석
│
├── database/
│   ├── session.py           # SQLAlchemy 엔진 + SessionLocal
│   └── robot-control-system-db/models.py  # 공유 DB (동적 import 유지)
│
├── web/
│   ├── server.py            # FastAPI 앱 (port 38000)
│   └── controller.py        # 태스크 네비게이션 상태
│
└── tests/
    ├── test_config.py        # config/ 패키지 로드 검증
    ├── test_matching.py      # 매칭 로직 단위 테스트
    └── test_ag_inspector.py  # AG 각도 계산 단위 테스트
```

---

## Architecture

### Data Flow

```
push_task.py → InspectionData (QUEUED)
    → main.py polls → DiagnosisSystem.process_task()
    → AG / DG / SW_LED / VLM Inspector
    → InspectionResult (DB) + 결과 이미지/JSON → RESULT_BASE_DIR
```

### Key Design Rules

1. **실행 파일 분리**: main.py(엔진), push_task.py(푸셔), web_server.py(웹) 각각 실행. 통합 CLI 없음.
2. **설정 분리**: 경로/환경은 `config/env.py`, 모델은 `config/model.py`, 도메인 규칙은 `config/domain.py`.
3. **AG Inspector**: Homography 워핑 로직 없음. keypoint → 각도 계산만.
4. **DB 동적 import**: `database/robot-control-system-db/models.py`는 `importlib.util`로 로드. 이 패턴 반드시 유지.
5. **구 config.py / database.py 유지**: 호환성을 위해 삭제하지 않음. 신규 코드는 `config/`, `database/session.py` 사용.

---

## Configuration

환경별 설정은 `.env` 파일로 관리:

```env
BASE_DIR=/data/inspection
RESULT_BASE_DIR=/data/results
DB_PATH=/data/robot-control-system.db
EXCEL_FILE=/data/checklist.xlsx
VLM_BACKEND=ollama    # ollama | trtllm
OLLAMA_API_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=qwen3-vl:8b
```

도메인 규칙 변경(레이블 추가 등)은 `config/domain.py`의 `LABEL_MAP` 편집.  
모델 경로 변경은 `config/model.py` 편집.

---

## Matching Logic

`core/matching.py`의 2단계 매칭:
1. `LABEL_MAP` 조회: `inspection_point_type` → detection label 목록
2. `is_type_compatible(target, label)`: 정규화(-/_제거) 후 exact match + suffix(ok/nok/na) + fuzzy(접두어 제거 후 포함)

Depth 정렬: `facility_2`에 `(rear)` 포함 시 작은 bounding box 우선 매칭.

---

## DB Notes

- `models.py`는 동적 import 필수: `sys.modules["models"] = models` 후 `from models import ...`
- `InspectionData.data_raw_dir`: `BASE_DIR` 기준 상대 경로
- `InspectionResult.data_result_dir`: 절대 경로
- InspectionPoint 마스터 정보: `X:\Projects\R25IA04\260515_Inspection_point_new_mapping_v11.xlsx` 기준으로 수동 등록 (스크립트: `scripts/load_inspection_points.py`)

---

## What NOT to Do

- `ag_inspector.py`에 Homography/평형화 코드 추가하지 말 것
- `config/env.py`에 도메인 규칙(LABEL_MAP 등) 혼재시키지 말 것
- 루트에 임시 실행용 `.py` 파일 추가하지 말 것
- `import config` 패턴 신규 코드에 사용하지 말 것 (대신 `from config.env import ...` 등 사용)
