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
    QHeaderView
)
from PySide6.QtCore import QDate

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

        # Placeholder for the rest of the UI
        self.layout().addWidget(QLabel("More UI components to be added here..."))

