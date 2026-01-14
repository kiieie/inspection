import pandas as pd
import config
import sys
import importlib.util
from pathlib import Path
from database import SessionLocal

def load_models():
    models_path = Path(config.DB_CONFIG['models_dir']) / config.DB_CONFIG['models_file']
    spec = importlib.util.spec_from_file_location("models", str(models_path))
    models = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models
    spec.loader.exec_module(models)
    return models

def compare():
    models = load_models()
    InspectionPoint = models.InspectionPoint
    
    # Load Excel
    df = pd.read_excel(config.EXCEL_FILE, sheet_name='inspection_point')
    
    # Load DB
    db = SessionLocal()
    db_rows = db.query(InspectionPoint).all()
    
    print(f"Excel total rows: {len(df)}")
    print(f"DB total rows: {len(db_rows)}")
    
    if len(df) > 0 and len(db_rows) > 0:
        excel_sample = df.iloc[0].to_dict()
        db_sample = db_rows[0]
        
        print("\n--- [Row 0 Comparison] ---")
        for col in df.columns:
            db_val = "N/A"
            attr_name = col
            # Mapping logic used in sync
            if col == 'report_items': attr_name = 'report_name'
            
            if hasattr(db_sample, attr_name):
                db_val = getattr(db_sample, attr_name)
            
            excel_val = excel_sample[col]
            
            # Special check for strings vs numbers
            s_excel = str(excel_val).strip()
            s_db = str(db_val).strip()
            
            match = s_excel == s_db
            # Handle float comparison for min/max etc
            if 'value' in col or 'min' in col or 'max' in col:
                try:
                    if abs(float(excel_val) - float(db_val)) < 0.0001: match = True
                except: pass

            print(f"Col: {col:<25} | Excel: {str(excel_val)[:30]:<32} | DB: {str(db_val)[:30]:<32} | Match: {match}")

    db.close()

if __name__ == "__main__":
    compare()
