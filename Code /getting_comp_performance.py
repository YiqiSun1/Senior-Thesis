# this gets the ROA and OCF data. 
import pandas as pd
ROA = pd.read_csv("./Data/ROA_data.csv")

ROA = ROA.sort_values(['gvkey', 'datadate'])

# Step 1: Get pure single-quarter OIBDPQ (YTD -> quarterly)
ROA['oibdpq_q'] = ROA.groupby(['gvkey', 'fyearq'])['oibdpq'].diff()
ROA['oibdpq_q'] = ROA['oibdpq_q'].fillna(ROA['oibdpq'])  # Q1 fix

# Step 2: Average total assets (current and prior quarter)
ROA['atq_lag'] = ROA.groupby('gvkey')['atq'].shift(1)
ROA['avg_atq'] = (ROA['atq'] + ROA['atq_lag']) / 2

# Step 3: Compute ROA
ROA['roa_q'] = ROA['oibdpq_q'] / ROA['avg_atq']  
print(ROA.loc[:, ['datadate','gvkey', 'fyearq', 'datadate', 'oibdpq', 'oibdpq_q', 'atq', 'atq_lag', 'avg_atq', 'roa_q']])
# df_comp_performance.drop_duplicates(subset=['Name', 'Email'])
# # load call date and stress scores
# stress_data = pd.read_csv("./Data/new_car_1_with_fundamental.csv")
# data = pd.read_csv("./Data/operating_CF.csv")
# print(data.head())
# data['ocf_q'] = data.groupby(['gvkey', 'datadate'])['oancfy'].diff()
# print(data.head())

# print(data.head())  
# for index, row in stress_data.iterrows():
#     symbol = row['symbol']
#     year   = row['year']
#     quarter= row['quarter']
#     print(symbol, year, quarter)
    
#     next_two_quarters = data[]
# OCF
data = pd.read_csv("./Data/new_comp_performance.csv")
data['ocf_q'] = data.groupby(['gvkey', 'fyearq'])['oancfy'].diff()
data['ocf_q'] = data['ocf_q'].fillna(data['oancfy'])
print(data.loc[:, ['gvkey', 'fyearq', 'oancfy', 'ocf_q', 'fqtr', 'datadate']])


final_data = data.merge(ROA[['gvkey', 'fyearq', 'roa_q', 'datadate']], on=['gvkey', 'fyearq', 'datadate'], how='left')
print(final_data.columns)
print(final_data.loc[:, ['gvkey', 'fyearq', 'datadate', 'ocf_q', 'roa_q']])

final_data.to_csv("./Data/ROA_OCF_data.csv", index=False)

# final_date = df_comp_performance.merge(data, on= )

# ROA
