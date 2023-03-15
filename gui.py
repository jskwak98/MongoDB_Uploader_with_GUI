import pickle
import time
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *

from observer import FileObserver
from mongoDBupdater import MongoUpdater
from localDBmanager import LocalDBManager
from write_excel import write_excel

class SaveGUI(QtWidgets.QWidget):

    searchQuery = Signal(str)
    delDocID = Signal(str, str)

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

        # initialize with db data
        self.manager.giveDBdata.connect(self.updater.new_client_init_data)
        self.updater.hereDBdata.connect(self.manager.init_savefile)

        # later change it into manager's slots
        self.observer.fileDeleted.connect(self.manager.handlefileDeleted)
        self.observer.fileMoved.connect(self.manager.handlefileMoved)
        self.observer.fileCreated.connect(self.manager.handlefileCreated)
        self.observer.fileModified.connect(self.manager.handlefileModified)

        # for search connect searchQuery signal with updater
        self.searchQuery.connect(self.updater.search)

        # to update table with search result from updater
        self.updater.searchResults.connect(self.update_table)

        # deletion of DB needs to be connected
        self.delDocID.connect(self.updater.delete)
        self.updater.delete_success.connect(self.after_delete)

        self.db_thread.start()
        self.manager.init_with_DB()

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
        self.search_table.setColumnCount(4)

        table_column = ["병명", "파일명", "다운로드", "삭제"]
        self.search_table.setHorizontalHeaderLabels(table_column)

        header = self.search_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
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
        if not results:
            # reset table
            while self.search_table.rowCount() > 0 :
                self.search_table.removeRow(0)
            QMessageBox.warning(self, '검색결과 없음', f'"{self.search_box.text()}"에 대한 검색결과가 존재하지 않습니다.')
        else:
            self.temp_search = results
            # reset table
            while self.search_table.rowCount() > 0 :
                self.search_table.removeRow(0)
            # add result
            for result in self.temp_search:
                row = self.search_table.rowCount()
                self.search_table.insertRow(row)
                self.search_table.setItem(row, 0, QTableWidgetItem(result['disease_name']))
                self.search_table.setItem(row, 1, QTableWidgetItem(result['category']))
                
                # buttons
                dld_btn = QPushButton("다운로드")
                del_btn = QPushButton("삭제")

                del_btn.clicked.connect(self.table_del)
                dld_btn.clicked.connect(self.table_dld)

                self.search_table.setCellWidget(row, 2, dld_btn)
                self.search_table.setCellWidget(row, 3, del_btn)

    def table_del(self):
        if self.turned_on:
            QMessageBox.warning(self, '삭제작업 불가', '자동저장 기능을 사용하는 중에는 DB 삭제가 불가합니다.')
        else:
            button = self.sender()

            item = self.search_table.indexAt(button.pos())
            data = self.temp_search[item.row()]
            disease = data['disease_name']
            qm = QMessageBox
            reply = qm.question(self, 'DB에서 삭제', f'"{disease}"를 온라인 DB에서 삭제합니다.\n이는 복구가 불가능 합니다.\n진행하시겠습니까?', qm.Yes | qm.No)

            ## TODO -> 실제 삭제와 연결, 그리고 Table Reset하기?
            ## 그냥 Search 한번 더 하면 그만임. 그러면 알아서 update 된다.
            if reply == qm.Yes:
                self.delDocID.emit(data['_id'], data['filename'])
            else:
                qm.information(self, '', '삭제하지 않았습니다.')
    
    def after_delete(self, success, filename):
        qm = QMessageBox
        if success:
            if self.manager.savefile[filename]:
                del self.manager.savefile[filename]
                self.manager.write_savefile()
            qm.information(self, '삭제완료', "삭제되었습니다.")
            # 재검색 및 테이블 재로딩
            self.search()
        else:
            qm.information(self, '삭제실패', "삭제되지않았습니다.")
        

    def table_dld(self):
        if self.turned_on:
            QMessageBox.warning(self, '다운로드 불가', '자동저장 기능을 사용하는 중에는 다운로드가 불가합니다.')
        else:
            button = self.sender()

            item = self.search_table.indexAt(button.pos())
            data = self.temp_search[item.row()]
            
            filename = data['filename']
            disease = data['disease_name']
            # overwrite
            if filename in self.manager.savefile and self.manager.check_deleted_recreated(filename):
                lp = self.manager.savefile[filename]["local_path"]
                qm = QMessageBox
                reply = qm.question(self, '덮어쓰기', f'"{disease}"의 데이터가 {lp}에 존재합니다.\n온라인 DB의 데이터로 덮어쓰시겠습니까?', qm.Yes | qm.No)
                if reply == qm.Yes:
                    if write_excel(data, lp):
                        self.manager.savefile[filename] = {"flag" : 0, "is_deleted" : False, "local_path": lp, "data" : data}
                        self.manager.write_savefile()
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
                    if write_excel(data):
                        self.manager.savefile[filename] = {"flag" : 0, "is_deleted" : False, "local_path": "./"+filename, "data" : data}
                        self.manager.write_savefile()
                        qm.information(self, '다운로드 완료', f'{filename}으로 {disease}의 데이터를 다운로드 했습니다.')
                    else:
                        qm.information(self, '다운로드 실패', f'다운로드를 실패했습니다.')
                else:
                    qm.information(self, '', '다운로드하지 않습니다.')
            
        



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