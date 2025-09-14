import yaml
from google.adk.agents import LlmAgent

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

script_agent = LlmAgent(
    name="script_agent",
    model=config["models"]["script_agent"],
    description="Writes a short, single-speaker Japanese ASMR script.",
    instruction=(
        "You are an ASMR scriptwriter. Write a script based on the situation given. "
        "Output ONLY the final script as plain text (no markdown / no JSON). "
        "Length: ~20-40 seconds. Tone: gentle, 2nd person, PG-13.\n\n"
    ),
    output_key="script_text", 
)
