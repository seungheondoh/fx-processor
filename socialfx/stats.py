import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import ast
from datasets import load_dataset
from sklearn.preprocessing import MultiLabelBinarizer
from data.vocab.eq_merged import EQ_MAPPING
from data.vocab.reverb_merge import REVERB_MAPPING


def get_raw_check_stats(df, fx_type):
    df = df.copy()
    df['text'] = df["text"].apply(lambda x: [i.strip() for i in x.lower().split(",")])
    mlb = MultiLabelBinarizer()
    binary = mlb.fit_transform(df["text"])
    df_binary = pd.DataFrame(binary, columns=mlb.classes_)
    tag_per_param = df_binary.sum(axis=0).mean()
    parmas_per_tag = df_binary.sum(axis=1).mean()
    num_of_parmas = len(df["id"].unique())
    num_of_words = len(mlb.classes_)
    return {
        "fx_type": fx_type,
        "split": "raw",
        "num_of_parmas": num_of_parmas,
        "num_of_words": num_of_words,
        "tag_per_param": tag_per_param,
        "parmas_per_tag": parmas_per_tag
    }

def get_tag_merge_stats(df, fx_type):
    df = df.copy()
    """Filter dataset to get English tags and their IDs"""
    filtered = []
    for idx, row in df.iterrows():
        tags = row["text"].lower().split(",")
        try:
            extra = ast.literal_eval(row["extra"])
            lang = extra["lang"].lower()
        except:
            lang = "english"
        text = []
        for tag in tags:
            if fx_type == "eq":
                tag = EQ_MAPPING.get(tag, tag)
            elif fx_type == "reverb":
                tag = REVERB_MAPPING.get(tag, tag)
            text.append(tag)
        filtered.append({
            "id": row["id"],
            "tags": text,
            "lang": lang
        })
    df_filtered = pd.DataFrame(filtered)
    df_filtered = df_filtered[df_filtered["lang"] == "english"]
    mlb = MultiLabelBinarizer()
    binary = mlb.fit_transform(df["text"])
    df_binary = pd.DataFrame(binary, columns=mlb.classes_)
    tag_per_param = df_binary.sum(axis=0).mean()
    parmas_per_tag = df_binary.sum(axis=1).mean()
    num_of_parmas = len(df["id"].unique())
    num_of_words = len(mlb.classes_)
    return {
        "fx_type": fx_type,
        "split": "tag_merge",
        "num_of_parmas": num_of_parmas,
        "num_of_words": num_of_words,
        "tag_per_param": tag_per_param,
        "parmas_per_tag": parmas_per_tag
    }

def get_eval_stats(fx_type):
    cls_db = load_dataset("seungheondoh/socialfx-cls-eval", split=fx_type)
    gen_db = load_dataset("seungheondoh/socialfx-gen-eval", split=fx_type)
    num_of_parmas = len(set(cls_db['input']))
    num_of_words = len(set(gen_db['input']))

    mlb = MultiLabelBinarizer()
    binary = mlb.fit_transform(cls_db["output"])
    df_binary = pd.DataFrame(binary, columns=mlb.classes_)
    # Calculate co-occurrence matrix
    tag_frequencies = df_binary.sum(axis=0)
    co_occurrence = np.dot(df_binary.T, df_binary)
    np.fill_diagonal(co_occurrence, 0)  # Remove self-connections
    # Normalize co-occurrence by tag frequencies
    normalized_co_occurrence = co_occurrence.copy()
    for i, j in zip(tag_frequencies, co_occurrence):
        normalized_co_occurrence[j] = j / i
    # Plot co-occurrence matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(normalized_co_occurrence, cmap='viridis', xticklabels=mlb.classes_, yticklabels=mlb.classes_)
    plt.title(f'Tag Co-occurrence Matrix for {fx_type}')
    plt.tight_layout()
    os.makedirs("./data/stats", exist_ok=True)
    plt.savefig(f"./data/stats/{fx_type}_co_occurrence.png")
    plt.close()

    # Plot tag distribution
    tag_counts = df_binary.sum(axis=0).sort_values(ascending=False) / len(df_binary)
    plt.figure(figsize=(12, 6))
    tag_counts.plot(kind='bar')
    plt.title(f'Tag Distribution for {fx_type}')
    plt.xlabel('Tags')
    plt.ylabel('Frequency')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(f"./data/stats/{fx_type}_tag_distribution.png")
    plt.close()
    tag_per_param = df_binary.sum(axis=0).mean()
    parmas_per_tag = df_binary.sum(axis=1).mean()
    return {
        "fx_type": fx_type,
        "split": "eval",
        "num_of_parmas": num_of_parmas,
        "num_of_words": num_of_words,
        "tag_per_param": tag_per_param,
        "parmas_per_tag": parmas_per_tag
    }

def main():
    dataset = load_dataset("seungheondoh/socialfx-original")
    results = []
    for fx_type in ['eq', 'reverb']:
        df = pd.DataFrame(dataset[fx_type])
        raw_stats = get_raw_check_stats(df, fx_type)
        merge_stats = get_tag_merge_stats(df, fx_type)
        eval_stats = get_eval_stats(fx_type)
        os.makedirs("./data/stats", exist_ok=True)
        pd.DataFrame([raw_stats, merge_stats, eval_stats]).to_csv(f"./data/stats/{fx_type}.csv", index=False)

if __name__ == "__main__":
    main()
