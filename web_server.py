
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import threading
import os
import sys
from pathlib import Path
from loguru import logger

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

# Import config and database setup
from config.env import BASE_DIR, RESULT_BASE_DIR
from database.session import SessionLocal
import models

# Import IntegratedInspector
# Note: IntegratedInspector inside tries to import 'main' which loads 'models'.
# We need to ensure 'models' is ready? 
# Usually 'integrated_inspector' will import 'main' and 'models'.
from utils.integrated_inspector import IntegratedInspector

# FastAPI App
app = FastAPI()

# Mount Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount Data Directories
app.mount("/data", StaticFiles(directory=str(BASE_DIR)), name="data")

# Mount Results Directory
RESULT_DIR = os.path.join(os.path.dirname(__file__), "test_results")

if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR, exist_ok=True)

app.mount("/results", StaticFiles(directory=RESULT_DIR), name="results")


# Templates
templates = Jinja2Templates(directory="templates")

# Global State
inspector_thread = None
inspector_instance = None

# Simple State Monitor
class ServerState:
    def __init__(self):
        self.mock_filler_running = False

state = ServerState()

@app.on_event("startup")
def startup_event():
    global inspector_instance, inspector_thread
    
    # 1. Start Integrated Inspector (Real Logic)
    inspector_instance = IntegratedInspector() 
    
    # Run in thread
    inspector_thread = threading.Thread(target=inspector_instance.run_loop, daemon=True)
    inspector_thread.start()
    
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
def get_status():
    return {
        "inspector_running": inspector_thread.is_alive() if inspector_thread else False,
        "mock_running": state.mock_filler_running
    }

@app.get("/api/latest-results")
def get_latest_results(limit: int = 50):
    """
    Returns InspectionResults with FULL metadata for the table.
    """
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
                
                # Criteria
                "criteria": f"{r.min_value} ~ {r.max_value}" if r.min_value is not None else (r.normal_min_value if r.normal_min_value else "State Check"),
                
                # Result
                "result_value": r.result_value,
                "judgement": r.judgement,
                "inspection_datetime": r.inspection_datetime.strftime("%Y-%m-%d %H:%M:%S") if r.inspection_datetime else "",
                
                # Spatial (JSON)
                "spatial_info": r.spatial_info if r.spatial_info else {},
                
                # Files
                "raw_img_url": f"/data/{os.path.relpath(r.data_raw_dir, BASE_DIR)}" if r.data_raw_dir and os.path.exists(r.data_raw_dir) else None,
                "res_img_url": f"/results/{os.path.basename(r.data_result_dir)}" if r.data_result_dir and os.path.exists(r.data_result_dir) else None
            }
            data.append(item)
        return data
    finally:
        db.close()

@app.post("/api/push-task")
def push_next_task():
    """Manual Trigger"""
    pass # Placeholder
    return {"status": "triggered"}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=38000, reload=True)
