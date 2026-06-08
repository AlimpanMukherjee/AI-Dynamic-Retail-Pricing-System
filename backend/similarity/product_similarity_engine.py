import os
import pandas as pd
from typing import List, Tuple, Dict, Any
from backend.similarity.similarity_utils import calculate_pack_size_similarity


class ProductSimilarityEngine:
    """
    Computes similarity between products in the catalog based on category,
    subcategory, and pack size, using business-rule weightings.
    """
    def __init__(self, products_csv_path: str = None):
        """
        Initializes the similarity engine and loads the product catalog.
        """
        if products_csv_path is None:
            import backend.config as cfg
            products_csv_path = cfg.CUSTOMER_PRODUCTS_PATH
        self.products_csv_path = products_csv_path
        self.df_products = None
        self.products_dict = {}
        self._load_catalog()

    def _load_catalog(self):
        """
        Loads the catalog from CSV and indexes it by product_id.
        """
        if not os.path.exists(self.products_csv_path):
            raise FileNotFoundError(f"Products dataset not found at: {self.products_csv_path}")
            
        self.df_products = pd.read_csv(self.products_csv_path)
        
        # Core checks for expected columns
        required_cols = ["product_id", "category", "subcategory", "pack_size_ml"]
        for col in required_cols:
            if col not in self.df_products.columns:
                raise ValueError(f"Required column '{col}' missing from products CSV.")
                
        # Clean and map to dictionary index for fast lookup
        self.df_products["product_id"] = self.df_products["product_id"].astype(str).str.strip()
        self.products_dict = self.df_products.set_index("product_id").to_dict(orient="index")

    def find_similar_products(self, target_product_id: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Finds the top K most similar products in the catalog using deterministic business weights:
          - Category Match = 40%
          - Subcategory Match = 40%
          - Pack Size Similarity = 20%
          
        Parameters:
            target_product_id (str): The product ID to query.
            k (int): Number of top matches to return.
            
        Returns:
            list: Sorted list of tuples (product_id, similarity_score) in descending order,
                  excluding the target product itself.
        """
        target_pid = str(target_product_id).strip()
        if target_pid not in self.products_dict:
            raise ValueError(f"Product ID '{target_pid}' not found in the catalog.")
            
        target = self.products_dict[target_pid]
        target_cat = str(target.get("category", "")).strip().lower()
        target_subcat = str(target.get("subcategory", "")).strip().lower()
        
        try:
            target_pack = float(target.get("pack_size_ml", 0))
        except (ValueError, TypeError):
            target_pack = 0.0

        scores = []
        
        for pid, prod in self.products_dict.items():
            if pid == target_pid:
                continue
                
            # Category match (40%)
            cat = str(prod.get("category", "")).strip().lower()
            cat_match = 1.0 if (cat == target_cat and target_cat != "") else 0.0
            
            # Subcategory match (40%)
            subcat = str(prod.get("subcategory", "")).strip().lower()
            subcat_match = 1.0 if (subcat == target_subcat and target_subcat != "") else 0.0
            
            # Pack size similarity (20%)
            try:
                pack = float(prod.get("pack_size_ml", 0))
            except (ValueError, TypeError):
                pack = 0.0
            pack_sim = calculate_pack_size_similarity(target_pack, pack)
            
            # Weighted calculation
            score = (0.40 * cat_match) + (0.40 * subcat_match) + (0.20 * pack_sim)
            scores.append((pid, float(round(score, 4))))
            
        # Sort by similarity score descending, and alphabetically by product ID to break ties deterministically
        scores.sort(key=lambda x: (-x[1], x[0]))
        
        return scores[:k]
