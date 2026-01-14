
import os
import sys
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal
import config
from datetime import datetime
from pathlib import Path
import importlib.util
import glob
import pandas as pd

# [DB Setup]
spec = importlib.util.spec_from_file_location("models", str(Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']))
models = importlib.util.module_from_spec(spec)
sys.modules["models"] = models
spec.loader.exec_module(models)

app = FastAPI(title="Real-time Diagnosis Web Board")

# 글로벌 상태 관리 (주입 인덱스)
class GlobalState:
    push_index = 0

state = GlobalState()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 폴더 설정
BASE_PATH = os.getcwd()
templates = Jinja2Templates(directory="templates")

# Static File serving
# test_results와 data(config.BASE_DIR)를 웹 경로로 연결
app.mount("/results", StaticFiles(directory=os.path.join(BASE_PATH, "test_results")), name="results")
app.mount("/data", StaticFiles(directory=config.BASE_DIR), name="data")

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """메인 대시보드 페이지 렌더링"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/latest-results")
def get_latest_results(limit: int = 50):
    """최신 진단 결과를 반환함 (마스터 정보 포함)"""
    db = SessionLocal()
    try:
        results = db.query(models.InspectionResult).order_by(models.InspectionResult.id.desc()).limit(limit).all()
        data = []
        for r in results:
            item = {
                "id": r.id,
                "site": r.site,
                "mission_name": r.mission_name,
                "inspection_name": r.inspection_name,
                "facility_1": r.facility_1,
                "facility_2": r.facility_2,
                "inspection_point_type": r.inspection_point_type,
                "min_value": r.min_value,
                "max_value": r.max_value,
                "result_value": r.result_value,
                "judgement": r.judgement,
                "datetime": r.inspection_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "spatial_info": r.spatial_info,
                "raw_img": f"/data/{os.path.relpath(r.data_raw_dir, config.BASE_DIR)}" if r.data_raw_dir and os.path.exists(r.data_raw_dir) else None,
                "res_img": f"/results/{os.path.relpath(r.data_result_dir, os.path.join(BASE_PATH, 'test_results'))}" if r.data_result_dir and os.path.exists(r.data_result_dir) else None
            }
            data.append(item)
        return data
    finally:
        db.close()

@app.get("/api/status")
def get_status():
    """시스템 전체 상태 요약"""
    db = SessionLocal()
    try:
        total_res = db.query(models.InspectionResult).count()
        fail_count = db.query(models.InspectionResult).filter(models.InspectionResult.judgement == "FAIL").count()
        last_task = db.query(models.InspectionData).order_by(models.InspectionData.id.desc()).first()
        
        return {
            "total_inspections": total_res,
            "fail_count": fail_count,
            "last_mission": last_task.mission_name if last_task else "N/A",
            "last_update": last_task.inspection_time.strftime("%Y-%m-%d %H:%M:%S") if last_task else "N/A",
            "next_index": state.push_index
        }
    finally:
        db.close()

def find_actual_image(base_dir, site, mission, insp_name):
    """사용자 규격에 맞는 실제 이미지 경로 탐색 (이식)"""
    pure_name = os.path.splitext(insp_name)[0]
    search_dirs = [
        os.path.join(base_dir, site, mission),
        os.path.join(base_dir, f"{mission}.walk", f"{mission}.walk_{insp_name}")
    ]
    for sd in search_dirs:
        if os.path.exists(sd):
            pattern = os.path.join(sd, f"{pure_name}*.[jJ][pP][gG]")
            files = glob.glob(pattern)
            if files: return max(files, key=os.path.getmtime)
    return None

@app.post("/api/push-task")
def push_next_task():
    """다음 점검 그룹을 강제로 주입함 (2026-01-14)"""
    db = SessionLocal()
    try:
        points = db.query(models.InspectionPoint).all()
        if not points: raise HTTPException(status_code=404, detail="No points in DB")

        df = pd.DataFrame([p.__dict__ for p in points])
        groups = df[['site', 'mission_name', 'inspection_name']].drop_duplicates().values.tolist()
        
        if not groups: raise HTTPException(status_code=404, detail="No groups found")
        
        group = groups[state.push_index % len(groups)]
        site, mission, insp_name = group
        
        img_path = find_actual_image(config.BASE_DIR, site, mission, insp_name)
        
        new_task = models.InspectionData(
            site=site, mission_name=mission, inspection_time=datetime.now(),
            data_raw_dir=os.path.abspath(img_path) if img_path else "No Image",
            data_result_dir=insp_name, state=models.DiagnosisState.QUEUED
        )
        db.add(new_task)
        db.commit()
        
        state.push_index += 1
        return {
            "status": "success",
            "task_id": new_task.id,
            "mission": mission,
            "inspection": insp_name,
            "next_index": state.push_index
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    # 기본 포트 38000에서 실행 (2026-01-14 변경)
    uvicorn.run(app, host="0.0.0.0", port=38000)
