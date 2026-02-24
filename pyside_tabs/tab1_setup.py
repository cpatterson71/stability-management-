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
    QScrollArea
)
from PySide6.QtCore import QDate, Qt, QAbstractTableModel
from dateutil.relativedelta import relativedelta
import pandas as pd

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

        # --- Packaging Editor ---
        self.setup_packaging_editor()

        # --- Storage Conditions & Timepoints ---
        self.setup_storage_conditions()

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
                # Create a new tab for this condition
                tab = QWidget()
                tab_layout = QVBoxLayout(tab)
                
                # Add a scroll area for the timepoints
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_content = QWidget()
                scroll_layout = QFormLayout(scroll_content)
                
                timepoints_dict = {
                    "1 month": 1, "2 months": 2, "3 months": 3, "6 months": 6,
                    "12 months": 12, "18 months": 18, "24 months": 24, "36 months": 36
                }

                for timepoint, months in timepoints_dict.items():
                    tp_checkbox = QCheckBox(timepoint)
                    # You can connect signals here to handle logic when a timepoint is selected
                    scroll_layout.addRow(tp_checkbox)

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


