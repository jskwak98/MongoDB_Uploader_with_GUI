import glob, os
import pickle
import openpyxl
from pprint import pprint
from typing import Union, List, Dict

from PySide6.QtCore import QObject, Signal, Slot
from bson.objectid import ObjectId


class LocalDBManager(QObject):
    """
    LocalDBManager does
    1. Make local save data that can be directly used to upload on DB server (it will be saved in pickle format)
    2. Compare current file status and synchronize it with the local save data
    3. Parse Excel files into compatible data format that can be used in MongoDB
    """
    # needs to be connected to MongoUpdater's update
    savefileUpdated = Signal(dict)
    changeTime = Signal()

    def __init__(self):
        super().__init__()
        self.savefile = {} # {filename : {"flag" : 0, 1, 2, 3 "data" : {str : str}}}, where flag 0 keep, 1 create, 2 update, 3 delete
        self.data = {} # {filename : {str : str}}
        self.filename_to_filepath = {}
        self.dirpath = "./save"
        self.datapath = "./save/savefile"

        if not os.path.exists(self.dirpath):
            os.makedirs("save")

        if not os.path.exists(self.datapath):
            self.init_savefile()

    def read_and_parse(self):
        # read and parse excel files into usable data and save it into self.data
        self.data = {}

        for excel_path in glob.iglob('**\*.xlsx', recursive=True):
            filedex = excel_path.split('\\')[-1]
            if filedex not in self.data and '$' not in filedex:
                docu = self.read(excel_path)
                if docu:
                    self.data[filedex] = docu
                    self.filename_to_filepath[filedex] = excel_path
            elif filedex in self.data and excel_path != self.data[filedex]['local_path']:
                self.data[filedex]['local_path'] = excel_path

    def read(self, excel_path):
        try:
            excel_document = openpyxl.load_workbook(excel_path)
            sheet = excel_document.worksheets[0]
            if sheet['A1'].value == '질병명' and sheet['B1'].value == '주제' and sheet['D1'].value == '컨텐츠속성': # and sheet['C1'].value == '내용': 몇 개의 파일은 이게 안적힘.
                docu = dict()
                docu["disease_name"] = sheet['A2'].value
                docu["category"] = sheet['D2'].value
                docu["definition"] = sheet['C2'].value
                docu["cause_symptom"] = sheet['C3'].value
                docu["care"] = sheet['C4'].value
                docu["filename"] = excel_path.split('\\')[-1]
                docu["_id"] = str(ObjectId()) # add ID at read side to make it string
            return docu

        except:
            print(f"error occurred at {excel_path}")
            return

    def init_savefile(self):
        # make self.savefile and save it as pickle file
        self.read_and_parse()
        for filename in self.data:
            self.savefile[filename] = {"flag" : 1, "is_deleted" : False, "local_path": self.filename_to_filepath[filename], "data" : self.data[filename]}
        self.write_savefile()

    def read_savefile(self):
        # read pickle file and save it in self.savefile
        with open(self.datapath, 'rb') as f:
            self.savefile = pickle.load(f)
    
    def synchronize(self):
        # read file system and synchronize it with self.savefile
        for filename in self.data:
            if filename not in self.savefile:    
                self.savefile[filename] = {"flag" : 1, "is_deleted" : False, "local_path": self.filename_to_filepath[filename], "data" : self.data[filename]}
            else:
                # if is_deleted = True
                # but new file has created
                # just create it, LOCAL IS ALWAYS RIGHT
                self.savefile[filename]["is_deleted"] = False
                self.savefile[filename]["local_path"] = self.filename_to_filepath[filename]
                for item in self.data[filename]:
                    if item == "_id":
                        continue
                    if self.data[filename][item] != self.savefile[filename]["data"][item]:
                        self.savefile[filename]["flag"] = 2 # update
                        self.savefile[filename]["data"][item] = self.data[filename][item] # change data into currently read one
        
        # documents deleted while detector is off
        # Not going to delete from the DB only because the file does not exist.
        del_keys = set(self.savefile.keys()) - set(self.data.keys())
        for filename in del_keys:
            self.savefile[filename]["is_deleted"] = True
        
    def write_savefile(self):
        # write pickle file based on self.savefile
        with open(self.datapath, 'wb') as f:
            pickle.dump(self.savefile, f)

    def save_current_state_to_savefile(self):
        # on demand savefile update
        # when you manual save and start autosaving
        # save current state to savefile
        # and reflect it to the DB
        self.read_and_parse()
        self.read_savefile()
        self.synchronize()
        self.write_savefile()
        # needs to be connected to MongoUpdater's update
        self.savefileUpdated.emit(self.savefile)

    def after_upload(self, updated_data):
        #print("received updated data, write savefile")
        self.savefile = updated_data
        self.write_savefile()
        self.changeTime.emit()
        #print("savefile saved")
    
    def check_deleted_recreated(self, filename):
        for excel_path in glob.iglob("**\\" + filename, recursive=True):
            self.savefile[filename]["local_path"] = excel_path
            return True
        return False
    
    # Slots for auto save
    def handlefileDeleted(self, src_path):
        # file deleted
        # originally deleted from databse, but now just change is_deleted true
        # it doesn't even have to be uploaded to the DB
        # it's just a local status
        src = src_path.split('\\')[-1]
        if src.endswith(".xlsx"):
            #print(f"Deleted {src}")
            self.savefile[src]["is_deleted"] = True
            self.write_savefile()
            
    def handlefileMoved(self, src_path, dest_path):
        # file moved and source path changes handling
        src = src_path.split('\\')[-1]
        dest = dest_path.split('\\')[-1]
        if src.endswith(".xlsx") and dest.endswith(".xlsx"):
            # To deal with the move operation, updates local path information
            self.savefile[src]["local_path"] = dest_path
            self.filename_to_filepath[dest] = dest_path
            isupdate = False
            # If file name is changed, then deal
            if src != dest:
                #print(f"filename changed {src} to {dest}")
                self.savefile[dest] = self.savefile[src]
                self.savefile[dest]['data']['filename'] = dest
                del self.savefile[src]
                del self.filename_to_filepath[src]
                isupdate = True
            self.write_savefile()
            if isupdate:
                # updates needed when you changed filename
                self.savefileUpdated.emit(self.savefile)
            
    
    def handlefileCreated(self, src_path):
        # file created
        if src_path.endswith(".xlsx"):
            #print(f"Created {src}")
            docu = self.read(src_path)
            if docu:
                src = src_path.split('\\')[-1]
                if self.savefile[src]: # You deleted this file from local before but you created again
                    self.savefile[src]["is_deleted"] = False
                    isupdate = False
                    for item in docu:
                        if docu[item] != self.savefile[src]["data"][item]:
                            self.savefile[src]["flag"] = 2 # update
                            self.savefile[src]["data"][item] = docu[item]
                            isupdate = True
                    if isupdate:
                        self.savefileUpdated.emit(self.savefile)
                else:  # new file created that has not been in this local device
                    self.savefile[src] = {"flag" : 1, "is_deleted" : False, "local_path": src_path, "data" : docu}
                    self.savefileUpdated.emit(self.savefile)

    def handlefileModified(self, src_path):
        # file modified
        if src_path.endswith(".xlsx"):
            #print(f"modified {src}")
            docu = self.read(src_path)
            if docu:
                src = src_path.split('\\')[-1]
                isupdate = False
                for item in docu:
                    if docu[item] != self.savefile[src]["data"][item]:
                        self.savefile[src]["flag"] = 2 # update
                        self.savefile[src]["data"][item] = docu[item]
                        isupdate = True
                if isupdate:
                    self.savefileUpdated.emit(self.savefile)