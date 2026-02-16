import sqlite3

def check_db_schema():
    try:
        conn = sqlite3.connect('gogocar.db')
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='user_profiles'")
        schema = cursor.fetchone()
        if schema:
            print("Full schema for user_profiles:")
            print(schema[0])
        else:
            print("Table user_profiles not found")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db_schema()
