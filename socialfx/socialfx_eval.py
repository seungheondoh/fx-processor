import ast
import os
from collections import Counter
from datasets import load_dataset, Dataset, DatasetDict
import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer
from data.vocab.eq_merged import EQ_MAPPING
from data.vocab.reverb_merged import REVERB_MAPPING

STOP_WORDS = ['drum','bass', 'nice', 'pleasant', 'good', 'none', 'unclear', "happy", "cold"]
EQ_TRESHOLD = 20
REVERB_TRESHOLD = 100

def tag_merge(df, fx_type):
    """Filter dataset to get English tags and their IDs"""
    filtered = []
    for idx, row in df.iterrows():
        tags = row["text"].lower().split(",")
        try:
            extra = ast.literal_eval(row["extra"])
            lang = extra["lang"].lower()
        except:
            lang = "english"
        for tag in tags:
            if fx_type == "eq":
                tag = EQ_MAPPING.get(tag, tag)
            elif fx_type == "reverb":
                tag = REVERB_MAPPING.get(tag, tag)
            if tag in STOP_WORDS:
                continue
            filtered.append({
                "id": row["id"],
                "tags": tag,
                "lang": lang
            })
    df_filtered = pd.DataFrame(filtered)
    return df_filtered[df_filtered["lang"] == "english"]

def eval_for_classification(tag2ids_dict):
    """Evaluate for classification"""
    id2tags = {_id:[] for k,v in tag2ids_dict.items() for _id in v }
    for tag,ids in tag2ids_dict.items():
        for _id in ids:
            id2tags[_id].append(tag)
    unique_ids = list(id2tags.keys())
    muiltilabel = [id2tags[i] for i in unique_ids]
    mlb = MultiLabelBinarizer()
    mlb.fit(muiltilabel)
    binarys = mlb.transform(muiltilabel)
    class_labels = list(mlb.classes_)
    results = []
    for _id, text, binary in zip(unique_ids, muiltilabel, binarys):
        results.append({
            "input": _id,
            "output": text,
            "binary": list(binary),
            "labels": class_labels,
        })
    return results

def eval_for_generation(tag2ids_dict):
    """Evaluate for generation"""
    results = []
    for k,v in tag2ids_dict.items():
        results.append({
            "input": k,
            "output": v,
        })
    return results

def main():
    dataset = load_dataset("seungheondoh/socialfx-original")
    cls_eval_dataset = {}
    gen_eval_dataset = {}
    for fx_type in ['eq', 'reverb']:
        df = pd.DataFrame(dataset[fx_type])
        df_filtered = tag_merge(df, fx_type)
        vocab = Counter(df_filtered['tags']).most_common()
        df_tags = pd.DataFrame(vocab, columns=['tag', 'freq'])
        if fx_type == "eq":
            target_tags = df_tags[df_tags['freq'] > EQ_TRESHOLD]['tag']
        else:
            target_tags = df_tags[df_tags['freq'] > REVERB_TRESHOLD]['tag']
        df_tag2ids = df_filtered.groupby("tags")["id"].agg(list)
        tag2ids_dict = df_tag2ids[target_tags].to_dict()
        gen_eval = eval_for_generation(tag2ids_dict)
        cls_eval = eval_for_classification(tag2ids_dict)
        gen_eval_dataset[fx_type] = Dataset.from_list(gen_eval)
        cls_eval_dataset[fx_type] = Dataset.from_list(cls_eval)
    DatasetDict(gen_eval_dataset).push_to_hub("seungheondoh/socialfx-gen-eval")
    DatasetDict(cls_eval_dataset).push_to_hub("seungheondoh/socialfx-cls-eval")

if __name__ == "__main__":
    main()
