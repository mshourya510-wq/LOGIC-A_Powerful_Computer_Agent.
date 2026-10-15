"""Generate four image variations from a Hugging Face inference endpoint."""
from dotenv import dotenv_values
from pathlib import Path
from random import randint
import argparse
import requests
import os

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "Data"
API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"


def GenerateImages(prompt: str):
    token = dotenv_values(ROOT / ".env").get("HuggingFaceAPIKey")
    if not token:
        raise RuntimeError("Add HuggingFaceAPIKey to .env to enable image generation.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {token}"}
    safe_name = "_".join("".join(c for c in part if c.isalnum() or c in "-_'") for part in prompt.split())[:100]
    paths = []
    for index in range(1, 5):
        response = requests.post(
            API_URL,
            headers=headers,
            json={"inputs": f"{prompt}, highly detailed, high resolution", "parameters": {"seed": randint(0, 1_000_000)}},
            timeout=180,
        )
        response.raise_for_status()
        image_path = DATA_DIR / f"{safe_name}{index}.jpg"
        image_path.write_bytes(response.content)
        paths.append(image_path)
    for image_path in paths:
        os.startfile(str(image_path))
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    GenerateImages(parser.parse_args().prompt)
