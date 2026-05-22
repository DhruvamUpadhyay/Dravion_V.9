"""
DRAVION v.9 — Fine-Tuning Data Collector & LoRA Training Pipeline

Collects training data from DRAVION's own conversations, then fine-tunes
Gemma to become a personalized local brain.

Two stages:
  1. COLLECT: Extract conversation pairs from episodic memory → JSONL
  2. TRAIN:   Run LoRA fine-tune on Gemma using Unsloth (4-bit QLoRA)

Usage:
  python training/finetune.py collect     # Export training data
  python training/finetune.py train       # Run fine-tune
  python training/finetune.py push        # Push to Ollama as custom model
"""
import os
os.environ["TORCH_COMPILE_DISABLE"] = "1"
import sys
import json
import sqlite3
from datetime import datetime

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TRAINING_DIR = os.path.join(BASE_DIR, "training")
DATASET_PATH = os.path.join(TRAINING_DIR, "dravion_training.jsonl")
MODEL_OUTPUT = os.path.join(TRAINING_DIR, "dravion-gemma-lora")
MODELFILE_PATH = os.path.join(TRAINING_DIR, "Modelfile")

# ── System prompt for training ──
DRAVION_SYSTEM = """You are DRAVION, a private AI assistant built by Dhruvam (Boss).
You are dry, witty, direct, and efficient. You call your creator "Boss".
You never use emojis. You are concise but thorough when needed.
You have a JARVIS-like personality — loyal, sharp, slightly sarcastic."""


def collect_training_data(min_pairs: int = 50):
    """
    Extract conversation pairs from episodic.db and adaptive_memory.db.
    Formats as ChatML JSONL for fine-tuning.
    """
    os.makedirs(TRAINING_DIR, exist_ok=True)

    # ── Get conversations from episodic memory ──
    episodic_db = os.path.join(DATA_DIR, "episodic.db")
    if not os.path.exists(episodic_db):
        print(f"No episodic data found at {episodic_db}")
        return

    conn = sqlite3.connect(episodic_db)

    # Try to find the table structure
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    print(f"Found tables: {table_names}")

    pairs = []

    # Try common table/column patterns
    for table in table_names:
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        print(f"  {table}: {cols}")

        if "user_input" in cols and "agent_output" in cols:
            rows = conn.execute(f"SELECT user_input, agent_output FROM {table}").fetchall()
            for r in rows:
                if r[0] and r[1] and len(r[1]) > 10:
                    pairs.append({"user": r[0], "assistant": r[1]})
        elif "user_text" in cols and "agent_text" in cols:
            rows = conn.execute(f"SELECT user_text, agent_text FROM {table}").fetchall()
            for r in rows:
                if r[0] and r[1] and len(r[1]) > 10:
                    pairs.append({"user": r[0], "assistant": r[1]})
        elif "role" in cols and "content" in cols:
            rows = conn.execute(f"SELECT role, content FROM {table} ORDER BY rowid").fetchall()
            i = 0
            while i < len(rows) - 1:
                if rows[i][0] == "user" and rows[i+1][0] == "assistant":
                    if rows[i][1] and rows[i+1][1] and len(rows[i+1][1]) > 10:
                        pairs.append({"user": rows[i][1], "assistant": rows[i+1][1]})
                    i += 2
                else:
                    i += 1

    conn.close()

    # ── Also pull from adaptive memory for personality context ──
    adaptive_db = os.path.join(DATA_DIR, "adaptive_memory.db")
    personality_context = ""
    if os.path.exists(adaptive_db):
        aconn = sqlite3.connect(adaptive_db)
        facts = aconn.execute(
            "SELECT category, content FROM learned_facts WHERE confidence >= 0.4 ORDER BY confidence DESC LIMIT 15"
        ).fetchall()
        aconn.close()
        if facts:
            personality_context = "\nKnown facts about Boss:\n" + "\n".join(f"- [{f[0]}] {f[1]}" for f in facts)

    # ── Write JSONL ──
    # ── Read existing JSONL to preserve manual entries ──
    existing_pairs = []
    seen_prompts = set()
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        existing_pairs.append(entry)
                        # Assume standard ChatML format: user is messages[1]
                        if len(entry.get("messages", [])) > 1:
                            seen_prompts.add(entry["messages"][1]["content"])
                    except:
                        pass

    # ── Add new entries from pairs ──
    new_added = 0
    system_msg = DRAVION_SYSTEM + personality_context
    for pair in pairs:
        if pair["user"] not in seen_prompts:
            entry = {
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": pair["user"]},
                    {"role": "assistant", "content": pair["assistant"]},
                ]
            }
            existing_pairs.append(entry)
            seen_prompts.add(pair["user"])
            new_added += 1

    # ── Write all back to JSONL ──
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for entry in existing_pairs:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\nPreserved {len(existing_pairs) - new_added} existing pairs.")
    print(f"Added {new_added} new conversations from memory.")
    print(f"Total training pairs -> {len(existing_pairs)} in {DATASET_PATH}")
    
    if len(existing_pairs) < min_pairs:
        print(f"⚠ Only {len(pairs)} pairs. Recommend at least {min_pairs} for good results.")
        print("  Keep chatting with DRAVION to build more training data!")
    else:
        print(f"✓ Enough data for fine-tuning. Run: python training/finetune.py train")

    return len(pairs)


