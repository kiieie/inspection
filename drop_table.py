from database import engine
from sqlalchemy import text

def drop_table():
    with engine.connect() as conn:
        print("🗑️  Dropping inspection_point table...")
        conn.execute(text("DROP TABLE IF EXISTS inspection_point"))
        conn.commit()
    print("✅ Done.")

if __name__ == "__main__":
    drop_table()
