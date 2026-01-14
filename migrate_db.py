import sqlite3
import os
import sys

# 프로젝트 경로 추가
sys.path.insert(0, os.getcwd())
import config

def migrate():
    db_path = config.DB_CONFIG['db_path']
    print(f"🚀 Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if spatial_info column exists
        cursor.execute("PRAGMA table_info(inspection_result)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'spatial_info' not in columns:
            print("➕ Adding 'spatial_info' column to 'inspection_result' table...")
            cursor.execute("ALTER TABLE inspection_result ADD COLUMN spatial_info JSON")
            conn.commit()
            print("✅ Successfully added 'spatial_info' column.")
        else:
            print("ℹ️ 'spatial_info' column already exists.")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
