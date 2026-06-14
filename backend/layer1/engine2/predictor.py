import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_demand_curve(model, features, base_row, price_range):
    # Vectorized generation to avoid slow loops
    rows = []
    for price in price_range:
        row = base_row.copy()
        row["price"] = price
        row["log_price"] = np.log(price)
        rows.append(row)
        
    df_temp = pd.DataFrame(rows)
    df_temp["demand"] = model.predict(df_temp[features])
    
    # Conditional post-prediction scaling:
    identity_features = ["retailer_encoded", "city_encoded", "retailer_strength", "city_strength"]
    if not any(f in features for f in identity_features):
        if "retailer_strength" in base_row and "city_strength" in base_row:
            df_temp["demand"] = df_temp["demand"] * base_row["retailer_strength"] * base_row["city_strength"]
            
    df_temp["demand"] = df_temp["demand"].clip(lower=0) # Demand cannot be negative
    
    return df_temp[["price", "demand"]]

def calculate_revenue(df_curve):
    df_curve["revenue"] = df_curve["price"] * df_curve["demand"]
    return df_curve

def find_optimal_price(df_curve):
    best_row = df_curve.loc[df_curve["revenue"].idxmax()]
    return best_row

def plot_curve(df_curve, product_id):
    plt.figure()
    plt.plot(df_curve["price"], df_curve["demand"], marker='o', color='darkblue')
    plt.xlabel("Price")
    plt.ylabel("Demand")
    plt.title(f"Demand Curve for {product_id}")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plot_filename = f"demand_curve_{product_id}.png"
    plt.savefig(plot_filename)
    plt.close()
