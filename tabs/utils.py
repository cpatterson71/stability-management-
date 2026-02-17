import streamlit as st
import sqlite3
import pandas as pd
import io
import logging
import os
import psycopg2
from dateutil.relativedelta import relativedelta
from datetime import datetime
import json
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def create_connection():
    """ create a database connection to the PostgreSQL database
    """
    logging.info("Attempting to create connection to PostgreSQL database...")
    conn = None
    try:
        db_host = os.environ.get("DB_HOST")
        db_name = os.environ.get("DB_NAME")
        db_user = os.environ.get("DB_USER")
        db_pass = os.environ.get("DB_PASS")
        db_port = os.environ.get("DB_PORT", "5432") # Ensure port is a string for logging consistently

        logging.info(f"DB_HOST: {db_host}")
        logging.info(f"DB_NAME: {db_name}")
        logging.info(f"DB_USER: {db_user}") # Be cautious with logging sensitive info in production
        logging.info(f"DB_PORT: {db_port}")
        
        # Connect to the PostgreSQL database using environment variables
        conn = psycopg2.connect(
            host=db_host,
            dbname=db_name,
            user=db_user,
            password=db_pass,
            port=db_port,
            sslmode='verify-full',
            sslrootcert='global-bundle.pem' 
        )
        logging.info("Database connection successful.")
    except Exception as e:
        st.error(f"Database connection error: Could not connect to PostgreSQL. Ensure environment variables are set correctly.")
        logging.error(f"Database connection error: {e}")
    return conn

def create_table(conn):
    """ create tables in the database
    :param conn: Connection object
    """
    logging.info("Attempting to create tables.")
    try:
        c = conn.cursor()

        # Corrected schema for PostgreSQL using SERIAL for auto-incrementing keys.
        sql_create_stability_studies_table = """ CREATE TABLE IF NOT EXISTS stability_studies (
                                        id SERIAL PRIMARY KEY,
                                        client_code text,
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
                                            id SERIAL PRIMARY KEY,
                                            study_id integer NOT NULL,
                                            storage_condition text NOT NULL,
                                            FOREIGN KEY (study_id) REFERENCES stability_studies (id) ON DELETE CASCADE
                                        );"""

        sql_create_timepoint_testing_info_table = """CREATE TABLE IF NOT EXISTS timepoint_testing_info (
                                            id SERIAL PRIMARY KEY,
                                            schedule_id integer NOT NULL,
                                            timepoint text,
                                            pull_date text NOT NULL,
                                            num_vials integer,
                                            num_copies integer,
                                            tests_to_perform text,
                                            FOREIGN KEY (schedule_id) REFERENCES storage_schedules (id) ON DELETE CASCADE
                                        );"""

        sql_create_master_tests_table = """CREATE TABLE IF NOT EXISTS master_tests (
                                            id SERIAL PRIMARY KEY,
                                            test_name text NOT NULL UNIQUE,
                                            test_method text,
                                            form_no text
                                        );"""
        
        # Drop tables before creating them to ensure schema is always fresh in development
        # c.execute("DROP TABLE IF EXISTS timepoint_testing_info;")
        # c.execute("DROP TABLE IF EXISTS storage_schedules;")
        # c.execute("DROP TABLE IF EXISTS stability_studies;")
        # c.execute("DROP TABLE IF EXISTS master_tests;")

        c.execute(sql_create_stability_studies_table)
        c.execute(sql_create_storage_schedules_table)
        c.execute(sql_create_timepoint_testing_info_table)
        c.execute(sql_create_master_tests_table)
        
        conn.commit()
        c.close()
        logging.info("Tables created successfully.")

    except Exception as e:
        st.error(f"Table creation error: {e}")
        logging.error(f"Table creation error: {e}")

