"""
Migration script to add is_top_selling and is_premium columns to the cars table
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('gogocar.db')
    cursor = conn.cursor()
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(cars)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_top_selling' not in columns:
            cursor.execute("ALTER TABLE cars ADD COLUMN is_top_selling BOOLEAN NOT NULL DEFAULT 0")
            print("Added is_top_selling column")
        else:
            print("is_top_selling column already exists")
        
        if 'is_premium' not in columns:
            cursor.execute("ALTER TABLE cars ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT 0")
            print("Added is_premium column")
        else:
            print("is_premium column already exists")
        
        conn.commit()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
