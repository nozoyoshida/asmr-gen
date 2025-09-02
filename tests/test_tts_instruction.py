import asyncio
import asyncio
import pathlib
import sys

import pytest

# Ensure project root is on the path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions.session import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from asmr_gen_adk.agents.tts_agent import tts_agent


def _make_ctx(state: dict):
    session_service = InMemorySessionService()
    session = Session(id="s", app_name="app", user_id="user", state=state)
    ctx = InvocationContext(
        session_service=session_service,
        invocation_id="inv",
        agent=tts_agent,
        session=session,
    )
    return ReadonlyContext(ctx)


def test_instruction_injects_script_text():
    ctx = _make_ctx({"script_text": "hello"})
    instruction = asyncio.run(tts_agent.instruction(ctx))
    assert "hello" in instruction


def test_missing_script_text_raises_value_error():
    ctx = _make_ctx({})
    with pytest.raises(ValueError):
        asyncio.run(tts_agent.instruction(ctx))
