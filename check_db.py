import sqlite3

def check_db():
    try:
        conn = sqlite3.connect('gogocar.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = cursor.fetchall()
        print("Columns in user_profiles:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
