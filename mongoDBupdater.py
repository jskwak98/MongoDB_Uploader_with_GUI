from pymongo import MongoClient, DeleteOne, UpdateOne, TEXT
from newInsertOne import InsertOne
from pprint import pprint
from typing import Union, List, Dict

from pymongo.errors import ConnectionFailure
from PySide6.QtCore import QObject, Signal, Slot

from localDBmanager import LocalDBManager


class MongoUpdater(QObject):
    """
    MongoUpdater does
    1. update MongoDB by referring to the data of localDBManager, Specifically localDBmanager.savefile
    2. and send result to localDBmanager
    """
    # needs to be connected to localDBmanager's after upload
    dbUploaded = Signal(dict, list, list)
    searchResults = Signal(list, list, bool)
    delete_success = Signal(bool, str)
    hereDBdata = Signal(list)
    nothingToUpload = Signal()
    onlineSyncData = Signal(list)
    docCount = Signal(int)

    def __init__(self):
        super().__init__()
        with open("secret.txt", "r") as f:
            URI = f.readline()

        self.client = MongoClient(URI)
        self.create_index_later = False
        try:
            self.client.admin.command('ismaster')
            # illcyclopedia for actual, _dev for dev
            self.db = self.client.illcyclopedia
            #self.db = self.client.illcyclopedia_dev
            # if collection diseases does not exist
            if "diseases" in self.db.list_collection_names():
                # if diseases collections exist, but it doesn't have search index
                if 'disease_name' not in self.db.diseases.index_information():
                    self.db.diseases.create_index(name="disease_name", keys=[('disease_name', TEXT)])
            else:
                self.create_index_later = True
        except ConnectionFailure:
            print("Server Not Available")
    
    def get_online_sync_data(self):
        dbdata = list(self.db.diseases.find({}))
        self.onlineSyncData.emit(dbdata)

    def new_client_init_data(self):
        dbdata = list(self.db.diseases.find({}))
        self.hereDBdata.emit(dbdata)

    def search(self, searchQuery):
        results = list(self.db.diseases.find({}))
        if searchQuery == '#':
            self.docCount.emit(len(results))
            return
        detail = []
        debugs = []
        isbug = False

        if searchQuery: # 정상 검색
            for result in results:
                if searchQuery in result['disease_name']:
                    detail.append(result)
            
        else: # 귀찮은 TODO -> 오타검정
            cates = {'피부/미용/성형 질환', '유전질환', '건강증진', '혈액/종양 질환', '눈/코/귀/인후/구강/치아', 
                '신장/비뇨기계 질환', '여성질환', '호흡기질환', '기타', '뇌/신경/정신질환', '근골격질환', 
                '응급질환', '소아/신생아 질환', '소화기계 질환', '순환기(심혈관계)질환', '감염성질환', '유방/내분비질환'}
            isbug = True
            for result in results:
                if result['category'] not in cates:
                    dn = result['disease_name'].replace('\n', ' ')
                    debugs.append(f"질병 : {dn}, 분류 오타 : {result['category']}")
                    detail.append(result)
            
        # list of dictionary containing the keyword emitted
        self.searchResults.emit(detail, debugs, isbug)

    def delete(self, docu_id, filename):
        result = self.db.diseases.delete_one({'_id':docu_id})
        if result.deleted_count:
            self.delete_success.emit(True, filename)
        else:
            self.delete_success.emit(False, filename)
        

    def update(self, update_data : Dict[str, Union[str, int, Dict[str, str]]]):
        operations = []
        added = []
        modified = []
        delfiles = []
        for filename in update_data:
            flag = update_data[filename]["flag"]
            # Operation Depending on Flag, 0 : NOP, 1 : Create, 2 : Update, 3 : Delete
            if flag == 0:
                continue
            elif flag == 1:
                operations.append(InsertOne(update_data[filename]['data']))
                update_data[filename]['flag'] = 0
                added.append((update_data[filename]['data']['disease_name'], update_data[filename]['local_path']))
            elif flag == 2:
                operations.append(UpdateOne({'_id': update_data[filename]['data']['_id']}, {'$set': update_data[filename]['data']}))
                update_data[filename]['flag'] = 0
                if update_data[filename]['is_deleted']:
                    lp = "로컬에 없음"
                else:
                    lp = update_data[filename]['local_path']
                modified.append((update_data[filename]['data']['disease_name'], lp))
            elif flag == 3:
                operations.append(DeleteOne({'_id': update_data[filename]['data']['_id']}))
                delfiles.append(filename)

        if operations:
            result = self.db.diseases.bulk_write(operations)
            success = not result.bulk_api_result['writeErrors']
            print(operations[:10])
            print(result)
            

            if success:
                if self.create_index_later:
                    # if it's initial upload to ODB and search index not created yet
                    self.db.diseases.create_index(name="disease_name", keys=[('disease_name', TEXT)])
                for filename in delfiles:
                    del update_data[filename]
                #print("update done, move to EP for savefile write")
                self.dbUploaded.emit(update_data, added, modified)
        
        else:
            self.nothingToUpload.emit()



if __name__ == "__main__":
    ep = LocalDBManager()
    md = MongoUpdater()
    
    ep.savefileUpdated.connect(md.update)
    md.dbUploaded.connect(ep.after_upload)

    ep.export_savefile()
    #pprint(ep.savefile)