# Feature Engineering Module for SIH26054 Digital Twin
# Defines the logic to calculate the structured feature vector X_t.
# X_t = X_raw \oplus X_phys \oplus X_temp \oplus X_context

import pandas as pd
import numpy as np
from typing import Union

def calculate_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates rolling window and temporal statistics (X_temp) for key sensor readings.
    
    Assumes:
    1. The DataFrame 'df' index is a datetime object (timestamp).
    2. Key sensors ('cht', 'egt', 'oil_pressure', 'vibration_rms') are present as columns.

    Args:
        df: DataFrame containing raw sensor readings.

    Returns:
        A DataFrame containing the calculated X_temp features.
    """
    print("--- Starting X_temp (Temporal Feature) Calculation ---")
    
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        raise ValueError("DataFrame index must be a pandas datetime index.")

    key_sensors = ['cht', 'egt', 'oil_pressure', 'vibration_rms']
    X_temp_features = pd.DataFrame(index=df.index)

    # 1. Rolling Window Statistics (Mean, Std, Min, Max) - Window: 60s
    for sensor in key_sensors:
        if sensor not in df.columns:
            print(f"Warning: Sensor '{sensor}' not found in data. Skipping rolling features.")
            continue
            
        rolling_mean = df[sensor].rolling(window=f'{60}s', min_periods=1).mean()
        rolling_std = df[sensor].rolling(window=f'{60}s', min_periods=1).std().fillna(0)
        rolling_min = df[sensor].rolling(window=f'{60}s', min_periods=1).min()
        rolling_max = df[sensor].rolling(window=f'{60}s', min_periods=1).max()

        X_temp_features[f'{sensor}_mean_60s'] = rolling_mean
        X_temp_features[f'{sensor}_std_60s'] = rolling_std
        X_temp_features[f'{sensor}_min_60s'] = rolling_min
        X_temp_features[f'{sensor}_max_60s'] = rolling_max

    # 2. Rate-of-Change (Approximation using diff and time delta)
    for sensor in ['cht', 'egt', 'oil_pressure', 'vibration_rms']:
        if sensor not in df.columns: continue
        
        time_delta = df.index.to_series().diff()
        safe_time_delta = np.where(time_delta.dt.total_seconds() > 0, time_delta.dt.total_seconds(), 1e-6)
        rate_of_change = df[sensor].diff() / safe_time_delta
        
        X_temp_features[f'{sensor}_roc'] = rate_of_change

    # 3. Trend Feature (Slope calculation)
    def rolling_slope(series: pd.Series, window: str) -> float:
        if series.dropna().empty: return np.nan
        valid_series = series.dropna()
        if len(valid_series) < 2: return np.nan
        
        time_index = (valid_series.index - valid_series.index.min()).total_seconds()
        value = valid_series.values
        
        slope, intercept = np.polyfit(time_index, value, 1)
        return slope

    for sensor in ['cht', 'egt', 'oil_pressure', 'vibration_rms']:
        if sensor in df.columns:
            X_temp_features[f'{sensor}_slope_60s'] = df[sensor].rolling(window=f'{60}s', min_periods=2).apply(
                lambda x: rolling_slope(x, '60s'), raw=False
            )
        
    return X_temp_features.dropna()


def run_prototype_validation():
    """
    Creates synthetic data and runs the full X_temp calculation pipeline 
    to validate dimensional integrity and NaN handling.
    """
    print("\n=================================================================")
    print("--- Running X_temp Prototype Validation (Synthetic Data) ---")
    print("=================================================================\n")

    # --- 1. Create Synthetic Data ---
    start_time = pd.to_datetime('2023-01-01 00:00:00')
    end_time = pd.to_datetime('2023-01-01 00:02:00') # 120 seconds of data
    timestamps = pd.date_range(start=start_time, end=end_time, freq='s')
    
    data = {
        'cht': np.sin(np.linspace(0, 2 * np.pi, len(timestamps))) * 10 + 100,
        'egt': np.cos(np.linspace(0, 2 * np.pi, len(timestamps))) * 5 + 500,
        'oil_pressure': np.linspace(40, 60, len(timestamps)) + np.random.normal(0, 1, len(timestamps)),
        'vibration_rms': np.linspace(0.5, 1.5, len(timestamps)) + np.random.normal(0, 0.1, len(timestamps)),
        'raw_rpm': np.linspace(3000, 3200, len(timestamps)) + np.random.normal(0, 1, len(timestamps)),
        'timestamp': timestamps
    }
    
    df_raw = pd.DataFrame(data)
    df_raw = df_raw.set_index('timestamp')
    
    print(f"Synthetic raw data created. Dimensions: {df_raw.shape}")

    # --- 2. Run Calculation ---
    try:
        x_temp = calculate_temporal_features(df_raw)
        
        # --- 3. Validation ---
        print("\n[SUCCESS] X_temp Feature Generation Complete.")
        print(f"Resulting X_temp DataFrame Shape: {x_temp.shape}")
        print("\nFirst 5 rows of X_temp:")
        print(x_temp.head())
        print("\nLast 5 rows of X_temp:")
        print(x_temp.tail())

    except Exception as e:
        print(f"\n[ERROR] An exception occurred during X_temp calculation: {e}")

if __name__ == "__main__":
    run_prototype_validation()