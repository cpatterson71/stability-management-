
import sqlite3
import pandas as pd
import os

def inspect_database(db_file):
    if not os.path.exists(db_file):
        print(f"Database file not found at: {db_file}")
        return

    conn = sqlite3.connect(db_file)
    
    print("--- Inspecting Database ---")

    try:
        print("\n[stability_studies table]")
        df_studies = pd.read_sql_query("SELECT * FROM stability_studies", conn)
        print(df_studies.to_string())
    except Exception as e:
        print(f"Could not read 'stability_studies' table: {e}")

    try:
        print("\n[storage_schedules table]")
        df_schedules = pd.read_sql_query("SELECT * FROM storage_schedules", conn)
        print(df_schedules.to_string())
    except Exception as e:
        print(f"Could not read 'storage_schedules' table: {e}")

    try:
        print("\n[master_tests table]")
        df_master_tests = pd.read_sql_query("SELECT * FROM master_tests", conn)
        print(df_master_tests.to_string())
    except Exception as e:
        print(f"Could not read 'master_tests' table: {e}")

    try:
        print("\n[timepoint_testing_info table]")
        df_timepoints = pd.read_sql_query("SELECT * FROM timepoint_testing_info", conn)
        print(df_timepoints.to_string())
    except Exception as e:
        print(f"Could not read 'timepoint_testing_info' table: {e}")
        
    print("\n--- Inspection Complete ---")

    conn.close()

if __name__ == '__main__':
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stability_studies.db")
    inspect_database(db_path)
