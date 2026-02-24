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
    QHBoxLayout
)
from PySide6.QtCore import QDate, Qt, QAbstractTableModel
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

        # Main form layout
        form_layout = QFormLayout()

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

        # Packaging Editor
        self.setup_packaging_editor()

    def setup_packaging_editor(self):
        packaging_groupbox = QGroupBox("Packaging (primary only)")
        packaging_layout = QVBoxLayout()

        self.packaging_table = QTableView()
        packaging_data = pd.DataFrame([
            ["", "", ""],
            ["", "", ""]
        ], columns=["Supplier Part Number", "Description", "Supplier"])
        self.packaging_model = PackagingTableModel(packaging_data)
        self.packaging_table.setModel(self.packaging_model)
        self.packaging_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        packaging_layout.addWidget(self.packaging_table)

        # Buttons for adding/removing rows
        button_layout = QHBoxLayout()
        add_row_button = QPushButton("Add Packaging")
        add_row_button.clicked.connect(self.add_packaging_row)
        remove_row_button = QPushButton("Remove Selected Packaging")
        remove_row_button.clicked.connect(self.remove_packaging_row)
        button_layout.addWidget(add_row_button)
        button_layout.addWidget(remove_row_button)
        packaging_layout.addLayout(button_layout)

        packaging_groupbox.setLayout(packaging_layout)
        self.layout().addWidget(packaging_groupbox)
    
    def add_packaging_row(self):
        self.packaging_model.insertRow(self.packaging_model.rowCount(), self.packaging_table.rootIndex())

    def remove_packaging_row(self):
        selected_rows = self.packaging_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        # Remove rows in reverse order to avoid index shifting issues
        for index in sorted(selected_rows, reverse=True):
            self.packaging_model.removeRow(index.row(), self.packaging_table.rootIndex())
