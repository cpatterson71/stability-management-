from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QGroupBox,
    QPushButton,
    QListView,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QFileDialog
)
from PySide6.QtCore import QStringListModel
import boto3
import webbrowser
import os
import pandas as pd
import io

# S3 Configuration Constants
S3_BUCKET_NAME = "ai-document-chat-document-store"
S3_FOLDER_PREFIX = "Stability_Summaries/"

class Tab3Summary(QWidget):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.s3_search_results = []
        self.selected_upload_path = None
        self.setLayout(QVBoxLayout())

        # --- Search Section ---
        search_groupbox = QGroupBox("Search for Stability Summary in S3")
        search_layout = QFormLayout()

        self.ss_client_code = QLineEdit()
        self.ss_description = QLineEdit()
        search_layout.addRow("Client Code:", self.ss_client_code)
        search_layout.addRow("Description:", self.ss_description)

        search_button = QPushButton("Search in S3")
        search_button.clicked.connect(self.search_s3)
        search_layout.addRow(search_button)
        
        self.results_list = QListView()
        self.results_model = QStringListModel()
        self.results_list.setModel(self.results_model)

        search_results_layout = QVBoxLayout()
        search_results_layout.addWidget(QLabel("Search Results:"))
        search_results_layout.addWidget(self.results_list)
        
        download_button = QPushButton("Download Selected File")
        download_button.clicked.connect(self.download_from_s3)
        search_results_layout.addWidget(download_button)

        search_layout.addRow(search_results_layout)
        search_groupbox.setLayout(search_layout)
        self.layout().addWidget(search_groupbox)

        # --- Upload Section ---
        upload_groupbox = QGroupBox("Upload New or Updated Summary")
        upload_layout = QVBoxLayout()

        upload_button_layout = QHBoxLayout()
        self.choose_file_button = QPushButton("Choose File...")
        self.choose_file_button.clicked.connect(self.choose_upload_file)
        self.selected_file_label = QLabel("No file selected.")
        upload_button_layout.addWidget(self.choose_file_button)
        upload_button_layout.addWidget(self.selected_file_label, 1)
        
        upload_layout.addLayout(upload_button_layout)
        
        self.upload_to_s3_button = QPushButton("Upload to S3")
        self.upload_to_s3_button.clicked.connect(self.upload_to_s3)
        upload_layout.addWidget(self.upload_to_s3_button)

        upload_groupbox.setLayout(upload_layout)
        self.layout().addWidget(upload_groupbox)

    def upload_to_s3(self):
        if not self.selected_upload_path:
            QMessageBox.warning(self, "No File", "Please choose a file to upload first.")
            return

        try:
            s3_client = boto3.client('s3')
            file_name = os.path.basename(self.selected_upload_path)
            s3_file_name = f"{S3_FOLDER_PREFIX}{file_name}"

            # Process the file to lock it, similar to the Streamlit version
            df = pd.read_excel(self.selected_upload_path)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                sheet_name = 'StabilitySummary'
                df.to_excel(writer, index=False, sheet_name=sheet_name)
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]
                unlocked_format = workbook.add_format({'locked': False})
                worksheet.protect()
                for row_num, row_data in df.iterrows():
                    for col_num, cell_value in enumerate(row_data):
                        if pd.isna(cell_value):
                            worksheet.write(row_num + 1, col_num, '', unlocked_format)
            processed_file_data = output.getvalue()

            # Check if file exists and ask for confirmation
            try:
                s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_file_name)
                reply = QMessageBox.question(self, 'Replace File?', 
                                             f"The file '{file_name}' already exists in S3. Do you want to replace it?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    QMessageBox.information(self, "Cancelled", "Upload cancelled.")
                    return
            except s3_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise # Re-raise other client errors

            # Upload the file
            s3_client.upload_fileobj(io.BytesIO(processed_file_data), S3_BUCKET_NAME, s3_file_name)
            QMessageBox.information(self, "Success", f"Successfully uploaded locked file to s3://{S3_BUCKET_NAME}/{s3_file_name}")
            
            # Clear selection and refresh search
            self.selected_upload_path = None
            self.selected_file_label.setText("No file selected.")
            self.search_s3()

        except Exception as e:
            QMessageBox.critical(self, "S3 Error", f"An error occurred during upload: {e}")


    def search_s3(self):
        self.s3_search_results = []
        try:
            s3_client = boto3.client('s3')
            
            all_objects = []
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=S3_FOLDER_PREFIX)
            for page in pages:
                all_objects.extend([obj['Key'] for obj in page.get('Contents', [])])

            filtered_objects = all_objects
            if self.ss_client_code.text():
                filtered_objects = [key for key in filtered_objects if self.ss_client_code.text().lower() in key.lower()]
            if self.ss_description.text():
                filtered_objects = [key for key in filtered_objects if self.ss_description.text().lower() in key.lower()]
            
            self.s3_search_results = filtered_objects
            
            s3_filenames = [key.split('/')[-1] for key in self.s3_search_results]
            self.results_model.setStringList(s3_filenames)

            if not self.s3_search_results:
                QMessageBox.information(self, "No Results", "No matching files found in S3.")

        except Exception as e:
            QMessageBox.critical(self, "S3 Error", f"Error searching S3: {e}")
            self.s3_search_results = []
            self.results_model.setStringList([])

    def download_from_s3(self):
        selected_indexes = self.results_list.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "No Selection", "Please select a file to download.")
            return

        selected_row = selected_indexes[0].row()
        selected_key = self.s3_search_results[selected_row]

        try:
            s3_client = boto3.client('s3')
            presigned_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': selected_key}, ExpiresIn=3600)
            webbrowser.open(presigned_url)
        except Exception as e:
            QMessageBox.critical(self, "S3 Error", f"Could not generate download link: {e}")
    
    def choose_upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose Excel File", "", "Excel Files (*.xlsx)")
        if file_path:
            self.selected_upload_path = file_path
            self.selected_file_label.setText(os.path.basename(file_path))
