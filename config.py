# [config.py] 전역 환경 설정 및 상수 관리
import os

# [Path Settings]
# BASE_DIR = "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis/Inspection_Raw_DATA_Dockerd/robot-control-system_inspection_data(docker X)"
BASE_DIR = "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis/"
EXCEL_FILE = "/home/kiie/synology/Projects/R25IA04/Inspection_point_Labeling.xlsx"
RESULT_BASE_DIR = "/home/kiie/projects/python/inspection/results"
# [Path Parser Settings]
IMAGE_PATH_PREFIX = "inspection_data"

# [Model Settings]
MODEL_CONFIG = {
    "classifier": "models/classifier/weights/best.pt",
    "ag_pose": "models/ag_inspector/weights/best.pt"
}

# # [VLM Settings - 설계서 5.1 반영]
# VLM_CONFIG = {
#     "api_url": "http://localhost:11434/api/generate",
#     "model": "llava"
# }

# [Database Settings - v2.5.0 추가]
# SQLite DB 파일 및 모델 디렉토리 경로 설정
DB_CONFIG = {
    "db_path": os.path.join(os.path.dirname(__file__), "examples", "robot-control-system-db", "myapi.db"),
    "models_dir": os.path.join(os.path.dirname(__file__), "examples", "robot-control-system-db"),
    "models_file": "models.py"
}

