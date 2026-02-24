import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout
from PySide6.QtWidgets import QMessageBox

# Add project root to Python path to find modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tabs.utils import create_connection, create_table
from pyside_tabs.tab1_setup import Tab1Setup
from pyside_tabs.tab2_schedule import Tab2Schedule
from pyside_tabs.tab3_summary import Tab3Summary

class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setWindowTitle("Stability Study Management")
        self.setGeometry(100, 100, 1200, 800)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.setup_tabs()

    def setup_tabs(self):
        # Integrate the new Tab1Setup widget
        tab1 = Tab1Setup(self.conn)
        self.tab_widget.addTab(tab1, "Stability Study Setup")

        # Integrate the new Tab2Schedule widget
        tab2 = Tab2Schedule(self.conn)
        self.tab_widget.addTab(tab2, "Stability Schedule")

        # Integrate the new Tab3Summary widget
        tab3 = Tab3Summary(self.conn)
        self.tab_widget.addTab(tab3, "Stability Summary")

    def closeEvent(self, event):
        # Close the database connection when the app closes
        if self.conn:
            self.conn.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- Database Connection ---
    conn = create_connection()

    if conn is None:
        QMessageBox.critical(None, "Database Error", "Error! Cannot create the database connection.")
        sys.exit(1)

    create_table(conn)
    
    window = MainWindow(conn)
    window.show()
    sys.exit(app.exec())
