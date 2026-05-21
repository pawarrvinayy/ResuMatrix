import pandas as pd
import numpy as np

import xgboost as xgb
from sklearn.feature_extraction.text import TfidfVectorizer
from mlflow.models import infer_signature
import mlflow

import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# This ensures that the necessary supporting files are present 
nltk.download('stopwords')
nltk.download('punkt_tab')
nltk.download('wordnet')
stop_words = set(stopwords.words('english'))


def clean_text(text):
    """Cleans text by removing special characters, numbers, and stopwords; applies lemmatization."""
    text = re.sub('http\S+\s*', ' ', text)  # remove URLs

    text = re.sub('RT|cc', ' ', text)  # remove RT and cc
    text = re.sub('#\S+', '', text)  # remove hashtags
    text = re.sub('@\S+', '  ', text)  # remove mentions
    text = re.sub('[%s]' % re.escape("""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""), ' ', text)  # remove punctuations

    text = re.sub(r'[^\x00-\x7f]',r' ', text)
    text = re.sub('\s+', ' ', text)  # remove extra whitespace

    tokens = word_tokenize(text.lower())  # Tokenization and lowercasing
    tokens = [word for word in tokens if word not in stop_words]  # Stopword Removal
    return " ".join(tokens)

def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.drop(df[df['label'] == "Potential Fit"].index, inplace=True)
    df['label'] = df['label'].map({"Good Fit": 1, "No Fit": 0})

    df.drop_duplicates(inplace=True)
    df.dropna(subset=["resume_text", "job_description_text"], inplace=True)

    # Clean data
    df['resume_text'] = df['resume_text'].apply(clean_text)
    df['job_description_text'] = df['job_description_text'].apply(clean_text)
    return df

# Vectorize data using tdidf on a given column
def vectorize(X: pd.Series):
    vectorizer = TfidfVectorizer()
    return vectorizer.fit_transform(list(X))

# Returns qids and sorted indices of the qids such that all qids are grouped together.
# Accepts a pandas series column (Choose the column that serves as a query for your ranks)
def generate_query_ids(X: pd.Series):
    qid = X.astype('category').cat.codes.values
    return qid, np.argsort(qid)


def calculate_map(y_true, y_pred, qid):

    unique_qids = np.unique(qid)
    map_values = []
    
    for qid_value in unique_qids:
        group_idx = np.where(qid == qid_value)[0]
        
        y_true_group = y_true[group_idx]
        y_pred_group = y_pred[group_idx]
        
        # Sort predictions and labels by prediction scores
        sorted_idx = np.argsort(y_pred_group)[::-1]
        y_true_group_sorted = y_true_group[sorted_idx]
        
        # Calculate precision and recall at each relevant position
        precisions = []
        relevant_count = 0

        for i, label in enumerate(y_true_group_sorted):

            if label == 1:
                relevant_count += 1
                precision = relevant_count / (i + 1)
                precisions.append(precision)
        
        # Calculate average precision for this query group
        if len(precisions) > 0:
            ap = np.mean(precisions)
        else:
            ap = 0
        
        map_values.append(ap)
    
    # Calculate mean average precision across all query groups
    map_value = np.mean(map_values)
    
    return map_value


def main():

    df = load_data("hf://datasets/cnamuangtoun/resume-job-description-fit/train.csv")
    X = vectorize(df['resume_text'])
    
    y = df['label'].values
    qid, sorted_indices = generate_query_ids(df["job_description_text"])

    X = X[sorted_indices]
    y = y[sorted_indices]
    qid = qid[sorted_indices]

    exp_name = "XGBoost Ranker"
    mlflow.set_experiment(exp_name)
    # Create group sizes (number of samples per query group)
    _, group_sizes = np.unique(qid, return_counts=True)
    
    LR = 0.01

    N_ESTIMATORS = 100
    MAX_DEPTH = 15

    with mlflow.start_run() as run:
    
        # Train XGBRanker with pairwise objective
        ranker = xgb.XGBRanker(objective='rank:map',  # Pairwise ranking objective
                            learning_rate=LR,
                            n_estimators=N_ESTIMATORS,
                            max_depth=MAX_DEPTH)
        
    
        ranker.fit(X, y, group=group_sizes)  # Pass query group sizes during training
    
        mlflow.log_param("objective", "rank:map")
        mlflow.log_param("learning_rate", LR)
        mlflow.log_param("n_estimators", N_ESTIMATORS)
        mlflow.log_param("max_depth", MAX_DEPTH)
        
    
        # Predictions
        preds = ranker.predict(X)
    
        map_value = calculate_map(y, preds, qid)
        print(f"Mean Average Precision: {map_value}")
        mlflow.log_metric("Mean Avg precision", map_value)
        print("MLFlow experiment complete!")


        # Save the model as an artifact
        signature = infer_signature(X[:5], ranker.predict(X[:5]))
        mlflow.xgboost.log_model(ranker, "model", input_example=X[:5], signature=signature)

if __name__ == "__main__":
    main()
