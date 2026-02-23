import os
import psycopg2
from dotenv import load_dotenv

def test_connection():
    """Tests the database connection using credentials from .env file."""
    print("Attempting to load environment variables from .env file...")
    # Navigate up one directory to find the .env file in the parent AI_Projects folder if not in current
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(dotenv_path):
        print(f"No .env file found at {dotenv_path}")
        # Try one level up
        parent_dir_dotenv = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(parent_dir_dotenv):
             dotenv_path = parent_dir_dotenv
        else:
             print("No .env found in parent directory either. Please check file location.")
             return


    load_dotenv(dotenv_path=dotenv_path)
    
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_port = os.getenv("DB_PORT")

    if not all([db_host, db_name, db_user, db_pass, db_port]):
        print("Error: One or more required database environment variables are not set.")
        print(f"DB_HOST: {'Set' if db_host else 'Not Set'}")
        print(f"DB_NAME: {'Set' if db_name else 'Not Set'}")
        print(f"DB_USER: {'Set' if db_user else 'Not Set'}")
        print(f"DB_PASS: {'Set' if db_pass else 'Not Set'}")
        print(f"DB_PORT: {'Set' if db_port else 'Not Set'}")
        return

    print(f"Attempting to connect to database at {db_host}...")

    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pass,
            port=db_port,
            connect_timeout=10  # 10-second timeout
        )
        print("✅ SUCCESS: Database connection established successfully!")
        conn.close()
    except psycopg2.OperationalError as e:
        print("❌ FAILURE: Could not connect to the database.")
        print("This is likely a network issue.")
        print("Please verify the following:")
        print("1. Your current IP address is authorized in the AWS RDS instance's security group.")
        print("2. The DB_HOST and DB_PORT are correct.")
        print(f"\nError details: {e}")
    except Exception as e:
        print(f"❌ FAILURE: An unexpected error occurred: {e}")
        print("This could be due to incorrect credentials (user, password, dbname). Please double-check them.")

if __name__ == "__main__":
    test_connection()
