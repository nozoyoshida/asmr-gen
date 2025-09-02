from google.adk.agents import LlmAgent

script_agent = LlmAgent(
    name="script_agent",
    model="gemini-2.5-pro",
    description="Writes a short, single-speaker Japanese ASMR script.",
    instruction=(
        "You are an ASMR scriptwriter. Output ONLY the final script as plain text "
        "(no markdown / no JSON). Length ~20–40 seconds, PG-13, gentle tone, 2nd person."
        " If user gave a situation, follow it closely."
    ),
    output_key="script_text", 
)
