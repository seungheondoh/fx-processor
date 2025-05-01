import ast
import os
from collections import Counter
from datasets import load_dataset, Dataset, DatasetDict
import pandas as pd
from constants import SYNONYM_MAP
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances

def filter_dataset(df):
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
            tag = SYNONYM_MAP.get(tag, tag)
            filtered.append({
                "id": row["id"],
                "tags": tag,
                "lang": lang
            })
    df_filtered = pd.DataFrame(filtered)
    return df_filtered[df_filtered["lang"] == "english"]

def get_embeddings(effect_list, fx_type, tag):
    """Get average embeddings across instruments for each effect"""
    embedding_list = []
    for effect in effect_list:
        avg_embs = []
        for inst in ['drums', 'guitar', 'piano']:
            avg_embs.append(np.load(f"/data3/seungheon/fx_embedding/FXenc/{inst}/{fx_type}/{effect}.npy"))
        embedding_list.append({
            "emb": np.mean(avg_embs, axis=0),
            "tag": tag,
            "effect": effect
        })
    return pd.DataFrame(embedding_list)

def get_representative_effects(embeddings, n_clusters):
    """Get representative effects using k-means clustering"""
    X = np.vstack(embeddings["emb"].values)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(X)
    centroids = kmeans.cluster_centers_

    effect_list = []
    for centroid in centroids:
        distances = euclidean_distances([centroid], X)[0]
        closest_idx = np.argmin(distances)
        closest_effect = embeddings.iloc[closest_idx]
        effect_list.append(closest_effect["effect"])
    return effect_list

def process_fx_type(df, fx_type):
    """Process single FX type to get tag-effect mappings"""
    parma_dict = {k: v for k, v in zip(df['id'], df['param_values'])}
    df_filtered = filter_dataset(df)
    top_tags = Counter(df_filtered['tags']).most_common(15)
    df_top_tags = df_filtered.groupby("tags")["id"].agg(list)
    tag2effect = []
    for tag, freq in top_tags:
        effect_list = df_top_tags[tag]
        n_clusters = min(200, int(len(effect_list)/2)) # max 200 sample for evaluation
        if fx_type == "eq":
            id2ratings = {_id: ast.literal_eval(extra)["ratings_consistency"] for _id, extra in zip(df["id"], df['extra'])}
            df_score = pd.DataFrame([{"id":i, "score": id2ratings[i]} for i in effect_list])
            df_score.sort_values(by="score", ascending=False, inplace=True)
            effect_list = df_score['id'].tolist()
        else:
            param_vector = np.stack([parma_dict[_id] for _id in effect_list])
            centorid_vector = param_vector.mean(axis=0)
            distances = euclidean_distances([centorid_vector], param_vector)[0]
            sorted_idx = distances.argsort()
            df_score = pd.DataFrame([{"id":effect_list[i], "score": distances[i]} for i in sorted_idx])
            df_score.sort_values(by="score", ascending=False, inplace=True)
            effect_list = df_score['id'].tolist()

        tag2effect.append({
            "text": tag,
            "freq": freq,
            "ids": effect_list[:n_clusters]
        })
    return tag2effect

def main():
    dataset = load_dataset("seungheondoh/socialfx-original")
    eval_dataset = {}
    for fx_type in dataset.keys():
        df = pd.DataFrame(dataset[fx_type])
        tag2effect = process_fx_type(df, fx_type)
        eval_dataset[fx_type] = Dataset.from_list(tag2effect)
    eval_dataset = DatasetDict(eval_dataset)
    eval_dataset.push_to_hub("seungheondoh/socialfx-eval")

if __name__ == "__main__":
    main()
