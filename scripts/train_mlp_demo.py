from __future__ import annotations

import argparse
import random

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import make_moons
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset


class MLPClassifier(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(2, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a reproducible MLP classifier on make_moons.")
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--noise", type=float, default=0.18)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--print-every", type=int, default=25)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def accuracy_from_logits(logits: torch.Tensor, labels: torch.Tensor) -> float:
    predictions = (torch.sigmoid(logits) > 0.5).float()
    return predictions.eq(labels).float().mean().item()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    features, labels = make_moons(n_samples=args.samples, noise=args.noise, random_state=args.seed)
    scaler = StandardScaler()
    features = scaler.fit_transform(features)

    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=args.test_size, random_state=args.seed
    )

    x_train_tensor = torch.tensor(x_train, dtype=torch.float32)
    y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
    x_test_tensor = torch.tensor(x_test, dtype=torch.float32)
    y_test_tensor = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

    train_loader = DataLoader(
        TensorDataset(x_train_tensor, y_train_tensor),
        batch_size=args.batch_size,
        shuffle=True,
    )

    model = MLPClassifier()
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss = 0.0
        seen = 0

        for features_batch, labels_batch in train_loader:
            optimizer.zero_grad()
            logits = model(features_batch)
            loss = criterion(logits, labels_batch)
            loss.backward()
            optimizer.step()

            batch_size = labels_batch.shape[0]
            epoch_loss += loss.item() * batch_size
            seen += batch_size

        with torch.no_grad():
            train_logits = model(x_train_tensor)
            train_acc = accuracy_from_logits(train_logits, y_train_tensor)

        if epoch == 1 or epoch % args.print_every == 0 or epoch == args.epochs:
            avg_loss = epoch_loss / max(seen, 1)
            print(f"epoch={epoch} train_loss={avg_loss:.4f} train_accuracy={train_acc:.4f}")

    model.eval()
    with torch.no_grad():
        test_logits = model(x_test_tensor)
        accuracy = accuracy_from_logits(test_logits, y_test_tensor)

    print(
        "final_metrics "
        f"seed={args.seed} epochs={args.epochs} lr={args.learning_rate} "
        f"batch_size={args.batch_size} test_accuracy={accuracy:.4f}"
    )


if __name__ == "__main__":
    main()
