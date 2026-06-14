from xgboost import XGBRegressor
from backend.layer1.engine2.config import FEATURE_COLUMNS, MODEL_PARAMS

def train_model(df):
    """
    Splits data chronologically and trains an XGBoost model with regularization.
    """
    features = FEATURE_COLUMNS
    params = MODEL_PARAMS

    X = df[features]
    y = df["units_sold"]

    # Chronological time-series split on dates to prevent temporal leakage
    unique_dates = sorted(df["date"].unique())
    n_dates = len(unique_dates)

    # Train (first 80%) vs Test (last 20%) split
    split_idx = int(n_dates * 0.8)
    split_date = unique_dates[split_idx]
    
    # Validation split for early stopping (last 10% of training dates)
    train_dates_only = unique_dates[:split_idx]
    val_split_idx = int(len(train_dates_only) * 0.9)
    val_split_date = train_dates_only[val_split_idx]

    # Split masks
    train_mask = df["date"] < val_split_date
    val_mask = (df["date"] >= val_split_date) & (df["date"] < split_date)
    test_mask = df["date"] >= split_date

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    # Hyperparameters tuned for generalization
    model = XGBRegressor(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        reg_alpha=params["reg_alpha"],
        reg_lambda=params["reg_lambda"],
        random_state=params["random_state"],
        early_stopping_rounds=params["early_stopping_rounds"]
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    train_r2 = model.score(X_train, y_train)
    val_r2 = model.score(X_val, y_val)
    test_r2 = model.score(X_test, y_test)

    print("Model training completed")
    print("Train R²:", round(train_r2, 4))
    print("Validation R²:", round(val_r2, 4))
    print("Test R²:", round(test_r2, 4))

    return model, features, {
        "train_r2": float(round(train_r2, 4)),
        "validation_r2": float(round(val_r2, 4)),
        "test_r2": float(round(test_r2, 4))
    }
