import pytest
import pandas as pd
import numpy as np
import os
import shutil

from backend.similarity.similarity_utils import calculate_pack_size_similarity
from backend.similarity.product_similarity_engine import ProductSimilarityEngine
from backend.similarity.cold_start_predictor import ColdStartPredictor
from backend.layer1.engine2 import determine_prediction_mode, hybrid_prediction
from backend.pipeline.pricing_pipeline import run_coordinated_pricing

@pytest.fixture(scope="module", autouse=True)
def setup_mock_products():
    """
    Setup fixture that backs up datasets and appends simulated cold-start (0 sales)
    and hybrid (45 sales) test products. Automatically restores backups on teardown.
    """
    files = ["products.csv", "procurement.csv", "inventory.csv", "competitors.csv", "sales.csv"]
    backup_paths = {}
    
    # 1. Create backups
    for f in files:
        src = f"datasets/{f}"
        dst = f"datasets/{f}.bak"
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            backup_paths[f] = dst

    try:
        # 2. Append mock product catalog profiles
        with open("datasets/products.csv", "a") as file:
            file.write("\nSKU_9999,Campa Cola Test,Campa,Beverages,14.0,100,Carbonated Soft Drink,200")
            file.write("\nSKU_9998,Campa Cola Hybrid,Campa,Beverages,14.0,100,Carbonated Soft Drink,200")

        # 3. Append procurement supplier info
        with open("datasets/procurement.csv", "a") as file:
            file.write("\nSKU_9999,Campa Cola Test,Campa,SUP_564,Mumbai,9.19,0.77,0.22,0.93,6,0.98,100")
            file.write("\nSKU_9998,Campa Cola Hybrid,Campa,SUP_564,Mumbai,9.19,0.77,0.22,0.93,6,0.98,100")

        # 4. Append inventory stock levels
        with open("datasets/inventory.csv", "a") as file:
            file.write("\nSKU_9999,Campa Cola Test,Campa,Beverages,Reliance Retail,Mumbai,Bengaluru,1424,124,319,202,55.76,14,112,529.24,0.78")
            file.write("\nSKU_9998,Campa Cola Hybrid,Campa,Beverages,Reliance Retail,Mumbai,Bengaluru,1424,124,319,202,55.76,14,112,529.24,0.78")

        # 5. Append competitors pricing
        with open("datasets/competitors.csv", "a") as file:
            file.write("\nSKU_9999,Campa Cola Test,Blinkit,14.17,Mumbai,True,4.3")
            file.write("\nSKU_9998,Campa Cola Hybrid,Blinkit,14.17,Mumbai,True,4.3")

        # 6. Append sales history:
        # SKU_9999 has 0 sales records -> Cold Start (0-30)
        # SKU_9998 has 45 sales records -> Hybrid (31-100)
        with open("datasets/sales.csv", "a") as file:
            for i in range(1, 46):
                date_str = f"2025-11-{i:02d}" if i <= 30 else f"2025-12-{i-30:02d}"
                file.write(f"\n{date_str},SKU_9998,Campa Cola Hybrid,Campa,Beverages,14.0,200,2800.0,0")

        yield
    finally:
        # 7. Restore all backup files
        for f, bak in backup_paths.items():
            src = f"datasets/{f}"
            if os.path.exists(bak):
                shutil.copyfile(bak, src)
                os.remove(bak)

def test_pack_size_similarity():
    """
    Tests pack size similarity function milestones.
    """
    # 200ml vs 200ml -> 1.0 (exact match)
    assert pytest.approx(calculate_pack_size_similarity(200, 200), 0.01) == 1.0
    
    # 200ml vs 250ml -> ~0.90 (close match)
    assert pytest.approx(calculate_pack_size_similarity(200, 250), 0.02) == 0.90
    
    # 200ml vs 2L (2000ml) -> ~0.10 (large size discrepancy)
    assert pytest.approx(calculate_pack_size_similarity(200, 2000), 0.02) == 0.10
    
    # Check invalid inputs
    assert calculate_pack_size_similarity(0, 200) == 0.0
    assert calculate_pack_size_similarity(200, -50) == 0.0

def test_determine_prediction_mode():
    """
    Tests prediction mode mapping thresholds:
      - 0 to 30 -> cold_start
      - 31 to 100 -> hybrid
      - > 100 -> normal
    """
    assert determine_prediction_mode(0) == "cold_start"
    assert determine_prediction_mode(15) == "cold_start"
    assert determine_prediction_mode(30) == "cold_start"
    
    assert determine_prediction_mode(31) == "hybrid"
    assert determine_prediction_mode(50) == "hybrid"
    assert determine_prediction_mode(100) == "hybrid"
    
    assert determine_prediction_mode(101) == "normal"
    assert determine_prediction_mode(500) == "normal"

