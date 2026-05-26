import pandas as pd
import numpy as np

# Load both
master   = pd.read_csv("Data/new_CAR_01_280.csv")
car_new  = pd.read_csv("Data/new_CAR_1.csv")

# Merge on symbol + call_date
compare = master[['symbol', 'call_date', 'car_01']].merge(
    car_new[['symbol', 'call_date', 'car_01']],
    on=['symbol', 'call_date'],
    how='inner',
    suffixes=('_old', '_new')
)

print(f"Matched rows: {len(compare)}")

# ─── CORRELATION ───
corr = compare['car_01_old'].corr(compare['car_01_new'])
print(f"\nCorrelation: {corr:.4f}")

# ─── DIFFERENCE ───
compare['diff'] = compare['car_01_old'] - compare['car_01_new']
print(f"\nDifference stats:")
print(compare['diff'].describe())

# ─── SPOT CHECK ───
print(f"\nLargest differences:")
print(compare.nlargest(10, 'diff')[['symbol', 'call_date', 
                                     'car_01_old', 'car_01_new', 'diff']])

# ─── VISUAL CHECK ───
import matplotlib.pyplot as plt

plt.figure(figsize=(6,6))
plt.scatter(compare['car_01_old'], compare['car_01_new'], alpha=0.3, s=5)
plt.axline((0,0), slope=1, color='red', linestyle='--', label='45 degree line')
plt.xlabel('CAR_01 Old')
plt.ylabel('CAR_01 New')
plt.title(f'CAR(0,1) Comparison (corr={corr:.4f})')
plt.legend()
plt.tight_layout()
plt.savefig('Data/car_comparison.png')
plt.show()