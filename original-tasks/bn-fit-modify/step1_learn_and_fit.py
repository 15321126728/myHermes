import pandas as pd
import numpy as np
from pgmpy.models import BayesianNetwork
from pgmpy.estimators import MaximumLikelihoodEstimator

# Load data
df = pd.read_csv('bn_sample_10k.csv')

# Define the DAG based on analysis:
# U has no parents (it's the source)
# Significant partial correlations indicate these 6 edges:
# U→Y, U→R, U→D, U→M, D→Y, R→M
# Direction for D→Y: Y comes before D in alphabet → Y is child of D
# Direction for R→M: M comes before R in alphabet → M is child of R
edges = [('U', 'Y'), ('U', 'R'), ('U', 'D'), ('U', 'M'), ('D', 'Y'), ('R', 'M')]

# Save DAG edges to CSV
with open('learned_dag.csv', 'w') as f:
    f.write('to,from\n')
    for to, from_ in edges:
        f.write(f'{to},{from_}\n')
print("Saved learned_dag.csv")

# Create and fit the Bayesian Network
model = BayesianNetwork(edges)
model.fit(df, estimator=MaximumLikelihoodEstimator)

# Print the CPDs
print("\nLearned CPDs:")
for cpd in model.get_cpds():
    print(cpd)

# Check model
print(f"\nModel check: {model.check_model()}")
