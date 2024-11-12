import logging
from datetime import datetime

# Konfiguriere Logging mit Datum und Uhrzeit im Dateinamen
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_erstellt.log")
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(message)s')

from gui_app import GUIApp

if __name__ == "__main__":
    GUIApp()
