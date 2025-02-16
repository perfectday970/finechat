#!C:\Python\Python310\python.exe

from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
import os
import torch
import json
from torch.utils.data import Dataset

# CUDA-Speicher-Konfiguration (optional, wenn du CPU verwenden möchtest)
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

# Dataset laden
dataset_path = "D:/xampp/temp_mpl/deepseek_finetune.jsonl"

def load_dataset(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            data.append(entry)
    return data

# Tokenizer und Modell laden
model_name = "D:/KI-Modelle/DeepSeek-R1-Distill-Qwen-1.5B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Wenn du CPU nutzen willst:
model.to('cpu')

# Dataset vorbereiten
class CustomDataset(Dataset):
    def __init__(self, data, tokenizer):
        self.data = data
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        example = self.data[idx]
        return self.tokenizer(example["input"], text_target=example["output"], padding="max_length", truncation=True, max_length=512)

# Trainingsdaten
data = load_dataset(dataset_path)
train_dataset = CustomDataset(data, tokenizer)

# Trainingsparameter (eval_strategy auf "no" gesetzt, falls du keine Evaluierung benötigst)
training_args = TrainingArguments(
    output_dir="./deepseek_finetuned",
    per_device_train_batch_size=1,
    num_train_epochs=3,
    logging_dir="./logs",
    save_strategy="epoch",
    fp16=True,
    use_cpu=True,  # CPU verwenden
    eval_strategy="no",  # Falls keine Evaluierung notwendig
)

# Trainer initialisieren
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

# Training starten
trainer.train()

# Testen des feingetunten Modells
def generate_response(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)  # Auf CPU verschieben
    output = model.generate(**inputs)
    return tokenizer.decode(output[0], skip_special_tokens=True)

# Beispieltest
print(generate_response("User: Was ist 2+2?"))
