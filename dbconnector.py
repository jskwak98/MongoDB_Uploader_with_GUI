from pymongo import MongoClient
import glob, os
import openpyxl
from pprint import pprint



class ExcelParser:
    def parse(self):
        data = []

        for excel_path in glob.iglob('*.xlsx', recursive=True):
            excel_document = openpyxl.load_workbook(excel_path)
            sheet = excel_document['Sheet1']
            docu = dict()
            docu["disease_name"] = sheet['A2'].value
            docu["category"] = sheet['D2'].value
            docu["definition"] = sheet['C2'].value
            docu["cause_symptom"] = sheet['C3'].value
            docu["care"] = sheet['C4'].value
            data.append(docu)

        return data

class MongoUpdater:

    def __init__(self):
        with open("secret.txt", "r") as f:
            URI = f.readline()
            print(URI)

        self.client = MongoClient(URI)
        self.db = self.client.sample_illcyclopedia

        print(self.db)

    def insert(self, data : list[dict[str, str]]):
        result = self.db.diseases.insert_many(data)
        print(result.inserted_ids)




if __name__ == "__main__":
    md = MongoUpdater()
    ep = ExcelParser()
    md.insert(ep.parse())