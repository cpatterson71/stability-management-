from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QGroupBox,
    QPushButton,
    QListView,
    QLabel,
    QHBoxLayout
)
from PySide6.QtCore import QStringListModel

class Tab3Summary(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setLayout(QVBoxLayout())

        # --- Search Section ---
        search_groupbox = QGroupBox("Search for Stability Summary in S3")
        search_layout = QFormLayout()

        self.ss_client_code = QLineEdit()
        self.ss_description = QLineEdit()
        search_layout.addRow("Client Code:", self.ss_client_code)
        search_layout.addRow("Description:", self.ss_description)

        search_button = QPushButton("Search in S3")
        search_layout.addRow(search_button)
        
        self.results_list = QListView()
        self.results_model = QStringListModel()
        self.results_list.setModel(self.results_model)

        search_results_layout = QVBoxLayout()
        search_results_layout.addWidget(QLabel("Search Results:"))
        search_results_layout.addWidget(self.results_list)
        
        download_button = QPushButton("Download Selected File")
        search_results_layout.addWidget(download_button)

        search_layout.addRow(search_results_layout)
        search_groupbox.setLayout(search_layout)
        self.layout().addWidget(search_groupbox)

        # --- Upload Section ---
        upload_groupbox = QGroupBox("Upload New or Updated Summary")
        upload_layout = QVBoxLayout()

        upload_button_layout = QHBoxLayout()
        self.choose_file_button = QPushButton("Choose File...")
        self.selected_file_label = QLabel("No file selected.")
        upload_button_layout.addWidget(self.choose_file_button)
        upload_button_layout.addWidget(self.selected_file_label, 1)
        
        upload_layout.addLayout(upload_button_layout)
        
        self.upload_to_s3_button = QPushButton("Upload to S3")
        upload_layout.addWidget(self.upload_to_s3_button)

        upload_groupbox.setLayout(upload_layout)
        self.layout().addWidget(upload_groupbox)
