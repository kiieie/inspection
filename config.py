# [config.py] 전역 환경 설정 및 상수 관리
import os

# [Path Settings]
BASE_DIR = "/home/kiie/synology/Projects/R25IA04/Inspection_and_Diagnosis/Inspection_Raw_DATA_Dockerd/robot-control-system_inspection_data(docker X)"
EXCEL_FILE = "/home/kiie/synology/Projects/R25IA04/Inspection_point_Labeling.xlsx"

# [Model Settings]
MODEL_CONFIG = {
    "classifier": "models/classifier/weights/best.pt",
    "ag_pose": "models/ag_inspector/weights/best.pt"
}

# [VLM Settings - 설계서 5.1 반영]
VLM_CONFIG = {
    "api_url": "http://localhost:11434/api/generate",
    "model": "llava"
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

# # [VLM Settings]
VLM_CONFIG = {
    "api_url": "http://10.73.136.208:11434/api/generate",  # 외부 서버일 경우 IP 변경
    "model": "qwen3-vl:32b",  # ollama list에 있는 모델명 정확히 기입
    "stream": True
}
# [config.py]
# VLM_CONFIG = {
#     "api_url": "http://localhost:11434/api/generate",
#     "model": "llava:latest",  # 23GB짜리 qwen 대신 4.7GB짜리 llava 사용
#     "stream": True
# }
# [VLM Prompts Mapping]
# 엑셀의 inspection_point_type에 따라 다른 질문을 던집니다.
# 키(Key)는 엑셀의 타입명 일부 혹은 전체입니다.
VLM_PROMPTS = {
    # CLI_1.py 참고 (덕트, 일반 설비 등)
    "Class_C-Duct": """3줄만. 형식 고정. 이유 설명 금지.
        1)청소상태(1~5):
        2)누수여부(O/X):
        3)부식여부(O/X):""",

    # CLI_2.py 참고 (배관 보온재)
    "Class_Pipe_condition": """1줄만. 형식 고정. 이유 설명 금지. 찢김이나 벗겨짐 등 특이사항 있는지 확인
        1) 파이프 겉 보온재 상태(양호/불량) :""",

    # CLI_3.py 참고 (누수/파손 일반)
    "Class_Water_level_gauge": """2줄만. 형식 고정. 이유 설명 금지.
        1)누수여부(O/X):
        2)파손여부(O/X):""",

    # CLI_4.py 참고 (콘센트)
    "Class_Outlet": """1줄만. 형식 고정. 이유 설명 금지. 콘센트 전원 이상 및 파손부위는 없는가?
        1)콘센트 이상 및 파손 여부(양호/불량):""",

    # CLI_5.py 참고 (전선/함체)
    "Class_Wire_condition": """1줄만. 형식 고정. 이유 설명 금지. 전선 및 전선관,접속단자 등 상태(손상,열화,변색 등) - 함 외부
        1)이상 여부(양호/불량):""",

    # CLI_6.py 참고 (소화기 정밀) - 필요시 Class_Fire 등으로 매핑
    "Class_Fire": """2줄만. 형식 고정. 이유 설명 금지. 소화기 위치가 적정한지(표시판 밑에 있어야함)와 깨짐이나 부식등이 있는지 확인
        1)소화기 위치(정상/비정상):
        2)소화기 상태(양호/불량):""",

    # 기본값 (매칭되는 게 없을 때)
    "DEFAULT": """화면의 설비 상태를 점검해주세요. 파손, 오염, 이상 여부를 3줄 이내로 요약하세요."""
}