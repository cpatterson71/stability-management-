from nicegui import ui, app
import pandas as pd
import logging
import boto3
import webbrowser
import os
import io
from tabs.utils import S3_BUCKET_NAME, S3_FOLDER_PREFIX

def tab3_summary_ui(conn):
    app.storage.user.s3_search_results_keys = []
    app.storage.user.s3_search_results_display = []
    app.storage.user.selected_s3_file_display = None # To bind the ui.select value
    app.storage.user.uploaded_file_path = None # For upload functionality

    with ui.column().classes('w-full'):
        ui.label('Stability Summary').classes('text-2xl font-bold')

        # --- Search Section ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Search for Stability Summary in S3')
            
            ui.input('Client Code').bind_value(app.storage.user, 'ss_client_code', '').classes('w-full')
            ui.input('Description').bind_value(app.storage.user, 'ss_description', '').classes('w-full')

            async def search_s3():
                app.storage.user.s3_search_results_keys = [] # Clear previous keys
                app.storage.user.s3_search_results_display = [] # Clear previous display names
                try:
                    s3_client = boto3.client('s3')
                    
                    all_objects = []
                    paginator = s3_client.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=S3_FOLDER_PREFIX)
                    for page in pages:
                        all_objects.extend([obj['Key'] for obj in page.get('Contents', [])])

                    filtered_objects = all_objects
                    if app.storage.user.ss_client_code:
                        filtered_objects = [key for key in filtered_objects if app.storage.user.ss_client_code.lower() in key.lower()]
                    if app.storage.user.ss_description:
                        filtered_objects = [key for key in filtered_objects if app.storage.user.ss_description.lower() in key.lower()]
                    
                    app.storage.user.s3_search_results_keys = filtered_objects
                    app.storage.user.s3_search_results_display = [key.split('/')[-1] for key in filtered_objects]
                    
                    if not app.storage.user.s3_search_results_keys:
                        ui.notify("No matching files found in S3.", type='info')
                    ui.update(results_select) # Update the ui.select component
                except Exception as e:
                    ui.notify(f"Error searching S3: {e}", type='negative')
                    app.storage.user.s3_search_results_keys = []
                    app.storage.user.s3_search_results_display = []
                    ui.update(results_select)


            ui.button('Search in S3', on_click=search_s3)

            ui.label('Search Results:').classes('mt-md')
            results_select = ui.select(
                options=app.storage.user.s3_search_results_display,
                label='Select a file to download'
            ).bind_value(app.storage.user, 'selected_s3_file_display').classes('w-full')

            async def download_from_s3():
                if not app.storage.user.selected_s3_file_display:
                    ui.notify("Please select a file to download.", type='warning')
                    return

                selected_key = None
                for key in app.storage.user.s3_search_results_keys:
                    if key.endswith(app.storage.user.selected_s3_file_display):
                        selected_key = key
                        break
                
                if not selected_key:
                    ui.notify("Selected file key not found.", type='negative')
                    return

                try:
                    s3_client = boto3.client('s3')
                    presigned_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': selected_key}, ExpiresIn=3600)
                    webbrowser.open(presigned_url)
                    ui.notify(f"Downloading {app.storage.user.selected_s3_file_display}", type='positive')
                except Exception as e:
                    ui.notify(f"Could not generate download link: {e}", type='negative')

            ui.button('Download Selected File', on_click=download_from_s3)

        # --- Upload Section ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Upload New or Updated Summary')
            
            async def upload_file_to_s3(e):
                if not e.content:
                    ui.notify("No file content received.", type='warning')
                    return

                try:
                    s3_client = boto3.client('s3')
                    file_name = e.name
                    s3_file_name = f"{S3_FOLDER_PREFIX}{file_name}"

                    # Process the file to lock it, similar to the Streamlit version
                    df = pd.read_excel(e.content)
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
                        if not await ui.run_javascript(f'confirm("The file \'{file_name}\' already exists in S3. Do you want to replace it?")', timeout=5.0):
                            ui.notify("Upload cancelled.", type='info')
                            return
                    except s3_client.exceptions.ClientError as exc:
                        if exc.response['Error']['Code'] != '404':
                            raise # Re-raise other client errors

                    # Upload the file
                    s3_client.upload_fileobj(io.BytesIO(processed_file_data), S3_BUCKET_NAME, s3_file_name)
                    ui.notify(f"Successfully uploaded locked file to s3://{S3_BUCKET_NAME}/{s3_file_name}", type='positive')
                    
                    # Refresh search results
                    await search_s3()

                except Exception as err:
                    ui.notify(f"An error occurred during upload: {err}", type='negative')

            ui.upload(label="Choose an Excel file to upload", auto_upload=True, on_upload=upload_file_to_s3).props('accept=".xlsx"')


