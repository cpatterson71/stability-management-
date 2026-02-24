from nicegui import ui, app
import pandas as pd
from datetime import date
import logging
import json
from tabs.utils import generate_schedule_dfs, generate_excel_from_dfs, sanitize_sheet_name

def tab1_setup_ui(conn):
    with ui.column().classes('w-full'):
        ui.label('Stability Study Setup').classes('text-2xl font-bold')

        # --- Main Form ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Study Details')
            
            ui.input('Client Code').bind_value(app.storage.user, 'client_code', '').classes('w-full')
            ui.input('Description').bind_value(app.storage.user, 'description', '').classes('w-full')
            ui.input('Active Content').bind_value(app.storage.user, 'active_content', '').classes('w-full')
            
            with ui.row().classes('w-full'):
                ui.checkbox('Drug Product (DP)').bind_value(app.storage.user, 'dp_checkbox', False)
                ui.checkbox('Drug Substance (DS)').bind_value(app.storage.user, 'ds_checkbox', False)
            
            ui.input('Lot Number').bind_value(app.storage.user, 'lot_number', '').classes('w-full')
            ui.input('Product No.').bind_value(app.storage.user, 'product_no', '').classes('w-full')
            ui.input('Protocol No.').bind_value(app.storage.user, 'protocol_no', '').classes('w-full')
            ui.input('Revision').bind_value(app.storage.user, 'revision', '').classes('w-full')
            ui.input('Specification No.').bind_value(app.storage.user, 'spec_no', '').classes('w-full')
            
            ui.date('Manufacturing Date', value=str(date.today())).bind_value(app.storage.user, 'mfg_date')
            ui.date('T0 (release date)', value=str(date.today())).bind_value(app.storage.user, 't0_release_date')

        # --- Packaging Editor ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Packaging (primary only)')
            
            # Initialize packaging data if not present
            if 'packaging_data' not in app.storage.user:
                app.storage.user.packaging_data = [
                    {"Supplier Part Number": "", "Description": "", "Supplier": ""},
                    {"Supplier Part Number": "", "Description": "", "Supplier": ""}
                ]

            packaging_table = ui.table(
                columns=[
                    {'name': 'spn', 'label': 'Supplier Part Number', 'field': 'Supplier Part Number', 'required': True, 'align': 'left'},
                    {'name': 'desc', 'label': 'Description', 'field': 'Description', 'required': True, 'align': 'left'},
                    {'name': 'supp', 'label': 'Supplier', 'field': 'Supplier', 'required': True, 'align': 'left'},
                ],
                rows=app.storage.user.packaging_data,
                row_key='Supplier Part Number',
                pagination={'rowsPerPage': 0}, # show all rows
            ).classes('w-full')
            
            async def add_packaging_row():
                app.storage.user.packaging_data.append({"Supplier Part Number": "", "Description": "", "Supplier": ""})
                packaging_table.update()

            async def remove_packaging_row():
                selected_rows = packaging_table.selected
                if not selected_rows:
                    ui.notify('Please select rows to remove.', type='warning')
                    return
                for row in selected_rows:
                    app.storage.user.packaging_data.remove(row)
                packaging_table.selected.clear() # Clear selection after removing
                packaging_table.update()

            with ui.row().classes('w-full justify-end'):
                ui.button('Add Packaging', on_click=add_packaging_row)
                ui.button('Remove Selected Packaging', on_click=remove_packaging_row)

        # --- Master Tests ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Step 1: Define Master Tests')
            
            # Load master tests from DB
            if 'master_tests_data' not in app.storage.user:
                app.storage.user.master_tests_data = [] # Initialize
            master_tests_table = ui.table(
                columns=[
                    {'name': 'Test', 'label': 'Test', 'field': 'Test', 'required': True, 'align': 'left'},
                    {'name': 'Test Method', 'label': 'Test Method', 'field': 'Test Method', 'required': True, 'align': 'left'},
                    {'name': 'Form No', 'label': 'Form No', 'field': 'Form No', 'required': True, 'align': 'left'},
                ],
                rows=app.storage.user.master_tests_data,
                row_key='Test',
                pagination={'rowsPerPage': 0},
            ).classes('w-full')

            def load_master_tests_to_table():
                try:
                    df = pd.read_sql_query('SELECT test_name AS "Test", test_method AS "Test Method", form_no AS "Form No" FROM master_tests', conn)
                    app.storage.user.master_tests_data = df.to_dict('records')
                    master_tests_table.rows = app.storage.user.master_tests_data
                    master_tests_table.update()
                except Exception as e:
                    ui.notify(f"Could not load master tests from database: {e}", type='negative')
            
            load_master_tests_to_table() # Initial load

            async def upload_master_tests(e):
                try:
                    df = pd.read_excel(e.content)
                    if df.empty or 'Test' not in df.columns or df['Test'].empty:
                        ui.notify("No 'Test' column found or file is empty.", type='warning')
                        return

                    processed_df = df.copy()
                    if 'Test Method' not in processed_df.columns:
                        processed_df['Test Method'] = ''
                    if 'Form No' not in processed_df.columns:
                        processed_df['Form No'] = ''
                    if 'Form #' in processed_df.columns:
                        processed_df['Form No'] = processed_df['Form #']

                    cur = conn.cursor()
                    for _, row in processed_df.iterrows():
                        cur.execute("INSERT OR IGNORE INTO master_tests (test_name, test_method, form_no) VALUES (?, ?, ?)",
                                    (row['Test'], row['Test Method'], row['Form No']))
                    conn.commit()
                    ui.notify("Master tests uploaded and saved to database.", type='positive')
                    load_master_tests_to_table() # Refresh table

                except Exception as err:
                    ui.notify(f"Error reading Excel file or saving to DB: {err}", type='negative')

            ui.upload(label="Upload Master Test Document", auto_upload=True, on_upload=upload_master_tests).props('accept=".xlsx"')

        # --- Storage Conditions & Timepoints ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Storage Conditions and Timepoints Selection')
            
            app.storage.user.selected_conditions = {} # Changed to dict for toggle bind_value
            app.storage.user.selected_timepoints = {}
            app.storage.user.completed_schedule = None # Initialize completed_schedule

            condition_options = ["5°C", "-20°C", "25°C / 60% RH", "30°C / 65% RH", "40°C / 75% RH"]
            
            with ui.row().classes('w-full wrap'):
                condition_checkboxes = {}
                for cond in condition_options:
                    cb = ui.checkbox(cond).bind_value(app.storage.user.selected_conditions, cond, 'toggle')
                    condition_checkboxes[cond] = cb
            
            ui.separator()

            with ui.tabs().classes('w-full') as tabs:
                pass # Tabs will be added dynamically

            with ui.tab_panels(tabs, value=None).classes('w-full'):
                for cond in condition_options:
                    with ui.tab_panel(cond).classes('w-full'):
                        ui.label(f'Configure Timepoints for {cond}')
                        
                        timepoints_dict = {
                            "1 month": 1, "2 months": 2, "3 months": 3, "6 months": 6,
                            "12 months": 12, "18 months": 18, "24 months": 24, "36 months": 36
                        }

                        if cond not in app.storage.user.selected_timepoints:
                            app.storage.user.selected_timepoints[cond] = {}

                        with ui.column().classes('w-full'):
                            with ui.row().classes('w-full items-center'):
                                ui.label('Timepoint').classes('font-bold w-1/4')
                                ui.label('Pull Date').classes('font-bold w-1/4')
                                ui.label('Number of Vials').classes('font-bold w-1/4')

                            for timepoint_name, months in timepoints_dict.items():
                                if timepoint_name not in app.storage.user.selected_timepoints[cond]:
                                    app.storage.user.selected_timepoints[cond][timepoint_name] = {
                                        'selected': False,
                                        'pull_date': str(pd.to_datetime(app.storage.user.mfg_date) + pd.DateOffset(months=months)).split(' ')[0],
                                        'num_vials': 1
                                    }
                                
                                with ui.row().classes('w-full items-center'):
                                    tp_checkbox = ui.checkbox(timepoint_name).classes('w-1/4')
                                    tp_date = ui.date().classes('w-1/4').props('minimal')
                                    tp_vials = ui.number('Vials', min=1, value=1).classes('w-1/4').props('minimal')

                                    tp_checkbox.bind_value(app.storage.user.selected_timepoints[cond][timepoint_name], 'selected')
                                    tp_date.bind_value(app.storage.user.selected_timepoints[cond][timepoint_name], 'pull_date')
                                    tp_vials.bind_value(app.storage.user.selected_timepoints[cond][timepoint_name], 'num_vials')

                                    # Enable/disable based on checkbox state
                                    tp_date.bind_enabled_from(tp_checkbox, 'value')
                                    tp_vials.bind_enabled_from(tp_checkbox, 'value')

            # Update tabs dynamically
            def update_tabs():
                for cond in condition_options:
                    if app.storage.user.selected_conditions.get(cond): # Check if the condition is truly selected
                        if tabs.get_tab(cond) is None:
                            tabs.add_tab(cond)
                            tabs.set_value(cond) # Set current tab to the newly added one
                    else:
                        if tabs.get_tab(cond) is not None:
                            tabs.remove_tab(cond)
                            tabs.set_value(None) # Clear selected tab if none are active

            for cb in condition_checkboxes.values():
                cb.on('change', update_tabs)
        
        # --- Action Buttons ---
        with ui.row().classes('w-full justify-around q-mt-md'):
            @ui.button('Generate Schedule Template').on('click')
            async def generate_schedule_template():
                selected_timepoints_processed = {}
                for cond, tps in app.storage.user.selected_timepoints.items():
                    selected_tps_for_cond = {}
                    for tp_name, tp_data in tps.items():
                        if tp_data['selected']:
                            selected_tps_for_cond[tp_name] = {
                                "months": 0, # Placeholder, not used in excel gen for NiceGUI
                                "pull_date": pd.to_datetime(tp_data['pull_date']).date(),
                                "num_vials": tp_data['num_vials']
                            }
                    if selected_tps_for_cond:
                        selected_timepoints_processed[cond] = selected_tps_for_cond

                if not selected_timepoints_processed:
                    ui.notify("Please select at least one storage condition and timepoint.", type='warning')
                    return

                study_details = {
                    "Description": app.storage.user.description,
                    "Active Content": app.storage.user.active_content,
                    "Lot Number": app.storage.user.lot_number,
                    "Product No.": app.storage.user.product_no,
                    "Protocol No.": app.storage.user.protocol_no,
                    "Revision": app.storage.user.revision,
                    "Specification No.": app.storage.user.spec_no,
                    "Manufacturing Date": app.storage.user.mfg_date,
                    "T0 (release date)": app.storage.user.t0_release_date,
                    "master_tests_df": pd.DataFrame(app.storage.user.master_tests_data)
                }
                
                selected_master_tests = [mt['Test'] for mt in app.storage.user.master_tests_data]

                try:
                    schedule_dfs = generate_schedule_dfs(selected_timepoints_processed, selected_master_tests)
                    excel_data = generate_excel_from_dfs(schedule_dfs, study_details)
                    ui.download(excel_data, 'stability_schedule_template.xlsx')
                    ui.notify('Schedule template generated successfully!', type='positive')
                except Exception as e:
                    ui.notify(f"An error occurred during Excel generation: {e}", type='negative')

            async def upload_completed_schedule(e):
                try:
                    xls = pd.ExcelFile(e.content)
                    schedule_data = {}
                    
                    if not app.storage.user.master_tests_data:
                        ui.notify("Please define master tests before uploading a schedule.", type='warning')
                        return

                    ordered_test_list = [mt['Test'] for mt in app.storage.user.master_tests_data]
                    
                    # Assuming selected_conditions is a list of strings and not an object in app.storage.user
                    # This might need adjustment if bind_value uses a dict for toggles.
                    current_selected_conditions = [cond for cond, is_selected in app.storage.user.selected_conditions.items() if is_selected]


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
                            for cond in current_selected_conditions:
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
                                ui.notify(f"Could not map sheet '{sheet_name}' to any selected condition. Skipping sheet.", type='warning')
                        else:
                            ui.notify(f"Could not find header row with 'Time Point' in sheet '{sheet_name}'. Skipping sheet.", type='warning')
                    
                    app.storage.user.completed_schedule = schedule_data
                    ui.notify("Completed schedule uploaded and parsed successfully!", type='positive')

                except Exception as e:
                    ui.notify(f"Error reading completed schedule file: {e}", type='negative')
                    app.storage.user.completed_schedule = None

            ui.upload(label="Upload Completed Schedule", auto_upload=True, on_upload=upload_completed_schedule).props('accept=".xlsx"')
            
            ui.upload(label="Upload Completed Schedule", auto_upload=True, on_upload=upload_completed_schedule).props('accept=".xlsx"')
            
            @ui.button('Save Study').on('click')
            async def save_study():
                if not app.storage.user.completed_schedule:
                    ui.notify("Please upload a completed schedule file before saving.", type='warning')
                    return

                try:
                    cur = conn.cursor()
                    lot_number = app.storage.user.lot_number

                    # Check if study exists
                    cur.execute("SELECT id FROM stability_studies WHERE lot_number = ?", (lot_number,))
                    existing_study = cur.fetchone()

                    # Gather data from UI
                    client_code = app.storage.user.client_code
                    description = app.storage.user.description
                    active_content = app.storage.user.active_content
                    dp_val = 1 if app.storage.user.dp_checkbox else 0
                    ds_val = 1 if app.storage.user.ds_checkbox else 0
                    mfg_date = app.storage.user.mfg_date
                    t0_date = app.storage.user.t0_release_date
                    product_no = app.storage.user.product_no
                    protocol_no = app.storage.user.protocol_no
                    revision = app.storage.user.revision
                    spec_no = app.storage.user.spec_no
                    
                    p_data = app.storage.user.packaging_data
                    p1_spn = p_data[0]["Supplier Part Number"] if len(p_data) > 0 else ""
                    p1_desc = p_data[0]["Description"] if len(p_data) > 0 else ""
                    p1_supp = p_data[0]["Supplier"] if len(p_data) > 0 else ""
                    p2_spn = p_data[1]["Supplier Part Number"] if len(p_data) > 1 else ""
                    p2_desc = p_data[1]["Description"] if len(p_data) > 1 else ""
                    p2_supp = p_data[1]["Supplier"] if len(p_data) > 1 else ""

                    if existing_study:
                        study_id = existing_study[0]
                        result = await ui.run_javascript(f'confirm("Lot Number {lot_number} already exists. Overwrite its data?")', timeout=5.0)
                        if not result:
                            ui.notify("Saving cancelled.", type='info')
                            return

                        sql_study_update = ''' UPDATE stability_studies SET
                                                client_code = ?, description = ?, active_content = ?, drug_product = ?, drug_substance = ?, 
                                                manufacturing_date = ?, t0_release_date = ?, packaging1_supplier_part_number = ?, 
                                                packaging1_description = ?, packaging1_supplier = ?, packaging2_supplier_part_number = ?, 
                                                packaging2_description = ?, packaging2_supplier = ?, product_no = ?, protocol_no = ?, 
                                                revision = ?, specification_no = ?
                                              WHERE id = ? '''
                        cur.execute(sql_study_update, (
                            client_code, description, active_content, dp_val, ds_val, mfg_date, t0_date,
                            p1_spn, p1_desc, p1_supp, p2_spn, p2_desc, p2_supp,
                            product_no, protocol_no, revision, spec_no, study_id
                        ))
                        # Delete old data
                        cur.execute("DELETE FROM timepoint_testing_info WHERE schedule_id IN (SELECT id FROM storage_schedules WHERE study_id = ?)", (study_id,))
                        cur.execute("DELETE FROM storage_schedules WHERE study_id = ?", (study_id,))
                    else:
                        sql_study_insert = ''' INSERT INTO stability_studies(
                                                    client_code, description, active_content, drug_product, drug_substance, lot_number, manufacturing_date, t0_release_date,
                                                    packaging1_supplier_part_number, packaging1_description, packaging1_supplier,
                                                    packaging2_supplier_part_number, packaging2_description, packaging2_supplier,
                                                    product_no, protocol_no, revision, specification_no
                                                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
                        cur.execute(sql_study_insert, (
                            client_code, description, active_content, dp_val, ds_val, lot_number, mfg_date, t0_date,
                            p1_spn, p1_desc, p1_supp, p2_spn, p2_desc, p2_supp,
                            product_no, protocol_no, revision, spec_no
                        ))
                        study_id = cur.lastrowid

                    # Insert new schedule data
                    for condition, timepoint_rows in app.storage.user.completed_schedule.items():
                        cur.execute("INSERT INTO storage_schedules(study_id, storage_condition) VALUES(?,?)", (study_id, condition))
                        schedule_id = cur.lastrowid
                        
                        for row in timepoint_rows:
                            if pd.notna(row.get('Date Scheduled')):
                                tests_str = json.dumps(row.get('tests_to_perform', []))
                                pull_date = pd.to_datetime(row['Date Scheduled']).strftime('%Y-%m-%d')
                                cur.execute("INSERT INTO timepoint_testing_info(schedule_id, timepoint, pull_date, num_vials, num_copies, tests_to_perform) VALUES(?,?,?,?,?,?)",
                                            (schedule_id, row['Time Point'], pull_date, row['Number of Vials'], 1, tests_str))

                    conn.commit()
                    ui.notify("Stability study and detailed schedule saved successfully!", type='positive')
                    clear_form()

                except Exception as e:
                    ui.notify(f"An error occurred while saving: {e}", type='negative')

            def clear_form():
                # Reset all input fields
                app.storage.user.client_code = ''
                app.storage.user.description = ''
                app.storage.user.active_content = ''
                app.storage.user.dp_checkbox = False
                app.storage.user.ds_checkbox = False
                app.storage.user.lot_number = ''
                app.storage.user.product_no = ''
                app.storage.user.protocol_no = ''
                app.storage.user.revision = ''
                app.storage.user.spec_no = ''
                app.storage.user.mfg_date = str(date.today())
                app.storage.user.t0_release_date = str(date.today())
                
                # Reset packaging editor
                app.storage.user.packaging_data = [
                    {"Supplier Part Number": "", "Description": "", "Supplier": ""},
                    {"Supplier Part Number": "", "Description": "", "Supplier": ""}
                ]
                packaging_table.update()

                # Uncheck and remove condition tabs
                for cond in condition_options:
                    if app.storage.user.selected_conditions.get(cond):
                        app.storage.user.selected_conditions[cond] = False
                        # tabs should update via bind_value, but direct removal might be needed
                        # tabs.remove_tab(cond) # NiceGUI automatically handles this with the binding
                
                app.storage.user.completed_schedule = None
                load_master_tests_to_table() # Reload master tests if they were updated