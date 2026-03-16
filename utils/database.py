import os
import sys
import argparse
import pandas as pd
import json

# 프로젝트 루트 경로와 models.py가 있는 폴더를 sys.path에 추가 (임포트 오류 해결)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_module_path = os.path.join(project_root, 'examples', 'robot-control-system-db')
sys.path.insert(0, db_module_path)
sys.path.insert(0, project_root)

try:
    from database import SessionLocal
    from models import InspectionPoint, InspectionResult
except ImportError as e:
    print(f"모듈 임포트 에러: {e}")
    sys.exit(1)

def push_to_db(excel_path):
    print(f"[{excel_path}] 파일에서 데이터를 읽어 inspection_point 테이블로 PUSH 합니다...")
    
    if not os.path.exists(excel_path):
        print(f"에러: {excel_path} 파일이 존재하지 않습니다.")
        return

    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"엑셀 파일 읽기 실패: {e}")
        return

    # NaN 값을 None(NULL)으로 치환
    df = df.where(pd.notnull(df), None)
    
    db = SessionLocal()
    try:
        # [User Request] push 할 때는 기존 테이블(inspection_result)의 내용을 지우고 해 줘.
        # 기존 검사 결과(inspection_result) 및 검사 포인트(inspection_point) 삭제
        print("기존 inspection_result 및 inspection_point 테이블의 데이터를 삭제합니다...")
        db.query(InspectionResult).delete()
        db.query(InspectionPoint).delete()
        db.commit()
        print("기존 데이터 삭제 완료.")

        count = 0
        for _, row in df.iterrows():
            item_kwargs = {}
            for col in df.columns:
                val = row[col]
                # hyperparameter, report_info 처리 (JSON 필드)
                if col in ['hyperparameter', 'report_info']:
                    if val is not None and isinstance(val, str):
                        try:
                            val = json.loads(val)
                        except json.JSONDecodeError:
                            pass
                item_kwargs[col] = val
            
            new_point = InspectionPoint(**item_kwargs)
            db.add(new_point)
            count += 1
            
        db.commit()
        print(f"성공적으로 {count} 건의 레코드를 inspection_point 테이블에 새로 저장했습니다.")
    except Exception as e:
        print(f"DB 저장 중 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()


def pull_from_db(excel_path):
    print(f"DB inspection_point 테이블에서 데이터를 읽어 [{excel_path}] 파일로 PULL 합니다...")
    db = SessionLocal()
    try:
        points = db.query(InspectionPoint).order_by(InspectionPoint.id.asc()).all()
        
        if not points:
            print("DB에 데이터가 없습니다.")
            return

        data = []
        for p in points:
            row = {
                'id': p.id,
                'site': p.site,
                'mission_name': p.mission_name,
                'inspection_name': p.inspection_name,
                'facility_1': p.facility_1,
                'facility_2': p.facility_2,
                'inspection_point_type': p.inspection_point_type,
                'model_type': p.model_type,
                'model_ver': p.model_ver,
                'hyperparameter': json.dumps(p.hyperparameter, ensure_ascii=False) if p.hyperparameter else None,
                'min_value': p.min_value,
                'max_value': p.max_value,
                'normal_min_value': p.normal_min_value,
                'normal_max_value': p.normal_max_value,
                'comment': p.comment,
                'report_name': p.report_name,
                'inspection_details': p.inspection_details,
                'inspection_period': p.inspection_period,
                'insepction_cell_number': p.insepction_cell_number,
                'query': p.query,
                'sort_key': p.sort_key,
                'report_info': json.dumps(p.report_info, ensure_ascii=False) if p.report_info else None
            }
            data.append(row)
            
        df = pd.DataFrame(data)
        
        # 디렉토리가 없으면 생성
        out_dir = os.path.dirname(os.path.dirname(os.path.abspath(excel_path)))
        if out_dir and not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception:
                pass
            
        df.to_excel(excel_path, index=False)
        print(f"성공적으로 {len(points)} 건의 레코드를 {excel_path}에 엑셀로 덤프했습니다.")
    except Exception as e:
        print(f"DB에서 엑셀 변환 중 에러 발생: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InspectionPoint DB 테이블과 엑셀 파일 간 양방향 동기화 도구")
    parser.add_argument("--push", type=str, metavar="EXCEL_FILE", help="[Excel -> DB] 기존 테이블 내용을 모두 지우고 엑셀 파일 데이터를 밀어넣습니다.")
    parser.add_argument("--pull", type=str, metavar="EXCEL_FILE", help="[DB -> Excel] DB 테이블 내용을 지정된 엑셀 파일로 추출합니다.")
    
    # 인자가 없으면 짧은 도움말(usage) 출력
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    
    if args.push:
        push_to_db(args.push)
    elif args.pull:
        pull_from_db(args.pull)
