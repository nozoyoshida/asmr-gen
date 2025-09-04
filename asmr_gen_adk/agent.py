from google.adk.agents import SequentialAgent
from .agents.script_agent import script_agent
from .agents.tts_agent import tts_agent
from .agents.jsonize_agent import jsonize_agent
from .agents.spatial_plan_agent import spatial_plan_agent
from .agents.asmr_agent import asmr_agent

root_agent = SequentialAgent(
    name="asmr_gen_seq",
    description="Generate a full ASMR experience from a situation.",
    sub_agents=[
        script_agent,
        tts_agent,
        jsonize_agent,
        spatial_plan_agent,
        asmr_agent,
    ],
)
