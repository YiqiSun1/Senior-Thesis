# Load Car_2_7 results

import pandas as pd
data = pd.read_csv("./Data/new_CAR_27.csv")
print(f"new_car_27_columns: {data.columns}")

# load com performance
fundamental = pd.read_csv("./Data/new_car_1_with_fundamental.csv")
print(f"fundamental_columns: {fundamental.columns}")

target_cols = ['symbol', 'year', 'quarter', 'call_date',
            'stress_whole', 'car_01', 'vol', 'mom', 'POSWORDS', 'NEGWORDS', 'lnmve',
       'bm', 'atq', 'UE', 'actual_eps', 'median_forecast', 'numest']
dupes = fundamental[target_cols].duplicated(
    subset=['symbol', 'year', 'quarter', 'call_date']
).sum()
print(f"Duplicates in fundamental: {dupes}")

final_data = data.merge(fundamental[target_cols], on=['symbol', 'year', 'quarter', 'call_date'], how='left')
print(f"final_data_columns: {final_data.columns}")
final_data.to_csv("./Data/new_CAR_7_with_fundamental.csv", index=False)
