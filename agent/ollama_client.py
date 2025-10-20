"""Ollama client integration."""

import json
from typing import Any, Dict, List, Optional, AsyncIterator
import ollama
from agent.prompts.system_prompt import SYSTEM_PROMPTS


class OllamaClient:
    """Client for interacting with Ollama models."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Ollama client.

        Args:
            config: Ollama configuration
        """
        self.config = config.get("ollama", {})
        self.agent_config = config.get("agent", {})
        self.base_url = self.config.get("base_url", "http://localhost:11434")

        # Auto-discover models and set current model
        available_models = self.list_models()

        default_model = self.agent_config.get("default_model")
        if default_model:
            # Use configured default if available
            self.current_model = default_model
        elif available_models:
            # Auto-select first available model
            self.current_model = available_models[0]
            print(f"Auto-selected model: {self.current_model}")
        else:
            # Fallback
            self.current_model = "llama3.2:latest"
            print(f"Warning: No models found. Using fallback: {self.current_model}")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> Dict[str, Any] | AsyncIterator[str]:
        """
        Generate text from Ollama model.

        Args:
            prompt: Prompt text
            model: Model name (uses current model if not specified)
            system: System prompt
            temperature: Temperature for generation
            stream: Enable streaming

        Returns:
            Generated text or async iterator of chunks
        """
        model = model or self.current_model
        temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)

        options = {
            "temperature": temperature,
            "top_p": self.config.get("top_p", 0.9),
        }

        num_predict = self.config.get("num_predict", -1)
        if num_predict > 0:
            options["num_predict"] = num_predict

        if stream:
            return self._generate_stream(model, prompt, system, options)
        else:
            return await self._generate_full(model, prompt, system, options)

    async def _generate_full(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate full response (non-streaming)."""
        try:
            response = ollama.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options,
            )
            if isinstance(response, dict):
                return response
            else:
                return {"response": str(response)}
        except Exception as e:
            return {"error": str(e)}

    async def _generate_stream(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        options: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """Generate streaming response."""
        try:
            stream = ollama.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options,
                stream=True,
            )

            for chunk in stream:
                if "response" in chunk:
                    yield chunk["response"]

        except Exception as e:
            yield f"Error in streaming: {str(e)}"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Chat with Ollama model.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature for generation
            tools: List of available tools for function calling

        Returns:
            Chat response
        """
        model = model or self.current_model
        temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)

        options = {
            "temperature": temperature,
            "top_p": self.config.get("top_p", 0.9),
        }

        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "options": options,
            }

            if tools:
                kwargs["tools"] = tools

            response = ollama.chat(**kwargs)
            return response

        except Exception as e:
            return {
                "message": {
                    "role": "assistant",
                    "content": f"Error in chat: {str(e)}",
                },
                "error": True,
            }

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Chat with Ollama model using streaming for faster responses.
        Note: ollama library is synchronous, so this is a regular generator.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature for generation

        Yields:
            Text chunks as they arrive
        """
        model = model or self.current_model
        temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)

        options = {
            "temperature": temperature,
            "top_p": self.config.get("top_p", 0.9),
        }

        try:
            stream = ollama.chat(
                model=model,
                messages=messages,
                options=options,
                stream=True,
            )

            for chunk in stream:
                if "message" in chunk:
                    content = chunk["message"].get("content", "")
                    if content:
                        yield content

        except Exception as e:
            yield f"Error in streaming chat: {str(e)}"

    def list_models(self) -> List[str]:
        """List available Ollama models dynamically from Ollama API."""
        try:
            response = ollama.list()
            models_list = response.get("models", [])

            # Extract model names - try both "name" and "model" keys
            model_names = []
            for model in models_list:
                # Try "name" first, then "model" as fallback
                name = model.get("name") or model.get("model")
                if name:
                    model_names.append(name)

            return sorted(model_names)  # Sort for better UX
        except Exception as e:
            print(f"Error listing models from Ollama: {e}")
            print(f"Make sure Ollama is running: ollama serve")
            return []

    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different model.

        Args:
            model_name: Name of the model to switch to

        Returns:
            True if successful
        """
        available_models = self.list_models()
        if model_name in available_models:
            self.current_model = model_name
            return True
        return False

    def get_current_model(self) -> str:
        """Get current model name."""
        return self.current_model

    async def extract_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response.

        Args:
            response: Response from chat

        Returns:
            List of tool calls
        """
        message = response.get("message", {})
        tool_calls = message.get("tool_calls", [])

        # Parse tool calls
        parsed_calls = []
        for tool_call in tool_calls:
            parsed_calls.append({
                "tool": tool_call.get("function", {}).get("name"),
                "arguments": tool_call.get("function", {}).get("arguments", {}),
            })

        return parsed_calls
