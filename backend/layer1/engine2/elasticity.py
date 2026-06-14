import numpy as np

def compute_elasticity(df_curve):
    df_curve = df_curve.copy()
    df_curve["log_price"] = np.log(df_curve["price"])
    df_curve["log_demand"] = np.log(df_curve["demand"] + 1)
    
    slope = 0.0
    if df_curve["log_price"].nunique() > 1 and df_curve["log_demand"].nunique() > 1:
        slope = np.polyfit(df_curve["log_price"], df_curve["log_demand"], 1)[0]
        
    return slope
