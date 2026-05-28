from __future__ import annotations

import argparse
from typing import Any

import numpy as np
from datasets import load_dataset
from sklearn.metrics import accuracy_score, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune a transformer on a small IMDB subset.")
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--train-samples", type=int, default=2000)
    parser.add_argument("--test-samples", type=int, default=500)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--train-batch-size", type=int, default=8)
    parser.add_argument("--eval-batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="./checkpoints/transformer_demo")
    return parser.parse_args()


def tokenize_batch(batch: dict, tokenizer: AutoTokenizer, max_length: int) -> dict:
    return tokenizer(batch["text"], padding="max_length", truncation=True, max_length=max_length)


def compute_metrics(eval_pred: Any) -> dict[str, float]:
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=1)
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "f1": float(f1_score(labels, predictions)),
    }


def main() -> None:
    args = parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_name, num_labels=2)

    dataset = load_dataset("stanfordnlp/imdb")
    train_subset = dataset["train"].shuffle(seed=args.seed).select(range(args.train_samples))
    test_subset = dataset["test"].shuffle(seed=args.seed).select(range(args.test_samples))

    tokenized_train = train_subset.map(
        lambda batch: tokenize_batch(batch, tokenizer, args.max_length), batched=True
    )
    tokenized_test = test_subset.map(
        lambda batch: tokenize_batch(batch, tokenizer, args.max_length), batched=True
    )

    tokenized_train = tokenized_train.remove_columns(["text"]).rename_column("label", "labels")
    tokenized_test = tokenized_test.remove_columns(["text"]).rename_column("label", "labels")

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        seed=args.seed,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print(
        "evaluation_summary "
        f"model={args.model_name} train_samples={args.train_samples} test_samples={args.test_samples} "
        f"accuracy={metrics.get('eval_accuracy', 0.0):.4f} f1={metrics.get('eval_f1', 0.0):.4f}"
    )


if __name__ == "__main__":
    main()
