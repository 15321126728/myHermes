import pandas as pd
import numpy as np
from pgmpy.models import LinearGaussianBayesianNetwork
from pgmpy.estimators import HillClimbSearch, BICGauss
from pgmpy.causal_discovery import ExpertKnowledge

df = pd.read_csv('bn_sample_10k.csv')
print("Data loaded:", df.shape)

expert = ExpertKnowledge(forbidden_edges=[("Y","U"),("R","U"),("D","U"),("M","U")])
hc = HillClimbSearch(df)
dag = hc.estimate(scoring_method=BICGauss(df), max_indegree=5, expert_knowledge=expert)
edges = list(dag.edges())
print("Learned DAG:", edges)

with open("learned_dag.csv", "w") as f:
    f.write("to,from
")
    for e in edges:
        f.write(f"{e[0]},{e[1]}
")
print("Saved learned_dag.csv")

bn = LinearGaussianBayesianNetwork(edges)
bn.fit(df)
print("Model fitted")

intervened_edges = [e for e in edges if e[1] != "Y"]
with open("intervened_dag.csv", "w") as f:
    f.write("to,from
")
    for e in intervened_edges:
        f.write(f"{e[0]},{e[1]}
")
print("Intervened DAG:", intervened_edges)

samples = bn.simulate(n_samples=10000, do={"Y": 0.0}, seed=42)
samples.to_csv("final_bn_sample.csv", index=False)
print(f"Sampled {len(samples)} points")
print(f"Y: mean={samples["Y"].mean():.6f}, std={samples["Y"].std():.6f}")
print(samples.head())
