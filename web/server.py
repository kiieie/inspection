from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from pathlib import Path

# Local Imports
from controller import TaskController
import sys

# Setup Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.append(str(PROJECT_ROOT))
import config

app = FastAPI(title="Inspection Dashboard")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Templates
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Result Images Mount (Mapping config.RESULT_BASE_DIR to /results)
if not os.path.exists(config.RESULT_BASE_DIR):
    os.makedirs(config.RESULT_BASE_DIR)
app.mount("/results", StaticFiles(directory=config.RESULT_BASE_DIR), name="results")

# Initialize Controller
controller = TaskController()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/status")
async def get_status():
    info = controller.get_current_task_info()
    return JSONResponse(info if info else {"error": "No tasks loaded"})

@app.get("/api/control/next")
async def control_next():
    success = controller.next_task()
    if success:
        return await push_task_internal()
    return JSONResponse({"status": "no_more_tasks"})

@app.get("/api/control/prev")
async def control_prev():
    success = controller.prev_task()
    if success:
        return await push_task_internal()
    return JSONResponse({"status": "no_prev_task"})

@app.get("/api/control/push")
async def control_push():
    return await push_task_internal()

async def push_task_internal():
    success, msg = controller.push_current_task()
    info = controller.get_current_task_info()
    return JSONResponse({
        "status": "success" if success else "error",
        "message": msg,
        "current_task": info
    })

def process_result_response(res):
    if not res:
        return JSONResponse({"status": "waiting"})
        
    full_path = str(res['image_path'])
    base_str = str(config.RESULT_BASE_DIR)
    
    full_path = os.path.normpath(full_path)
    base_str = os.path.normpath(base_str)
    
    if full_path.startswith(base_str):
        rel_path = full_path[len(base_str):]
        if rel_path.startswith(os.sep): rel_path = rel_path[1:]
        web_path = f"/results/{rel_path}"
        res['web_image_url'] = web_path.replace(os.sep, "/")
    else:
        res['web_image_url'] = ""

    return JSONResponse(res)

@app.get("/api/latest_result")
async def get_latest_result():
    try:
        res = controller.get_latest_result()
        return process_result_response(res)
    except Exception as e:
        print(f"❌ Error in latest_result: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/history/prev")
async def history_prev(current_id: int):
    try:
        res = controller.get_history_prev(current_id)
        return process_result_response(res)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/history/next")
async def history_next(current_id: int):
    try:
        res = controller.get_history_next(current_id)
        return process_result_response(res)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=38000, reload=True)
