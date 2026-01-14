# [config_optimized.py] - Optimized Configuration for Production and Development
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Centralized configuration with environment support and optimization"""
    
    def __init__(self, env: str = "development"):
        self.env = env
        self.base_dir = Path(__file__).parent
        self._load_config()
    
    def _load_config(self):
        """Load configuration based on environment"""
        # Environment detection
        self.env = os.getenv("INSPECTION_ENV", self.env)
        self.is_production = self.env == "production"
        self.is_development = self.env == "development"
        
        # [Performance Settings]
        self.PERFORMANCE = {
            "enable_model_caching": not self.is_development,  # Disable in dev for hot reload
            "lazy_loading": True,  # Load models only when needed
            "max_concurrent_models": 1 if self.is_production else 2,  # Limit memory usage
            "image_batch_size": 1,  # Process one image at a time to reduce memory
            "garbage_collection_interval": 10,  # Force GC every N processed images
            "max_memory_mb": 150 if self.is_production else 300,  # Memory limit
        }
        
        # [Path Settings - Environment aware]
        base_data_dir = os.getenv(
            "INSPECTION_DATA_DIR",
            "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis/Inspection_Raw_DATA_Dockerd/robot-control-system_inspection_data(docker X)"
        )
        
        self.PATHS = {
            "base_dir": base_data_dir,
            "excel_file": os.getenv("INSPECTION_EXCEL_FILE", "/home/kiie/synology/Projects/R25IA04/Inspection_point_Labeling.xlsx"),
            "models_dir": self.base_dir / "models",
            "cache_dir": self.base_dir / "cache",
            "temp_dir": "/tmp/inspection_cache"
        }
        
        # Ensure cache directories exist
        for path in [self.PATHS["cache_dir"], self.PATHS["temp_dir"]]:
            Path(path).mkdir(parents=True, exist_ok=True)
        
        # [Model Settings - Optimized for memory]
        self.MODELS = {
            "classifier": {
                "path": self.PATHS["models_dir"] / "classifier" / "weights" / "best.pt",
                "cache_key": "classifier_v1",
                "conf_threshold": 0.15 if self.is_production else 0.1,  # Slightly higher in prod
                "device": "cpu",  # Force CPU to avoid GPU memory overhead
                "half_precision": True,  # Use FP16 to reduce memory
                "max_det": 50  # Limit detections to reduce processing
            },
            "ag_pose": {
                "path": self.PATHS["models_dir"] / "ag_inspector" / "weights" / "best.pt",
                "cache_key": "ag_pose_v1",
                "conf_threshold": 0.25,
                "device": "cpu",
                "half_precision": True,
                "max_det": 20
            }
        }
        
        # [VLM Settings - Optimized]
        self.VLM = {
            "api_url": os.getenv("VLM_API_URL", "http://localhost:11434/api/generate"),
            "model": os.getenv("VLM_MODEL", "qwen3-vl:8b"),
            "timeout": 30,  # Timeout in seconds
            "max_retries": 2,
            "cache_responses": self.is_production,  # Cache VLM responses in prod
            "batch_requests": False  # Process one at a time to reduce memory
        }
        
        # [Database Settings]
        self.DATABASE = {
            "db_path": self.base_dir / "examples" / "robot-control-system-db" / "myapi.db",
            "connection_pool_size": 1,
            "timeout": 10
        }
        
        # [Memory Optimization]
        self.MEMORY_OPT = {
            "max_image_size": (1920, 1080),  # Downsample large images
            "jpeg_quality": 85,  # Compress cached images
            "clear_cache_on_startup": self.is_development,
            "monitor_memory": True,
            "memory_warning_threshold": 0.8  # Alert at 80% of max_memory_mb
        }
        
        # [CPU Optimization]
        self.CPU_OPT = {
            "max_workers": 1,  # Single-threaded to reduce CPU usage
            "thread_pool_size": 2,
            "enable_multiprocessing": False,  # Avoid process overhead
            "opencv_threads": 1,  # Limit OpenCV threads
            "numpy_threads": 1
        }
        
        # [Monitoring]
        self.MONITORING = {
            "enable_profiling": self.is_development,
            "log_memory_usage": True,
            "log_cpu_usage": True,
            "performance_log_interval": 50  # Log every N operations
        }
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model configuration with environment overrides"""
        config = self.MODELS.get(model_name, {}).copy()
        if not config:
            raise ValueError(f"Model {model_name} not found in configuration")
        return config
    
    def get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a given key"""
        return self.PATHS["cache_dir"] / f"{cache_key}.cache"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization"""
        return {
            "env": self.env,
            "performance": self.PERFORMANCE,
            "paths": {k: str(v) for k, v in self.PATHS.items()},
            "models": self.MODELS,
            "vlm": self.VLM,
            "memory_opt": self.MEMORY_OPT,
            "cpu_opt": self.CPU_OPT
        }

