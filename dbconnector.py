from pymongo import MongoClient, InsertOne, DeleteOne, UpdateOne
import glob, os
import pickle
import openpyxl
from pprint import pprint
from typing import Union, List, Dict

from pymongo.errors import ConnectionFailure

from PySide6.QtCore import QObject, Signal, Slot


class ExcelParser(QObject):
    """
    ExcelParser does
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
        self.dirpath = "./save"
        self.datapath = "./save/savefile"

        if not os.path.exists(self.dirpath):
            os.makedirs("save")

        if not os.path.exists(self.datapath):
            self.read_and_parse()
            self.make_savefile()

    def read_and_parse(self):
        # read and parse excel files into usable data and save it into self.data
        self.data = {}

        for excel_path in glob.iglob('**\*.xlsx', recursive=True):
            filedex = excel_path.split('\\')[-1]
            if filedex not in self.data and '$' not in filedex:
                docu = self.read(excel_path)
                if docu:
                    self.data[filedex] = docu

    def read(self, excel_path):
        try:
            excel_document = openpyxl.load_workbook(excel_path)
            sheet = excel_document['Sheet1']
            if sheet.max_row == 4 and sheet.max_col == 4:
                docu = dict()
                docu["disease_name"] = sheet['A2'].value
                docu["category"] = sheet['D2'].value
                docu["definition"] = sheet['C2'].value
                docu["cause_symptom"] = sheet['C3'].value
                docu["care"] = sheet['C4'].value
            return docu

        except:
            return

    def make_savefile(self):
        # make self.savefile and save it as pickle file
        self.read_and_parse()
        for filename in self.data:
            self.savefile[filename] = {"flag" : 1, "data" : self.data[filename]}
        self.write_savefile()

    def read_savefile(self):
        # read pickle file and save it in self.savefile
        with open(self.datapath, 'rb') as f:
            self.savefile = pickle.load(f)
    
    def synchronize(self):
        # read file system and synchronize it with self.savefile
        for filename in self.data:
            if filename not in self.savefile:
                self.savefile[filename] = {"flag" : 1, "data" : self.data[filename]}
            else:
                for item in self.data[filename]:
                    if self.data[filename][item] != self.savefile[filename]["data"][item]:
                        self.savefile[filename]["flag"] = 2 # update
                        self.savefile[filename]["data"][item] = self.data[filename][item] # change data into currently read one
        
        # documents need to be deleted
        del_keys = set(self.savefile.keys()) - set(self.data.keys())
        for filename in del_keys:
            self.savefile[filename]["flag"] = 3
        
    def write_savefile(self):
        # write pickle file based on self.savefile
        with open(self.datapath, 'wb') as f:
            pickle.dump(self.savefile, f)

    def export_savefile(self):
        # on demand savefile update
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
    
    # Slots for auto save
    def handlefileDeleted(self, src):
        # file deleted
        src = src.split('\\')[-1]
        if src.endswith(".xlsx"):
            #print(f"Deleted {src}")
            self.savefile[src]["flag"] = 3
            self.savefileUpdated.emit(self.savefile)
            
    def handlefileMoved(self, src, dest):
        # file moved, only deals with the filename changes
        src = src.split('\\')[-1]
        dest = dest.split('\\')[-1]
        if src.endswith(".xlsx") and dest.endswith(".xlsx") and src != dest:
            #print(f"filename changed {src} to {dest}")
            self.savefile[dest] = self.savefile[src]
            del self.savefile[src]
            self.write_savefile()
    
    def handlefileCreated(self, src):
        # file created
        if src.endswith(".xlsx"):
            #print(f"Created {src}")
            docu = self.read(src)
            if docu:
                src = src.split('\\')[-1]

                self.savefile[src] = {"flag" : 1, "data" : docu}
                self.savefileUpdated.emit(self.savefile)

    def handlefileModified(self, src):
        # file modified
        if src.endswith(".xlsx"):
            #print(f"modified {src}")
            docu = self.read(src)
            if docu:
                src = src.split('\\')[-1]
                isupdate = False
                for item in docu:
                    if docu[item] != self.savefile[src]["data"][item]:
                        self.savefile[src]["flag"] = 2 # update
                        self.savefile[src]["data"][item] = docu[item]
                        isupdate = True
                if isupdate:
                    self.savefileUpdated.emit(self.savefile)


class MongoUpdater(QObject):
    """
    MongoUpdater does
    1. update MongoDB by referring to the data of excel parser
    2. and send result to ExcelParser
    """
    # needs to be connected to ExcelParser's after upload
    dbUploaded = Signal(dict)
    searchResults = Signal(dict)

    def __init__(self):
        super().__init__()
        with open("secret.txt", "r") as f:
            URI = f.readline()

        self.client = MongoClient(URI)
        try:
            self.client.admin.command('ismaster')
            self.db = self.client.illcyclopedia
        except ConnectionFailure:
            print("Server Not Available")

    def search(self, searchQuery):
        pass

    def update(self, update_data : Dict[str, Union[str, int, Dict[str, str]]]):
        operations = []
        delfiles = []
        for filename in update_data:
            flag = update_data[filename]["flag"]
            # Operation Depending on Flag, 0 : NOP, 1 : Create, 2 : Update, 3 : Delete
            if flag == 0:
                continue
            elif flag == 1:
                operations.append(InsertOne(update_data[filename]['data']))
                update_data[filename]['flag'] = 0
            elif flag == 2:
                operations.append(UpdateOne({'_id': update_data[filename]['data']['_id']}, {'$set': update_data[filename]['data']}))
                update_data[filename]['flag'] = 0
            elif flag == 3:
                operations.append(DeleteOne({'_id': update_data[filename]['data']['_id']}))
                delfiles.append(filename)

        if operations:
            result = self.db.diseases.bulk_write(operations)
            success = not result.bulk_api_result['writeErrors']

            if success:
                for filename in delfiles:
                    del update_data[filename]
                #print("update done, move to EP for savefile write")
                self.dbUploaded.emit(update_data)



if __name__ == "__main__":
    ep = ExcelParser()
    md = MongoUpdater()
    
    ep.savefileUpdated.connect(md.update)
    md.dbUploaded.connect(ep.after_upload)

    ep.export_savefile()
    #pprint(ep.savefile)