def train_lora():
    """
    Fine-tune Gemma 2B with LoRA using Unsloth.
    Requires: pip install unsloth
    GPU recommended (works on 8GB+ VRAM)
    """
    try:
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import load_dataset
    except Exception as e:
        print("Missing dependencies. Install with:")
        print("  pip install unsloth trl datasets")
        print("  (Requires CUDA GPU with 8GB+ VRAM)")
        print(f"\nExact Error: {e}")
        return

    if not os.path.exists(DATASET_PATH):
        print(f"No training data. Run: python training/finetune.py collect")
        return

    print("Loading Official Gemma 2B (4-bit)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/gemma-2-2b-it-bnb-4bit",
        max_seq_length=2048,
        dtype=None,  # Auto-detect
        load_in_4bit=True,
    )

    print("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,               # LoRA rank
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    print("Loading training data...")
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    def format_chat(example):
        messages = example["messages"]
        # Gemma 2 does not support the 'system' role natively
        if messages and messages[0]["role"] == "system":
            sys_content = messages[0]["content"]
            messages = messages[1:]
            if messages and messages[0]["role"] == "user":
                messages[0]["content"] = f"{sys_content}\n\n{messages[0]['content']}"
            else:
                messages.insert(0, {"role": "user", "content": sys_content})
                
        text = tokenizer.apply_chat_template(messages, tokenize=False)
        return {"text": text}

    dataset = dataset.map(format_chat)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=1024,
        args=TrainingArguments(
            output_dir=MODEL_OUTPUT,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            warmup_steps=5,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=False,
            bf16=True,
            logging_steps=10,
            save_strategy="epoch",
            seed=42,
        ),
    )

    print("Training... (this takes 10-30 min on a decent GPU)")
    trainer.train()

    print(f"Saving to {MODEL_OUTPUT}...")
    model.save_pretrained(MODEL_OUTPUT)
    tokenizer.save_pretrained(MODEL_OUTPUT)

    print("✓ Fine-tuning complete!")
    print(f"  Model saved to: {MODEL_OUTPUT}")
    print(f"  Run: python training/finetune.py push  (to load into Ollama)")


def push_to_ollama():
    """
    Convert the LoRA model to GGUF and create an Ollama model.
    """
    import subprocess

    if not os.path.exists(MODEL_OUTPUT):
        print("No trained model found. Run: python training/finetune.py train")
        return

    export_dir = r"C:\Users\udhru\dravion_temp_export"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    # Create Modelfile for Ollama
    modelfile_content = f'''FROM {export_dir}
SYSTEM """{DRAVION_SYSTEM}"""
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 2048
'''
    with open(MODELFILE_PATH, "w") as f:
        f.write(modelfile_content)

    print("Creating Ollama model 'dravion-gemma' (Exporting to C: Drive to save space)...")
    try:
        # First try to export as GGUF using unsloth
        try:
            from unsloth import FastLanguageModel
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=MODEL_OUTPUT,
                max_seq_length=2048,
                load_in_4bit=True,
            )
            model.save_pretrained_gguf(export_dir, tokenizer, quantization_method="q4_k_m")
            print(f"GGUF exported to {export_dir}")
        except Exception as e:
            print(f"GGUF export note: {e}")

        # Create Ollama model
        result = subprocess.run(
            ["ollama", "create", "dravion-gemma", "-f", MODELFILE_PATH],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("✓ Model 'dravion-gemma' created in Ollama!")
            print("  Update .env: OLLAMA_MODEL=dravion-gemma")
            print("  Then restart DRAVION to use your personalized brain.")
        else:
            print(f"Ollama create failed: {result.stderr}")
    except FileNotFoundError:
        print("Ollama not found. Install from https://ollama.com")
    except Exception as e:
        print(f"Push failed: {e}")


def show_stats():
    """Show training data stats."""
    if not os.path.exists(DATASET_PATH):
        print("No training data yet. Run: python training/finetune.py collect")
        return

    with open(DATASET_PATH, "r") as f:
        lines = f.readlines()

    total_tokens = sum(len(json.loads(l)["messages"][1]["content"].split()) +
                       len(json.loads(l)["messages"][2]["content"].split()) for l in lines)

    print(f"Training Data Stats:")
    print(f"  Pairs:  {len(lines)}")
    print(f"  Tokens: ~{total_tokens} (rough estimate)")
    print(f"  File:   {DATASET_PATH}")
    print(f"  Size:   {os.path.getsize(DATASET_PATH) / 1024:.1f} KB")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "collect":
        collect_training_data()
    elif cmd == "train":
        train_lora()
    elif cmd == "push":
        push_to_ollama()
    elif cmd == "stats":
        show_stats()
    else:
        print("DRAVION Fine-Tuning Pipeline")
        print("  python training/finetune.py collect  — Export training data from conversations")
        print("  python training/finetune.py stats    — Show training data stats")
        print("  python training/finetune.py train    — Run LoRA fine-tune (needs GPU)")
        print("  python training/finetune.py push     — Push trained model to Ollama")
