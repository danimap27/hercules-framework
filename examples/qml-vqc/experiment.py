"""
experiment.py — Example: PennyLane VQC binary classification sweep.

Trains a variational quantum circuit on a small binary classification task
and outputs accuracy and training time. runner.py calls this with
the parameters for each run.
"""

import argparse
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.datasets import make_classification
from sklearn.preprocessing import MinMaxScaler
import pennylane as qml


def build_circuit(n_qubits: int, n_layers: int, ansatz: str, diff_method: str = "adjoint"):
    dev = qml.device("default.qubit", wires=n_qubits)

    @qml.qnode(dev, diff_method=diff_method)
    def circuit(params, x):
        qml.AngleEmbedding(x, wires=range(n_qubits), rotation="Y")
        if ansatz == "strongly_entangling":
            qml.StronglyEntanglingLayers(params, wires=range(n_qubits))
        elif ansatz == "basic_entangler":
            qml.BasicEntanglerLayers(params, wires=range(n_qubits))
        return qml.expval(qml.PauliZ(0))

    return circuit


def get_param_shape(ansatz: str, n_qubits: int, n_layers: int) -> tuple:
    if ansatz == "strongly_entangling":
        return (n_layers, n_qubits, 3)
    return (n_layers, n_qubits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ansatz", default="strongly_entangling")
    ap.add_argument("--n-qubits", type=int, default=4)
    ap.add_argument("--n-layers", type=int, default=2)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Synthetic binary dataset
    X, y = make_classification(
        n_samples=200, n_features=args.n_qubits, n_informative=args.n_qubits,
        n_redundant=0, random_state=args.seed
    )
    scaler = MinMaxScaler(feature_range=(0, np.pi))
    X = scaler.fit_transform(X).astype(np.float32)
    y = y.astype(np.int64)

    ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
    loader = DataLoader(ds, batch_size=32, shuffle=True)

    circuit = build_circuit(args.n_qubits, args.n_layers, args.ansatz)
    shape = get_param_shape(args.ansatz, args.n_qubits, args.n_layers)

    params = nn.Parameter((torch.rand(shape) * 2 * np.pi) - np.pi)
    optimizer = torch.optim.Adam([params], lr=args.lr)
    criterion = nn.MSELoss()

    t0 = time.time()
    for _ in range(args.epochs):
        for xb, yb in loader:
            optimizer.zero_grad()
            out = torch.stack([circuit(params, xb[i]) for i in range(len(xb))])
            targets = yb.float() * 2.0 - 1.0
            criterion(out, targets).backward()
            optimizer.step()

    # Evaluate
    correct = 0
    with torch.no_grad():
        for xb, yb in loader:
            out = torch.stack([circuit(params, xb[i]) for i in range(len(xb))])
            correct += ((out > 0).long() == yb).sum().item()

    print(f"accuracy={correct/len(ds):.4f}")
    print(f"train_time={time.time()-t0:.1f}")


if __name__ == "__main__":
    main()
