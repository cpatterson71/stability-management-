from nicegui import ui, app
import os
import sys
import pandas as pd
import logging

# Add project root to Python path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tabs.utils import create_connection, create_table

# --- Database Connection ---
conn = create_connection()

if conn is None:
    logging.critical("Database Error: Cannot create the database connection.")
    sys.exit(1)

create_table(conn)

@ui.page('/')
def main_page():
    with ui.header().classes('items-center justify-between'):
        ui.label('Stability Study Management')
        # Add navigation here later
        
    with ui.left_drawer().classes('bg-blue-100') as left_drawer:
        ui.label('Navigation')
        ui.link('Setup', '/setup')
        ui.link('Schedule', '/schedule')
        ui.link('Summary', '/summary')

    with ui.page('/setup'):
        ui.label('Stability Study Setup (NiceGUI)')
        ui.label('This page will contain the UI for setting up stability studies.')

    with ui.page('/schedule'):
        ui.label('Stability Schedule (NiceGUI)')
        ui.label('This page will display the stability schedule.')

    with ui.page('/summary'):
        ui.label('Stability Summary (NiceGUI)')
        ui.label('This page will handle S3 search and uploads.')

app.on_shutdown(lambda: conn.close() if conn else None)
ui.run()
