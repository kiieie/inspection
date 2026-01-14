from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import config

# [database.py] SQLAlchemy 연결 및 엔진 설정
# config.py에 정의된 경로를 사용합니다.
DATABASE_URL = f"sqlite:///{config.DB_CONFIG['db_path']}"

# 엔진 생성 (SQLite의 경우 check_same_thread=False 설정 필요)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 세션 생성기
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 정의 (models.py에서 상속받음)
Base = declarative_base()

def get_db():
    """데이터베이스 세션을 생성하고 종료를 관리하는 의존성 주입 함수"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
