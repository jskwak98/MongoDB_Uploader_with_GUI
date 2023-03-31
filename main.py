import sys
from gui import SaveGUI
from PySide6.QtWidgets import QApplication

app = QApplication([])

gui = SaveGUI()
gui.resize(700, 400)
gui.show()

sys.exit(app.exec())
