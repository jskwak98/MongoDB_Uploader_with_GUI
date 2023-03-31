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
from detailWindow import LookWindow
from logWindow import LogWindow

class SaveGUI(QtWidgets.QWidget):

    searchQuery = Signal(str)
    delDocID = Signal(str, str)

    def __init__(self):
        super().__init__()
        title = "질병백서 DB 관리 프로그램"
        self.setWindowTitle(title)

        self.turned_on = False
        self.look = None

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

        # use manager thread since it takes long time
        self.db_thread = QThread()
        self.manager_thread = QThread()
        self.manager = LocalDBManager()
        self.manager.moveToThread(self.manager_thread)

        # only updater use db_thread, use updater with the main thread
        self.updater = MongoUpdater()
        self.updater.moveToThread(self.db_thread)
        self.manager.savefileUpdated.connect(self.updater.update)
        self.updater.dbUploaded.connect(self.manager.after_upload)
        self.updater.nothingToUpload.connect(self.no_upload)
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

        # online db synchronization connected
        self.manager.syncOnlineData.connect(self.after_sync)
        self.updater.onlineSyncData.connect(self.manager.get_online_data_to_overwrite)

        # number of search results
        self.updater.docCount.connect(self.showDocCount)

        # manager thread start
        self.manager_thread.start()
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
        self.search_box.setPlaceholderText('병명 검색, # 으로 총 문서 수 확인, 빈칸으로 오타검정')
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self.search)
        self.search_box.returnPressed.connect(self.search)

        sbview.addWidget(self.search_box)
        sbview.addWidget(self.search_btn)
        searchs.setLayout(sbview)
        

        # search table
        self.search_table = QTableWidget()
        self.search_table.setColumnCount(2)

        table_column = ["병명", "상세보기"]
        self.search_table.setHorizontalHeaderLabels(table_column)

        header = self.search_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
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
        self.sync_btn = QPushButton("온라인DB 기준으로 동기화")

        manualview.addStretch(1)
        manualview.addWidget(guide)
        manualview.addWidget(self.last_time)
        manualview.addStretch(2)
        manualview.addWidget(self.manualsave)
        manualview.addStretch(2)
        manualview.addWidget(self.sync_btn)
        manualview.addStretch(1)
        self.manualframe.setLayout(manualview)

        self.manualsave.clicked.connect(self.manual_save)
        self.sync_btn.clicked.connect(self.sync_with_online_modification)

    def closeEvent(self, event):
        self.manager_thread.quit()
        self.manager_thread.wait(1500)
        self.db_thread.quit()
        self.db_thread.wait(1500)
        if self.turned_on:
            self.observer.stop()
            self.monitor_thread.quit()
            self.monitor_thread.wait(1500)
        event.accept()

    def search(self):
        self.searchQuery.emit(self.search_box.text())

    def update_table(self, results, debugs, isbug):
        if not results:
            # reset table
            while self.search_table.rowCount() > 0 :
                self.search_table.removeRow(0)
            if not isbug:
                QMessageBox.warning(self, '검색결과 없음', f'"{self.search_box.text()}"에 대한 검색결과가 존재하지 않습니다.')
            if isbug:
                QMessageBox.warning(self, '카테고리 오타 없음', "병 분류 오타가 존재하지 않습니다.")
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
                
                # button
                look_btn = QPushButton("상세보기")
                look_btn.clicked.connect(self.table_look)
                self.search_table.setCellWidget(row, 1, look_btn)
            if isbug:
                bugs = "\n".join(debugs)
                QMessageBox.warning(self, '카테고리 오타 발견', f"다음 파일들에서 병 분류 오타가 발생했습니다.\n상세보기 창에서 카테고리를 재설정하고 수정 및 동기화 해주세요.\n{bugs}")
    
    def table_look(self):
        button = self.sender()

        item = self.search_table.indexAt(button.pos())
        data = self.temp_search[item.row()]
        
        if self.look is None:
            self.look = LookWindow(data, self)
            self.look.delDocID.connect(self.updater.delete)
            self.look.searchAgain.connect(self.search)
            self.updater.delete_success.connect(self.look.after_delete)
            self.look.updateDB.connect(self.manager.emit_save)
            self.look.show()
    
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
        
    def no_upload(self):
        QMessageBox.information(self, '업로드할 파일 없음', f'업로드할 파일이 없습니다.\n모든 상태가 최신입니다.')

    def sync_with_online_modification(self):
        if self.turned_on:
            QMessageBox.warning(self, '동기화 불가', '자동저장 기능을 사용중에는 동기화가 불가합니다.')
        else:
            qm = QMessageBox
            reply = qm.question(self, '온라인과 동기화', f'온라인 DB와 컴퓨터의 엑셀 파일을 동기화합니다.\n웹사이트를 통해 수정한 내역들이 모두 엑셀 파일에 덮어써집니다.\n다소 시간이 소요될 수 있습니다.\n진행하시겠습니까?', qm.Yes | qm.No)
            if reply == qm.Yes:
                self.updater.get_online_sync_data()
            else:
                qm.information(self, '취소', '동기화를 취소합니다.')
    
    def after_sync(self, overwritten_files): 
        if not overwritten_files:
            qm = QMessageBox
            qm.information(self, '동기화 완료', "동기화가 완료되었습니다.\n덮어씌워진 파일은 없습니다.")
        else:
            info = ""
            for hist in overwritten_files:
                dn, path = hist
                info += f"\n병명 : {dn} || 경로 : {path}"
            qm = QMessageBox
            qm.information(self, '동기화 완료', "동기화가 완료되었습니다.\n덮어씌워진 파일은 다음과 같습니다." + info)

    def showDocCount(self, docCount):
        qm = QMessageBox
        qm.information(self, '총 문서 수', f"등록된 총 문서 수는 {docCount}개 입니다.")


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
    def settime(self, added, modified):
        now = time.strftime('%y-%m-%d %H:%M:%S')
        self.last_time.setText(now)
        self.log = LogWindow(added, modified)
        self.log.searchAgain.connect(self.search)
        self.log.show()
        self.log.raise_()