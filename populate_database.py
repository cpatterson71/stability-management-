import openpyxl
import sqlite3
import pandas as pd
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io
import logging

def read_excel_with_openpyxl(filename, sheet_name, header_row, data_start_row):
    """
    Reads an Excel sheet into a pandas DataFrame using openpyxl,
    starting from a specific row for the header and data.
    """
    workbook = openpyxl.load_workbook(filename, data_only=True)
    sheet = workbook[sheet_name]
    
    # Extract headers from the header_row
    headers = [cell.value for cell in sheet[header_row]]
    
    # Extract data from the rows following the header row
    data = []
    for row in sheet.iter_rows(min_row=data_start_row, values_only=True):
        data.append(list(row))
        
    df = pd.DataFrame(data, columns=headers)
    return df

# Configure logging
logging.basicConfig(filename='populate_db_log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"Successfully connected to {db_file}")
    except sqlite3.Error as e:
        print(e)
        logging.error(e)

    return conn

def create_table(conn):
    """ create tables from the create_table_sql statements
    :param conn: Connection object
    :return:
    """
    try:
        c = conn.cursor()

        sql_create_stability_studies_table = """ CREATE TABLE IF NOT EXISTS stability_studies (
                                        id integer PRIMARY KEY,
                                        description text NOT NULL,
                                        active_content text,
                                        drug_product integer,
                                        drug_substance integer,
                                        lot_number text NOT NULL,
                                        manufacturing_date text,
                                        t0_release_date text,
                                        packaging1_supplier_part_number text,
                                        packaging1_description text,
                                        packaging1_supplier text,
                                        packaging2_supplier_part_number text,
                                        packaging2_description text,
                                        packaging2_supplier text,
                                        product_no text,
                                        protocol_no text,
                                        revision text,
                                        specification_no text
                                    ); """
        
        sql_create_storage_schedules_table = """CREATE TABLE IF NOT EXISTS storage_schedules (
                                            id integer PRIMARY KEY,
                                            study_id integer NOT NULL,
                                            storage_condition text NOT NULL,
                                            FOREIGN KEY (study_id) REFERENCES stability_studies (id)
                                        );"""

        sql_create_timepoint_testing_info_table = """CREATE TABLE IF NOT EXISTS timepoint_testing_info (
                                            id integer PRIMARY KEY,
                                            schedule_id integer NOT NULL,
                                            timepoint text,
                                            pull_date text NOT NULL,
                                            num_vials integer,
                                            tests_to_perform text,
                                            FOREIGN KEY (schedule_id) REFERENCES storage_schedules (id)
                                        );"""

        c.execute("DROP TABLE IF EXISTS stability_studies;")
        c.execute(sql_create_stability_studies_table)
        c.execute("DROP TABLE IF EXISTS storage_schedules;")
        c.execute(sql_create_storage_schedules_table)
        c.execute("DROP TABLE IF EXISTS timepoint_testing_info;")
        c.execute(sql_create_timepoint_testing_info_table)
        print("Tables created successfully.")
    except sqlite3.Error as e:
        print(e)
        logging.error(e)

def main():
    database = "stability_studies.db"
    excel_file = r"C:\Users\carlp\OneDrive\Desktop\AI_Projects\AI_Stability_Application\stability_schedule_template (2).xlsx"

    # --- Create a connection to the database ---
    conn = create_connection(database)
    if conn is None:
        return
        
    # --- Create tables ---
    create_table(conn)

    # --- In a real scenario, you'd get these from the app or another source ---
    # For this script, we'll use some placeholder values.
    # In a future step, we could read these from a config file or the excel file itself.
    study_details = {
        "description": "Test Study from Script",
        "active_content": "Test Content",
        "drug_product": 1,
        "drug_substance": 0,
        "lot_number": "LPI2024206",
        "manufacturing_date": "2024-01-01",
        "t0_release_date": "2024-01-15",
        "packaging1_supplier_part_number": "P1-SPN",
        "packaging1_description": "P1-Desc",
        "packaging1_supplier": "P1-Supp",
        "packaging2_supplier_part_number": "P2-SPN",
        "packaging2_description": "P2-Desc",
        "packaging2_supplier": "P2-Supp",
        "product_no": "PN-123",
        "protocol_no": "PRO-456",
        "revision": "01",
        "specification_no": "SPEC-789"
    }

    print("--- Starting Database Population ---")
    logging.info("--- Starting Database Population ---")

    try:
        # --- 1. Save the main study info ---
        sql_study = ''' INSERT INTO stability_studies(
                                description, active_content, drug_product, drug_substance, lot_number, manufacturing_date, t0_release_date,
                                packaging1_supplier_part_number, packaging1_description, packaging1_supplier,
                                packaging2_supplier_part_number, packaging2_description, packaging2_supplier,
                                product_no, protocol_no, revision, specification_no
                            )
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql_study, tuple(study_details.values()))
        study_id = cur.lastrowid
        print(f"Inserted study with ID: {study_id}")
        logging.info(f"Inserted study with ID: {study_id}")

        # --- 2. Read and save schedules from the uploaded excel file ---
        xls = pd.ExcelFile(excel_file)
        
        sql_schedule = '''INSERT INTO storage_schedules(study_id, storage_condition) VALUES(?,?)'''
        sql_timepoint_info = '''INSERT INTO timepoint_testing_info(schedule_id, timepoint, pull_date, num_vials, tests_to_perform) VALUES(?,?,?,?,?)'''
        
        # Assume the conditions are the sheet names for simplicity
        for sheet_name in xls.sheet_names:
            print(f"Processing sheet: {sheet_name}")
            logging.info(f"Processing sheet: {sheet_name}")

            condition = sheet_name 

            df = read_excel_with_openpyxl(excel_file, sheet_name, header_row=16, data_start_row=17)
            
            print(f"DataFrame columns for sheet '{sheet_name}': {df.columns.tolist()}")
            logging.info(f"DataFrame columns for sheet '{sheet_name}': {df.columns.tolist()}")
            
            available_tests = [col for col in df.columns if col not in ['Time Point', 'Number of Vials', 'Date Scheduled']]
            
            cur.execute(sql_schedule, (study_id, condition))
            schedule_id = cur.lastrowid
            print(f"  - Created schedule_id: {schedule_id} for condition: {condition}")
            logging.info(f"  - Created schedule_id: {schedule_id} for condition: {condition}")
            
            for index, row in df.iterrows():
                tests_to_perform = [test for test in available_tests if str(row.get(test, '')).strip()]
                tests_str = json.dumps(tests_to_perform)
                
                pull_date_str = pd.to_datetime(row['Date Scheduled']).strftime('%Y-%m-%d')
                
                cur.execute(sql_timepoint_info, (
                    schedule_id,
                    row['Time Point'],
                    pull_date_str,
                    row['Number of Vials'],
                    tests_str
                ))
        
        conn.commit()
        print("--- Database Population Complete ---")
        logging.info("--- Database Population Complete ---")

    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"An error occurred during database population: {e}", exc_info=True)
        conn.rollback() # Rollback changes on error
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    main()