def generate_schedule_dfs(selected_timepoints, selected_master_tests):
    schedule_dfs = {}
    for condition, timepoints in selected_timepoints.items():
        schedule_data = []
        for timepoint, data in timepoints.items():
            row = {
                "Time Point": timepoint,
                "Number of Vials": data['num_vials'],
                "Date Scheduled": data['pull_date'].strftime('%Y-%m-%d'),
            }
            for test in selected_master_tests:
                row[test] = ''
            schedule_data.append(row)
        
        df_schedule = pd.DataFrame(schedule_data)
        
        if not df_schedule.empty:
            cols = ["Time Point", "Number of Vials", "Date Scheduled"] + selected_master_tests
            df_schedule = df_schedule[cols]
        
        schedule_dfs[condition] = df_schedule
    return schedule_dfs

def sanitize_sheet_name(name):
    return name.replace('/', '-')

def generate_excel_from_dfs(dfs, study_details):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for condition, df in dfs.items():
            lot_number = study_details.get("Lot Number", "LXXXX")
            sanitized_condition = sanitize_sheet_name(condition)
            sheet_name = f"{lot_number} {sanitized_condition}"

            worksheet = writer.book.add_worksheet(sheet_name)
            workbook = writer.book
            header_format = workbook.add_format({'bold': True, 'valign': 'vcenter', 'align': 'center'})
            
            header_data = [
                ("Drug Product:", study_details.get("Description", "")),
                ("Storage Condition:", condition),
                ("Product No.:", study_details.get("Product No.", "")),
                ("Lot No.:", lot_number),
                ("Active Ingredient:", study_details.get("Active Content", "")),
                ("Date of Manufacture:", study_details.get("Manufacturing Date", "")),
                ("Date of T0:", study_details.get("T0 (release date)", "")),
                ("Protocol No.:", study_details.get("Protocol No.", "")),
                ("Revision:", study_details.get("Revision", "")),
                ("Specification No.:", study_details.get("Specification No.", "")),
            ]

            for row_num, (key, value) in enumerate(header_data):
                worksheet.write(row_num, 0, key, workbook.add_format({'bold': True}))
                worksheet.write(row_num, 1, value)
            
            header_row_start = len(header_data) + 1 
            master_tests_df = study_details.get("master_tests_df", pd.DataFrame())

            worksheet.merge_range(header_row_start, 0, header_row_start + 3, 0, "Time Point", header_format)
            worksheet.merge_range(header_row_start, 1, header_row_start + 3, 1, "Number of Vials", header_format)
            worksheet.merge_range(header_row_start, 2, header_row_start + 3, 2, "Date Scheduled", header_format)

            test_start_col_idx = 3
            for i, test_info in master_tests_df.iterrows():
                col_idx = test_start_col_idx + i
                worksheet.write(header_row_start + 0, col_idx, "Test", header_format)
                worksheet.write(header_row_start + 1, col_idx, test_info.get('Test', ''), header_format)
                worksheet.write(header_row_start + 2, col_idx, test_info.get('Test Method', ''), header_format)
                worksheet.write(header_row_start + 3, col_idx, test_info.get('Form No', ''), header_format)

            simple_header_row = header_row_start + 4
            simple_headers = ["Time Point", "Number of Vials", "Date Scheduled"] + master_tests_df['Test'].tolist()
            for col_num, header_name in enumerate(simple_headers):
                worksheet.write(simple_header_row, col_num, header_name, header_format)

            df.to_excel(writer, index=False, sheet_name=sheet_name, startrow=simple_header_row + 1, header=False) 
            
            fixed_columns = ["Time Point", "Number of Vials", "Date Scheduled"]
            for i, col_name in enumerate(fixed_columns):
                worksheet.set_column(i, i, len(col_name) + 5)

            for i, test_info in master_tests_df.iterrows():
                col_idx = test_start_col_idx + i
                header1 = "Test"
                header2 = str(test_info.get('Test', ''))
                header3 = str(test_info.get('Test Method', ''))
                header4 = str(test_info.get('Form No', ''))
                
                max_len = max(len(header1), len(header2), len(header3), len(header4))

                try:
                    max_len = max(max_len, df[header2].astype(str).map(len).max())
                except (KeyError, TypeError, ValueError):
                    pass
                
                column_width = min(max_len + 2, 50) 
                worksheet.set_column(col_idx, col_idx, column_width)

    return output.getvalue()