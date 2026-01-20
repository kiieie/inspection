from sqlalchemy import ( Column, Integer, Float, String, DateTime, Time,
                         Text, Boolean, Enum, ForeignKey, Date, JSON )
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from datetime import datetime
from enum import Enum as PyEnum
import random
from sqlalchemy.orm import validates


# Enum for the robot type
class RobotType(PyEnum):
    Spot = "Spot"
    Ros = "Ros"  # This now matches the frontend input
    Etc = "Etc"

# Robot table
class Robot(Base):
    __tablename__ = "robot"

    id = Column(Integer, primary_key=True)
    site = Column(String, nullable=True)
    robottype = Column(Enum(RobotType), nullable=False) # it is added
    robotname = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    rosDomainID = Column(Integer, nullable=True)
    ptz_module = Column(Boolean, nullable=True)

# --------------------------------------------------------------------------------

# Spot autowalk mission table
class Mission(Base):
    __tablename__ = "mission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site: Mapped[str | None] = mapped_column(String, nullable=True)
    missionname: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    waypoints: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True, default=[])
    edges: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True, default=[])
    obstacles: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True, default=[])
    optimal_route: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    reference_map: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_fiducial_position_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_fiducial_position_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_pixels_per_meter: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_rot: Mapped[float | None] = mapped_column(Float, nullable=True)
    canvas_offset_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    canvas_offset_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    canvas_scale: Mapped[float | None] = mapped_column(Float, nullable=True)
    canvas_rotation: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_info: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True, default=None)

# --------------------------------------------------------------------------------

# Enum for the mission state
class MissionState(PyEnum):
    scheduled = "Scheduled"
    in_progress = "In Progress"
    completed = "Completed"
    failed = "Failed"

