import sqlite3

def check_db():
    try:
        conn = sqlite3.connect('gogocar.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, isadmin FROM user_profiles")
        users = cursor.fetchall()
        print("Users in database:")
        for user in users:
            print(user)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
