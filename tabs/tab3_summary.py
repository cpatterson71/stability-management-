import streamlit as st
import pandas as pd
import io
import logging
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# S3 Configuration Constants
S3_BUCKET_NAME = "ai-document-chat-document-store"
S3_FOLDER_PREFIX = "Stability_Summaries/"

def show_summary_tab():
    logging.info("Entering Tab 3: Stability Summary")
    st.header("Stability Summary")

    # --- Part 1: File Replacement Confirmation UI ---
    if 'confirm_replace' in st.session_state and st.session_state.get('confirm_replace'):
        s3_file_to_replace = st.session_state.confirm_replace
        st.warning(f"The file `{s3_file_to_replace}` already exists in S3. Do you want to replace it?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Replace It", key="confirm_yes"):
                try:
                    s3_client = boto3.client('s3')
                    file_data = st.session_state.uploaded_file_data
                    s3_client.upload_fileobj(io.BytesIO(file_data), S3_BUCKET_NAME, s3_file_to_replace)
                    st.success(f"Successfully replaced file in s3://{S3_BUCKET_NAME}/{s3_file_to_replace}")
                    st.session_state.confirm_replace = None
                    st.session_state.uploaded_file_data = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to replace file: {e}")
        with col2:
            if st.button("No, Cancel", key="confirm_no"):
                st.info("Upload cancelled.")
                st.session_state.confirm_replace = None
                st.session_state.uploaded_file_data = None
                st.rerun()
    
    # --- Part 2: Main Search and Upload UI (hidden during confirmation) ---
    else:
        with st.expander("Search for Stability Summary in S3", expanded=True):
            ss_client_code = st.text_input("Client Code", key="ss_client_code")
            ss_description = st.text_input("Description", key="ss_description")

            if st.button("Search", key="ss_search"):
                st.session_state.ss_search_results = [] # Clear old results
                try:
                    s3_client = boto3.client('s3')
                    
                    # List all objects in the folder
                    all_objects = []
                    paginator = s3_client.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=S3_FOLDER_PREFIX)
                    for page in pages:
                        all_objects.extend([obj['Key'] for obj in page.get('Contents', [])])

                    # Filter based on user input
                    filtered_objects = all_objects
                    if ss_client_code:
                        filtered_objects = [key for key in filtered_objects if ss_client_code.lower() in key.lower()]
                    if ss_description:
                        filtered_objects = [key for key in filtered_objects if ss_description.lower() in key.lower()]
                    
                    st.session_state.s3_search_results = filtered_objects
                    if not st.session_state.s3_search_results:
                        st.info("No matching files found in S3 for the given criteria.")
                except Exception as e:
                    st.error(f"Error searching S3: {e}")
                    st.session_state.s3_search_results = []

        # Display S3 Results and actions
        if st.session_state.get('s3_search_results'):
            st.subheader("Search Results")
            s3_filenames = [key.split('/')[-1] for key in st.session_state.s3_search_results]
            
            if s3_filenames:
                selected_s3_file_display = st.radio("Select a file to download:", s3_filenames, key="selected_s3_radio")
                if st.button("Open Selected File", key="open_s3_file"):
                    selected_s3_key = next((key for key in st.session_state.s3_search_results if key.endswith(selected_s3_file_display)), None)
                    if selected_s3_key:
                        try:
                            s3_client = boto3.client('s3')
                            presigned_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': selected_s3_key}, ExpiresIn=3600)
                            link = f'[Click here to download {selected_s3_file_display}]({presigned_url})'
                            st.markdown(link, unsafe_allow_html=True)
                            st.info("""
                                **To upload an updated version:**
                                1. Make your changes in the downloaded Excel file.
                                2. Use the file uploader below to select your updated file.
                                3. Click the **"Upload to S3"** button.
                            """)
                        except Exception as e:
                            st.error(f"Could not generate download link: {e}")

        st.markdown("---")
        st.subheader("Upload New or Updated Summary")
        uploaded_file = st.file_uploader("Choose an Excel file to upload", type=['xlsx'])

        if st.button("Upload to S3", key="ss_upload_s3"):
            if uploaded_file is not None:
                try:
                    s3_client = boto3.client('s3')
                    s3_file_name = f"{S3_FOLDER_PREFIX}{uploaded_file.name}"
                    
                    df = pd.read_excel(uploaded_file)
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

                    try:
                        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_file_name)
                        st.session_state.confirm_replace = s3_file_name
                        st.session_state.uploaded_file_data = processed_file_data
                        st.rerun()
                    except s3_client.exceptions.ClientError as e:
                        if e.response['Error']['Code'] == '404':
                            s3_client.upload_fileobj(io.BytesIO(processed_file_data), S3_BUCKET_NAME, s3_file_name)
                            st.success(f"Successfully uploaded locked file to s3://{S3_BUCKET_NAME}/{s3_file_name}")
                            st.rerun()
                        else:
                            raise
                except Exception as e:
                    st.error(f"An error occurred during upload: {e}")
            else:
                st.warning("Please choose a file to upload first.")
