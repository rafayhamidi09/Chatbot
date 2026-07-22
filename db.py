import psycopg2
from psycopg2 import Error, sql
from datetime import date, timedelta


class PostgresDBHandler:
    def __init__(self,
                 host="127.0.0.1",
                 dbname="mychatdb",
                 user="postgres",
                 password="2009",
                 port=5432):

        self.config = {
            "host": host,
            "database": dbname,
            "user": user,
            "password": password,
            "port": port
        }

    def _connect_raw(self):
        """Establishes a raw connection for pre-vector operations."""
        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()
        return conn, cursor

    def create_tables(self):
        print("Creating extension and tables...")
        try:
            conn, cursor = self._connect_raw()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shifts (
                    shift_id Serial primary key,
                    shift_name TEXT NOT NULL,
                    shift_start_time TIME NOT NULL,
                    shift_end_time TIME NOT NULL,
                    break_duration INTERVAL DEFAULT '01:00:00',
                    grace_period_minutes INTEGER DEFAULT 15,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS department (
                    department_id Serial primary key,
                    department_name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_department_name UNIQUE(department_name)
                );
            """)

            conn.commit()
            print("Tables created successfully.")

        except Exception as e:
            print(f"Error creating tables: {e}")
            if conn:
                conn.rollback()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


if __name__ == "__main__":
    db_handler = PostgresDBHandler()
    db_handler.create_tables()
    print("Database handler initialized successfully!")
