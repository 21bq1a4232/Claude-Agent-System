"""Tests for AgentCore."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.agent_core import AgentCore


@pytest.fixture
def config():
    """Create a test configuration."""
    return {
        "agent": {
            "default_model": "test-model",
            "enabled": True,
            "verbose": False,
            "max_steps": 5,
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "temperature": 0.7,
            "top_p": 0.9,
        },
        "loop": {
            "phases": {
                "think": {"enabled": True, "prompt_template": "system_think"},
                "plan": {"enabled": True, "prompt_template": "system_plan"},
                "act": {"enabled": True, "prompt_template": "system_act"},
                "observe": {"enabled": True},
                "reflect": {"enabled": True},
            }
        },
    }


@pytest.fixture
def agent_core(config):
    """Create an AgentCore instance."""
    with patch("agent.agent_core.OllamaClient"), \
         patch("agent.agent_core.ContextManager"), \
         patch("agent.agent_core.ErrorRecoverySystem"), \
         patch("agent.agent_core.ToolExecutor"):
        return AgentCore(config)


@pytest.mark.asyncio
async def test_agent_initialization(config):
    """Test agent initialization."""
    with patch("agent.agent_core.OllamaClient"), \
         patch("agent.agent_core.ContextManager"), \
         patch("agent.agent_core.ErrorRecoverySystem"), \
         patch("agent.agent_core.ToolExecutor"):
        agent = AgentCore(config)
        assert agent.enabled is True
        assert agent.max_steps == 5


@pytest.mark.asyncio
async def test_direct_response(agent_core):
    """Test direct response mode."""
    agent_core.enabled = False
    agent_core.ollama.chat = AsyncMock(
        return_value={
            "message": {"content": "Direct response"}
        }
    )
    agent_core.context.get_messages_for_llm = MagicMock(return_value=[])
    agent_core.context.add_message = MagicMock()

    response = await agent_core.process_request("Test message")

    assert response == "Direct response"
    agent_core.context.add_message.assert_called()


@pytest.mark.asyncio
async def test_toggle_agent_mode(agent_core):
    """Test toggling agent mode."""
    initial_state = agent_core.enabled
    new_state = agent_core.toggle_agent_mode()

    assert new_state != initial_state
    assert agent_core.enabled == new_state


@pytest.mark.asyncio
async def test_switch_model(agent_core):
    """Test switching models."""
    agent_core.ollama.switch_model = MagicMock(return_value=True)

    result = agent_core.switch_model("new-model")

    assert result is True
    agent_core.ollama.switch_model.assert_called_once_with("new-model")


@pytest.mark.asyncio
async def test_list_models(agent_core):
    """Test listing models."""
    agent_core.ollama.list_models = MagicMock(
        return_value=["model1", "model2", "model3"]
    )

    models = agent_core.list_models()

    assert len(models) == 3
    assert "model1" in models


@pytest.mark.asyncio
async def test_think_phase(agent_core):
    """Test think phase."""
    agent_core.ollama.generate = AsyncMock(
        return_value="Analyzing the request..."
    )

    thought = await agent_core._think("Test request", 1)

    assert thought == "Analyzing the request..."
    agent_core.ollama.generate.assert_called_once()


@pytest.mark.asyncio
async def test_plan_phase(agent_core):
    """Test plan phase."""
    agent_core.ollama.generate = AsyncMock(
        return_value="1. Read file\n2. Process data\n3. Write results"
    )

    plan = await agent_core._plan("Test request", 1)

    assert "Read file" in plan
    agent_core.ollama.generate.assert_called_once()


@pytest.mark.asyncio
async def test_observe_success(agent_core):
    """Test observe phase with successful action."""
    action_result = {
        "action": "read_file",
        "result": {"content": "file content"},
        "success": True,
    }

    observation = await agent_core._observe(action_result)

    assert observation["complete"] is True
    assert observation["error"] is None


@pytest.mark.asyncio
async def test_observe_error(agent_core):
    """Test observe phase with error."""
    action_result = {
        "action": "read_file",
        "error": {"message": "File not found"},
        "success": False,
    }
    agent_core.error_recovery.handle_error = AsyncMock(
        return_value={"strategy": "retry"}
    )

    observation = await agent_core._observe(action_result)

    assert observation["complete"] is False
    assert observation["error"] is not None


@pytest.mark.asyncio
async def test_reflect_phase(agent_core):
    """Test reflect phase."""
    observation = {
        "complete": True,
        "error": None,
        "result": {"success": True},
    }

    reflection = await agent_core._reflect(observation)

    assert "success" in reflection.lower()


@pytest.mark.asyncio
async def test_cleanup(agent_core):
    """Test cleanup."""
    agent_core.tool_executor.close = AsyncMock()

    await agent_core.cleanup()

    agent_core.tool_executor.close.assert_called_once()
