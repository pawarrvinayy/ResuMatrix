import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from model_training.similarity_with_xgboost import train_xgboost_model, predict_xgboost
from data_processing.data_preprocessing import load_data, extract_embeddings
import pickle
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def execute_similarity_with_xgboost():
    # Load and preprocess data
    train_df = load_data("train")
    X_train, y_train = extract_embeddings(train_df)

    test_df = load_data("test")
    X_test, y_test = extract_embeddings(test_df)

    xgboost_model_with_similarity = train_xgboost_model(X_train, y_train, X_test, y_test)

    # Make predictions on test data
    y_pred = predict_xgboost(xgboost_model_with_similarity, X_test)

    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("Classification report:", classification_report(y_test, y_pred))
    print("Confusion matrix:", confusion_matrix(y_test, y_pred))
    return xgboost_model_with_similarity


if __name__ == "__main__":
    xgboost_model_with_similarity = execute_similarity_with_xgboost()

filename = os.path.join('src', 'saved_models', 'xgboost_model_with_similarity.pkl')
pickle.dump(xgboost_model_with_similarity, open(filename, 'wb'))