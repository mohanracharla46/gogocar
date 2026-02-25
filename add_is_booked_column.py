"""
Migration script to add is_booked column to the cars table
"""
import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'gogocar.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(cars)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_booked' not in columns:
            cursor.execute("ALTER TABLE cars ADD COLUMN is_booked BOOLEAN NOT NULL DEFAULT 0")
            print("Added is_booked column")
        else:
            print("is_booked column already exists")
        
        conn.commit()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
