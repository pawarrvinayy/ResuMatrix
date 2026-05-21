import pytest
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from src.data_processing.data_preprocessing import clean_text, encode_labels, load_data, tf_idf_vectorization, get_embeddings, extract_embeddings, compute_jaccard_similarity, lambda_and_cosine_similarity

test_str = '''
ExperienceData, Research & Marketing Consultant,01/2019-01/2019Pfizer–Columbus,OH,Https://rpinsights.com, https://rpmarketingco.com.Designing membership surveys and managing CRM databases for non-profit organization. Within-industry experience: eCommerce, information services, information technology, and retail. #CRM
'''

@pytest.fixture
def sample_df():
    df = pd.read_csv("hf://datasets/cnamuangtoun/resume-job-description-fit/train.csv")
    df.iloc[0].label = "Potential Fit"
    df.iloc[1].label = "Good Fit"
    df.iloc[2].label = "No Fit"
    return df.head(3)

def test_clean_text():
    cleaned_text = clean_text(test_str)
    assert 'https' not in cleaned_text
    assert '.com' not in cleaned_text
    assert '#CRM' not in cleaned_text

def test_encode_labels(sample_df):
    print(sample_df.head())
    encoded_df = encode_labels(sample_df)
    print(encoded_df.head())
    assert set(encoded_df['label'].unique()) == {0, 1}
    assert 'Potential Fit' not in encoded_df['label'].values

def test_load_data():
    df = load_data('train')
    assert isinstance(df, pd.DataFrame)
    assert 'resume_text' in df.columns
    assert 'job_description_text' in df.columns
    assert 'label' in df.columns

def test_tf_idf_vectorization():
    df = load_data('train')
    X, y, vectorizer = tf_idf_vectorization(df)
    assert X.shape[0] == len(df['job_description_text'] + df['resume_text'])
    assert y.shape[0] == len(df['label'])
    assert isinstance(vectorizer, TfidfVectorizer)
    print(vectorizer)

def test_get_embeddings():
    text = "Sample text for embedding"
    embedding = get_embeddings(text)
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (768,)  # BERT base model output size

def test_extract_embeddings(sample_df):
    embeddings = extract_embeddings(sample_df)
    assert isinstance(embeddings, np.ndarray)

def test_compute_jaccard_similarity():
    text1 = "This is the first text"
    text2 = "This is the second text"
    similarity = compute_jaccard_similarity(text1, text2)
    assert 0 <= similarity <= 1

def test_lambda_and_cosine_similarity():
    df = load_data("train").head(3)
    result_df = lambda_and_cosine_similarity(df)
    assert 'jaccard_similarity' in result_df.columns
    assert 'tfidf_cosine_similarity' in result_df.columns
    assert 'resume_length' in result_df.columns
    assert 'jd_length' in result_df.columns
    assert 'resume_readability' in result_df.columns
    assert 'jd_readability' in result_df.columns

