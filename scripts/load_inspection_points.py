"""
load_inspection_points.py
InspectionPoint 테이블을 Excel 기반으로 초기화하는 스크립트.

Usage:
    python scripts/load_inspection_points.py
    python scripts/load_inspection_points.py --excel "X:\\path\\to\\file.xlsx"
    python scripts/load_inspection_points.py --dry-run   # DB 저장 없이 미리보기만
"""

import sys
import os
import argparse
import importlib.util
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# ─── 경로 설정 ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_EXCEL = r"X:\Projects\R25IA04\260515_Inspection_point_new_mapping_v11.xlsx"
DEFAULT_DB    = str(PROJECT_ROOT / "database" / "robot-control-system-db" / "myapi.db")

# ─── DB 연결 (config 없이 독립 실행) ─────────────────────────────────────────
def make_session(db_path: str):
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )
    Base = declarative_base()

    # models.py 동적 import (프로젝트 규칙 유지)
    models_path = PROJECT_ROOT / "database" / "robot-control-system-db" / "models.py"

    # database.py가 Base를 export하므로 sys.modules에 stub 주입
    import types
    db_stub = types.ModuleType("database")
    db_stub.Base = Base
    sys.modules["database"] = db_stub

    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models_mod = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models_mod
    spec.loader.exec_module(models_mod)

    Session = sessionmaker(bind=engine)
    return Session, models_mod

# ─── Excel → InspectionPoint 변환 ────────────────────────────────────────────
COLUMN_MAP = {
    "site":                   "site",
    "mission_name":           "mission_name",
    "inspection_name":        "inspection_name",
    "facility_1":             "facility_1",
    "facility_2":             "facility_2",
    "inspection_point_type":  "inspection_point_type",
    "report_name":            "report_name",
    "cell_num":               "insepction_cell_number",   # 모델 원문 오타 유지
    "report_details":         "inspection_details",
    "comment":                "comment",
    "min_value":              "min_value",
    "max_value":              "max_value",
    "normal_min_value":       "normal_min_value",
    "normal_max_value":       "normal_max_value",
    "sort_num":               "sort_key",
}

def load_excel(excel_path: str) -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name=0, dtype=str)
    df = df.where(pd.notna(df), None)   # NaN → None
    print(f"[Excel] {len(df)} rows loaded from '{excel_path}'")
    return df

def row_to_point(row: pd.Series, InspectionPoint):
    def safe_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # LOCAL / GLOBAL은 report_info JSON에 저장
    report_info = {}
    if row.get("LOCAL") is not None:
        report_info["LOCAL"] = row["LOCAL"]
    if row.get("GLOBAL") is not None:
        report_info["GLOBAL"] = row["GLOBAL"]

    kwargs = {}
    for excel_col, model_col in COLUMN_MAP.items():
        val = row.get(excel_col)
        if model_col in ("min_value", "max_value", "normal_min_value", "normal_max_value"):
            kwargs[model_col] = safe_float(val)
        elif model_col == "sort_key":
            kwargs[model_col] = str(int(float(val))) if val is not None else None
        else:
            kwargs[model_col] = val

    kwargs["report_info"] = report_info if report_info else None

    return InspectionPoint(**kwargs)


def main():
    parser = argparse.ArgumentParser(description="InspectionPoint 테이블 Excel 기반 초기화")
    parser.add_argument("--excel", default=DEFAULT_EXCEL, help="Excel 파일 경로")
    parser.add_argument("--db",    default=DEFAULT_DB,    help="SQLite DB 경로")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 미리보기")
    args = parser.parse_args()

    print(f"[Config] Excel: {args.excel}")
    print(f"[Config] DB   : {args.db}")

    # 1. Excel 로드
    df = load_excel(args.excel)

    # 2. DB 세션 준비
    Session, models_mod = make_session(args.db)
    InspectionPoint = models_mod.InspectionPoint

    if args.dry_run:
        print("\n[Dry-run] 첫 5행 미리보기:")
        for _, row in df.head(5).iterrows():
            pt = row_to_point(row, InspectionPoint)
            print(f"  site={pt.site}, mission={pt.mission_name}, insp={pt.inspection_name}, "
                  f"type={pt.inspection_point_type}, sort={pt.sort_key}")
        print(f"\n[Dry-run] 총 {len(df)}행이 삽입될 예정입니다. (DB 저장 안 함)")
        return

    # 3. 기존 데이터 삭제 + 새 데이터 삽입 (트랜잭션)
    db = Session()
    try:
        deleted = db.query(InspectionPoint).delete()
        print(f"[DB] 기존 InspectionPoint {deleted}행 삭제 완료")

        points = [row_to_point(row, InspectionPoint) for _, row in df.iterrows()]
        db.bulk_save_objects(points)
        db.commit()
        print(f"[DB] {len(points)}행 삽입 완료 ✅")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] 롤백됨: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