def test_hybrid_prediction_blending():
    """
    Verifies that hybrid interpolation is smooth and continuous.
    """
    hist_metrics = {"optimal_price": 10.0, "expected_demand": 100.0, "elasticity": -1.0}
    sim_metrics = {"optimal_price": 20.0, "expected_demand": 200.0, "elasticity": -2.0, "similar_products_used": []}
    
    # 31 records: 10% history (10.0 * 0.1 + 20.0 * 0.9 = 19.0)
    res_31 = hybrid_prediction(hist_metrics, sim_metrics, 31)
    assert pytest.approx(res_31["optimal_price"], 0.1) == 19.0
    assert pytest.approx(res_31["expected_demand"], 1.0) == 190.0
    assert pytest.approx(res_31["elasticity"], 0.05) == -1.9
    
    # 50 records: 30% history (10.0 * 0.3 + 20.0 * 0.7 = 17.0)
    res_50 = hybrid_prediction(hist_metrics, sim_metrics, 50)
    assert pytest.approx(res_50["optimal_price"], 0.1) == 17.0
    assert pytest.approx(res_50["expected_demand"], 1.0) == 170.0
    assert pytest.approx(res_50["elasticity"], 0.05) == -1.7
    
    # 100 records: 100% history (10.0)
    res_100 = hybrid_prediction(hist_metrics, sim_metrics, 100)
    assert pytest.approx(res_100["optimal_price"], 0.1) == 10.0
    assert pytest.approx(res_100["expected_demand"], 1.0) == 100.0
    assert pytest.approx(res_100["elasticity"], 0.05) == -1.0

def test_similarity_engine():
    """
    Verifies ProductSimilarityEngine searches.
    """
    engine = ProductSimilarityEngine("datasets/products.csv")
    
    # Look up simulated target product Campa Cola Test (SKU_9999)
    similar_items = engine.find_similar_products("SKU_9999", k=5)
    
    assert len(similar_items) == 5
    assert "SKU_9999" not in [item[0] for item in similar_items]
    
    # Assert similarity scores are sorted in descending order
    scores = [item[1] for item in similar_items]
    assert scores == sorted(scores, reverse=True)
    
    for score in scores:
        assert 0.0 <= score <= 1.0

def test_pipeline_integration():
    """
    Runs the full end-to-end pricing pipeline (Layers 1-3) to ensure:
      - Normal products continue to function without changes.
      - Cold Start products function correctly using similar product signals.
      - Hybrid products smoothly blend signals.
    """
    # 1. Normal Product (SKU_1000 has > 100 sales records)
    normal_result = run_coordinated_pricing(
        product_id="SKU_1000",
        retailer_company="Reliance Retail",
        store_location="Mumbai"
    )
    
    assert normal_result["product_id"] == "SKU_1000"
    assert normal_result["pricing_state"]["E2"]["prediction_source"] == "historical_sales"
    assert normal_result["final_price"] > 0
    
    # 2. Cold Start Product (SKU_9999 has 0 sales records)
    cold_result = run_coordinated_pricing(
        product_id="SKU_9999",
        retailer_company="Reliance Retail",
        store_location="Mumbai"
    )
    
    assert cold_result["product_id"] == "SKU_9999"
    assert cold_result["pricing_state"]["E2"]["prediction_source"] == "similar_products"
    assert len(cold_result["pricing_state"]["E2"]["similar_products_used"]) > 0
    assert cold_result["final_price"] > 0
    
    # 3. Hybrid Product (SKU_9998 has 45 sales records)
    hybrid_result = run_coordinated_pricing(
        product_id="SKU_9998",
        retailer_company="Reliance Retail",
        store_location="Mumbai"
    )
    
    assert hybrid_result["product_id"] == "SKU_9998"
    assert hybrid_result["pricing_state"]["E2"]["prediction_source"] == "hybrid"
    assert len(hybrid_result["pricing_state"]["E2"]["similar_products_used"]) > 0
    assert hybrid_result["final_price"] > 0

    # Verify Layer 2 and Layer 3 outputs are produced without changes to their codebase
    assert "coordinated_weights" in cold_result
    assert "final_price" in cold_result
    assert "winning_candidate" in cold_result
