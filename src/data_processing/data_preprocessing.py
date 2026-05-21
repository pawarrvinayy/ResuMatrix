import pandas as pd
import numpy as np
import re
import nltk
import torch
torch.set_num_threads(1)
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import jaccard_score
from textstat import flesch_reading_ease

# Ensure necessary NLTK resources are available
nltk.download('stopwords')
nltk.download('punkt_tab')
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

DEVICE = "cpu"
print(DEVICE)

# Ensure necessary NLTK resources are available
nltk.download('stopwords')
nltk.download('punkt_tab')
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# model_id = "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4"
# Load BERT tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased').to(DEVICE)
vectorizer = TfidfVectorizer(stop_words="english")


def clean_text(text):
    """Cleans text by removing special characters, numbers, and stopwords; applies lemmatization."""
    text = re.sub(r'http\S+\s*', ' ', text)  # remove URLs
    text = re.sub(r'RT|cc', ' ', text)  # remove RT and cc
    text = re.sub(r'#\S+', '', text)  # remove hashtags
    text = re.sub(r'@\S+', '  ', text)  # remove mentions
    text = re.sub(r'[%s]' % re.escape(r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""), ' ', text)  # remove punctuations
    text = re.sub(r'[^\x00-\x7f]',r' ', text)
    text = re.sub(r'\s+', ' ', text)  # remove extra whitespace
    tokens = word_tokenize(text.lower())  # Tokenization and lowercasing
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]  # Lemmatization & Stopword Removal
    return " ".join(tokens)

def encode_labels(df):
    """Encodes labels and removes rows with 'potential fit' label."""
    # Directly remove rows where label is 'Potential Fit'
    df = df[df["label"] != "Potential Fit"]
    # Map labels to numerical values (Good Fit: 1, No Fit: 0)
    df['label'] = df['label'].map({"Good Fit": 1, "No Fit": 0})
    return df


def load_data(data_type="train"):
    """Loads dataset, encodes labels, and applies text preprocessing."""
    df = pd.read_csv("hf://datasets/cnamuangtoun/resume-job-description-fit/train.csv")
    # df.drop_duplicates(inplace=True)
    df.dropna(subset=["resume_text", "job_description_text", "label"], inplace=True)
    df = encode_labels(df)
    df = df.head(10000)

    # Apply text cleaning
    df['resume_text'] = df['resume_text'].apply(clean_text)
    df['job_description_text'] = df['job_description_text'].apply(clean_text)

    return df

def tf_idf_vectorization(data_df):
    """Performs TF-IDF vectorization on preprocessed text."""
    all_text = pd.concat([data_df['resume_text'], data_df['job_description_text']], axis=0)

    vectorizer = TfidfVectorizer(max_features=5000, stop_words='english', ngram_range=(1, 2))
    vectorizer.fit(all_text)

    resume_tfidf = vectorizer.transform(data_df['resume_text'])
    job_tfidf = vectorizer.transform(data_df['job_description_text'])

    # Combine resume and job description features
    X = hstack([resume_tfidf, job_tfidf])
    y = data_df['label']

    return X, y, vectorizer

def get_embeddings_batch(texts, batch_size=8):
    """Generate BERT embeddings for a list of texts using batching."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        inputs = tokenizer(batch, padding=True, truncation=True, return_tensors='pt', max_length=512).to(DEVICE)
        with torch.no_grad():
            outputs = model(**inputs)
        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        all_embeddings.extend(embeddings)
    return all_embeddings

def extract_embeddings(df, data_type="train"):
    """Generate embeddings for resumes and job descriptions."""
    df['resume_embeddings'] = get_embeddings_batch(df['resume_text'].tolist())
    df['job_embeddings'] = get_embeddings_batch(df['job_description_text'].tolist())
    if data_type == "deployment":
        return df
    X = np.array([np.concatenate([r, j]) for r, j in zip(df['resume_embeddings'], df['job_embeddings'])])
    if data_type == "train":
        y = df['label'].values
        return X, y
    return X

# def extract_embeddings(df):
#     """Generate embeddings for resumes and job descriptions."""
#     resume_embeddings = np.array([get_embeddings(text) for text in df["resume_text"]])
#     jd_embeddings = np.array([get_embeddings(text) for text in df["job_description_text"]])
#
#     # Compute cosine similarity between resume and job description embeddings
#     cosine_similarities = [cosine_similarity([r], [j])[0][0] for r, j in zip(resume_embeddings, jd_embeddings)]
#     # Convert to NumPy array
#     cosine_similarities = np.array(cosine_similarities).reshape(-1, 1)
#     return cosine_similarities


def compute_jaccard_similarity(text1, text2):
    vectorizer = CountVectorizer(ngram_range=(2, 3), stop_words="english", binary=True)
    X = vectorizer.fit_transform([text1, text2])
    return jaccard_score(X.toarray()[0], X.toarray()[1])

def lambda_and_cosine_similarity(df):

    """Compute Jaccard similarity and cosine similarity between resumes and job descriptions."""
    df["jaccard_similarity"] = df.apply(lambda row: compute_jaccard_similarity(row["resume_text"], row["job_description_text"]), axis=1)
    tfidf_matrix = vectorizer.fit_transform(df["resume_text"].tolist() + df["job_description_text"].tolist())

    # Split the TF-IDF matrix into resume and job description parts
    resume_tfidf = tfidf_matrix[:len(df)]
    jd_tfidf = tfidf_matrix[len(df):]

    # Compute cosine similarity between resume and job description TF-IDF vectors
    df["tfidf_cosine_similarity"] = [cosine_similarity(resume_tfidf[i], jd_tfidf[i])[0][0] for i in range(len(df))]

    # Calculate length of resumes and job descriptions
    df["resume_length"] = df["resume_text"].apply(lambda x: len(x.split()))
    df["jd_length"] = df["job_description_text"].apply(lambda x: len(x.split()))

    # Calculate readability scores
    df["resume_readability"] = df["resume_text"].apply(lambda x: flesch_reading_ease(x))
    df["jd_readability"] = df["job_description_text"].apply(lambda x: flesch_reading_ease(x))

    return df



