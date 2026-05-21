# import pandas as pd
import numpy as np
from gensim.models import Word2Vec
# from datasets import load_dataset


# ds = load_dataset("cnamuangtoun/resume-job-description-fit")
#
# train_df = pd.DataFrame(ds['train'])
# test_df = pd.DataFrame(ds['test'])


def tokenize_text(df):
    df['resume_tokens'] = df['resume_text'].apply(lambda x: str(x).split())
    df['job_desc_tokens'] = df['job_description_text'].apply(lambda x: str(x).split())


def get_embedding(text, model):
    vectors = [model.wv[word] for word in text if word in model.wv]
    return sum(vectors) / len(vectors) if vectors else np.zeros(model.vector_size)


def generate_embeddings(df):
    tokenize_text(df)

    w2v_model = Word2Vec(sentences=df['resume_tokens'].tolist() + df['job_desc_tokens'].tolist(),
                         vector_size=100, window=5, min_count=2, workers=4)

    df['resume_embedding'] = df['resume_tokens'].apply(lambda x: get_embedding(x, w2v_model))
    df['job_desc_embedding'] = df['job_desc_tokens'].apply(lambda x: get_embedding(x, w2v_model))
