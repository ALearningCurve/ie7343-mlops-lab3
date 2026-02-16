import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
import pickle
import base64
from pathlib import Path
from typing import Any
import logging


class Paths:
    """Relevant paths in this project."""

    # airflow docker file mounts working_data to   /opt/airflow/working_data
    working_data_root = Path("/opt/airflow/working_data")

    # Data paths
    data_root = working_data_root
    raw_csv = data_root / "data.csv"
    train_csv = data_root / "train.csv"
    test_csv = data_root / "test.csv"

    # Model paths
    models_root = working_data_root / "model"

    @classmethod
    def ensure_dirs(cls):
        """Ensure all required directories exist."""
        cls.models_root.mkdir(parents=True, exist_ok=True)


class Marshaller:
    @staticmethod
    def marshall(data: Any) -> str:
        """Given data to store as a string.

        Args:
            data: Anything which is pickle-able

        Returns:
            string encoding
        """
        serialized_data = pickle.dumps(data)
        return base64.b64encode(serialized_data).decode("ascii")

    @staticmethod
    def unmarshall(data: str) -> Any:
        """Given data string, unmarshall into py object.

        Args:
            data: string input

        Returns:
            py object variant
        """
        data_bytes = base64.b64decode(data)
        return pickle.loads(data_bytes)


def load_data():
    """
    Loads training data from a CSV file, serializes it, and returns the serialized data.
    Returns:
        str: Base64-encoded serialized data (JSON-safe).
    """
    df = pd.read_csv(Paths.train_csv)
    return Marshaller.marshall(df)


def ingress_data(test_size: float = 0.2, random_state: int = 42):
    """
    Splits raw data into train/test CSVs under working_data.
    """
    df = pd.read_csv(Paths.raw_csv)
    train_df, test_df = train_test_split(
        df, test_size=test_size, random_state=random_state
    )
    train_df.to_csv(Paths.train_csv, index=False)
    test_df.to_csv(Paths.test_csv, index=False)
    return {
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
    }


def data_preprocessing(data_b64: str):
    """
    Deserializes base64-encoded data, performs preprocessing,
    separates features and target, scales features,
    and returns base64-encoded dictionary with X, y, and scaler.
    """
    df = Marshaller.unmarshall(data_b64)

    # Drop rows with missing values
    # and those with non-numeric columns
    df = df.dropna()
    numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns.tolist()
    target_col = "median_house_value"
    if target_col in numeric_cols:
        numeric_cols.remove(target_col)

    X = df[numeric_cols].values
    y = df[target_col].values

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Prepare data dictionary
    data_dict = {
        "X": X_scaled,
        "y": y,
        "scaler": scaler,
        "feature_names": numeric_cols,
    }

    # Serialize and encode
    return Marshaller.marshall(data_dict)


def build_save_model(data_b64: str, filename: str):
    """
    Builds and trains a regression model with hyperparameter tuning using GridSearchCV.
    Compares LinearRegression, Ridge, Lasso, and ElasticNet with different parameters.
    Returns training metrics (R² score, RMSE, and best hyperparameters).
    """
    logger = logging.getLogger()
    logger.info("starting training task")
    data_dict = Marshaller.unmarshall(data_b64)

    X = data_dict["X"]
    y = data_dict["y"]

    pipeline = Pipeline([("regressor", LinearRegression())])
    param_grid = [
        {"regressor": [LinearRegression()]},
        {
            "regressor": [Ridge()],
            "regressor__alpha": [0.001, 1.0, 100.0],
            "regressor__max_iter": [5000],
        },
    ]

    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        scoring="r2",
        cv=3,
        n_jobs=-1,
        verbose=3,
    )
    grid_search.fit(X, y)

    best_model = grid_search.best_estimator_
    raw_params = grid_search.best_params_
    regressor = raw_params.get("regressor")
    best_params = {
        "model": regressor.__class__.__name__ if regressor else "LinearRegression"
    }
    for key, value in raw_params.items():
        if key.startswith("regressor__"):
            best_params[key.replace("regressor__", "")] = value

    print(
        f"\nBest model: {best_params['model']} with CV R² score: {grid_search.best_score_:.4f}"
    )

    # Calculate training metrics with best model
    y_pred = best_model.predict(X)
    r2_score = best_model.score(X, y)
    rmse = ((y - y_pred) ** 2).mean() ** 0.5

    # Prepare model package (includes scaler and feature names)
    model_package = {
        "model": best_model,
        "scaler": data_dict["scaler"],
        "feature_names": data_dict["feature_names"],
        "best_params": best_params,
        "models_tested": grid_search.cv_results_["params"],
    }

    # Save model package
    Paths.ensure_dirs()
    output_path = Paths.models_root / filename
    with open(output_path, "wb") as f:
        pickle.dump(model_package, f)

    # Return metrics as dictionary
    return {
        "r2_score": float(r2_score),
        "rmse": float(rmse),
        "best_params": best_params,
        "models_count": len(grid_search.cv_results_["params"]),
        "cv_r2": float(grid_search.best_score_),
    }


def load_evaluate_model(filename: str, metrics: dict):
    """
    Loads the saved model and evaluates it on test data.
    Returns test evaluation metrics and predictions.
    """
    # Load the model package
    output_path = Paths.models_root / filename
    model_package = pickle.load(open(output_path, "rb"))

    model = model_package["model"]
    scaler = model_package["scaler"]
    feature_names = model_package["feature_names"]
    best_params = model_package.get("best_params", {})

    print(
        f"Training Metrics - R² Score: {metrics['r2_score']:.4f}, RMSE: ${metrics['rmse']:.2f}"
    )
    print(f"Best Model Hyperparameters: {best_params}")
    print(f"Models tested: {metrics.get('models_count', 'N/A')}")

    # Evaluate on test data if it exists
    test_df = pd.read_csv(Paths.test_csv)
    test_df = test_df.dropna()

    # Prepare test features
    X_test = test_df[feature_names].values
    y_test = test_df["median_house_value"].values

    # Scale using training scaler
    X_test_scaled = scaler.transform(X_test)

    # Make predictions
    y_pred_test = model.predict(X_test_scaled)
    test_r2_score = model.score(X_test_scaled, y_test)
    test_rmse = ((y_test - y_pred_test) ** 2).mean() ** 0.5

    print(f"Test Metrics - R² Score: {test_r2_score:.4f}, RMSE: ${test_rmse:.2f}")

    return {
        "train_r2": float(metrics["r2_score"]),
        "train_rmse": float(metrics["rmse"]),
        "test_r2": float(test_r2_score),
        "test_rmse": float(test_rmse),
        "test_predictions": y_pred_test.tolist()[:5],  # Return first 5 predictions
        "best_params": best_params,
        "models_count": metrics.get("models_count", 0),
    }
