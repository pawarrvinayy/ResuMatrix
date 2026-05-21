import mlflow
import mlflow.sklearn
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.metrics import (
    accuracy_score, roc_auc_score, f1_score, precision_score,
    recall_score, log_loss, confusion_matrix
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import spacy
nlp = spacy.load("en_core_web_sm")


RELEVANT_ENTITIES = {
    "ORG", 
    "GPE", 
    "NORP"
}

def extract_named_entities(text):
    doc = nlp(text)
    return set([ent.text.lower() for ent in doc.ents if ent.label_ in RELEVANT_ENTITIES])

def extract_features(df):
    features = df[[
        #"cosine_similarities",
        "jaccard_similarity", "tfidf_cosine_similarity",
        # "skill_match_score",
        "resume_length", "jd_length", "resume_readability", "jd_readability",
        #"sbert_similarity",
        "entity_overlap"
    ]]

    X = features.values
    y = df["label"].values
    return X, y


def extract_entity_overlap(df):
    # Extract entities from resumes and JDs
    df["jd_entities"] = df["job_description_text"].apply(extract_named_entities)
    df["resume_entities"] = df["resume_text"].apply(extract_named_entities)
    #test
    # Compute total entity overlap
    df["entity_overlap"] = df.apply(lambda row: len(row["resume_entities"] & row["jd_entities"]), axis=1)

    # Compute entity overlap ratio
    df["entity_overlap_ratio"] = df.apply(
        lambda row: len(row["resume_entities"] & row["jd_entities"]) / 
                    (len(row["resume_entities"] | row["jd_entities"]) + 1e-5), axis=1
    )
    return df

# Compute overlap for specific entity types
def compute_overlap(row, entity_type):
    resume_ents = {ent for ent in row["resume_entities"] if nlp(ent).ents and nlp(ent).ents[0].label_ == entity_type}
    jd_ents = {ent for ent in row["jd_entities"] if nlp(ent).ents and nlp(ent).ents[0].label_ == entity_type}
    return len(resume_ents & jd_ents)

def compute_entity_overlap(df):
    for entity in RELEVANT_ENTITIES:
        df[f"{entity.lower()}_overlap"] = df.apply(lambda row: compute_overlap(row, entity), axis=1)
    return df


def train_xgboost_model(X_train, y_train, X_test, y_test):

    with mlflow.start_run():

        mlflow.set_experiment("XGBoost Model with NER")
        #test
        xgb_model = XGBClassifier()
        xgb_model.fit(X_train, y_train)

        # Predict on test set
        y_pred = xgb_model.predict(X_test)
        y_pred_proba = xgb_model.predict_proba(X_test)[:, 1]  # Probabilities for AUC & log loss

        # Compute metrics
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_pred_proba)
        f1 = f1_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        logloss = log_loss(y_test, y_pred_proba)

        # Log metrics in MLflow
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("AUC", auc)
        mlflow.log_metric("F1 Score", f1)
        mlflow.log_metric("Precision", precision)
        mlflow.log_metric("Recall", recall)
        mlflow.log_metric("Log Loss", logloss)

        # Log model
        mlflow.sklearn.log_model(xgb_model, "xgboost_model")

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=["No Fit", "Good Fit"], yticklabels=["No Fit", "Good Fit"])
        plt.xlabel("Predicted")
        plt.ylabel("Actual")
        plt.title("Confusion Matrix")

        # Save confusion matrix image
        cm_path = "confusion_matrix.png"
        plt.savefig(cm_path)
        plt.close()

        # Log confusion matrix image
        mlflow.log_artifact(cm_path)

        print(f"XGBoost Model Accuracy: {accuracy:.4f}")
        print(f"XGBoost Model AUC: {auc:.4f}")
        print(f"XGBoost Model F1 Score: {f1:.4f}")
        print(f"XGBoost Model Precision: {precision:.4f}")
        print(f"XGBoost Model Recall: {recall:.4f}")
        print(f"XGBoost Model Log Loss: {logloss:.4f}")

        return xgb_model

def predict_xgboost_with_ner(model, data):
    """Predict using the trained XGboost model."""
    return model.predict(data)
