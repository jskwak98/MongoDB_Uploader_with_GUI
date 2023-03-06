import pickle
import time
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from observer import FileObserver
from mongoDBupdater import MongoUpdater
from localDBmanager import LocalDBManager

class SaveGUI(QtWidgets.QWidget):

    searchQuery = Signal(str)

    def __init__(self):
        super().__init__()
        with open("title.txt", "r", encoding = 'UTF-8') as f:
            title = f.readline()
            print(title)
        self.setWindowTitle(title)

        self.turned_on = False

        self.init_threads()
        self.init_auto_save()
        self.init_manual_save()
        self.init_search_frame()

        # 전체 Frame 만들기
        self.layout = QtWidgets.QHBoxLayout(self)
        leftside = QWidget()
        leftview = QVBoxLayout()
        leftview.addWidget(self.autoframe)
        leftview.addWidget(self.manualframe)
        leftside.setLayout(leftview)

        

        self.layout.addWidget(leftside)
        leftside.resize(380, 380)
        self.layout.addWidget(self.searchframe)

    def init_threads(self):
        self.monitor_thread = QThread()
        self.observer = FileObserver()
        self.observer.moveToThread(self.monitor_thread)
        self.monitor_thread.started.connect(self.observer.run)
        #self.monitor_thread.finished.connect(self.monitor_thread.deleteLater)

        self.db_thread = QThread()
        self.manager = LocalDBManager()

        # only updater use db_thread, use updater with the main thread
        self.updater = MongoUpdater()
        self.updater.moveToThread(self.db_thread)
        self.manager.savefileUpdated.connect(self.updater.update)
        self.updater.dbUploaded.connect(self.manager.after_upload)
        self.manager.changeTime.connect(self.settime)

        # later change it into manager's slots
        self.observer.fileDeleted.connect(self.manager.handlefileDeleted)
        self.observer.fileMoved.connect(self.manager.handlefileMoved)
        self.observer.fileCreated.connect(self.manager.handlefileCreated)
        self.observer.fileModified.connect(self.manager.handlefileModified)

        # for search connect searchQuery signal with updater
        self.searchQuery.connect(self.updater.search)

        # to update table with search result from updater
        self.updater.searchResults.connect(self.update_table)

        self.db_thread.start()

    def init_auto_save(self):
        # 자동저장 frame 만들기
        self.autoframe = QGroupBox("자동저장 및 업로드")

        autoview = QVBoxLayout()

        # Status Point
        self.dot = QLabel("●")
        self.dot.setFont(QtGui.QFont("Gothic", 15))
        self.dot.setStyleSheet("Color : red")
        self.dot.setAlignment(QtCore.Qt.AlignCenter)

        # set autoview
        buttons = QWidget()
        buttonview = QHBoxLayout()
        self.autosave = QPushButton("자동저장 시작")
        self.autosave_stop = QPushButton("자동저장 중단")
        buttonview.addWidget(self.autosave)
        buttonview.addWidget(self.autosave_stop)
        buttons.setLayout(buttonview)

        # make autoview
        autoview.addStretch(2)
        autoview.addWidget(self.dot)
        autoview.addStretch(1)
        autoview.addWidget(buttons)
        autoview.addStretch(2)

        self.autoframe.setLayout(autoview)

        self.autosave.clicked.connect(self.save_start)
        self.autosave_stop.clicked.connect(self.save_stop)

    def init_search_frame(self):
        # Search 용 frame 만들기
        self.searchframe = QGroupBox("DB 검색 및 수정")

        searchs = QWidget()
        searchview = QVBoxLayout()

        # search lineinput
        sbview = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('병명 입력')
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self.search)

        sbview.addWidget(self.search_box)
        sbview.addWidget(self.search_btn)
        searchs.setLayout(sbview)

        # search table
        self.search_table = QTableWidget()
        self.search_table.setColumnCount(5)

        table_column = ["병명", "파일명", "마지막 수정일자", "다운로드", "삭제"]
        self.search_table.setHorizontalHeaderLabels(table_column)

        # add all widgets
        searchview.addWidget(searchs)
        searchview.addWidget(self.search_table)

        self.searchframe.setLayout(searchview)


    
    def init_manual_save(self):
        # 수동저장 frame 만들기
        self.manualframe = QGroupBox("수동저장 및 업로드")
        manualview = QVBoxLayout()

        guide = QLabel("마지막 저장 시각")
        guide.setAlignment(QtCore.Qt.AlignCenter)

        self.last_time = QLabel("-") # pickle로 시간 가져오면서
        self.last_time.setFont(QtGui.QFont("Gothic", 15))
        self.last_time.setAlignment(QtCore.Qt.AlignCenter)

        self.manualsave = QPushButton("수동저장")

        manualview.addStretch(1)
        manualview.addWidget(guide)
        manualview.addWidget(self.last_time)
        manualview.addStretch(2)
        manualview.addWidget(self.manualsave)
        manualview.addStretch(1)
        self.manualframe.setLayout(manualview)

        self.manualsave.clicked.connect(self.manual_save)

    def closeEvent(self, event):
        self.db_thread.quit()
        self.db_thread.wait(1500)
        if self.turned_on:
            self.observer.stop()
            self.monitor_thread.quit()
            self.monitor_thread.wait(1500)
        event.accept()

    def search(self):
        self.searchQuery.emit(self.search_box.text())

    def update_table(self, results):
        pass


    def readDB(self):
        # based on the last read time from DB, get updated elements which will not be in your local db
        # TODO
        pass


    @QtCore.Slot()
    def save_start(self):
        if self.turned_on:
            return
        else:
            self.dot.setStyleSheet("Color : green")
            self.save()
            self.monitor_thread.start()
            #print("Start Saving")
            self.turned_on = True

    @QtCore.Slot()
    def save_stop(self):
        if self.turned_on:
            self.dot.setStyleSheet("Color : red")
            #print("Stop Saving")
            self.observer.stop()
            self.monitor_thread.quit()
            self.monitor_thread.wait(2500)
            self.turned_on = False
        else:
            return
    
    @QtCore.Slot()
    def manual_save(self):
        if self.turned_on:
            QMessageBox.warning(self, '수동저장 불가', '자동저장 기능을 사용중에는 수동저장이 불가합니다.')
        else:
            self.save()
    
    @QtCore.Slot()
    def save(self):
        self.manager.save_current_state_to_savefile()
    
    @QtCore.Slot()
    def settime(self):
        now = time.strftime('%y-%m-%d %H:%M:%S')
        self.last_time.setText(now)