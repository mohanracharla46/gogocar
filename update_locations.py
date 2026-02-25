import sqlite3

def update_locations():
    conn = sqlite3.connect('gogocar.db')
    cursor = conn.cursor()
    try:
        # Update Chilkalurupet -> Chilakalurupet
        cursor.execute("UPDATE locations SET location = 'Chilakalurupet' WHERE location = 'Chilkalurupet'")
        
        # Insert Guntur if it doesn't exist
        cursor.execute("SELECT * FROM locations WHERE location = 'Guntur'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO locations (location) VALUES ('Guntur')")
            print("Added Guntur to locations.")
            
        conn.commit()
        print("Locations updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    update_locations()
