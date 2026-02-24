from nicegui import ui
import pandas as pd
from datetime import date
import logging
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

        # --- Packaging Editor (Placeholder) ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Packaging (primary only)')
            ui.label('Packaging editor will go here.')

        # --- Master Tests (Placeholder) ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Step 1: Define Master Tests')
            ui.label('Master Tests UI will go here.')

        # --- Storage Conditions & Timepoints (Placeholder) ---
        with ui.card().classes('w-full'):
            ui.card_section().classes('bg-blue-grey-10 text-white').header().add_slot('default').set_text('Storage Conditions and Timepoints Selection')
            ui.label('Storage Conditions UI will go here.')
        
        # --- Action Buttons (Placeholder) ---
        with ui.row().classes('w-full justify-around q-mt-md'):
            ui.button('Generate Schedule Template')
            ui.button('Upload Completed Schedule')
            ui.button('Save Study')
