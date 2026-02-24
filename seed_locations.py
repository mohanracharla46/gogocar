
import sqlite3

def seed_locations():
    conn = sqlite3.connect('gogocar.db')
    cursor = conn.cursor()
    try:
        # Check if locations exist
        cursor.execute("SELECT location FROM locations WHERE location IN ('Madhapur (HYD)', 'Chilkalurupet')")
        existing = [row[0] for row in cursor.fetchall()]
        
        if 'Madhapur (HYD)' not in existing:
            cursor.execute("INSERT INTO locations (location) VALUES ('Madhapur (HYD)')")
            print("Added Madhapur (HYD)")
        
        if 'Chilkalurupet' not in existing:
            cursor.execute("INSERT INTO locations (location) VALUES ('Chilkalurupet')")
            print("Added Chilkalurupet")
            
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_locations()
