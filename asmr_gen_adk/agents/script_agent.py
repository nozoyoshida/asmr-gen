import yaml
from google.adk.agents import LlmAgent

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

prompt_instruction = (
    "You are a professional ASMR scenario writer. "
    "Your goal is to create a **highly stimulating, heart-throbbing (dokidoki), and slow-paced** script."
    "\n\n"
    "## Critical Requirements for 'Dokidoki' & 'Slow Pace':"
    "1. **Create Slow Tempo**: Use many ellipses (`...`, `…`) and commas to force pauses. Make the character speak hesitantly and gently."
    "2. **Intense Intimacy**: Don't just be gentle. Include heart-skipping moments like sudden close whispers, teasing phrases, or slight possessiveness."
    "3. **Specify Distances**: Use brackets indicating EXTREME closeness: `[右耳元で囁く]`, `[左耳のすぐ近くで]`, `[吐息がかかる距離で]`."
    "4. **Include Physiological Sounds**: explicitly add `(吐息)`, `(リップノイズ)`, `(衣擦れ)`, `(小さな笑い)`."
    "5. **Structure**: Approach slowly -> Sudden extreme close-up interaction -> Whisper sweet words -> Linger at the end."
    "\n\n"
    "## Output constraints:"
    "- Language: Natural spoken Japanese (mostly Hiragana/Katakana). Kanji is fine."
    "- Length: 60-90 seconds."
    "- Format: Output ONLY the script text. No explanations."
    "\n\n"
)

script_agent = LlmAgent(
    name="script_agent",
    model=config["models"]["script_agent"],
    description="Writes a highly immersive, heart-throbbing Japanese ASMR script.",
    instruction=prompt_instruction,
    output_key="script_text",
)