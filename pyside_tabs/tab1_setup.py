from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDateEdit,
    QGroupBox,
    QPushButton,
    QTableView,
    QLabel,
    QHeaderView,
    QHBoxLayout,
    QTabWidget,
    QScrollArea,
    QSpinBox,
    QFileDialog,
    QMessageBox
)
from PySide6.QtCore import QDate, Qt, QAbstractTableModel
from dateutil.relativedelta import relativedelta
import pandas as pd
import os
from tabs.utils import generate_schedule_dfs, generate_excel_from_dfs, sanitize_sheet_name
import json

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with QTableView."""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._data.columns[col]
        return None

class PackagingTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._data.iloc[index.row(), index.column()]

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])

    def flags(self, index):
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def insertRow(self, row, parent):
        self.beginInsertRows(parent, row, row)
        new_row = pd.DataFrame([["", "", ""]], columns=self._data.columns)
        self._data = pd.concat([self._data.iloc[:row], new_row, self._data.iloc[row:]]).reset_index(drop=True)
        self.endInsertRows()
        return True

    def removeRow(self, row, parent):
        self.beginRemoveRows(parent, row, row)
        self._data = self._data.drop(self._data.index[row]).reset_index(drop=True)
        self.endRemoveRows()
        return True

class Tab1Setup(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setLayout(QVBoxLayout())
        
        # Keep track of condition checkboxes
        self.condition_checkboxes = {}
        self.condition_tabs = {}
        self.master_tests_model = None

        # --- Main Form ---
        form_layout = QFormLayout()
        # ... (rest of the form widgets)
        self.client_code_input = QLineEdit()
        form_layout.addRow("Client Code:", self.client_code_input)
        self.desc_input = QLineEdit()
        form_layout.addRow("Description:", self.desc_input)
        self.active_content_input = QLineEdit()
        form_layout.addRow("Active Content:", self.active_content_input)
        self.dp_checkbox = QCheckBox("Drug Product (DP)")
        self.ds_checkbox = QCheckBox("Drug Substance (DS)")
        form_layout.addRow(self.dp_checkbox, self.ds_checkbox)
        self.lot_number_input = QLineEdit()
        form_layout.addRow("Lot Number:", self.lot_number_input)
        self.product_no_input = QLineEdit()
        form_layout.addRow("Product No.:", self.product_no_input)
        self.protocol_no_input = QLineEdit()
        form_layout.addRow("Protocol No.:", self.protocol_no_input)
        self.revision_input = QLineEdit()
        form_layout.addRow("Revision:", self.revision_input)
        self.spec_no_input = QLineEdit()
        form_layout.addRow("Specification No.:", self.spec_no_input)
        self.mfg_date_input = QDateEdit(QDate.currentDate())
        self.mfg_date_input.setCalendarPopup(True)
        form_layout.addRow("Manufacturing Date:", self.mfg_date_input)
        self.t0_release_date_input = QDateEdit(QDate.currentDate())
        self.t0_release_date_input.setCalendarPopup(True)
        form_layout.addRow("T0 (release date):", self.t0_release_date_input)
        self.layout().addLayout(form_layout)

        # --- Master Tests ---
        self.setup_master_tests()

        # --- Packaging Editor ---
        self.setup_packaging_editor()

        self.setup_storage_conditions()

        # --- Action Buttons ---
        self.setup_action_buttons()

    def setup_action_buttons(self):
        action_button_layout = QHBoxLayout()

        self.generate_excel_button = QPushButton("Generate Schedule Template")
        self.generate_excel_button.clicked.connect(self.generate_excel)
        action_button_layout.addWidget(self.generate_excel_button)

        self.upload_schedule_button = QPushButton("Upload Completed Schedule")
        self.upload_schedule_button.clicked.connect(self.upload_schedule)
        action_button_layout.addWidget(self.upload_schedule_button)

        self.save_study_button = QPushButton("Save Study")
        self.save_study_button.clicked.connect(self.save_study)
        action_button_layout.addWidget(self.save_study_button)

        self.layout().addLayout(action_button_layout)

    def generate_excel(self):
        # 1. Gather data from the UI
        selected_timepoints = {}
        for condition, tab in self.condition_tabs.items():
            condition_timepoints = {}
            # Find the scroll area content widget
            scroll_area = tab.findChild(QScrollArea)
            if not scroll_area:
                continue
            scroll_content = scroll_area.widget()
            # Iterate through the layouts to find the timepoint rows
            for i in range(1, scroll_content.layout().count()): # Start from 1 to skip header
                row_layout = scroll_content.layout().itemAt(i).layout()
                if not row_layout:
                    continue
                
                tp_checkbox = row_layout.itemAt(0).widget()
                if tp_checkbox and tp_checkbox.isChecked():
                    pull_date_edit = row_layout.itemAt(1).widget()
                    num_vials_spinbox = row_layout.itemAt(2).widget()
                    
                    timepoint_name = tp_checkbox.text()
                    # A dummy 'months' value is needed for generate_schedule_dfs, it's not used in the excel generation itself.
                    condition_timepoints[timepoint_name] = {
                        "months": 0, 
                        "pull_date": pull_date_edit.date().toPython(),
                        "num_vials": num_vials_spinbox.value()
                    }
            if condition_timepoints:
                selected_timepoints[condition] = condition_timepoints

        if not selected_timepoints:
            QMessageBox.warning(self, "No Selection", "Please select at least one storage condition and timepoint.")
            return

        study_details = {
            "Description": self.desc_input.text(),
            "Active Content": self.active_content_input.text(),
            "Lot Number": self.lot_number_input.text(),
            "Product No.": self.product_no_input.text(),
            "Protocol No.": self.protocol_no_input.text(),
            "Revision": self.revision_input.text(),
            "Specification No.": self.spec_no_input.text(),
            "Manufacturing Date": self.mfg_date_input.date().toString("yyyy-MM-dd"),
            "T0 (release date)": self.t0_release_date_input.date().toString("yyyy-MM-dd"),
            "master_tests_df": self.master_tests_model._data if self.master_tests_model else pd.DataFrame()
        }
        
        selected_master_tests = []
        if self.master_tests_model and not self.master_tests_model._data.empty:
            selected_master_tests = self.master_tests_model._data['Test'].tolist()

        # 2. Call utility functions
        try:
            schedule_dfs = generate_schedule_dfs(selected_timepoints, selected_master_tests)
            excel_data = generate_excel_from_dfs(schedule_dfs, study_details)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during Excel generation: {e}")
            return

        # 3. Open Save File Dialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Schedule Template", "stability_schedule_template.xlsx", "Excel Files (*.xlsx)")

        if file_path:
            try:
                with open(file_path, "wb") as f:
                    f.write(excel_data)
                QMessageBox.information(self, "Success", f"Schedule template saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")


    def upload_schedule(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Completed Schedule File", "", "Excel Files (*.xlsx)")
        if not file_path:
            return

        try:
            xls = pd.ExcelFile(file_path)
            schedule_data = {}
            
            if not self.master_tests_model or self.master_tests_model._data.empty:
                QMessageBox.warning(self, "Master Tests Missing", "Please define master tests before uploading a schedule.")
                return

            ordered_test_list = self.master_tests_model._data['Test'].tolist()
            
            selected_conditions = [cb.text() for cb in self.condition_checkboxes.values() if cb.isChecked()]

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
                        QMessageBox.warning(self, "Sheet Mismatch", f"Could not map sheet '{sheet_name}' to any selected condition. Skipping sheet.")
                else:
                    QMessageBox.warning(self, "Header Not Found", f"Could not find header row with 'Time Point' in sheet '{sheet_name}'. Skipping sheet.")
            
            self.completed_schedule = schedule_data
            QMessageBox.information(self, "Success", "Completed schedule uploaded and parsed successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading completed schedule file: {e}")
            self.completed_schedule = None


    def save_study(self):
        if not hasattr(self, 'completed_schedule') or not self.completed_schedule:
            QMessageBox.warning(self, "Warning", "Please upload a completed schedule file before saving.")
            return

        try:
            cur = self.conn.cursor()
            lot_number = self.lot_number_input.text()

            # Check if study exists
            cur.execute("SELECT id FROM stability_studies WHERE lot_number = ?", (lot_number,))
            existing_study = cur.fetchone()

            # Gather data from UI
            client_code = self.client_code_input.text()
            description = self.desc_input.text()
            active_content = self.active_content_input.text()
            dp_val = 1 if self.dp_checkbox.isChecked() else 0
            ds_val = 1 if self.ds_checkbox.isChecked() else 0
            mfg_date = self.mfg_date_input.date().toString("yyyy-MM-dd")
            t0_date = self.t0_release_date_input.date().toString("yyyy-MM-dd")
            product_no = self.product_no_input.text()
            protocol_no = self.protocol_no_input.text()
            revision = self.revision_input.text()
            spec_no = self.spec_no_input.text()
            
            p_df = self.packaging_model._data
            p1_spn = p_df.iloc[0]["Supplier Part Number"] if len(p_df) > 0 else ""
            p1_desc = p_df.iloc[0]["Description"] if len(p_df) > 0 else ""
            p1_supp = p_df.iloc[0]["Supplier"] if len(p_df) > 0 else ""
            p2_spn = p_df.iloc[1]["Supplier Part Number"] if len(p_df) > 1 else ""
            p2_desc = p_df.iloc[1]["Description"] if len(p_df) > 1 else ""
            p2_supp = p_df.iloc[1]["Supplier"] if len(p_df) > 1 else ""

            if existing_study:
                study_id = existing_study[0]
                if QMessageBox.question(self, "Confirm Overwrite", 
                                        f"Lot Number {lot_number} already exists. Overwrite its data?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
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
            for condition, timepoint_rows in self.completed_schedule.items():
                cur.execute("INSERT INTO storage_schedules(study_id, storage_condition) VALUES(?,?)", (study_id, condition))
                schedule_id = cur.lastrowid
                
                for row in timepoint_rows:
                    if pd.notna(row.get('Date Scheduled')):
                        tests_str = json.dumps(row.get('tests_to_perform', []))
                        pull_date = pd.to_datetime(row['Date Scheduled']).strftime('%Y-%m-%d')
                        cur.execute("INSERT INTO timepoint_testing_info(schedule_id, timepoint, pull_date, num_vials, num_copies, tests_to_perform) VALUES(?,?,?,?,?,?)",
                                    (schedule_id, row['Time Point'], pull_date, row['Number of Vials'], 1, tests_str))

            self.conn.commit()
            QMessageBox.information(self, "Success", "Stability study and detailed schedule saved successfully!")
            self.clear_form()

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred while saving: {e}")

    def clear_form(self):
        # Reset all input fields
        self.client_code_input.clear()
        self.desc_input.clear()
        self.active_content_input.clear()
        self.dp_checkbox.setChecked(False)
        self.ds_checkbox.setChecked(False)
        self.lot_number_input.clear()
        self.product_no_input.clear()
        self.protocol_no_input.clear()
        self.revision_input.clear()
        self.spec_no_input.clear()
        self.mfg_date_input.setDate(QDate.currentDate())
        self.t0_release_date_input.setDate(QDate.currentDate())
        
        # Reset packaging editor
        self.setup_packaging_editor() # Re-creates the model with empty data

        # Uncheck and remove condition tabs
        for checkbox in self.condition_checkboxes.values():
            checkbox.setChecked(False) 
        
        self.completed_schedule = None



    def setup_master_tests(self):
        master_tests_groupbox = QGroupBox("Step 1: Define Master Tests")
        master_tests_layout = QVBoxLayout()

        upload_button = QPushButton("Upload Master Test Document (.xlsx)")
        upload_button.clicked.connect(self.upload_master_tests)
        master_tests_layout.addWidget(upload_button)

        self.master_tests_table = QTableView()
        master_tests_layout.addWidget(QLabel("Master Test Methods (loaded from database):"))
        master_tests_layout.addWidget(self.master_tests_table)
        
        master_tests_groupbox.setLayout(master_tests_layout)
        self.layout().addWidget(master_tests_groupbox)

        # Initial load of tests from DB
        self.load_master_tests_to_view()

    def upload_master_tests(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Master Test File", "", "Excel Files (*.xlsx)")
        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)
            if df.empty or 'Test' not in df.columns or df['Test'].empty:
                QMessageBox.warning(self, "Warning", "No 'Test' column found or file is empty.")
                return

            processed_df = df.copy()
            if 'Test Method' not in processed_df.columns:
                processed_df['Test Method'] = ''
            if 'Form No' not in processed_df.columns:
                processed_df['Form No'] = ''
            if 'Form #' in processed_df.columns:
                processed_df['Form No'] = processed_df['Form #']

            cur = self.conn.cursor()
            for _, row in processed_df.iterrows():
                # Using INSERT OR IGNORE for SQLite
                cur.execute("INSERT OR IGNORE INTO master_tests (test_name, test_method, form_no) VALUES (?, ?, ?)",
                            (row['Test'], row['Test Method'], row['Form No']))
            self.conn.commit()
            QMessageBox.information(self, "Success", "Master tests uploaded and saved to database.")
            self.load_master_tests_to_view()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading Excel file or saving to DB: {e}")

    def load_master_tests_to_view(self):
        try:
            df = pd.read_sql_query('SELECT test_name AS "Test", test_method AS "Test Method", form_no AS "Form No" FROM master_tests', self.conn)
            self.master_tests_model = PandasModel(df)
            self.master_tests_table.setModel(self.master_tests_model)
            self.master_tests_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load master tests from database: {e}")
            # Create an empty model if loading fails
            self.master_tests_model = PandasModel(pd.DataFrame())
            self.master_tests_table.setModel(self.master_tests_model)


    def setup_packaging_editor(self):
        # ... (same as before)
        packaging_groupbox = QGroupBox("Packaging (primary only)")
        packaging_layout = QVBoxLayout()
        self.packaging_table = QTableView()
        packaging_data = pd.DataFrame([["", "", ""]], columns=["Supplier Part Number", "Description", "Supplier"])
        self.packaging_model = PackagingTableModel(packaging_data)
        self.packaging_table.setModel(self.packaging_model)
        self.packaging_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        packaging_layout.addWidget(self.packaging_table)
        button_layout = QHBoxLayout()
        add_row_button = QPushButton("Add Packaging")
        add_row_button.clicked.connect(lambda: self.packaging_model.insertRow(self.packaging_model.rowCount(), self.packaging_table.rootIndex()))
        remove_row_button = QPushButton("Remove Selected Packaging")
        remove_row_button.clicked.connect(self.remove_packaging_row)
        button_layout.addWidget(add_row_button)
        button_layout.addWidget(remove_row_button)
        packaging_layout.addLayout(button_layout)
        packaging_groupbox.setLayout(packaging_layout)
        self.layout().addWidget(packaging_groupbox)

    def remove_packaging_row(self):
        selected_rows = self.packaging_table.selectionModel().selectedRows()
        for index in sorted(selected_rows, reverse=True):
            self.packaging_model.removeRow(index.row(), self.packaging_table.rootIndex())

    def setup_storage_conditions(self):
        storage_groupbox = QGroupBox("Storage Conditions and Timepoints Selection")
        storage_layout = QVBoxLayout()

        conditions_layout = QHBoxLayout()
        cond_map = ["5°C", "-20°C", "25°C / 60% RH", "30°C / 65% RH", "40°C / 75% RH"]
        for cond in cond_map:
            cb = QCheckBox(cond)
            cb.stateChanged.connect(self.update_condition_tabs)
            self.condition_checkboxes[cond] = cb
            conditions_layout.addWidget(cb)
        
        storage_layout.addLayout(conditions_layout)

        self.condition_tab_widget = QTabWidget()
        storage_layout.addWidget(self.condition_tab_widget)
        
        storage_groupbox.setLayout(storage_layout)
        self.layout().addWidget(storage_groupbox)

    def update_condition_tabs(self, state):
        checkbox = self.sender()
        condition_name = checkbox.text()

        if state == Qt.CheckState.Checked.value:
            if condition_name not in self.condition_tabs:
                tab = QWidget()
                tab_layout = QVBoxLayout(tab)
                
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_content = QWidget()
                scroll_layout = QVBoxLayout(scroll_content)

                # Header Row
                header_layout = QHBoxLayout()
                header_layout.addWidget(QLabel("Timepoint"), 2)
                header_layout.addWidget(QLabel("Pull Date"), 2)
                header_layout.addWidget(QLabel("Number of Vials"), 1)
                scroll_layout.addLayout(header_layout)

                timepoints_dict = {
                    "1 month": 1, "2 months": 2, "3 months": 3, "6 months": 6,
                    "12 months": 12, "18 months": 18, "24 months": 24, "36 months": 36
                }
                
                t0_date = self.t0_release_date_input.date()

                for timepoint, months in timepoints_dict.items():
                    row_layout = QHBoxLayout()
                    
                    tp_checkbox = QCheckBox(timepoint)
                    pull_date_edit = QDateEdit(t0_date.addMonths(months))
                    pull_date_edit.setCalendarPopup(True)
                    num_vials_spinbox = QSpinBox()
                    num_vials_spinbox.setMinimum(1)
                    num_vials_spinbox.setValue(1)

                    # Initially disable date/spinbox until checkbox is checked
                    pull_date_edit.setEnabled(False)
                    num_vials_spinbox.setEnabled(False)
                    
                    # Connect checkbox to enable/disable the other widgets
                    tp_checkbox.toggled.connect(pull_date_edit.setEnabled)
                    tp_checkbox.toggled.connect(num_vials_spinbox.setEnabled)

                    row_layout.addWidget(tp_checkbox, 2)
                    row_layout.addWidget(pull_date_edit, 2)
                    row_layout.addWidget(num_vials_spinbox, 1)
                    
                    scroll_layout.addLayout(row_layout)

                scroll_area.setWidget(scroll_content)
                tab_layout.addWidget(scroll_area)
                
                self.condition_tabs[condition_name] = tab
                self.condition_tab_widget.addTab(tab, condition_name)

        elif state == Qt.CheckState.Unchecked.value:
            if condition_name in self.condition_tabs:
                tab_widget = self.condition_tabs[condition_name]
                index = self.condition_tab_widget.indexOf(tab_widget)
                if index != -1:
                    self.condition_tab_widget.removeTab(index)
                del self.condition_tabs[condition_name]

