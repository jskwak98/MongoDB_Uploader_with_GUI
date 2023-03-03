import sys
from gui import SaveGUI
from PySide6 import QtWidgets


app = QtWidgets.QApplication([])

gui = SaveGUI()
gui.resize(782, 400)
gui.show()

sys.exit(app.exec())