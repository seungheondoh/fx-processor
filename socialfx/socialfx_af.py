import torch
import torchaudio
import os
import pandas as pd
import random
from uuid import uuid4

SOCIALFX_PATH = "./data/raw"
ORIGINAL_EQ_KEY = ["RSC_20Hz_band", "RSC_50Hz_band", "RSC_83Hz_band", "RSC_120Hz_band", "RSC_161Hz_band", "RSC_208Hz_band", "RSC_259Hz_band", "RSC_318Hz_band", "RSC_383Hz_band", "RSC_455Hz_band", "RSC_537Hz_band", "RSC_628Hz_band", "RSC_729Hz_band", "RSC_843Hz_band", "RSC_971Hz_band", "RSC_1114Hz_band", "RSC_1273Hz_band", "RSC_1452Hz_band", "RSC_1652Hz_band", "RSC_1875Hz_band", "RSC_2126Hz_band", "RSC_2406Hz_band", "RSC_2719Hz_band", "RSC_3070Hz_band", "RSC_3462Hz_band", "RSC_3901Hz_band", "RSC_4392Hz_band", "RSC_4941Hz_band", "RSC_5556Hz_band", "RSC_6244Hz_band", "RSC_7014Hz_band", "RSC_7875Hz_band", "RSC_8839Hz_band", "RSC_9917Hz_band", "RSC_11124Hz_band", "RSC_12474Hz_band", "RSC_13984Hz_band", "RSC_15675Hz_band", "RSC_17566Hz_band", "RSC_19682Hz_band"]
EQ_KEY_NAME = ["band0_gain_db", "band1_gain_db", "band2_gain_db", "band3_gain_db", "band4_gain_db", "band5_gain_db", "band6_gain_db", "band7_gain_db", "band8_gain_db", "band9_gain_db", "band10_gain_db", "band11_gain_db", "band12_gain_db", "band13_gain_db", "band14_gain_db", "band15_gain_db", "band16_gain_db", "band17_gain_db", "band18_gain_db", "band19_gain_db", "band20_gain_db", "band21_gain_db", "band22_gain_db", "band23_gain_db", "band24_gain_db", "band25_gain_db", "band26_gain_db", "band27_gain_db", "band28_gain_db", "band29_gain_db", "band30_gain_db", "band31_gain_db", "band32_gain_db", "band33_gain_db", "band34_gain_db", "band35_gain_db", "band36_gain_db", "band37_gain_db", "band38_gain_db", "band39_gain_db"]
REVERB_KEY_NAME = ["delay_time", "decay", "stereo_spread", "cutoff_freq", "wet_gain", "wet_dry"]
COMP_KEY_NAME = ["threshold_db", "ratio", "attack_ms", "release_ms", "knee_db"]
EQ_MAPPING = {key: name for key, name in zip(ORIGINAL_EQ_KEY, EQ_KEY_NAME)}
KEY_MAPPING = {}

def eq_processor(df_eq):
    results = []
    for idx in range(len(df_eq)):
        row = df_eq.iloc[idx]
        text = row.name
        descriptor = row.pop("descriptor")
        audio_id = row.pop("audio_id")
        ratings_consistency = row.pop("ratings_consistency")
        param_values = row.values
        param_keys = row.keys()
        extra = {"lang": descriptor, "ratings_consistency": float(ratings_consistency)}
        if isinstance(text, str):
            results.append({
                "id": f"eq_{idx}",
                "text": f"{text.lower()}",
                "param_values": param_values,
                "param_keys": param_keys,
                "extra": f"{extra}"
            })
    return results

def reverb_processor(df_reverb):
    results = []
    for idx in range(len(df_reverb)):
        row = df_reverb.iloc[idx]
        text = row['words']
        param_values = [float(i) for i in row['param'].split(",")]
        param_keys = REVERB_KEY_NAME
        extra = {"lang": row['language'], "agreed": row['agreed'], "didnotagree": row['didnotagree']}
        if isinstance(text, str):
            results.append({
                "id": f"reverb_{idx}",
                "text": f"{text.lower()}",
                "param_values": param_values,
                "param_keys": param_keys,
                "extra": f"{extra}"
            })
    return results

def comp_processor(df_comp):
    results = []
    for idx in range(len(df_comp)):
        row = df_comp.iloc[idx]
        text = row['words']
        param_values = [float(i) for i in row['param'].split(",")]
        param_keys = COMP_KEY_NAME
        extra = {"agreed": row['agreed'], "didnotagree": row['didnotagree']}
        if isinstance(text, str):
            results.append({
                "id": f"comp_{idx}",
                "text": f"{text.lower()}",
                "param_values": param_values,
                "param_keys": param_keys,
                "extra": f"{extra}"
            })
    return results
def main():
    df_eq = pd.read_csv(f"{SOCIALFX_PATH}/eq_contributions.csv")
    df_reverb = pd.read_csv(f"{SOCIALFX_PATH}/reverb_contributions.csv")
    df_comp = pd.read_csv(f"{SOCIALFX_PATH}/comp_contributions.csv")
    eq_results = eq_processor(df_eq)
    reverb_results = reverb_processor(df_reverb)
    comp_results = comp_processor(df_comp)
    print(len(eq_results)) # 1595
    print(len(reverb_results)) # 6791
    print(len(comp_results)) # 1148
    from datasets import Dataset, DatasetDict
    dataset = DatasetDict({
        "eq": Dataset.from_list(eq_results),
        "reverb": Dataset.from_list(reverb_results),
        "comp": Dataset.from_list(comp_results)
    })
    dataset.push_to_hub("seungheondoh/socialfx-original")

if __name__ == "__main__":
    main()
