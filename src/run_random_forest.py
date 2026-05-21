import pickle
from data_processing.data_preprocessing import load_data, tf_idf_vectorization
from model_training.random_forest_classifier import train_random_forest
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import mlflow
import os

def execute_random_forest():

    # Load and preprocess training data
    train_data = load_data("train")
    X_train, y_train, vectorizer = tf_idf_vectorization(data_df=train_data)

    # Load and preprocess test data
    test_data = load_data("test")
    X_test, y_test, _ = tf_idf_vectorization(data_df=test_data)

    # Train Random Forest model
    model = train_random_forest(X_train, y_train, X_test, y_test)

    # Make predictions on test data
    y_pred = model.predict(X_test)
    #test
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("Classification report:", classification_report(y_test, y_pred))
    print("Confusion matrix:", confusion_matrix(y_test, y_pred))
    return model

if __name__ == '__main__':
    model = execute_random_forest()

filename = os.path.join('src', 'saved_models', 'random_forest_model.pkl')
pickle.dump(model, open(filename, 'wb'))