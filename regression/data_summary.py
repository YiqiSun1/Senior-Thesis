import pandas as pd

df = pd.read_csv("./Data/new_CAR_1_with_fundamental.csv")

def summary_stats(df, vars):
    stats = df[vars].describe().T[['count', 'mean', 'std', 'min', '50%', 'max']]
    stats.columns = ['N', 'Mean', 'SD', 'Min', 'Median', 'Max']
    stats = stats.round(3)
    stats['N'] = stats['N'].astype(int)  # count should be integer
    return stats

print(summary_stats(df, ['car_01', 'stress_qa', 'stress_pr', 'vol', 'mom', 'lnmve', 'bm', 'UE', 'POSWORDS', 'NEGWORDS']))