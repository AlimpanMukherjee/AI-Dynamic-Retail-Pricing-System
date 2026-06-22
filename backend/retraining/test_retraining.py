import os
import pytest
import pandas as pd
import backend.config as cfg
from backend.retraining.retrain_model import (
    _initialize_registry,
    train_new_model,
    activate_model,
    load_active_model,
    OPERATIONAL_MODEL_PATH,
    OPERATIONAL_METADATA_PATH
)

@pytest.fixture
def temp_retraining_paths(tmp_path, monkeypatch):
    """
    Isolates registry paths and models folders inside a temporary directory.
    """
    registry_file = tmp_path / "model_registry.csv"
    models_dir = tmp_path / "models"
    op_model_dir = tmp_path / "op_models"
    op_model_file = op_model_dir / "engine2_model.pkl"
    op_meta_file = op_model_dir / "engine2_metadata.json"

    # Pre-create folders
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(op_model_dir, exist_ok=True)

    monkeypatch.setattr(cfg, "CUSTOMER_MODEL_REGISTRY_PATH", str(registry_file))
    monkeypatch.setattr(cfg, "MODELS_DIR", str(models_dir))

    # Temporarily override operational constants inside retrain_model module
    import backend.retraining.retrain_model as rm
    monkeypatch.setattr(rm, "OPERATIONAL_MODEL_DIR", str(op_model_dir))
    monkeypatch.setattr(rm, "OPERATIONAL_MODEL_PATH", str(op_model_file))
    monkeypatch.setattr(rm, "OPERATIONAL_METADATA_PATH", str(op_meta_file))

    # Also route sales, products, and inventory to test datasets if not already
    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", os.path.join(cfg.DEV_DATA_DIR, "sales.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_PRODUCTS_PATH", os.path.join(cfg.DEV_DATA_DIR, "products.csv"))
    monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", os.path.join(cfg.DEV_DATA_DIR, "inventory_current.csv"))

    return {
        "registry": registry_file,
        "models_dir": models_dir,
        "op_model_file": op_model_file,
        "op_meta_file": op_meta_file
    }


def test_registry_initialization(temp_retraining_paths):
    # Registry path should not exist at first
    assert not os.path.exists(temp_retraining_paths["registry"])
    
    # Initialize
    _initialize_registry()
    assert os.path.exists(temp_retraining_paths["registry"])
    
    df = pd.read_csv(temp_retraining_paths["registry"])
    assert list(df.columns) == [
        "model_version", "training_date", "training_rows", "train_r2", "val_r2", "test_r2", "active"
    ]


def test_train_and_activate_workflow(temp_retraining_paths):
    _initialize_registry()

    # Train a new model version
    version, eval_stats, rows = train_new_model()
    
    assert version == "v1"
    assert rows > 0
    assert "train_r2" in eval_stats
    
    # Check that model file was saved in the root models directory
    pkl_file = os.path.join(temp_retraining_paths["models_dir"], f"model_{version}.pkl")
    assert os.path.exists(pkl_file)

    # Check registry log
    df_reg = pd.read_csv(temp_retraining_paths["registry"])
    assert len(df_reg) == 1
    assert df_reg.iloc[0]["model_version"] == "v1"
    assert df_reg.iloc[0]["active"] == False  # Inactive initially
    
    # Activate version
    success = activate_model(version)
    assert success == True
    
    # Registry active status should be updated
    df_reg_updated = pd.read_csv(temp_retraining_paths["registry"])
    assert df_reg_updated.iloc[0]["active"] == True
    
    # Active pickled file should be copied to the operational path
    assert os.path.exists(temp_retraining_paths["op_model_file"])
    assert os.path.exists(temp_retraining_paths["op_meta_file"])

    # Verify load_active_model loads from active PKL file
    model, features, encoders = load_active_model()
    assert model is not None
    assert len(features) > 0
    assert encoders is not None


def test_customer_profile_and_confidence_calculations():
    from backend.onboarding.customer_profile import calculate_engine2_confidence
    assert calculate_engine2_confidence(5000) == 1.0
    assert calculate_engine2_confidence(2500) == 0.8
    assert calculate_engine2_confidence(1000) == 0.6
    assert calculate_engine2_confidence(500) == 0.4
    assert calculate_engine2_confidence(120) == 0.2
    assert calculate_engine2_confidence(50) == 0.1
    assert calculate_engine2_confidence(0) == 0.1


def test_retraining_insufficient_data(temp_retraining_paths, monkeypatch):
    # Mock CUSTOMER_SALES_PATH to a file with 10 rows
    sales_file = temp_retraining_paths["registry"].parent / "low_sales.csv"
    pd.DataFrame({"a": range(10)}).to_csv(sales_file, index=False)
    monkeypatch.setattr(cfg, "CUSTOMER_SALES_PATH", str(sales_file))

    res = train_new_model()
    assert isinstance(res, dict)
    assert res["status"] == "limited_data"
    assert "Insufficient data" in res["message"]
