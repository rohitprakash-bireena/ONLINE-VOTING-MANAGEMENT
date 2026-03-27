import os
import mysql.connector


def require_env(name):
    value = os.getenv(name)
    if value is None or value.strip() == '':
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# ==========================================
# Database Connection Function
# ==========================================
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=require_env("DB_HOST"),
            user=require_env("DB_USER"),
            password=require_env("DB_PASSWORD"),
            database=require_env("DB_NAME"),
            port=int(require_env("DB_PORT"))
        )
        return connection
    except (mysql.connector.Error, RuntimeError, ValueError) as err:
        print(f"Database Error: {err}")
        return None