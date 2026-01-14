import streamlit as st
import pandas as pd
import os
import logging
from dotenv import load_dotenv

from tabs.utils import create_connection, create_table
from tabs.tab1_setup import show_setup_tab
from tabs.tab2_schedule import show_schedule_tab
from tabs.tab3_summary import show_summary_tab

# Load environment variables from .env file
load_dotenv()

st.set_page_config(page_title="Stability Study Management", layout="wide")

# Configure logging to output to the console
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("--- app.py script started ---")

def main():
    logging.info("--- main() function started ---")
    st.title("Stability Study Management")

    # --- Initialize Session State ---
    # This ensures that session state variables are available to all tabs from the start.
    if 'master_tests_df' not in st.session_state:
        st.session_state.master_tests_df = pd.DataFrame()
    if 'completed_schedule' not in st.session_state:
        st.session_state.completed_schedule = None
    if 'ss_search_results' not in st.session_state:
        st.session_state.ss_search_results = []
    if 's3_search_results' not in st.session_state:
        st.session_state.s3_search_results = []
    if 'confirm_replace' not in st.session_state:
        st.session_state.confirm_replace = None
    if 'uploaded_file_data' not in st.session_state:
        st.session_state.uploaded_file_data = None
    if 'schedule_df' not in st.session_state:
        st.session_state.schedule_df = pd.DataFrame()
    if 'df_display' not in st.session_state:
        st.session_state.df_display = pd.DataFrame()
    if 'filtered_schedule_df' not in st.session_state:
        st.session_state.filtered_schedule_df = pd.DataFrame()
    if 'docs_to_download' not in st.session_state:
        st.session_state.docs_to_download = {}

    # --- Database Connection ---
    conn = create_connection()

    if conn is not None:
        create_table(conn)
        logging.info("Database connection and table creation complete.")
        
        # Load master tests from the database on startup if not already loaded
        if st.session_state.master_tests_df.empty:
            try:
                st.session_state.master_tests_df = pd.read_sql_query("SELECT test_name AS 'Test', test_method AS 'Test Method', form_no AS 'Form No' FROM master_tests", conn)
                logging.info("Master tests loaded from database into session state.")
            except Exception as e:
                logging.error(f"Could not load master tests from database: {e}")
                st.session_state.master_tests_df = pd.DataFrame() # Ensure it's a dataframe
    else:
        st.error("Error! Cannot create the database connection.")
        logging.error("Failed to create database connection. Stopping.")
        st.stop()

    # --- Tabbed Interface ---
    logging.info("Defining tabs.")
    tab1, tab2, tab3 = st.tabs(["Stability Study Setup", "Stability Schedule", "Stability Summary"])

    with tab1:
        show_setup_tab(conn)

    with tab2:
        show_schedule_tab(conn)

    with tab3:
        show_summary_tab()

    # Close the connection at the end of the script run
    if conn is not None:
        conn.close()
        logging.info("Database connection closed.")

if __name__ == '__main__':
    logging.info("--- Script is being run directly ---")
    main()