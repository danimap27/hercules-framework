"""
experiment.py — Example: PyTorch image classification sweep.

This is the actual experiment code. It takes CLI arguments,
trains a model, and prints metrics. runner.py calls this with
the parameters for each run.
"""

import argparse
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import torchvision
import torchvision.transforms as T
import torchvision.models as models


def build_model(name: str, num_classes: int = 10) -> nn.Module:
    if name == "resnet18":
        m = models.resnet18(weights=None)
        m.fc = nn.Linear(512, num_classes)
    elif name == "mobilenetv2":
        m = models.mobilenet_v2(weights=None)
        m.classifier[1] = nn.Linear(1280, num_classes)
    else:
        raise ValueError(f"Unknown model: {name}")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="resnet18")
    ap.add_argument("--lr", type=float, default=0.001)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--data-dir", default="./data")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    transform = T.Compose([T.ToTensor(), T.Normalize((0.5,), (0.5,))])
    train_ds = torchvision.datasets.CIFAR10(args.data_dir, train=True, download=True, transform=transform)
    test_ds  = torchvision.datasets.CIFAR10(args.data_dir, train=False, download=True, transform=transform)
    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True, num_workers=2)
    test_loader  = DataLoader(test_ds,  batch_size=256, num_workers=2)

    model = build_model(args.model).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    t0 = time.time()
    for epoch in range(args.epochs):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            criterion(model(xb), yb).backward()
            optimizer.step()

    model.eval()
    correct, total, total_loss = 0, 0, 0.0
    with torch.no_grad():
        for xb, yb in test_loader:
            xb, yb = xb.to(device), yb.to(device)
            out = model(xb)
            total_loss += criterion(out, yb).item() * len(yb)
            correct += (out.argmax(1) == yb).sum().item()
            total += len(yb)

    print(f"accuracy={correct/total:.4f}")
    print(f"loss={total_loss/total:.4f}")
    print(f"train_time={time.time()-t0:.1f}")


if __name__ == "__main__":
    main()
