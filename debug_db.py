import sys
from pathlib import Path
import importlib.util
import config

# Dynamic Import of models
if "models" not in sys.modules:
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
else:
    models = sys.modules["models"]

from database import SessionLocal
from models import InspectionData, DiagnosisState, InspectionResult

db = SessionLocal()
try:
    print("=== INSPECTION DATA (Latest 5 COMPLETED) ===")
    tasks = db.query(InspectionData).filter(
        InspectionData.state == DiagnosisState.COMPLETED
    ).order_by(InspectionData.id.desc()).limit(5).all()
    
    for t in tasks:
        print(f"Task ID: {t.id}")
        print(f"  Result Dir: {t.data_result_dir}")
        
        results = db.query(InspectionResult).filter(
            InspectionResult.data_result_dir == t.data_result_dir
        ).all()
        print(f"  InspectionResults Count: {len(results)}")
        if results:
            print(f"  Sample Result Path: {results[0].data_result_dir}")
        else:
            print("  ❌ NO RESULTS LINKED!")
            
    print("\n=== LATEST RAW INSPECTION RESULTS (Latest 5) ===")
    raw_results = db.query(InspectionResult).order_by(InspectionResult.id.desc()).limit(5).all()
    for r in raw_results:
        print(f"Res ID: {r.id}, Path: {r.data_result_dir}")

finally:
    db.close()