# Global config instance
config = Config(env=os.getenv("INSPECTION_ENV", "development"))

# Legacy compatibility - expose old style variables
BASE_DIR = str(config.PATHS["base_dir"])
EXCEL_FILE = str(config.PATHS["excel_file"])
MODEL_CONFIG = {name: cfg["path"] for name, cfg in config.MODELS.items()}
VLM_CONFIG = config.VLM
DB_CONFIG = config.DATABASE

# Load LABEL_MAP (keeping existing structure)
LABEL_MAP = {
    "A":["B","c","d","f","g","h"],
    "AG_Ammeter01_A-0-300":["AG_Ammeter01_AC_NA"],
    "AG_Ammeter02_A-0-30":["AG_Ammeter02_AC_NA"],
    "AG_Ammeter03_A-0-100":["AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
    "AG_Ammeter04_A-0-100":["AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
    "AG_Pressure_Fire-extinguisher":["AG_Pressure_Fire-extinguisher","AG_Pressure_Fire-extingusher"," AG_Pressure_Fire-extingusher_NA","AG_Pressure_Fire-extinguisher_NA"],
    "AG_Pressure01_P-0-1":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Pressure02_P-0-1.5":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Pressure03_P-0-1.5":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Pressure04_P-0-1.5":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Pressure05_P-0-16":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Pressure06_P-0-1.5":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Pressure07_P-0-2":["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
    "AG_Temperature_T-0-100":["AG_Temperature_NA_NA"],
    "AG_Thermo-hygro":["AG_Thermo-hygro_NA_NA"],
    "AG_Voltimeter_V-0-30":["AG_Voltimeter_AC_NA"],
    "Class_C-Duct_Clean_ok":["Class_C-Duct_Clean_ok"],
    "Class_D-Gen_No-oil_ok":["Class_D-Gen_No-oil_ok"],
    "Class_Plumb_Clean_ok":["Class_Plumb_Clean_ok"],
    "Class_W-Drains_Clean_ok":["Class_W-Drains_Clean_ok"],
    "Class_W-Tank_Gauge_ok":["Class_W-Tank_Gauge_ok"],
    "DG_Air-Conditioner":["DG_Temp_Air-Conditioner_NA"],
    "DG_BMS":[""],
    "DG_Boost-pump":["DG_Boost-pump_bar_NA"],
    "DG_Digital_Integrated_Meter":["DG_Va-Ia-P-UH_V-A-P-Mwh_NA"],
    "DG_Digital_Meter":["DG_VAP_Meter_NA"],
    "DG_UPS-600KVA":["DG_VA_NA_NA"],
    "DG_Electric-Water-Heater":["DG_Heater_Temp_NA"],
    "DG_Gen-Status":["DG_Gen-Status_Alt-Eng_NA"],
    "DG_PB_max":["DG_PB-Demend_R_NA"],
    "DG_Pump":["DG_Pump_ME_NA"],
    "DG_Thermo-hygro":["DG_Temp-Humi01_C-per_NA","DG_Temp-Humi02_C-per_NA"],
    "DG_TR_temp":["DG_Tr-Temp_C_NA","DG_Pump_ME_NA"],
    "DG_UPS_100KVA":["DG_RST-RST_VVV-VVV-AAA_NA"],
    "DG_UPS_600KVA":["DG_VA_NA_NA"],
    "ETC_Fire_Extinguisher":["Etc_Fire-Extinguisher_NA_NA"],
    "ETC_Fire_Hydrant-sign":["Etc_Fire-Hydrant-sign_NA_NA"],
    "Class_Outlet":["Etc_Outlet_No-plug_ok"],
    "LED_DELD_run-on":["LED_Leakage_Green-on_ok","LED_DELD_run-on_nok"],
    "LED_DMFR_run-on":["LED_DMFR_Run-on_ok","LED_DMFR_run-on_nok"],
    "LED_Controller":[""],
    "LED_Green":["LED_Green_off_nok","LED_Green_off_ok","LED_Green_on_nok","LED_Green_on_ok"],
    "LED_Green_off":["LED_Green_off_nok","LED_Green_off_ok"],
    "LED_Green_on":["LED_Green_on_nok","LED_Green_on_ok"],
    "LED_Green-dot":["LED_Green-dot_off_nok","LED_Green-dot_off_ok"," LED_Green-dot_on_nok","LED_Green-dot_on_ok"],
    "LED_Green-dot_off":["LED_Green-dot_off_nok","LED_Green-dot_off_ok"],
    "LED_Green-dot_on":["LED_Green-dot_on_nok","LED_Green-dot_on_ok"],
    "LED_Panel":["LED_Panel_off_ok","LED_Panel_off_nok","LED_Panel_on_ok","LED_Panel_on_nok"],
    "LED_Panel_off":["LED_Panel_off_ok","LED_Panel_off_nok"],
    "LED_Panel_on":["LED_Panel_on_ok","LED_Panel_on_nok"],
    "LED_Panel-green-dot":["LED_Panel-green-dot_on_ok","LED_Panel-green-dot_on_nok"," LED_Panel-green-dot_off_ok","LED_Panel-green-dot_off_nok"],
    "LED_Panel-green-dot_off":["LED_Panel-green-dot_off_ok","LED_Panel-green-dot_off_nok"],
    "LED_Panel-green-dot_on":["LED_Panel-green-dot_on_ok","LED_Panel-green-dot_on_nok"],
    "LED_Panel-red-dot":["LED_Panel-red-dot_on_ok","LED_Panel-red-dot_on_nok","LED_Panel-red-dot_off_ok","LED_Panel-red-dot_off_nok"],
    "LED_Panel-red-dot_off":["LED_Panel-red-dot_off_ok","LED_Panel-red-dot_off_nok"],
    "LED_Panel-red-dot_on":["LED_Panel-red-dot_on_ok","LED_Panel-red-dot_on_nok"],
    "LED_pd":["LED_PD_on_ok","LED_PD_on_nok","LED_PD_off_ok","LED_PD_off_nok"],
    "LED_PD_off":["LED_PD_off_ok","LED_PD_off_nok"],
    "LED_PD_on":["LED_PD_on_ok","LED_PD_on_nok"],
    "LED_Red":["LED_Red_off_nok","LED_Red_off_ok"," LED_Red_on_nok","LED_Red_on_ok"],
    "LED_Red_off":["LED_Red_off_nok","LED_Red_off_ok"],
    "LED_Red_on":["LED_Red_on_nok","LED_Red_on_ok"],
    "LED_Red-dot":["LED_Red-dot_off_nok","LED_Red-dot_off_ok"," LED_Red-dot_on_nok","LED_Red-dot_on_ok"],
    "LED_Red-dot_off":["LED_Red-dot_off_nok","LED_Red-dot_off_ok"],
    "LED_Red-dot_on":["LED_Red-dot_on_nok","LED_Red-dot_on_ok"],
    "LED_Yellow_off":["LED_Yellow_off_ok","LED_Yellow_off_nok"],
    "LED_Yellow_on":["LED_Yellow_on_ok","LED_Yellow_on_nok"],
    "Sw_Nobe_Center":["Sw_Nobe_Center_ok","Sw_Nobe_Center_nok"],
    "Sw_Nobe_Left":["Sw_Nobe_Left_ok","Sw_Nobe_Left_nok"],
    "Sw_Nobe_Right":["Sw_Nobe_Right_ok","Sw_Nobe_Right_nok"],
    "Sw_Nobe-dot_Center":["Sw_Nobe-dot_Center_ok","Sw_Nobe-dot_Center_nok"],
    "Sw_Nobe-dot_Center_nok":["Sw_Nobe-dot_Center_nok"],
    "Sw_Nobe-dot_Left":["Sw_Nobe-dot_Left_ok","Sw_Nobe-dot_Left_nok"],
    "Sw_Nobe-dot_Left_nok":["Sw_Nobe-dot_Left_nok"],
    "Sw_Nobe-dot_Right":["Sw_Nobe-dot_Right_ok","Sw_Nobe-dot_Right_nok"],
    "Sw_Nobe-dot_Right_nok":["Sw_Nobe-dot_Right_nok"],
    "Sw_Pump_Center":["Sw_Pump_Center_ok"],
    "Sw_Pump_Left":["Sw_Pump_Left_ok"],
    "Sw_Pump_Right":["Sw_Pump_Right_ok"],
    "Sw_Round_Center":["Sw_Round_Center_ok","Sw_Round_Center_nok"],
    "Sw_Round_Left":["Sw_Round_Left_ok","Sw_Round_Left_nok"],
    "Sw_Round_Right":["Sw_Round_Right_ok","Sw_Round_Right_nok"],
    "Sw_Round-dot_Center":["Sw_Round-dot_Center_ok","Sw_Round-dot_Center_nok"],
    "Sw_Round-dot_Left":["Sw_Round-dot_Left_ok","Sw_Round-dot_Left_nok"],
    "Sw_Round-dot_Right":["Sw_Round-dot_Right_ok","Sw_Round-dot_Right_nok"],
    "Sw_Valve_Closed":["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
    "Sw_Valve_Opened":["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
    "Sw_Valve":["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
    "Class_C-Duct_Clean":["Class_C-Duct_Clean"],
    "Class_Clean":["Class_Clean"],
    "Class_Outlet":["Class_Outlet"],
    "Class_Plumb_Clean":["Class_Plumb_Clean"],
    "Class_W-Tank_Gauge":["Class_W-Tank_Gauge"],
    "Class_Water_Clean":["Class_Water_Clean"]
}

# Other legacy configs
COLORS = {
    "PASS": (0, 255, 0),
    "FAIL": (0, 0, 255),
    "UNKNOWN": (0, 255, 255),
    "OUTLINE": (0, 0, 0)
}

STATUS_MAPPING = {
    "on": "on", "off": "off", "open": "open", "close": "close", 
    "run": "run", "stop": "stop", "trip": "trip", "fault": "fault"
}

VLM_PROMPTS = {
    "DG_Air-Conditioner": "Write only the value. 1 line. No reason. Number only. 1) Number:",
    "DG_BMS": "Write only the status. 1 line. No reason. If normal 'Normal', if abnormal 'Abnormal'. 1) Status:",
    "DG_TR-temp": "Write only the numbers. 2 lines. No reason. 1) PEAK: , 2) Temp. Controller:",
    "DG_Digital-Integrated-Meter": "Write only the values. 4 lines. No reason. 1) Va: , 2) Ia: , 3) P: , 4) WH:",
    "DG_GIMAC-DC": "Write only the numbers. 3 lines. No reason. 1) Top: , 2) Mid: , 3) Bottom:",
    "Class_C-Duct": """Write in 3 lines. English only. No reason.
        1) Cleaning State(1~5):
        2) Leakage(O/X):
        3) Corrosion(O/X):""",
    "Class_Pipe_condition": """Write in 1 line. English only. No reason.
        1) Insulation State(Good/Poor):""",
    "Class_Water_level_gauge": """Write in 2 lines. English only. No reason.
        1) Leakage(O/X):
        2) Damage(O/X):""",
    "Class_Outlet": """Write in 1 line. English only. No reason.
        1) Outlet Condition(Good/Poor):""",
    "Class_Wire_condition": """Write in 1 line. English only. No reason.
        1) Abnormality(Good/Poor):""",
    "Class_Fire": """Write in 2 lines. English only. No reason.
        1) Location(Normal/Abnormal):
        2) Fire-extinguisher State(Good/Poor):""",
    "Class_Clean": """Write in 1 line. English only. No reason.
        1) Cleaning State(Good/Poor):""",
    "DEFAULT": """Describe the equipment state in 1-2 lines. English only. Focus on damage or abnormality."""
}