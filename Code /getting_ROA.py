import pandas as pd 

# load call date and stress scores
data = pd.read_csv("./Data/new_car_1_with_fundamental.csv")
print(data.head())

print(data.columns)
