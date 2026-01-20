# AGENTS.md - Industrial Inspection System Guidelines

이 문서는 이 프로젝트에서 활동하는 AI 에이전트들을 위한 종합 가이드라인입니다. 프로젝트의 구조, 개발 주기, 코딩 표준 및 협업 규칙을 정의합니다.

## 🚀 개발 주기 및 명령어 (Makefile)

모든 명령은 프로젝트 루트 디렉토리에서 실행되어야 합니다.

### 1. 설치 및 설정
- **의존성 설치:** `make install` (pip 및 pre-commit 설치)
- **개발 환경 구축:** `make dev` (환경 설정 스크립트 실행)

### 2. 테스트 (Pytest)
- **전체 테스트:** `make test` (pytest + coverage report)
- **빠른 테스트:** `make test-fast` (coverage 제외, 짧은 traceback)
- **단위 테스트:** `make test-unit` (unit 마커가 달린 테스트만 실행)
- **통합 테스트:** `make test-int` (integration 마커가 달린 테스트만 실행)
- **개별 테스트 실행 예시:**
  - 파일 단위: `pytest test/test_file.py`
  - 함수 단위: `pytest test/test_file.py::test_function_name`

### 3. 품질 관리 및 포맷팅
- **린트 체크:** `make lint` (flake8, mypy 실행)
- **코드 포맷팅:** `make format` (black, isort 실행)
- **통합 개발 사이클:** `make dev-cycle` (clean -> format -> lint -> test-fast)

### 4. 성능 및 모니터링
- **프로파일링:** `make profile` (cProfile을 통한 성능 측정)
- **메모리 체크:** `make memory` (현재 프로세스의 메모리 사용량 확인)
- **모니터링:** `make monitor` (성능 모니터링 스크립트 실행)

---

## 🛠️ 코딩 표준 및 컨벤션

### 1. 언어 및 소통 규칙
- **기본 언어:** 모든 생각 과정, 답변, 주석, 구현 계획은 **한국어**로 작성합니다.
- **주석:** 매우 상세하고 친절하게 작성합니다. 다른 사람이 보고 바로 수정할 수 있을 정도의 정보를 포함해야 합니다.
- **구현 계획:** 코드 수정 전, 변경 사항에 대한 상세 계획을 한국어로 먼저 제시합니다.

### 2. 코드 포맷팅 (Black & Isort)
- **Line Length:** 최대 88자 (`black` 기본 설정).
- **Import 정렬:** `isort`를 사용하며 `profile=black` 설정을 따릅니다.
  1. Standard Library (`os`, `sys`, `pathlib` 등)
  2. Third-party Libraries (`cv2`, `numpy`, `loguru`, `ultralytics` 등)
  3. Local Modules (`config`, `database`, `utils` 등)

### 3. 네이밍 규칙
- **클래스:** `PascalCase` (예: `DiagnosisSystem`)
- **함수/변수:** `snake_case` (예: `process_inspection_task`)
- **상수:** `UPPER_SNAKE_CASE` (예: `DEFAULT_CONFIDENCE_THRESHOLD`)
- **프라이빗 멤버:** `_single_leading_underscore`를 사용합니다.

### 4. 타입 힌팅 (Type Hinting)
- 모든 새로운 함수와 클래스 메서드에는 명시적인 타입 힌트를 사용해야 합니다.
- `typing` 모듈 (`List`, `Dict`, `Optional`, `Any`, `Union` 등)을 적극 활용합니다.

### 5. 에러 처리 및 로깅
- **로깅:** `loguru` 라이브러리를 독점적으로 사용합니다. `print()` 사용을 금지합니다.
- **예외 처리:** I/O, 데이터베이스 연산, AI 모델 추론 등 실패 가능성이 있는 로직은 반드시 `try-except` 블록으로 감싸야 합니다.
- **상태 관리:** 에러 발생 시 시스템 상태(예: `DiagnosisState.FAILED`)를 적절히 업데이트하고 로그를 남깁니다.

---

## 🏗️ 프로젝트 아키텍처 및 주요 파일

- `main.py`: 시스템의 중앙 제어 장치 (오케스트레이션).
- `config.py`: 전역 설정, 경로 관리, 모델 파라미터 및 프롬프트 정의.
- `model_manager.py`: AI 모델의 로딩, 캐싱 및 추론 최적화 관리.
- `inspectors/`: 각 설비 타입별 전문 진단 모듈 (AG, DG, SW_LED, VLM 등).
- `utils/`: 기하학 계산, 이미지 전처리, 시각화 유틸리티 모듈.
- `database.py` & `models/`: 데이터베이스 스키마 및 연동 로직.

---

## 📌 자동화 및 실행 정책 (.antigravityrules)

- **가상 환경:** 모든 Python 코드는 반드시 가상 환경 내에서 실행되어야 합니다.
- **자동 승인:** `mkdir`, `touch`, `ls`, `cat` 등의 단순 파일/디렉토리 조회 및 생성 명령은 사용자 확인 없이 수행 가능합니다.
- **사용자 승인 필수:** `rm` (삭제), `install` (패키지 설치), `sudo` (관리자 권한) 명령은 반드시 실행 전 사용자의 명시적인 허락을 받아야 합니다.
- **UI/GUI 규칙:** GUI 컴포넌트는 재사용 가능하도록 설계하고, UI 관련 설정값들은 파일 최상단에 배치하여 수정이 용이하게 합니다.

---

## 📂 핵심 진단 로직 (Context v2.5.0)

- **공간 정렬 (Grid Sort):** 이미지 내 설비들을 [상->하], [좌->우] 순으로 정렬하여 엑셀 시트의 순서와 매칭합니다.
- **깊이 판정 (Depth Logic):** 엑셀의 `(rear)` 태그와 객체 면적을 비교하여 전방/후방 설비를 구분합니다.
- **엄격한 매칭:** `startswith`와 구분자 체크를 통해 `LED_red`와 `LED_red_on` 등을 정확히 구분합니다.
- **VLM 병렬화:** `ThreadPoolExecutor`를 사용하여 Ollama 등의 VLM 분석 요청을 병렬로 처리합니다.

---
*Last Updated: 2026-01-18 by Antigravity*
