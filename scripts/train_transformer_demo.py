from __future__ import annotations

from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments


def tokenize_batch(batch: dict, tokenizer: AutoTokenizer) -> dict:
    return tokenizer(batch["text"], padding="max_length", truncation=True, max_length=256)


def main() -> None:
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

    dataset = load_dataset("imdb")
    train_subset = dataset["train"].shuffle(seed=42).select(range(2000))
    test_subset = dataset["test"].shuffle(seed=42).select(range(500))

    tokenized_train = train_subset.map(lambda batch: tokenize_batch(batch, tokenizer), batched=True)
    tokenized_test = test_subset.map(lambda batch: tokenize_batch(batch, tokenizer), batched=True)

    tokenized_train = tokenized_train.remove_columns(["text"]).rename_column("label", "labels")
    tokenized_test = tokenized_test.remove_columns(["text"]).rename_column("label", "labels")

    training_args = TrainingArguments(
        output_dir="./checkpoints/transformer_demo",
        num_train_epochs=1,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_steps=50,
        learning_rate=2e-5,
        weight_decay=0.01,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print(metrics)


if __name__ == "__main__":
    main()