# Schedule table
class Schedule(Base):
    __tablename__ = "schedule"
    
    id = Column(Integer, primary_key=True)
    site = Column(String, nullable=True)
    robot_name = Column(String, nullable=False)
    mission_name = Column(String, nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    period = Column(Integer, nullable=False) # inspection period in days
    state = Column(Enum(MissionState), default=MissionState.scheduled)
    color = Column(String, nullable=True) # Random color for display in the calendar
    last_modified = Column(DateTime, default=datetime.utcnow)
    activation = Column(String, nullable=False)
    
    def generate_random_color(self):
        # Simple function to generate a random color for the calendar
        return f"#{random.randint(0, 0xFFFFFF):06x}"

class MissionResultState(PyEnum):
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUEUED = "QUEUED"
    STOPPED = "STOPPED"
    DATA_ACQUIRED = "DATA_ACQUIRED"
    
# Schedule mission table
class MissionResult(Base):
    __tablename__ = "mission_result"
    id = Column(Integer, primary_key=True)
    site = Column(String, nullable=False)
    robot_name = Column(String, nullable=False)
    mission_name = Column(String, nullable=False)
    scheduled_datetime = Column(DateTime, nullable=False)
    actual_start_datetime = Column(DateTime, nullable=True)
    actual_end_datetime = Column(DateTime, nullable=True)
    start_soc = Column(Integer, nullable=True)
    end_soc = Column(Integer, nullable=True)
    state = Column(Enum(MissionResultState), default=MissionState.scheduled)
    result = Column(String, nullable=True)
    activation = Column(String, nullable=True)

# --------------------------------------------------------------------------------

# inspection point table
class InspectionPoint(Base):
    __tablename__ = "inspection_point"
    id = Column(Integer, primary_key=True)
    site = Column(String, nullable=False)
    mission_name = Column(String, nullable=False)
    inspection_name = Column(String, nullable=False)
    facility_1 = Column(String, nullable=True)
    facility_2 = Column(String, nullable=True)
    inspection_point_type = Column(String, nullable=True)
    model_type = Column(String, nullable=True)
    model_ver = Column(String, nullable=True)
    hyperparameter = Column(JSON, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    normal_min_value = Column(Float, nullable=True)
    normal_max_value = Column(Float, nullable=True)
    comment = Column(String, nullable=True)
    
    # [Report & Extra Columns] 엑셀의 모든 추가 데이터를 수용하기 위한 필드
    report_name = Column(String, nullable=True)
    inspection_details = Column(String, nullable=True)      # 점검 세부 내용
    inspection_period = Column(String, nullable=True)       # 점검 주기
    insepction_cell_number = Column(String, nullable=True)  # 엑셀 셀 번호 (원문 오타 유지)
    query = Column(String, nullable=True)                   # VLM 질의용 쿼리
    sort_key = Column(String, nullable=True)                # 정렬 키
    
    report_info = Column(JSON, nullable=True)               # 기타 유동적 정보 (JSON)

# --------------------------------------------------------------------------------

# inspection result table
class InspectionResult(Base):
    __tablename__ = "inspection_result"
    id = Column(Integer, primary_key=True)
    
    # [Point Master Data - Snapshot] InspectionPoint의 모든 필드 포함 (2026-01-13 고도화)
    site = Column(String, nullable=False)
    mission_name = Column(String, nullable=False)
    inspection_name = Column(String, nullable=False)
    facility_1 = Column(String, nullable=True)
    facility_2 = Column(String, nullable=True)
    inspection_point_type = Column(String, nullable=True)
    model_type = Column(String, nullable=True)
    model_ver = Column(String, nullable=True)
    hyperparameter = Column(JSON, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    normal_min_value = Column(Float, nullable=True)
    normal_max_value = Column(Float, nullable=True)
    comment_master = Column(String, nullable=True) # Point의 comment와 구분
    report_name = Column(String, nullable=True)
    inspection_details = Column(String, nullable=True)
    inspection_period = Column(String, nullable=True)
    insepction_cell_number = Column(String, nullable=True)
    query = Column(String, nullable=True)
    sort_key = Column(String, nullable=True)
    
    # [Inspection Actual Data] 진단 실측 정보
    inspection_datetime = Column(DateTime, nullable=False, default=datetime.now)
    result_value = Column(String, nullable=True)    # 판독 수치 또는 상태 (영어 정규화)
    judgement = Column(String, nullable=True)       # PASS / FAIL
    comment_result = Column(String, nullable=True)  # 진단 시 특이사항
    
    inspection_point_id = Column(Integer, nullable=True) # 마스터 ID 참조
    data_raw_dir = Column(String, nullable=True)         # 원본 이미지 절대 경로
    data_result_dir = Column(String, nullable=True)      # 결과 이미지 절대 경로
    spatial_info = Column(JSON, nullable=True)           # 공간 정보 (Bounding Box 등)
    # mission_id = Column(String, nullable=True)

# --------------------------------------------------------------------------------

# user table
class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    level = Column(Integer, nullable=False)
    site = Column(JSON, nullable=True, default=[])
    last_modified = Column(DateTime, default=datetime.utcnow)

# --------------------------------------------------------------------------------


class ModelType(PyEnum):
    Gauge = "Gauge"
    Falldown = "Falldown"
    SafetyHelmet = "Safety Helmet"

class ModelSize(PyEnum):
    Small = "Small"
    Medium = "Medium"
    Large = "Large"

# --------------------------------------------------------------------------------

# log table
class EventLog(Base):
    __tablename__ = "event_log"
    id = Column(Integer, primary_key=True)
    site = Column(String, nullable=False)
    robotname = Column(String, nullable=False)
    type = Column(String, nullable=False) #정상, 경보, 에러
    keyword = Column(String, nullable=False)
    content = Column(String, nullable=None)
    event_time = Column(DateTime, default=datetime.utcnow)

# --------------------------------------------------------------------------------

# 🚩 Inspection Report Metadata table
class ReportMetadata(Base):
    """
    점검 리포트 양식의 메타데이터 및 DB-엑셀 매핑 정보를 저장합니다.
    이를 통해 서버에서 엑셀 파일에 데이터를 동적으로 채울 수 있습니다.
    """
    __tablename__ = "report_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # 보고서 식별 정보
    category: Mapped[str] = mapped_column(String, nullable=False) # 예: "electrical", "fire_protection"
    report_name: Mapped[str] = mapped_column(String, nullable=False, unique=True) # 예: "UPS 무정전전원장치 점검일지"
    template_filename: Mapped[str] = mapped_column(String, nullable=False) # 서버에 저장된 엑셀 파일명 (예: "UPS_Checklist_v1.xlsx")
    
    # 엑셀 조작 및 매핑 설정
    # 단일 값 (점검일, 점검자 등)의 DB 키와 엑셀 셀 주소 매핑 정보
    metadata_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True, default={}) 
    
    # 반복되는 점검 항목 데이터 테이블에 대한 설정
    table_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default={})

class DiagnosisState(PyEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

# data table
class InspectionData(Base):
    __tablename__ = "inspection_data"
    id = Column(Integer, primary_key=True)
    site = Column(String, nullable=False)
    mission_name = Column(String, nullable=False)
    inspection_name = Column(String, nullable=True) # Added
    inspection_time = Column(DateTime, default=datetime.utcnow)
    data_raw_dir = Column(String, nullable=False)
    data_result_dir = Column(String, nullable=False)
    state = Column(Enum(DiagnosisState), default=DiagnosisState.QUEUED)