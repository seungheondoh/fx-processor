import os
import json
import pandas as pd
from datasets import load_dataset
from tqdm import tqdm
dataset = load_dataset("seungheondoh/socialfx-original")

for key in dataset.keys():
    db = dataset[key]
    for item in tqdm(db):
        _id = item['id']
        results = {"text": item['text'], "param_values": item['param_values']}
        os.makedirs(f"./json/{key}", exist_ok=True)
        with open(f"./json/{key}/{_id}.json", "w") as f:
            json.dump(results, f, indent=4)
