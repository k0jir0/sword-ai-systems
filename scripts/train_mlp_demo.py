from __future__ import annotations

import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import make_moons
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


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


def main() -> None:
    features, labels = make_moons(n_samples=2000, noise=0.18, random_state=42)
    scaler = StandardScaler()
    features = scaler.fit_transform(features)

    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )

    x_train_tensor = torch.tensor(x_train, dtype=torch.float32)
    y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
    x_test_tensor = torch.tensor(x_test, dtype=torch.float32)
    y_test_tensor = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

    model = MLPClassifier()
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    for epoch in range(1, 401):
        model.train()
        optimizer.zero_grad()
        logits = model(x_train_tensor)
        loss = criterion(logits, y_train_tensor)
        loss.backward()
        optimizer.step()

        if epoch % 100 == 0:
            print(f"epoch={epoch} loss={loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        test_logits = model(x_test_tensor)
        predictions = (torch.sigmoid(test_logits) > 0.5).float()
        accuracy = (predictions.eq(y_test_tensor)).float().mean().item()

    print(f"test_accuracy={accuracy:.4f}")


if __name__ == "__main__":
    main()
