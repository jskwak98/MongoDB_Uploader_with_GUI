import pickle
from pprint import pprint

with open("./save/savefile", 'rb') as f:
    save = pickle.load(f)

pprint(save)