import torch
import torchaudio
import os
import json
from tqdm import tqdm
import pandas as pd
import random
import numpy as np
from datasets import load_dataset, Dataset, DatasetDict, concatenate_datasets
from collections import Counter
from dsp_utils.dsp import socialfx_eq, socialfx_reverb, socialfx_compressor
from ast import literal_eval
from functools import partial

AUDIO_PATH = "./dsp_utils/original/raw/audio"
OUTPUT_PATH = "../data/socialfx"

def mp_helper(mp_input):
    x, sr = torchaudio.load(mp_input['audio_path'])
    if mp_input['fx_type'] == "eq":
        x_after = socialfx_eq(x.numpy(), sr, **mp_input['params'])
    elif mp_input['fx_type'] == "comp":
        x_after = socialfx_compressor(x.numpy(), sr, **mp_input['params'])
    elif mp_input['fx_type'] == "reverb":
        x_after = socialfx_reverb(x.numpy(), sr, **mp_input['params'])
    audio_path = f"{OUTPUT_PATH}/{mp_input['inst_case']}/{mp_input['fx_type']}/{mp_input['id']}.wav"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    torchaudio.save(audio_path, torch.from_numpy(x_after.astype(np.float32)), sr)

def main():
    dataset = load_dataset("seungheondoh/socialfx-effect-dasp")
    mp_inputs = []
    for fx_type in dataset.keys():
        if fx_type == "comp":
            db = dataset[fx_type]
            for row in tqdm(db):
                row['params'] = literal_eval(row['params'])
                for inst_case in ['drums', 'guitar', 'piano']:
                    mp_inputs.append({
                        "id": row['id'],
                        "inst_case": inst_case,
                        "audio_path": f"{AUDIO_PATH}/{inst_case}.wav",
                        "fx_type": fx_type,
                        "params": row['params']
                    })
    print(len(mp_inputs))
    import multiprocessing as mp
    num_workers = mp.cpu_count() // 2
    print(num_workers)
    with mp.Pool(num_workers) as p:
        p.map(mp_helper, mp_inputs)

if __name__ == "__main__":
    main()
