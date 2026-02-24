
import sqlite3

def check_locations():
    conn = sqlite3.connect('gogocar.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM locations")
        rows = cursor.fetchall()
        print("Locations in DB:")
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_locations()
