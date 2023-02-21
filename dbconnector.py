from pymongo import MongoClient

with open("secret.txt", "r") as f:
    URI = f.readline()
    print(URI)

client = MongoClient(URI)
db = client.test
print(db)