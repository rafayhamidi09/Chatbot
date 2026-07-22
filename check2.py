# Database connection test script
from DB_handling import DB_connection

def test_connection():
    try:
        conn = DB_connection()
        print("Database connection: OK")
        conn.close()
    except Exception as e:
        print(f"Database connection: FAILED - {e}")

if __name__ == "__main__":
    test_connection()
