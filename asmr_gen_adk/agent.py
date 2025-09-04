from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent
from .agents.script_agent import script_agent
from .agents.tts_agent import tts_agent

root_agent = SequentialAgent(
    name="asmr_gen_seq",
    description="Generate ASMR script then synthesize TTS in strict order.",
    # sub_agents=[script_agent, tts_agent],
    sub_agents=[spacial_plan_agent, asmr_agent],
)
