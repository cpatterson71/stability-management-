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

        # --- Storage Conditions & Timepoints ---
        self.setup_storage_conditions()

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

