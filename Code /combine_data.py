import pandas as pd

# Load main results
main = pd.read_parquet('./data_testing_storage/stress_scores_final.parquet')

# Load retry results
retry = pd.read_parquet('./data_testing_storage/stress_scores_final_resubmission.parquet')

print(f"Main:  {len(main)} rows")
print(f"Retry: {len(retry)} rows")

# Combine
combined = pd.concat([main, retry], ignore_index=True)

# Drop duplicates — keep last (retry results are more recent)
combined = combined.drop_duplicates(
    subset=['symbol', 'year', 'quarter', 'section'],
    keep='last'
)

print(f"Combined: {len(combined)} rows")

# Verify
print(f"\nBy section:")
print(combined['section'].value_counts())

print(f"\nScore distribution:")
print(combined['stress_score'].value_counts().sort_index())

# Save
combined.to_parquet('./data_testing_storage/stress_scores_combined.parquet', index=False)
combined.to_csv('./data_testing_storage/stress_scores_combined.csv', index=False)

print("\n✅ Saved stress_scores_combined")