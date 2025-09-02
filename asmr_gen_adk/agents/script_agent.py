import os
from datetime import datetime
from google.adk.agents import LlmAgent

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "scripts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_script(text: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"script_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

script_agent = LlmAgent(
    name="script_agent",
    model="gemini-2.5-pro",
    description="Writes a short, single-speaker ASMR script in Japanese given a situation.",
    instruction=(
        "You are an ASMR scriptwriter. Output ONLY the final script as plain text. "
        "No markdown, no JSON."
        "\nAfter producing text, call save_script(text) tool to persist it."
    ),
    tools=[save_script],
)
