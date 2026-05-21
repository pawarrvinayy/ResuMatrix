from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import mlflow

def train_random_forest(X_train, y_train, X_test, y_test):
    """Trains a Random Forest model with hyperparameter tuning and logs it with MLflow."""
    with mlflow.start_run():

        mlflow.set_experiment("Random Forest Classifier")

        # Define hyperparameters for tuning
        param_grid = {
            'n_estimators': [100, 200, 300],  # Number of trees in the forest
            'max_depth': [None, 10, 20, 30],  # Maximum depth of the tree
            'min_samples_split': [2, 5, 10],  # Minimum samples required to split a node
            'min_samples_leaf': [1, 2, 4]  # Minimum samples required at a leaf node
        }

        # Initialize Random Forest model
        rf = RandomForestClassifier(random_state=42)

        # Perform grid search for hyperparameter tuning
        grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, scoring='accuracy', n_jobs=-1)
        grid_search.fit(X_train, y_train)

        # Log best hyperparameters
        best_params = grid_search.best_params_
        mlflow.log_params(best_params)

        # Train the best model
        best_model = grid_search.best_estimator_
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

        # Save the model
        mlflow.sklearn.log_model(best_model, "random_forest_model")

        print(f"Random Forest Model trained and logged with accuracy: {accuracy:.4f}")
        print("Best Hyperparameters:", best_params)

        return best_model