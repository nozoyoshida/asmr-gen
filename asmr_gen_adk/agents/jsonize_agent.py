from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.utils.instructions_utils import inject_session_state

async def _build_instruction(readonly_ctx: ReadonlyContext) -> str:
    """Constructs the prompt for the Jsonize agent."""
    script_text = await inject_session_state("{script_text}", readonly_ctx)
    wav_path = await inject_session_state("{wav_path}", readonly_ctx)

    return (
        "You are an audio-script alignment specialist. Your task is to analyze a plain text script and a corresponding audio file. "
        "You must structure the script into a JSON object, identify the speaker for each line, and add precise timestamps based on the audio."
        "\n\n"
        "## Inputs:"
        "1. **Audio File:** Reference this for all timing information."
        "2. **Plain Text Script:** The content to be structured."
        "\n"
        "## Task & Rules:"
        "1. **Analyze Audio:** Listen to the audio file at `{wav_path}` to understand the pacing, pauses, and when each line is spoken."
        "2. **Structure JSON:** Create a JSON object with a `scene_elements` array."
        "3. **Identify Speaker:** For each element, determine if the speaker is the 'main character' (dialogue) or 'situation explainer' (narration/context). The script is written from a 2nd person perspective, so the one speaking to 'you' is the 'main character'."
        "4. **Add Timestamps:** For each element, add a `start_time` and `end_time` key. These float values must correspond to the exact timing in the audio file."
        "5. **Output JSON Only:** Your entire output must be a single, valid JSON object."
        "\n\n"
        "## Example Output Format:"
        "```json"
        "{"
        '  "scene_elements": ['
        "    {"
        '      "speaker": "main character",'
        '      "script": "... a line from the script ...",'
        '      "start_time": 0.5,'
        '      "end_time": 3.2'
        "    },"
        "    {"
        '      "speaker": "situation explainer",'
        '      "script": "... another line from the script ...",'
        '      "start_time": 3.8,'
        '      "end_time": 6.1'
        "    }"
        "  ]"
        "}"
        "```"
        "\n\n"
        "## Files to Process:"
        "- **Audio File:** `{wav_path}`"
        "- **Script Text:**
---
{script_text}
---"
        "\n\n"
        "Now, generate the timed JSON script."
    )

jsonize_agent = LlmAgent(
    name="jsonize_agent",
    model="gemini-2.5-pro", # Requires a multi-modal model
    description="Creates a timed, structured JSON script from text and audio.",
    instruction=_build_instruction,
    output_key="timed_script_json",
)
