from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *


class LogWindow(QWidget):
    searchAgain = Signal()

    def __init__(self, added, modified):
        super().__init__()
        self.setWindowTitle("DB 업데이트 내역")

        layout = QVBoxLayout()

        add_label = QLabel("DB에 추가된 항목")
        add_label.setStyleSheet("font-weight: bold")
        self.added = QTextEdit()
        self.added.setText(self.parse(added))
        self.added.setReadOnly(True)

        modified_label = QLabel("DB에 수정된 항목")
        modified_label.setStyleSheet("font-weight: bold")
        self.modified = QTextEdit()
        self.modified.setText(self.parse(modified))
        self.modified.setReadOnly(True)

        exit_btn = QPushButton("확인")
        exit_btn.clicked.connect(self.close)

        layout.addWidget(add_label)
        layout.addWidget(self.added)
        layout.addWidget(modified_label)
        layout.addWidget(self.modified)
        layout.addWidget(exit_btn)

        self.resize(800,600)
        self.setLayout(layout)
    
    def parse(self, data):
        text = ""
        for d in data:
            dn, path = d
            dn = dn.replace("\n", ' ')
            text += f"병명 : {dn} | 경로 : {path}\n"
        if not text:
            text = "해당사항 없음"
        return text
    
    def closeEvent(self, event):
        self.searchAgain.emit()
        event.accept()

if __name__ == "__main__":
    import sys

    
    app = QApplication([])
    added = [('거대유방증  (유방비대증)', '비밀.path'), ('폐렴구균', '폐렴구균.path')]
    modified = [('부신종양(부신선종)', '부신.path')]

    gui = LogWindow(added, modified)
    #gui.resize(400, 700)
    gui.show()

    sys.exit(app.exec())