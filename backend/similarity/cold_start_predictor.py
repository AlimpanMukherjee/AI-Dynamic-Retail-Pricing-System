import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Tuple
from backend.similarity.product_similarity_engine import ProductSimilarityEngine


# Configure logging
logger = logging.getLogger("pricing_system.similarity.cold_start_predictor")

class ColdStartPredictor:
    """
    Generates pricing and demand estimates for products with insufficient sales history
    by borrowing intelligence from similar products.
    """
    def __init__(self, products_csv_path: str = None):
        """
        Initializes the ColdStartPredictor.
        """
        if products_csv_path is None:
            import backend.config as cfg
            products_csv_path = cfg.CUSTOMER_PRODUCTS_PATH
        self.similarity_engine = ProductSimilarityEngine(products_csv_path)
        self.products_dict = self.similarity_engine.products_dict

    def predict_cold_start(
        self,
        target_product_id: str,
        df: pd.DataFrame,
        model,
        features: List[str],
        retailer_company: str = None,
        store_location: str = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Runs cold-start prediction:
          1. Finds top similar products using deterministic business rules.
          2. Extracts their pricing & demand parameters (optimal price, demand, elasticity).
          3. Computes similarity-weighted averages to borrow their intelligence.
          
        Parameters:
            target_product_id (str): Product ID of the cold start SKU.
            df (pd.DataFrame): Joined and preprocessed global sales dataset.
            model: Trained global XGBoost model.
            features (list): Ordered feature names used by the XGBoost model.
            retailer_company (str, optional): Retailer context.
            store_location (str, optional): Location context.
            k (int): Number of similar products to consider.
            
        Returns:
            dict: Cold start recommendation containing optimal_price, expected_demand, elasticity, and metadata.
        """
        # Find similar products
        similar_items = self.similarity_engine.find_similar_products(target_product_id, k=k)
        
        logger.info(f"[Similarity] Found {len(similar_items)} similar products for {target_product_id}: {similar_items}")
        print(f"[Similarity] Found {len(similar_items)} similar products for {target_product_id}")

        valid_similar_products_used = []
        weighted_optimal_price = 0.0
        weighted_expected_demand = 0.0
        weighted_elasticity = 0.0
        total_weight = 0.0

        # Import engine2 helpers locally to avoid circular dependencies
        from backend.layer1.engine2 import (
            generate_demand_curve,
            calculate_revenue,
            find_optimal_price,
            compute_elasticity
        )

        for sim_id, similarity_score in similar_items:
            # Skip if similarity score is 0.0 (totally unrelated)
            if similarity_score <= 0.0:
                continue

            # Slice sales data for the similar product
            df_sim = df[df["product_id"] == sim_id]
            if df_sim.empty:
                logger.debug(f"[Similarity] Similar product {sim_id} has no sales records. Skipping.")
                continue

            # Try localized context filtering
            df_sim_filtered = df_sim.copy()
            if retailer_company:
                temp = df_sim_filtered[df_sim_filtered["retailer_company"].str.lower() == retailer_company.lower()]
                if not temp.empty:
                    df_sim_filtered = temp
            if store_location:
                temp = df_sim_filtered[df_sim_filtered["store_location"].str.lower() == store_location.lower()]
                if not temp.empty:
                    df_sim_filtered = temp

            # Extract base row for similar product
            try:
                base_row = df_sim_filtered.iloc[-1].to_dict()
                
                # Generate candidate price range
                p_min = df_sim_filtered["price"].min()
                p_max = df_sim_filtered["price"].max()
                if p_min == p_max or p_min <= 0:
                    p_min = base_row.get("price", 10.0) * 0.7
                    p_max = base_row.get("price", 10.0) * 1.3
                    
                price_range = np.linspace(p_min * 0.7, p_max * 1.3, 20)
                
                # Reconstruct similar product's demand curve & metrics
                df_curve = generate_demand_curve(model, features, base_row, price_range)
                df_curve = calculate_revenue(df_curve)
                
                sim_optimal = find_optimal_price(df_curve)
                sim_elasticity = compute_elasticity(df_curve)
                
                sim_optimal_price = float(sim_optimal["price"])
                sim_expected_demand = float(sim_optimal["demand"])
                sim_elast = float(sim_elasticity)
                
                # Add to weighted averages
                weighted_optimal_price += similarity_score * sim_optimal_price
                weighted_expected_demand += similarity_score * sim_expected_demand
                weighted_elasticity += similarity_score * sim_elast
                total_weight += similarity_score
                
                valid_similar_products_used.append((sim_id, similarity_score))
                
            except Exception as e:
                logger.warning(f"[Similarity] Error extracting metrics for similar product {sim_id}: {str(e)}")
                continue

        # If we successfully borrowed intelligence from similar products
        if total_weight > 0.0:
            aggregated_optimal_price = float(round(weighted_optimal_price / total_weight, 2))
            aggregated_expected_demand = float(round(weighted_expected_demand / total_weight, 2))
            aggregated_elasticity = float(round(weighted_elasticity / total_weight, 3))
        else:
            # Fallback to catalog defaults if no similar products have sales history
            logger.warning(f"[Similarity] No similar products with sales records found. Using defaults.")
            print("[Similarity] WARNING: No similar products with sales records. Using defaults.")
            
            target_item = self.products_dict.get(target_product_id, {})
            # Use base market price if available, else standard fallback
            aggregated_optimal_price = float(target_item.get("base_market_price", 25.0))
            aggregated_expected_demand = 50.0  # Safe default baseline
            aggregated_elasticity = -1.5  # Typical retail elasticity index

        return {
            "prediction_mode": "cold_start",
            "optimal_price": aggregated_optimal_price,
            "expected_demand": aggregated_expected_demand,
            "elasticity": aggregated_elasticity,
            "similar_products_used": valid_similar_products_used
        }
