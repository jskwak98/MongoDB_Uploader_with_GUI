from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from write_excel import write_excel
from copy import copy


class LookWindow(QWidget):
    delDocID = Signal(str, str)
    searchAgain = Signal()
    updateDB = Signal()

    def __init__(self, data, parent=None):
        super().__init__()
        if parent:
            self.parent = parent
        self.data = data.copy()
        self.filename = data['filename']
        self.disease = data['disease_name']
        self.cate = data['category']
        self.defi = data['definition']
        self.cs = data['cause_symptom']
        self.care = data['care']

        self.setWindowTitle(self.disease)
        
        layout = QVBoxLayout()

        d_label = QLabel("병명")
        d_label.setStyleSheet("font-weight: bold")
        self.disease_in = QLineEdit()
        self.disease_in.setText(self.disease)

        c_label = QLabel("분류")
        c_label.setStyleSheet("font-weight: bold")
        self.cate_in = QComboBox()
        cates = ['피부/미용/성형 질환', '유전질환', '건강증진', '혈액/종양 질환', '눈/코/귀/인후/구강/치아', 
                '신장/비뇨기계 질환', '여성질환', '호흡기질환', '기타', '뇌/신경/정신질환', '근골격질환', 
                '응급질환', '소아/신생아 질환', '소화기계 질환', '순환기(심혈관계)질환', '감염성질환', '유방/내분비질환']
        for cate in cates:
            self.cate_in.addItem(cate)
        self.cate_in.setCurrentText(self.cate)

        de_label = QLabel("질병 정의")
        de_label.setStyleSheet("font-weight: bold")
        self.defi_in = QTextEdit()
        self.defi_in.setText(self.defi)

        cs_label = QLabel("원인 및 증상")
        cs_label.setStyleSheet("font-weight: bold")
        self.cs_in = QTextEdit()
        self.cs_in.setText(self.cs)

        ca_label = QLabel("예방, 치료 및 관리")
        ca_label.setStyleSheet("font-weight: bold")
        self.care_in = QTextEdit()
        self.care_in.setText(self.care)

        buttons = QWidget()
        button_layout =QHBoxLayout()

        self.modify_btn = QPushButton("수정 및 동기화")
        self.modify_btn.clicked.connect(self.modify)
        self.dld_btn = QPushButton("다운로드")
        self.dld_btn.clicked.connect(self.download)
        self.del_btn = QPushButton("삭제")
        self.del_btn.clicked.connect(self.delete)
        self.exit_btn = QPushButton("닫기")
        self.exit_btn.clicked.connect(self.close)

        button_layout.addWidget(self.modify_btn)
        button_layout.addWidget(self.dld_btn)
        button_layout.addWidget(self.del_btn)
        button_layout.addWidget(self.exit_btn)

        buttons.setLayout(button_layout)

        layout.addWidget(d_label)
        layout.addWidget(self.disease_in)
        layout.addWidget(c_label)
        layout.addWidget(self.cate_in)
        layout.addWidget(de_label)
        layout.addWidget(self.defi_in)
        layout.addWidget(cs_label)
        layout.addWidget(self.cs_in)
        layout.addWidget(ca_label)
        layout.addWidget(self.care_in)
        layout.addWidget(buttons)

        self.resize(400,700)
        self.setLayout(layout)
    
    def modify(self):
        if self.parent.turned_on:
            QMessageBox.warning(self, '수정/동기화 불가', '자동저장 기능을 사용하는 중에는 수정/동기화가 불가합니다.')
        else:
            # Modify self.data firstly, then change savefile, rewrite local excel(if exists), then modify remote.
            filename = self.filename
            manager = self.parent.manager
            disease = self.data['disease_name']

            # modification of self.data
            self.data['disease_name'] = self.disease_in.text()
            self.data['category'] = self.cate_in.currentText()
            self.data['definition'] = self.defi_in.toPlainText()
            self.data['cause_symptom'] = self.cs_in.toPlainText()
            self.data['care'] = self.care_in.toPlainText()

            # Change Savefile and Rewrite Local if exists            
            if filename in manager.savefile and manager.check_deleted_recreated(filename):
                lp = manager.savefile[filename]["local_path"]
                qm = QMessageBox
                reply = qm.question(self, '덮어쓰기', f'"{disease}"의 데이터가 {lp}에 존재합니다.\n수정한 데이터로 덮어쓰시겠습니까?', qm.Yes | qm.No)
                if reply == qm.Yes:
                    if write_excel(self.data, lp):
                        manager.savefile[filename] = {"flag" : 2, "is_deleted" : False, "local_path": lp, "data" : self.data}
                        manager.write_savefile()
                        qm.information(self, '덮어쓰기 완료', f'{lp}에 {disease}의 데이터를 성공적으로 덮어썼습니다.')
                    else:
                        qm.information(self, '덮어쓰기 실패', f'덮어쓰기 실패, 다운로드를 재시도하거나,\n수동저장 후 재시도 해주세요.')
                else:
                    qm.information(self, '', '덮어쓰지 않습니다. 데이터를 수정하지 않습니다.')
            # Online Data
            else:
                manager.savefile[filename] = {"flag" : 2, "is_deleted" : True, "local_path": "./"+filename, "data" : self.data}
                manager.write_savefile()
            
            # modify remote based on the savefile
            self.updateDB.emit()

    def download(self):
        if self.parent.turned_on:
            QMessageBox.warning(self, '다운로드 불가', '자동저장 기능을 사용하는 중에는 다운로드가 불가합니다.')
        else:
            filename = self.filename
            manager = self.parent.manager
            disease = self.data['disease_name']
            # overwrite
            if filename in manager.savefile and manager.check_deleted_recreated(filename):
                lp = manager.savefile[filename]["local_path"]
                qm = QMessageBox
                reply = qm.question(self, '덮어쓰기', f'"{disease}"의 데이터가 {lp}에 존재합니다.\n온라인 DB의 데이터로 덮어쓰시겠습니까?', qm.Yes | qm.No)
                if reply == qm.Yes:
                    if write_excel(self.data, lp):
                        manager.savefile[filename] = {"flag" : 0, "is_deleted" : False, "local_path": lp, "data" : self.data}
                        manager.write_savefile()
                        qm.information(self, '덮어쓰기 완료', f'{lp}에 {disease}의 데이터를 성공적으로 덮어썼습니다.')
                    else:
                        qm.information(self, '덮어쓰기 실패', f'덮어쓰기 실패, 다운로드를 재시도하거나,\n수동저장 후 재시도 해주세요.')
                else:
                    qm.information(self, '', '덮어쓰지 않습니다.')
            # New Download
            else:
                qm = QMessageBox
                reply = qm.question(self, '다운로드', f'"{disease}"의 데이터를 다운로드 하시겠습니까?', qm.Yes | qm.No)
                if reply == qm.Yes:
                    if write_excel(self.data):
                        manager.savefile[filename] = {"flag" : 0, "is_deleted" : False, "local_path": "./"+filename, "data" : self.data}
                        manager.write_savefile()
                        qm.information(self, '다운로드 완료', f'{filename}으로 {disease}의 데이터를 다운로드 했습니다.')
                    else:
                        qm.information(self, '다운로드 실패', f'다운로드를 실패했습니다.')
                else:
                    qm.information(self, '', '다운로드하지 않습니다.')
    
    def delete(self):
        if self.parent.turned_on:
            QMessageBox.warning(self, '삭제작업 불가', '자동저장 기능을 사용하는 중에는 DB 삭제가 불가합니다.')
        else:
            disease = self.data['disease_name']
            qm = QMessageBox
            reply = qm.question(self, 'DB에서 삭제', f'"{disease}"를 온라인 DB에서 삭제합니다.\n이는 복구가 불가능 합니다.\n진행하시겠습니까?', qm.Yes | qm.No)

            if reply == qm.Yes:
                self.delDocID.emit(self.data['_id'], self.data['filename'])
            else:
                qm.information(self, '', '삭제하지 않았습니다.')
    
    def after_delete(self, success, filename):
        qm = QMessageBox
        if success:
            qm.information(self, '삭제완료', "삭제되었습니다.")
            self.close()
        else:
            qm.information(self, '삭제실패', "삭제되지않았습니다.") 
    
    def closeEvent(self, event):
        self.parent.look = None
        event.accept()
        


    
if __name__ == "__main__":
    import sys

    
    app = QApplication([])
    data = { 'filename' : '감기.xlsx',
            'disease_name' : '감기',
            'category' : '호흡기질환',
            'definition' : '감기는 아픈 병이다\n\n\n\n룰루랄라',
            'cause_symptom' : '차게 자면 걸린다. 콜록콜록 한다.',
            'care' : '따뜻한 물 마시고 코코낸내하면 좋겠다. \n 그 원인은 다음과 같다. \n 1. you get strong as you do coconenne'
    }

    gui = LookWindow(data)
    gui.resize(400, 700)
    gui.show()

    sys.exit(app.exec())