# [NEW] 라벨 매칭 테이블 (Excel Type : AI Model Label 리스트)
# AI 모델을 다시 학습시키지 않고도 여기서 매칭 관계를 정의할 수 있습니다.
# [config.py]
# LABEL_MAP = {
#     # 소화기 게이지: 모델이 AG_Pressure 또는 AG_Pressure_Green 등으로 검출할 경우 모두 매칭
#     "A":["A"],
#     "AG_Pressure_Fire-extinguisher": ["AG_Pressure_Fire-extinguisher", "AG_Pressure_Fire-extingusher", "AG_Pressure_Fire-extingusher_NA","AG_Pressure_Fire-extinguisher_NA"],
#     "AG_Thermo-hygro": ["AG_Thermo-hygro_NA_NA"],
#     "AG_Pressure01_P-0-1": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Pressure02_P-0-1.5": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Pressure03_P-0-1.5": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Pressure04_P-0-1.5": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Pressure05_P-0-16": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Pressure06_P-0-1.5": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Pressure07_P-0-2": ["AG_Pressure01_NA_NA","AG_Pressure02_NA_NA","AG_Pressure03_NA_NA","AG_Pressure04_NA_NA","AG_Pressure05_NA_NA","AG_Pressure06_NA_NA","AG_Pressure07_NA_NA"],
#     "AG_Temperature_T-0-100": "AG_Temperature_NA_NA",
#     "AG_Ammeter01_A-0-300": "AG_Ammeter01_AC_NA",
#     "AG_Ammeter02_A-0-30": "AG_Ammeter02_AC_NA",
#     "AG_Voltimeter_V-0-30": "AG_Voltimeter_AC_NA",
#     "AG_Ammeter03_A-0-100": ["AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
#     "AG_Ammeter04_A-0-100": ["AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
#     "DG_Air-Conditioner": "DG_Temp_Air-Conditioner_NA",
#     "DG_Digital_Multi_Function_Relay": "DG_VA_NA_NA",
#     "DG_Digital_Meter": "DG_VAP_Meter_NA",
#     "DG_Gen-Status": "DG_Gen-Status_Alt-Eng_NA",
#     "DG_Pump": "DG_Pump_ME_NA",
#     "DG_Electric_water_heater": "DG_Heater_Temp_NA",
#     "DG_Boost-pump": "DG_Boost-pump_bar_NA",
#     "DG_Digital_Integrated_Meter": "DG_Va-Ia-P-UH_V-A-P-Mwh_NA",
#     "DG_TR_temp": ["DG_Tr-Temp_C_NA","DG_Pump_ME_NA"],
#     "DG_Controller": "DG_Temp-Humi01_C-per_NA",
#     "DG_REC-KY-1500": "DG_Temp-Humi02_C-per_NA",
#     "DG_Thermo-hygro": "DG_DC-Volt_V_NA",
#     "DG_UPS_600KVA": "DG_TR-Temp_C_NA",
#     "DG_Thermo-hygro": "DG_ACV-DCV-OCA_V-V-A_NA",
#     "DG_PB_max": "DG_PB-Demend_R_NA",
#     "DG_UPS_100KVA": "DG_RST-RST_VVV-VVV-AAA_NA",
#     "DG_BMS": "DG_Va-Ia-P-UH_V-A-P-Mwh_NA",
#     "DG_Vab-bc-ca_kV_NA": "DG_Vab-bc-ca_kV_NA",
#     "LED_Green_off": ["LED_Green_off_nok","LED_Green_off_ok"],
#     "LED_Green_on": ["LED_Green_on_nok","LED_Green_on_ok"],
#     "LED_Green": ["LED_Green_off_nok","LED_Green_off_ok","LED_Green_on_nok","LED_Green_on_ok"],
#     "LED_Green-dot_off": ["LED_Green-dot_off_nok", "LED_Green-dot_off_ok"],
#     "LED_Green-dot_on": ["LED_Green-dot_on_nok","LED_Green-dot_on_ok"],
#     "LED_Green-dot": ["LED_Green-dot_off_nok", "LED_Green-dot_off_ok", "LED_Green-dot_on_nok","LED_Green-dot_on_ok"],
#     "LED_Red_off": ["LED_Red_off_nok","LED_Red_off_ok"],
#     "LED_Red_on": ["LED_Red_on_nok","LED_Red_on_ok"],
#     "LED_Red": ["LED_Red_off_nok","LED_Red_off_ok", "LED_Red_on_nok","LED_Red_on_ok"],
#     "LED_Red-dot_off": ["LED_Red-dot_off_nok","LED_Red-dot_off_ok"],
#     "LED_Red-dot_on": ["LED_Red-dot_on_nok","LED_Red-dot_on_ok"],
#     "LED_Red-dot": ["LED_Red-dot_off_nok","LED_Red-dot_off_ok", "LED_Red-dot_on_nok","LED_Red-dot_on_ok"],
#     "LED_Yellow_off": ["LED_Yellow_off_ok","LED_Yellow_off_nok"],
#     "LED_Yellow_on": ["LED_Yellow_on_ok","LED_Yellow_on_nok"],
#     "LED_Panel-green-dot_off": ["LED_Panel-green-dot_off_ok","LED_Panel-green-dot_off_nok"],
#     "LED_Panel-green-dot_on": ["LED_Panel-green-dot_on_ok","LED_Panel-green-dot_on_nok"],
#     "LED_Panel-green-dot": ["LED_Panel-green-dot_on_ok","LED_Panel-green-dot_on_nok", "LED_Panel-green-dot_off_ok","LED_Panel-green-dot_off_nok"],
#     "LED_Panel-red-dot_on": ["LED_Panel-red-dot_on_ok","LED_Panel-red-dot_on_nok"],
#     "LED_Panel-red-dot_off": ["LED_Panel-red-dot_off_ok","LED_Panel-red-dot_off_nok"],
#     "LED_Panel-red-dot": ["LED_Panel-red-dot_on_ok","LED_Panel-red-dot_on_nok","LED_Panel-red-dot_off_ok","LED_Panel-red-dot_off_nok"],
#     "LED_Panel_off": ["LED_Panel_off_ok","LED_Panel_off_nok"],
#     "LED_Panel_on": ["LED_Panel_on_ok","LED_Panel_on_nok"],
#     "LED_Panel":  ["LED_Panel_off_ok","LED_Panel_off_nok","LED_Panel_on_ok","LED_Panel_on_nok"],
#     "LED_PD_on": ["LED_PD_on_ok","LED_PD_on_nok"],
#     "LED_PD_off": ["LED_PD_off_ok","LED_PD_off_nok"],
#     "LED_pd": ["LED_PD_on_ok","LED_PD_on_nok","LED_PD_off_ok","LED_PD_off_nok"],
#     "LED_DMFR_run-on": ["LED_DMFR_run-on_ok","LED_DMFR_run-on_nok"],
#     "LED_DELD_run-on": ["LED_DELD_run-on_ok","LED_DELD_run-on_nok"],
#     "Sw_Nobe-dot_Left": ["Sw_Nobe-dot_Left_ok","Sw_Nobe-dot_Left_nok"],
#     "Sw_Nobe-dot_Center": ["Sw_Nobe-dot_Center_ok","Sw_Nobe-dot_Center_nok"],
#     "Sw_Nobe-dot_Right": ["Sw_Nobe-dot_Right_ok","Sw_Nobe-dot_Right_nok"],
#     "Sw_Nobe-dot_Left_nok": "Sw_Nobe-dot_Left_nok",
#     "Sw_Nobe-dot_Center_nok": "Sw_Nobe-dot_Center_nok",
#     "Sw_Nobe-dot_Right_nok": "Sw_Nobe-dot_Right_nok",
#     "Sw_Nobe_Left": ["Sw_Nobe_Left_ok","Sw_Nobe_Left_nok"],
#     "Sw_Nobe_Center": ["Sw_Nobe_Center_ok","Sw_Nobe_Center_nok"],
#     "Sw_Nobe_Right": ["Sw_Nobe_Right_ok","Sw_Nobe_Right_nok"],
#     "Sw_Pump_Left": ["Sw_Pump_Left_ok"],
#     "Sw_Pump_Center": ["Sw_Pump_Center_ok"],
#     "Sw_Pump_Right": ["Sw_Pump_Right_ok"],
#     "Sw_Round-dot_Left": ["Sw_Round-dot_Left_ok","Sw_Round-dot_Left_nok"],
#     "Sw_Round-dot_Center": ["Sw_Round-dot_Center_ok","Sw_Round-dot_Center_nok"],
#     "Sw_Round-dot_Right": ["Sw_Round-dot_Right_ok","Sw_Round-dot_Right_nok"],
#     "Sw_Round_Left": ["Sw_Round_Left_ok","Sw_Round_Left_nok"],
#     "Sw_Round_Center": ["Sw_Round_Center_ok","Sw_Round_Center_nok"],
#     "Sw_Round_Right": ["Sw_Round_Right_ok","Sw_Round_Right_nok"],
#     "Sw_Valve_Closed": ["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
#     "Sw_Valve_Opened": ["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
#     "ETC_Fire_Extinguisher": "Etc_Fire-Extinguisher_NA_NA",
#     "ETC_Fire_Hydrant-sign": "Etc_Fire-Hydrant-sign_NA_NA",
#     "ETC_Outlet_No-plug_ok": "Etc_Outlet_No-plug_ok",
#     "Class_C-Duct_Clean_ok": "Class_C-Duct_Clean_ok",
#     "Class_W-Tank_Gauge_ok": "Class_W-Tank_Gauge_ok",
#     "Class_D-Gen_No-oil_ok": "Class_D-Gen_No-oil_ok",
#     "Class_Plumb_Clean_ok": "Class_Plumb_Clean_ok",
#     "Class_W-Drains_Clean_ok": "Class_W-Drains_Clean_ok"

