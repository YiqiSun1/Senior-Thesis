# import pandas as pd

# # load our fundamental data

# master_data = pd.read_csv("./Data/new_car_1_with_fundamental.csv")
# target_data = pd.read_csv("./Data/ROA_OCF_data.csv")

# result = []
# for index, row in master_data.iterrows():
#     symbol = row['symbol']
#     year   = row['year']
#     quarter= row['quarter']
#     call_date = row['call_date']
#     current_year = row['year']
#     current_quarter = row['quarter']

#     # if the call_date doesn't have two future quarters, then skip
    
#     future_two_quarters = target_data[(target_data['tic'] == symbol) & (target_data['datadate'] > call_date)]
#     if len(future_two_quarters) < 2:
#         continue
#     future_two_quarter_date = future_two_quarters['datadate'].iloc[1]
#     future_two_quarters_df = future_two_quarters[(future_two_quarters['datadate'] == future_two_quarter_date) & (future_two_quarters['tic'] == symbol)]
    
#     print(f"current: {symbol} | call_date: {call_date} | future_two_quarter_date: {future_two_quarter_date} | future_two_quarters_df: {future_two_quarters_df[['datadate', 'roa_q', 'ocf_q']]}")
#     result.append({
#         'symbol': symbol,
#         'year': year,
#         'quarter': quarter,
#         'call_date': call_date,
#         'future_roa': future_two_quarters_df['roa_q'],
#         'future_OCF': future_two_quarters_df['ocf_q']
#     })
#     print(result)
#     if index == 1: 
#         break

# # merge everything
# df = pd.DataFrame(result)
# df.to_csv("./Data/merged_ROA_OCF.csv", index=False) 
# master_data.merge(roa_data, on=['gvkey', 'fyearq', 'datadate'], how='left')

import pandas as pd

master_data = pd.read_csv("./Data/new_car_1_with_fundamental.csv")
target_data = pd.read_csv("./Data/ROA_OCF_data.csv")

# Ensure dates are datetime for proper comparison
master_data['call_date'] = pd.to_datetime(master_data['call_date'])
target_data['datadate']  = pd.to_datetime(target_data['datadate'])

# For each firm, rank future quarters after call_date
# Step 1: cross join on symbol/tic
merged = master_data.merge(target_data, left_on='symbol', right_on='tic', how='left')

# Step 2: keep only future quarters
merged = merged[merged['datadate'] > merged['call_date']]

# Step 3: rank future quarters per firm-call (1=next quarter, 2=two quarters out)
merged['future_rank'] = merged.groupby(['symbol', 'call_date'])['datadate'].rank(method='first').astype(int)

# Step 4: keep only the 2nd future quarter
result = merged[merged['future_rank'] == 2].copy()

# Step 5: save
result.to_csv("./Data/merged_ROA_OCF.csv", index=False)