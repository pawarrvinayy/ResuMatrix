import pickle
import mlflow
import os

from model_training.knn_classifier import train_knn, predict_knn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from data_processing.data_preprocessing import load_data, tf_idf_vectorization

def execute_knn():

    # Load and preprocess training data
    train_data = load_data("train")
    X_train, y_train, vectorizer = tf_idf_vectorization(data_df=train_data)

    # Load and preprocess test data
    test_data = load_data("test")
    X_test, y_test, _ = tf_idf_vectorization(data_df=test_data)

    # Train KNN model
    knn_model = train_knn(X_train, y_train, X_test, y_test)

    # Make predictions on test data
    y_pred = predict_knn(knn_model, X_test)

    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("Classification report:", classification_report(y_test, y_pred))
    print("Confusion matrix:", confusion_matrix(y_test, y_pred))
    return knn_model

if __name__ == '__main__':
    knn_model = execute_knn()

filename = os.path.join('src', 'saved_models', 'knn_classifier.pkl')
pickle.dump(knn_model, open(filename, 'wb'))