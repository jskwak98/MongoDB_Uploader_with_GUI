from pymongo import MongoClient, InsertOne, DeleteOne, UpdateOne
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
    ep = LocalDBManager()
    md = MongoUpdater()
    
    ep.savefileUpdated.connect(md.update)
    md.dbUploaded.connect(ep.after_upload)

    ep.export_savefile()
    #pprint(ep.savefile)