# }
LABEL_MAP = {
    "A":["B","c","d","f","g","h"],
    "AG_Ammeter01_A-0-300":["AG_Ammeter01_AC_NA","AG_Ammeter02_AC_NA","AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
    "AG_Ammeter02_A-0-30":["AG_Ammeter01_AC_NA","AG_Ammeter02_AC_NA","AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
    "AG_Ammeter03_A-0-100":["AG_Ammeter01_AC_NA","AG_Ammeter02_AC_NA","AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
    "AG_Ammeter04_A-0-100":["AG_Ammeter01_AC_NA","AG_Ammeter02_AC_NA","AG_Ammeter03_AC_NA","AG_Ammeter04_AC_NA"],
    "AG_Pressure_Fire-extinguisher":["AG_Pressure_Fire-extinguisher","AG_Pressure_Fire-extingusher","AG_Pressure_Fire-extingusher_NA","AG_Pressure_Fire-extinguisher_NA"],
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
    "DG_GIMAC-DC":["DG_ACV-DCV-OCA_V-V-A_NA"],
    "DG_BMS":[""],
    "DG_Boost-pump":["DG_Boost-pump_bar_NA"],
    "DG_Digital-Integrated-Meter":["DG_Va-Ia-P-UH_V-A-P-Mwh_NA"],
    "DG_Digital-Meter":["DG_VAP_Meter_NA"],
    "DG_UPS-600KVA":["DG_VA_NA_NA"],
    "DG_Electric-Water-Heater":["DG_Heater_Temp_NA"],
    "DG_Gen-Status":["DG_Gen-Status_Alt-Eng_NA"],
    "DG_PB_max":["DG_PB-Demend_R_NA"],
    "DG_Pump":["DG_Pump_ME_NA"],
    "DG_Thermo-hygro":["DG_Temp-Humi01_C-per_NA","DG_Temp-Humi02_C-per_NA"],
    "DG_TR-temp":["DG_Tr-Temp_C_NA","DG_Pump_ME_NA"],
    "DG_UPS_100KVA":["DG_RST-RST_VVV-VVV-AAA_NA"],
    "DG_UPS_600KVA":["DG_VA_NA_NA"],
    "ETC_Fire_Extinguisher":["Etc_Fire-Extinguisher_NA_NA"],
    "ETC_Fire_Hydrant-sign":["Etc_Fire-Hydrant-sign_NA_NA"],
    "Class_Outlet":["Etc_Outlet_No-plug_ok"],
    "LED_DELD_PAB-on":["LED_Leakage_Green-on_ok","LED_DELD_run-on"],
    "LED_DMFR_run-on":["LED_DMFR_Run-on_ok","LED_DMFR_run-on_nok"],
    "LED_Controller":[""],
    "LED_Green":["LED_Green_off","LED_Green_off_ok","LED_Green_on","LED_Green_on_ok"],
    "LED_Green_off":["LED_Green_off_nok","LED_Green_off_ok"],
    "LED_Green_on":["LED_Green_on_nok","LED_Green_on_ok"],
    "LED_Green-dot":["LED_Green-dot_off_nok","LED_Green-dot_off_ok","LED_Green-dot_on_nok","LED_Green-dot_on_ok"],
    "LED_Green-dot_off":["LED_Green-dot_off_nok","LED_Green-dot_off_ok"],
    "LED_Green-dot_on":["LED_Green-dot_on_nok","LED_Green-dot_on_ok"],
    "LED_Panel":["LED_Panel_off_ok","LED_Panel_off_nok","LED_Panel_on_ok","LED_Panel_on_nok"],
    "LED_Panel_off":["LED_Panel_off_ok","LED_Panel_off_nok"],
    "LED_Panel_on":["LED_Panel_on_ok","LED_Panel_on_nok"],
    "LED_Panel-green-dot":["LED_Panel-green-dot_on_ok","LED_Panel-green-dot_on_nok","LED_Panel-green-dot_off_ok","LED_Panel-green-dot_off_nok"],
    "LED_Panel-green-dot_off":["LED_Panel-green-dot_off_ok","LED_Panel-green-dot_off_nok"],
    "LED_Panel-green-dot_on":["LED_Panel-green-dot_on_ok","LED_Panel-green-dot_on_nok"],
    "LED_Panel-red-dot":["LED_Panel-red-dot_on_ok","LED_Panel-red-dot_on_nok","LED_Panel-red-dot_off_ok","LED_Panel-red-dot_off_nok"],
    "LED_Panel-red-dot_off":["LED_Panel-red-dot_off_ok","LED_Panel-red-dot_off_nok"],
    "LED_Panel-red-dot_on":["LED_Panel-red-dot_on_ok","LED_Panel-red-dot_on_nok"],
    "LED_pd":["LED_PD_on_ok","LED_PD_on_nok","LED_PD_off_ok","LED_PD_off_nok"],
    "LED_PD_off":["LED_PD_off_ok","LED_PD_off_nok"],
    "LED_PD_on":["LED_PD_on_ok","LED_PD_on_nok"],
    "LED_Red":["LED_Red_off","LED_Red_off_ok","LED_Red_on","LED_Red_on_ok"],
    "LED_Red_off":["LED_Red_off"],
    "LED_Red_on":["LED_Red_on_nok","LED_Red_on_ok"],
    "LED_Red-dot":["LED_Red-dot_off_nok","LED_Red-dot_off_ok","LED_Red-dot_on_nok","LED_Red-dot_on_ok"],
    "LED_Red-dot_off":["LED_Red-dot_off_nok","LED_Red-dot_off_ok"],
    "LED_Red-dot_on":["LED_Red-dot_on_nok","LED_Red-dot_on_ok"],
    "LED_Yellow_off":["LED_Yellow_off_ok","LED_Yellow_off_nok"],
    "LED_Yellow_on":["LED_Yellow_on_ok","LED_Yellow_on_nok"],
    "Sw_Nobe":["Sw_Nobe_Center","Sw_Nobe_Left","Sw_Nobe_Right"],
    "Sw_Nobe_Center":["Sw_Nobe_Center_ok","Sw_Nobe_Center_nok"],
    "Sw_Nobe_Left":["Sw_Nobe_Left_ok","Sw_Nobe_Left_nok"],
    "Sw_Nobe_Right":["Sw_Nobe_Right_ok","Sw_Nobe_Right_nok"],
    "Sw_Nobe-dot_Center":["Sw_Nobe-dot_Center_ok","Sw_Nobe-dot_Center_nok"],
    "Sw_Nobe-dot_Center_nok":["Sw_Nobe-dot_Center_nok"],
    "Sw_Nobe-dot_Left":["Sw_Nobe-dot_Left_ok","Sw_Nobe-dot_Left_nok"],
    "Sw_Nobe-dot_Left_nok":["Sw_Nobe-dot_Left_nok"],
    "Sw_Nobe-dot_Right":["Sw_Nobe-dot_Right_ok","Sw_Nobe-dot_Right_nok"],
    "Sw_Nobe-dot_Right_nok":["Sw_Nobe-dot_Right_nok"],
    "Sw_Pump":["Sw_Pump_Left","Sw_Pump_Center","Sw_Pump_Right"],
    "Sw_Pump_Center":["Sw_Pump_Center"],
    "Sw_Pump_Left":["Sw_Pump_Left"],
    "Sw_Pump_Right":["Sw_Pump_Right"],
    "Sw_Round_Center":["Sw_Round_Center"],
    "Sw_Round_Left":["Sw_Round_Left"],
    "Sw_Round_Right":["Sw_Round_Right"],
    "Sw_Round-dot_Center":["Sw_Round-dot_Center"],
    "Sw_Round-dot_Left":["Sw_Round-dot_Left"],
    "Sw_Round-dot_Right":["Sw_Round-dot_Right"],
    "Sw_Valve_Closed":["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
    "Sw_Valve_Opened":["Valve_Valve_Closed_ok","Valve_Valve_Opened_ok"],
    "Sw_Valve":["Sw_Valve_Closed","Sw_Valve_Opened"],
    "Class_C-Duct_Clean":["Class_C-Duct_Clean"],
    "Class_Clean":["Class_Clean"],
    "Class_Outlet":["Class_Outlet"],
    "Class_Plumb_Clean":["Class_Plumb_Clean"],
    "Class_W-Tank_Gauge":["Class_W-Tank_Gauge"],
    "Class_Water_Clean":["Class_Water_Clean"]
}

# [Display Settings - 설계서 4.1, 4.2 반영]
COLORS = {
    "PASS": (0, 255, 0),      # Green
    "FAIL": (0, 0, 255),      # Red
    "UNKNOWN": (0, 255, 255), # Yellow
    "OUTLINE": (0, 0, 0)      # Black (가독성용 아웃라인)
}

# [Diagnosis Logic Settings - AttributeError 해결]
STATUS_MAPPING = {
    "on": "on", "off": "off", "open": "open", "close": "close", 
    "run": "run", "stop": "stop", "trip": "trip", "fault": "fault"
}

# [config.py] 에 추가

# [VLM Settings]
VLM_CONFIG = {
    "use_backend": "ollama",  # "ollama" or "trtllm"
    "ollama": {
        "api_url": "http://localhost:11434/api/generate",  # 혹은 외부 서버 IP: "http://10.134.34.208:11434/api/generate"
        "model": "qwen3-vl:8b",
        "stream": False
    },
    "trtllm": {
        "model_urls": {
            "4b": "http://10.52.194.208:18080/qwen3_vl/4b/infer",
            "8b": "http://10.52.194.208:18080/qwen3_vl/8b/infer"
        },
        "default_model": "8b"
    }
}

# [DG VLM Settings] - DG_* 전용 VLM 설정
DG_VLM_CONFIG = {
    "use_backend": "ollama",
    "ollama": {
        "api_url": "http://localhost:11434/api/generate",
        "model": "qwen3-vl:8b",
        "stream": False,
        "temperature": 0.0 # DG의 경우 더 정확한 값을 위해 0.0 권장
    },
    "trtllm": {
        "model_urls": {
            "8b": "http://10.52.194.208:18080/qwen3_vl/8b/infer"
        },
        "default_model": "8b"
    }
}
# [VLM Prompts Mapping]
# 엑셀의 inspection_point_type에 따라 다른 질문을 던집니다.
# 키(Key)는 엑셀의 타입명 일부 혹은 전체입니다.
VLM_PROMPTS = {
    # [Derived from DB/Excel - Translated to English 2026-01-14]
    
    # Class Items (Restored)
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
    
    # 1. Digital Gauges (Generic)
    # "DG_Air-Conditioner": "1 line only. Fixed format. No explanation. Number only. 1) Number",
    "DG_Air-Conditioner": "Read the red number. Output format: (Number). Example: (24). No other text.",
    # "DG_Gen-Status": "1 line only. Fixed format. No explanation. Number only. 1) Coolant Temp",
    "DG_Gen-Status": "Read the Coolant Temp number. Output format: (Number). Example: (85). No other text.",
    # "DG_Electric-Water-Heater": "1 line only. Fixed format. No explanation. Red number only. 1) Number",
    "DG_Electric-Water-Heater": "Read the red number. Output format: (Number). Example: (45). No other text.",
    # "DG_Pump": "1 line only. Fixed format. No explanation. Number only. 1) Number",
    "DG_Pump": "Read the number. Output format: (Number). Example: (3.5). No other text.",

    # 2. Status Indicators
    "DG_BMS": "1 line only. Fixed format. No explanation. If Top-Right shows Normal operation write 'Normal', else 'Abnormal'. No other text.",
    
    # 3. Complex Meters
    # 3. Complex Meters
    # "DG_TR-temp": "1 lines only. Fixed format. No explanation. Red numbers. 1) PEAK ; 2) Temp. Controller",
    "DG_TR-temp": "Read the actual PEAK and Temp. Controller numbers from the image. Output format: (PEAK|Temp). Format Example: (999|99.9). Do not copy the example, read the real values. No other text.",
    # "DG_Digital-Integrated-Meter": "1 lines only. Fixed format. No explanation. number only. 1) Va ; 2) Ia ; 3) P ; 4) WH",
    "DG_Digital-Integrated-Meter": "Read the actual Va, Ia, P, WH values from the image. Output format: (Va|Ia|P|WH). Format Example: (999|99|99|9999). Do not copy the example, read the real values. No other text.",
    # "DG_GIMAC-DC": "1 lines only. Fixed format. No explanation. Numbers only. 1) Top ; 2) Middle ; 3) Bottom",
    "DG_GIMAC-DC": "Read the actual Top, Middle, Bottom numbers from the image. Output format: (Top|Middle|Bottom). Format Example: (999|99|999). Do not copy the example, read the real values. No other text.",
    # "DG_PB-max": "1 lines only. Fixed format. No explanation. Large numbers 4 columns only. if not detected NaN. 1) Col 1 ; 2) Col 2 ; 3) Col 3 ; 4) Col 4",
    "DG_PB-max": "Read the actual 4 large numbers in columns from the image. Output format: (Col1|Col2|Col3|Col4). Format Example: (999|999|999|999). Do not copy the example, read the real values. No other text.",
    # "DG_Thermo-hygro": "1 lines only. Fixed format. No explanation. Numbers. if not detected NaN. 1) Temp  ; 2) Humidity",
    "DG_Thermo-hygro": "Read the actual Temp and Humidity from the image. Output format: (Temp|Humidity). Format Example: (99.9|99). Do not copy the example, read the real values. No other text.",
    "DG_Digital-Meter": "Read Top, Middle, Bottom red numbers 1 lines only. No explanation. if not detected NaN. Output format: (Top| Middle| Bottom)",
    # "DG_Digital-Meter": "Read Top, Middle, Bottom numbers. Top number has 1 digits after decimal point. care about decimal point on Middle and Bottom numbers. all have 4 digits.  Output format: (Top| Middle| Bottom). Example: (xxxx|0.000|0.000). Separator: Pipe (|). No other text.",
    # "DG_Boost-pump": "1 lines only. Fixed format. No explanation. Numbers inside top circle.if not detected NaN. 1) Set Pressure  ;  2) Current Pressure",
    "DG_Boost-pump": "Read the actual Set Pressure and Current Pressure inside the circle from the image. Output format: (Set|Current). Format Example: (9.9|9.9). Do not copy the example, read the real values. No other text.",
    
    # 4. UPS Systems (Complex Layouts)
    # "DG_UPS-100KVA": """1 lines only. Fixed format. No explanation. Bypass is at top-left R S T Voltage(V). Input is at bottom-left R S T Voltage(V) and Current(A). Battery is at bottom-center Voltage(V) and below it Current(A). Output is at bottom-right R S T Voltage(V) and Current(A).1) Input Voltage(V) (R), (S), (T) ; Current(A) (R), (S), (T)  ; 2) Output Voltage(V) (R), (S), (T) ; Current(A) (R), (S), (T)  ;  3) Bypass Voltage(V) (R), (S), (T)  ; 4) Battery (V), (A)""",
    "DG_UPS-100KVA": """Read Input V(R,S,T), Input A(R,S,T), Output V(R,S,T), Output A(R,S,T), Bypass V(R,S,T), Battery V, Battery A. Output format: (InputV_R, InputV_S, InputV_T, InputA_R, InputA_S, InputA_T, OutputV_R, OutputV_S, OutputV_T, OutputA_R, OutputA_S, OutputA_T, BypassV_R, BypassV_S, BypassV_T, BattV, BattA). Example: (220, 220, 220, 10, 10, 10, 220, 220, 220, 10, 10, 10, 220, 220, 220, 500, 10). Separator: Comma. Forbidden: Semicolon. No other text.""",

    # "DG_UPS-600KVA": """1 lines only. Fixed format. No explanation. Input is at bottom-left R S T Voltage(V) and Current(A). Output is below it R S T Voltage(V) and Current(A). Bypass is below output R S T Voltage(V). SOC is at bottom-right SOC % and Voltage(V), Current(A). 1) Input Voltage(V) (R), (S), (T) ; Current(A) (R), (S), (T)  ; 2) Output Voltage(V) (R), (S), (T)  ;  Current(A) (R), (S), (T)  ;  3) Bypass Voltage(V) (R), (S), (T)  ; 4) SOC % (V), (A)""",
    "DG_UPS-600KVA": """Read Input V(R,S,T), Input A(R,S,T), Output V(R,S,T), Output A(R,S,T), Bypass V(R,S,T), SOC %, Batt V, Batt A. Output format: (InputV_R, InputV_S, InputV_T, InputA_R, InputA_S, InputA_T, OutputV_R, OutputV_S, OutputV_T, OutputA_R, OutputA_S, OutputA_T, BypassV_R, BypassV_S, BypassV_T, SOC, BattV, BattA). No other text.""",
    
    # Default
    "DEFAULT": "Describe the equipment state in 1-2 lines. English only. Focus on damage or abnormality."
}



'''

curl http://localhost:11434/api/generate -d @- <<EOF
{
  "model": "$MODEL",
  "prompt": "1 lines only. Fixed format. No explanation. Input is at bottom-left R S T Voltage(V) and Current(A). Output is below it R S T Voltage(V) and Current(A). Bypass is below output R S T Voltage(V). SOC is at bottom-right SOC % and Voltage(V), Current(A). 1) Input Voltage(V) (R), (S), (T)  ;  Current(A) (R), (S), (T)  ; 2) Output Voltage(V) (R), (S), (T)  ;  Current(A) (R), (S), (T)  ;  3) Bypass Voltage(V) (R), (S), (T)  ; 4) SOC % (V), (A)",
  "images": ["$IMG_DATA"],
  "stream": false 
}
EOF

kiie@ml:~$ IMG_PATH=~/Pictures/DG_UPS_600kVA.jpg
kiie@ml:~$ IMG_DATA=$(base64 -w 0 "$IMG_PATH")

curl http://10.134.34.208:18000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "model": "Qwen/Qwen3-VL-8B-Instruct",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "1 lines only. Fixed format. No explanation. Input is at bottom-left R S T Voltage(V) and Current(A). Output is below it R S T Voltage(V) and Current(A). Bypass is below output R S T Voltage(V). SOC is at bottom-right SOC % and Voltage(V), Current(A). Format: 1) Input V(R,S,T), A(R,S,T); 2) Output V(R,S,T), A(R,S,T); 3) Bypass V(R,S,T); 4) SOC % (V, A)"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,$IMG_DATA"
          }
        }
      ]
    }
  ],
  "max_tokens": 200,
  "temperature": 0.0
}
EOF
{"id":"chatcmpl-4eb85db2ff834efbbb4100b365beff6f","object":"chat.completion","created":1768442489,"model":"Qwen/Qwen3-VL-8B-Instruct","choices":[{"index":0,"message":{"role":"assistant","content":"1) Input V(220.7,220.6,221.0), A(130,125,119); 2) Output V(220.5,219.7,220.7), A(118,113,111); 3) Bypass V(220.9,220.7,220.5); 4) SOC 100.0% (560.0V, 1.0A)","refusal":null,"annotations":null,"audio":null,"function_call":null,"tool_calls":[],"reasoning":null,"reasoning_content":null},"logprobs":null,"finish_reason":"stop","stop_reason":null,"token_ids":null}],"service_tier":null,"system_fingerprint":null,"usage":{"prompt_tokens":637,"total_tokens":763,"completion_tokens":126,"prompt_tokens_details":null},"prompt_logprobs":null,"prompt_token_ids":null,"kv_transfer_params":null}kiie@ml:~$ 

'''