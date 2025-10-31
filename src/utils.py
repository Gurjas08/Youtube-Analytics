# src/utils.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_config():
    cfg_path = ROOT / "config.json" #name of your config file
    if not cfg_path.exists():
        raise FileNotFoundError("config.json not found. Create it from config.example.json and add your API key.")
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)
