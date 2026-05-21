from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV
import mlflow
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


def hyperparameter_tuning(X_train, y_train):
    """Performs hyperparameter tuning for KNN."""
    param_grid = {
        'n_neighbors': [3, 5, 7, 9, 11],  # Number of neighbors to test
        'weights': ['uniform', 'distance'],  # Weighting strategy
        'metric': ['euclidean', 'manhattan', 'minkowski']  # Distance metric
    }

    knn = KNeighborsClassifier()

    grid_search = GridSearchCV(knn, param_grid, scoring='accuracy', cv=3, n_jobs=-1, verbose=2)
    grid_search.fit(X_train, y_train)

    print(f"Best Parameters: {grid_search.best_params_}")
    print(f"Best Score: {grid_search.best_score_}")

    return grid_search.best_estimator_, grid_search.best_params_

def train_knn(X_train, y_train, X_test, y_test):
    """Trains a KNN model and logs it with MLflow."""
    with mlflow.start_run():

        mlflow.set_experiment("KNN Classifier")
        # Perform hyperparameter tuning
        best_model, best_params = hyperparameter_tuning(X_train, y_train)

        # Log hyperparameters
        mlflow.log_params(best_params)

        # Train the best model
        best_model.fit(X_train, y_train)

        # Predict on test set
        y_pred = best_model.predict(X_test)

        # Log metrics
        accuracy = accuracy_score(y_test, y_pred)
        mlflow.log_metrics({"accuracy": accuracy})

        # Log classification report
        class_report = classification_report(y_test, y_pred)
        mlflow.log_metrics({"classification_report": class_report})

        conf_matrix = confusion_matrix(y_test, y_pred)
        mlflow.log_metrics({"confusion_matrix": conf_matrix})

        # Save the KNN model
        mlflow.sklearn.log_model(best_model, "knn_model")

        print(f"KNN Model trained and logged with accuracy: {accuracy:.4f}")

        return best_model
    
def predict_knn(model, data):
    """Predict using the trained KNN model."""
    return model.predict(data)