# Operational Inventory Source Audit Report

| File Name | Line Number | Content | Target / Source Type |
| --- | --- | --- | --- |
| app.py | 14 | `# 1. Trigger legacy inventory database auto-migration (inventory.csv -> inventory_current & inventory_history)` | inventory.csv (Direct Legacy String) |
| implementation_flow.md | 65 | `customer_data/inventory.csv` | inventory.csv (Direct Legacy String) |
| implementation_flow.md | 75 | `datasets/inventory.csv` | inventory.csv (Direct Legacy String) |
| implementation_flow.md | 169 | `inventory.csv` | inventory.csv (Direct Legacy String) |
| implementation_flow.md | 208 | `inventory.csv` | inventory.csv (Direct Legacy String) |
| project_structure.md | 77 | `|   |-- inventory.csv                   # Historical initial stock details` | inventory.csv (Direct Legacy String) |
| backend/config.py | 13 | `DEV_INVENTORY_PATH = os.path.join(DEV_DATA_DIR, "inventory_current.csv")` | DEV_INVENTORY_PATH (Developer Reference) |
| backend/config.py | 14 | `DEV_INVENTORY_CURRENT_PATH = os.path.join(DEV_DATA_DIR, "inventory_current.csv")` | inventory_current.csv (Direct String) |
| backend/config.py | 34 | `elif name == "CUSTOMER_INVENTORY_PATH":` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/config.py | 35 | `return os.path.join(_get_customer_data_dir(), "inventory_current.csv")` | inventory_current.csv (Direct String) |
| backend/config.py | 36 | `elif name == "CUSTOMER_INVENTORY_CURRENT_PATH":` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/config.py | 37 | `return os.path.join(_get_customer_data_dir(), "inventory_current.csv")` | inventory_current.csv (Direct String) |
| backend/data_ingestion/inventory_ingestion.py | 6 | `Validates and UPSERTs new inventory records to inventory_current.csv` | inventory_current.csv (Direct String) |
| backend/inventory/inventory_ingestion.py | 16 | `If they do not exist, and legacy inventory.csv exists, automatically migrates them.` | inventory.csv (Direct Legacy String) |
| backend/inventory/inventory_ingestion.py | 18 | `current_path = cfg.CUSTOMER_INVENTORY_CURRENT_PATH` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/inventory/inventory_ingestion.py | 26 | `old_inventory_path = os.path.join(data_dir, "inventory.csv")` | inventory.csv (Direct Legacy String) |
| backend/inventory/inventory_ingestion.py | 30 | `old_inventory_path = os.path.join(cfg.DEV_DATA_DIR, "inventory.csv")` | inventory.csv (Direct Legacy String) |
| backend/inventory/inventory_ingestion.py | 33 | `logger.info("Legacy inventory.csv not found. Skipping auto-migration.")` | inventory.csv (Direct Legacy String) |
| backend/inventory/inventory_ingestion.py | 36 | `logger.info(f"Legacy inventory.csv found at {old_inventory_path}. Migrating datasets...")` | inventory.csv (Direct Legacy String) |
| backend/inventory/inventory_ingestion.py | 169 | `Performs UPSERT logic into inventory_current.csv.` | inventory_current.csv (Direct String) |
| backend/inventory/inventory_ingestion.py | 176 | `current_path = cfg.CUSTOMER_INVENTORY_CURRENT_PATH` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/inventory/inventory_ingestion.py | 315 | `Deducts the units sold in sales_df from the current stock in inventory_current.csv.` | inventory_current.csv (Direct String) |
| backend/inventory/inventory_ingestion.py | 319 | `inventory_path = cfg.CUSTOMER_INVENTORY_CURRENT_PATH` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/inventory/test_inventory_ops.py | 24 | `current_file = tmp_path / "inventory_current.csv"` | inventory_current.csv (Direct String) |
| backend/inventory/test_inventory_ops.py | 28 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(current_file))` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/inventory/test_inventory_ops.py | 30 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(current_file))` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/inventory/test_inventory_ops.py | 33 | `# Pre-populate a fake old inventory.csv to simulate legacy data` | inventory.csv (Direct Legacy String) |
| backend/inventory/test_inventory_ops.py | 34 | `old_file = tmp_path / "inventory.csv"` | inventory.csv (Direct Legacy String) |
| backend/layer1/engine2.py | 24 | `inventory_csv_path=cfg.DEV_INVENTORY_PATH,` | DEV_INVENTORY_PATH (Developer Reference) |
| backend/layer1/engine3.py | 176 | `csv_path = cfg.CUSTOMER_INVENTORY_PATH` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/layer1/engine3.py | 241 | `result = run_pipeline(cfg.CUSTOMER_INVENTORY_PATH, "SKU_1000", "Reliance Retail", "Bengaluru")` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/layer1/engine2/engine2.py | 59 | `inventory_csv_path = cfg.CUSTOMER_INVENTORY_PATH` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/layer1/engine2/test_engine2_ops.py | 181 | `inv_file = tmp_path / "inventory.csv"` | inventory.csv (Direct Legacy String) |
| backend/layer1/engine2/test_engine2_ops.py | 187 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inv_file))` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/layer1/engine2/test_engine2_ops.py | 188 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inv_file))` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/layer1/engine2/test_engine2_ops.py | 331 | `inv_file = tmp_path / "inventory.csv"` | inventory.csv (Direct Legacy String) |
| backend/layer1/engine2/test_engine2_ops.py | 338 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", str(inv_file))` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/layer1/engine2/test_engine2_ops.py | 339 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_CURRENT_PATH", str(inv_file))` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
| backend/layer2/generate_training_data.py | 47 | `inventory_csv = "datasets/inventory.csv"` | inventory.csv (Direct Legacy String) |
| backend/onboarding/test_validators.py | 178 | `temp_file = tmp_path / "inventory.csv"` | inventory.csv (Direct Legacy String) |
| backend/onboarding/upload_inventory.py | 4 | `from backend.config import CUSTOMER_INVENTORY_PATH` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/onboarding/upload_inventory.py | 6 | `def upload_inventory(file_source, target_path=CUSTOMER_INVENTORY_PATH) -> str:` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/pipeline/pricing_pipeline.py | 45 | `inventory_csv = cfg.CUSTOMER_INVENTORY_PATH` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/retraining/retrain_model.py | 95 | `inventory_path = cfg.CUSTOMER_INVENTORY_PATH` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/retraining/retrain_model.py | 97 | `inventory_path = cfg.DEV_INVENTORY_PATH` | DEV_INVENTORY_PATH (Developer Reference) |
| backend/retraining/test_retraining.py | 41 | `monkeypatch.setattr(cfg, "CUSTOMER_INVENTORY_PATH", os.path.join(cfg.DEV_DATA_DIR, "inventory_current.csv"))` | CUSTOMER_INVENTORY_PATH (Target Operational) |
| backend/similarity/test_cold_start.py | 19 | `files = ["products.csv", "procurement.csv", "inventory_current.csv", "inventory_history.csv", "competitors.csv", "sales.csv"]` | inventory_current.csv (Direct String) |
| backend/similarity/test_cold_start.py | 42 | `with open("datasets/inventory_current.csv", "a") as file:` | inventory_current.csv (Direct String) |
| frontend/services/inventory_service.py | 22 | `current_path = cfg.CUSTOMER_INVENTORY_CURRENT_PATH` | CUSTOMER_INVENTORY_CURRENT_PATH (Target Operational) |
