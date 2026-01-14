import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import logging
from .utils import generate_schedule_dfs, generate_excel_from_dfs, sanitize_sheet_name

def show_setup_tab(conn):
    logging.info("Entering Tab 1: Stability Study Setup")
    st.header("Stability Study Setup")

    selected_master_tests = st.session_state.master_tests_df['Test'].tolist()
    
    client_code_input = st.text_input("Client Code")
    desc_input = st.text_input("Description")
    active_content_input = st.text_input("Active Content")
    dp_checkbox = st.checkbox("Drug Product (DP)")
    ds_checkbox = st.checkbox("Drug Substance (DS)")
    lot_number_input = st.text_input("Lot Number")
    product_no_input = st.text_input("Product No.")
    protocol_no_input = st.text_input("Protocol No.")
    revision_input = st.text_input("Revision")
    spec_no_input = st.text_input("Specification No.")
    mfg_date_input = st.date_input("Manufacturing Date", datetime.today().date())
    t0_release_date_input = st.date_input("T0 (release date)", datetime.today().date())
    
    with st.expander("Packaging (primary only)", expanded=True):
        packaging_data = [
            {"Supplier Part Number": "", "Description": "", "Supplier": ""},
            {"Supplier Part Number": "", "Description": "", "Supplier": ""}
        ]
        edited_packaging_df = st.data_editor(
            pd.DataFrame(packaging_data),
            key="packaging_editor",
            hide_index=True,
            num_rows="dynamic"
        )
        # Get data from the edited table
        p1_spn_input = edited_packaging_df.iloc[0]["Supplier Part Number"] if len(edited_packaging_df) > 0 else ""
        p1_desc_input = edited_packaging_df.iloc[0]["Description"] if len(edited_packaging_df) > 0 else ""
        p1_supp_input = edited_packaging_df.iloc[0]["Supplier"] if len(edited_packaging_df) > 0 else ""
        p2_spn_input = edited_packaging_df.iloc[1]["Supplier Part Number"] if len(edited_packaging_df) > 1 else ""
        p2_desc_input = edited_packaging_df.iloc[1]["Description"] if len(edited_packaging_df) > 1 else ""
        p2_supp_input = edited_packaging_df.iloc[1]["Supplier"] if len(edited_packaging_df) > 1 else ""

    with st.expander("Storage Conditions and Timepoints Selection", expanded=True):
        selected_conditions = []
        cond_map = {
            "5°C": "cond_5c",
            "-20°C": "cond_minus_20c",
            "25°C / 60% RH": "cond_25c_60rh",
            "30°C / 65% RH": "cond_30c_65rh",
            "40°C / 75% RH": "cond_40c_75rh"
        }
        for cond, key in cond_map.items():
            if st.checkbox(cond, key=key):
                selected_conditions.append(cond)

        if selected_conditions:
            st.markdown("---")
            tabs = st.tabs([sanitize_sheet_name(c) for c in selected_conditions])
            
            selected_timepoints = {}

            for i, condition in enumerate(selected_conditions):
                with tabs[i]:
                    timepoints_dict = {
                        "1 month": 1, "2 months": 2, "3 months": 3, "6 months": 6,
                        "12 months": 12, "18 months": 18, "24 months": 24, "36 months": 36
                    }
                    condition_timepoints = {}
                    
                    col1, col2, col3 = st.columns([2,2,1])
                    with col1:
                        st.write("Timepoint")
                    with col2:
                        st.write("Pull Date")
                    with col3:
                        st.write("Number of Vials")

                    for timepoint, months in timepoints_dict.items():
                        col1, col2, col3 = st.columns([2,2,1])
                        with col1:
                            selected = st.checkbox(timepoint, key=f"tp_select_{condition}_{months}")
                        if selected:
                            with col2:
                                pull_date = st.date_input("Pull Date", value=t0_release_date_input + relativedelta(months=months), key=f"pull_date_{condition}_{timepoint}", label_visibility="collapsed")
                            with col3:
                                num_vials = st.number_input("Number of Vials", min_value=1, value=1, key=f"num_vials_{condition}_{timepoint}", label_visibility="collapsed")
                            condition_timepoints[timepoint] = {"months": months, "pull_date": pull_date, "num_vials": num_vials}
                    
                    selected_timepoints[condition] = condition_timepoints

    with st.expander("Step 1: Define Master Tests", expanded=True):
        master_test_file = st.file_uploader("Upload Master Test Document", type=['xlsx'], key="master_test_uploader")

        if master_test_file is not None:
            try:
                df = pd.read_excel(master_test_file)
                if not df.empty:
                    
                    # --- Ensure target columns exist ---
                    # Create a copy to avoid SettingWithCopyWarning
                    processed_df = df.copy() 

                    # Ensure 'Test' column exists and is not empty to proceed
                    if 'Test' not in processed_df.columns or processed_df['Test'].empty:
                        st.warning("No 'Test' column found in the Excel file or it is empty. Skipping file processing.")
                        return # Exit if no valid 'Test' column

                    # Standardize 'Test Method'
                    if 'Test Method' not in processed_df.columns:
                        processed_df['Test Method'] = ''
                    
                    # Standardize 'Form No' logic
                    if 'Form No' not in processed_df.columns:
                        processed_df['Form No'] = '' # Initialize if missing
                    
                    # If 'Form #' exists, copy its content to 'Form No'
                    if 'Form #' in processed_df.columns and not processed_df['Form #'].empty:
                        processed_df['Form No'] = processed_df['Form #']
                        # Optionally drop the original 'Form #' to keep df clean, if desired
                        # processed_df.drop(columns=['Form #'], inplace=True)

                    # --- Save to database ---
                    cur = conn.cursor()
                    for index, row in processed_df.iterrows(): # Iterate over processed_df
                        # Using INSERT OR IGNORE to avoid duplicates on test_name
                        cur.execute("INSERT INTO master_tests (test_name, test_method, form_no) VALUES (%s, %s, %s) ON CONFLICT (test_name) DO NOTHING",
                                    (row['Test'], row['Test Method'], row['Form No']))
                    conn.commit()
                    
                    # Reload from DB to ensure session state is up-to-date
                    st.session_state.master_tests_df = pd.read_sql_query("SELECT test_name AS 'Test', test_method AS 'Test Method', form_no AS 'Form No' FROM master_tests", conn)

                    st.write("**Master Test Methods (loaded from database):**")
                    st.dataframe(st.session_state.master_tests_df, hide_index=True)
                else:
                    st.warning("The uploaded Excel file is empty or does not contain a valid table.")
            except Exception as e:
                st.error(f"Error reading Excel file or saving to DB: {e}")
                # Attempt to load from DB anyway, in case it was a DB error but data exists
                try:
                    st.session_state.master_tests_df = pd.read_sql_query("SELECT test_name AS 'Test', test_method AS 'Test Method', form_no AS 'Form No' FROM master_tests", conn)
                except Exception as db_e:
                    st.error(f"Could not load master tests from database: {db_e}")
                    st.session_state.master_tests_df = pd.DataFrame()

    if st.session_state.master_tests_df.empty:
        st.warning("Please upload a valid master test document to proceed.")
        st.info("Currently, no master tests are stored in the database.")
        st.stop()
    
    if 'selected_timepoints' in locals() and selected_timepoints:
        schedule_dfs = generate_schedule_dfs(selected_timepoints, selected_master_tests)

        if st.button("Generate Excel File"):
            study_details = {
                "Description": desc_input,
                "Active Content": active_content_input,
                "Lot Number": lot_number_input,
                "Product No.": product_no_input,
                "Protocol No.": protocol_no_input,
                "Revision": revision_input,
                "Specification No.": spec_no_input,
                "Manufacturing Date": mfg_date_input.strftime('%Y-%m-%d'),
                "T0 (release date)": t0_release_date_input.strftime('%Y-%m-%d'),
                "master_tests_df": st.session_state.master_tests_df
            }
            excel_data = generate_excel_from_dfs(schedule_dfs, study_details)

            st.download_button(
                label="📥 Download Schedule Template",
                data=excel_data,
                file_name="stability_schedule_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        completed_schedule_file = st.file_uploader("Upload Completed Schedule", type=['xlsx'])

        if completed_schedule_file is not None:
            try:
                xls = pd.ExcelFile(completed_schedule_file)
                schedule_data = {}
                
                ordered_test_list = st.session_state.master_tests_df['Test'].tolist()

                for sheet_name in xls.sheet_names:
                    df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                    
                    header_row_index = -1
                    for i, row in df_sheet.iterrows():
                        if str(row.iloc[0]).strip() == "Time Point":
                            header_row_index = i
                            break
                    
                    if header_row_index != -1:
                        data_df = df_sheet.iloc[header_row_index + 1:].copy()
                        data_df.columns = ["Time Point", "Number of Vials", "Date Scheduled"] + data_df.columns[3:].tolist()

                        original_condition = None
                        for cond in selected_conditions:
                            sanitized_cond = sanitize_sheet_name(cond)
                            if sheet_name.endswith(sanitized_cond):
                                original_condition = cond
                                break 
                        
                        if original_condition:
                            records = []
                            for index, row in data_df.iterrows():
                                record = {
                                    "Time Point": row["Time Point"],
                                    "Number of Vials": row["Number of Vials"],
                                    "Date Scheduled": row["Date Scheduled"],
                                }
                                tests_for_this_row = []
                                for i in range(3, len(row)):
                                    if str(row.iloc[i]).strip():
                                        test_index = i - 3
                                        if test_index < len(ordered_test_list):
                                            tests_for_this_row.append(ordered_test_list[test_index])
                                record['tests_to_perform'] = tests_for_this_row
                                records.append(record)
                            schedule_data[original_condition] = records
                        else:
                            st.warning(f"Could not map sheet '{sheet_name}' to any selected condition. Skipping sheet.")
                    else:
                        st.warning(f"Could not find header row with 'Time Point' in sheet '{sheet_name}'. Skipping sheet.")
                
                st.session_state.completed_schedule = schedule_data
                st.success("Completed schedule uploaded and parsed successfully!")

            except Exception as e:
                st.error(f"Error reading completed schedule file: {e}")
                logging.error(f"Error parsing completed schedule: {e}", exc_info=True)

    if st.button("Save Study"):
        if conn is not None and st.session_state.get('completed_schedule') is not None:
            try:
                master_tests_from_db_df = pd.read_sql_query("SELECT test_name FROM master_tests", conn)
                master_test_list = master_tests_from_db_df['test_name'].tolist()
                cur = conn.cursor()
                cur.execute("SELECT id FROM stability_studies WHERE lot_number = %s", (lot_number_input,))
                existing_study = cur.fetchone()

                if existing_study:
                    st.warning(f"Lot Number {lot_number_input} already exists. Overwriting its data.")
                    study_id = existing_study[0]
                    
                    dp_val = 1 if dp_checkbox else 0
                    ds_val = 1 if ds_checkbox else 0
                    sql_study_update = ''' UPDATE stability_studies SET
                                            client_code = %s, description = %s, active_content = %s, drug_product = %s, drug_substance = %s, 
                                            manufacturing_date = %s, t0_release_date = %s, packaging1_supplier_part_number = %s, 
                                            packaging1_description = %s, packaging1_supplier = %s, packaging2_supplier_part_number = %s, 
                                            packaging2_description = %s, packaging2_supplier = %s, product_no = %s, protocol_no = %s, 
                                            revision = %s, specification_no = %s
                                          WHERE id = %s '''
                    cur.execute(sql_study_update, (
                        client_code_input, desc_input, active_content_input, dp_val, ds_val,
                        mfg_date_input.strftime('%Y-%m-%d'), t0_release_date_input.strftime('%Y-%m-%d'),
                        p1_spn_input, p1_desc_input, p1_supp_input, p2_spn_input, p2_desc_input, p2_supp_input,
                        product_no_input, protocol_no_input, revision_input, spec_no_input, study_id
                    ))

                    cur.execute("DELETE FROM timepoint_testing_info WHERE schedule_id IN (SELECT id FROM storage_schedules WHERE study_id = %s)", (study_id,))
                    cur.execute("DELETE FROM storage_schedules WHERE study_id = %s", (study_id,))
                else:
                    dp_val = 1 if dp_checkbox else 0
                    ds_val = 1 if ds_checkbox else 0
                    sql_study_insert = ''' INSERT INTO stability_studies(
                                                client_code, description, active_content, drug_product, drug_substance, lot_number, manufacturing_date, t0_release_date,
                                                packaging1_supplier_part_number, packaging1_description, packaging1_supplier,
                                                packaging2_supplier_part_number, packaging2_description, packaging2_supplier,
                                                product_no, protocol_no, revision, specification_no
                                            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '''
                    cur.execute(sql_study_insert, (
                        client_code_input, desc_input, active_content_input, dp_val, ds_val, lot_number_input, 
                        mfg_date_input.strftime('%Y-%m-%d'), t0_release_date_input.strftime('%Y-%m-%d'),
                        p1_spn_input, p1_desc_input, p1_supp_input, p2_spn_input, p2_desc_input, p2_supp_input,
                        product_no_input, protocol_no_input, revision_input, spec_no_input
                    ))
                    study_id = cur.lastrowid
                
                sql_schedule = '''INSERT INTO storage_schedules(study_id, storage_condition) VALUES(%s,%s)'''
                sql_timepoint_info = '''INSERT INTO timepoint_testing_info(schedule_id, timepoint, pull_date, num_vials, num_copies, tests_to_perform) VALUES(%s,%s,%s,%s,%s,%s)'''
                
                if 'completed_schedule' in st.session_state and st.session_state.completed_schedule:
                    for condition, timepoint_rows in st.session_state.completed_schedule.items():
                        cur.execute(sql_schedule, (study_id, condition))
                        schedule_id = cur.lastrowid
                        
                        for row in timepoint_rows:
                            if pd.notna(row.get('Date Scheduled')):
                                tests_to_perform = row.get('tests_to_perform', [])
                                tests_str = json.dumps(tests_to_perform)
                                pull_date_str = pd.to_datetime(row['Date Scheduled']).strftime('%Y-%m-%d')
                                
                                cur.execute(sql_timepoint_info, (
                                    schedule_id,
                                    row['Time Point'],
                                    pull_date_str,
                                    row['Number of Vials'],
                                    1, # Default value for num_copies
                                    tests_str
                                ))

                conn.commit()
                st.success("Stability study and detailed schedule saved successfully!")
                # Clear inputs for new entry
                st.session_state['client_code'] = ''
                st.session_state['description'] = ''
                st.session_state['active_content'] = ''
                st.session_state['drug_product'] = False
                st.session_state['drug_substance'] = False
                st.session_state['lot_number'] = ''
                st.session_state['product_no'] = ''
                st.session_state['protocol_no_tab1'] = '' # Renamed to avoid conflict with tab3
                st.session_state['revision'] = ''
                st.session_state['specification_no'] = ''
                st.session_state['mfg_date'] = datetime.today().date()
                st.session_state['t0_release_date'] = datetime.today().date()
                # For packaging, reset the data editor default or session state if it exists
                st.session_state['packaging_editor'] = pd.DataFrame([
                    {"Supplier Part Number": "", "Description": "", "Supplier": ""},
                    {"Supplier Part Number": "", "Description": "", "Supplier": ""}
                ])
                st.session_state.completed_schedule = None
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred while saving: {e}")
                logging.error(f"Error during 'Save Study': {e}", exc_info=True)
        else:
            st.warning("Please upload a completed schedule file before saving.")