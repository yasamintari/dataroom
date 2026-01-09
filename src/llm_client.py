"""
Universal LLM client supporting multiple providers.

Supports:
- Databricks Foundation Models (DBRX, Llama, Mixtral, GPT-OSS)
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)

Model switching requires no code changes - just update config.yaml
"""

import os
from typing import Optional
from src.config import get_config


class LLMClient:
    """Universal LLM client supporting multiple providers."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize LLM client.

        Args:
            model_name: Model name (defaults to config.primary_model)
            provider: Provider (databricks|openai|anthropic|google, defaults to config)
            temperature: Sampling temperature (defaults to config)
            max_tokens: Max tokens (defaults to config)
        """
        config = get_config()

        self.model_name = model_name or config.primary_model
        self.provider = provider or config.model_provider
        self.temperature = temperature if temperature is not None else config.temperature
        self.max_tokens = max_tokens if max_tokens is not None else config.max_tokens

        # Initialize provider-specific client
        self._client = None
        self._setup_provider()

    def _setup_provider(self):
        """Set up provider-specific client."""
        if self.provider == "databricks":
            self._setup_databricks()
        elif self.provider == "openai":
            self._setup_openai()
        elif self.provider == "anthropic":
            self._setup_anthropic()
        elif self.provider == "google":
            self._setup_google()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _setup_databricks(self):
        """Set up Databricks client."""
        try:
            from databricks.sdk import WorkspaceClient
            self._client = WorkspaceClient()
        except Exception as e:
            print(f"Warning: Could not initialize Databricks client: {e}")
            print("Make sure DATABRICKS_HOST and DATABRICKS_TOKEN are set")

    def _setup_openai(self):
        """Set up OpenAI client."""
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self._client = openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _setup_anthropic(self):
        """Set up Anthropic client."""
        try:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def _setup_google(self):
        """Set up Google Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self._client = genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            max_tokens: Max tokens to generate (overrides default)
            temperature: Sampling temperature (overrides default)

        Returns:
            Generated text

        Note:
            This method is provider-agnostic. Switching models requires no code changes.
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            if self.provider == "databricks":
                return self._generate_databricks(prompt, max_tokens, temperature)
            elif self.provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, max_tokens, temperature)
            elif self.provider == "google":
                return self._generate_google(prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            return f"Error generating response: {e}"

    def _generate_databricks(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using Databricks Foundation Models."""
        try:
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

            response = self._client.serving_endpoints.query(
                name=self.model_name,
                messages=[ChatMessage(
                    role=ChatMessageRole.USER,
                    content=prompt
                )],
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content

        except Exception as e:
            # Fallback: Try using MLflow AI Gateway
            try:
                import mlflow.deployments
                client = mlflow.deployments.get_deploy_client("databricks")

                response = client.predict(
                    endpoint=self.model_name,
                    inputs={
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )

                if "choices" in response:
                    return response["choices"][0]["text"]
                elif "predictions" in response:
                    return response["predictions"][0]
                else:
                    return str(response)

            except Exception as mlflow_error:
                raise Exception(f"Databricks generation failed: {e}, MLflow fallback failed: {mlflow_error}")

    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using OpenAI."""
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        return response.choices[0].message.content

    def _generate_anthropic(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using Anthropic Claude."""
        message = self._client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def _generate_google(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate using Google Gemini."""
        model = self._client.GenerativeModel(self.model_name)

        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        return response.text


# Convenience functions
def create_llm_client(model_name: Optional[str] = None, provider: Optional[str] = None) -> LLMClient:
    """
    Create LLM client from config.

    Args:
        model_name: Override model from config
        provider: Override provider from config

    Returns:
        LLMClient instance
    """
    return LLMClient(model_name=model_name, provider=provider)


def get_analysis_llm() -> LLMClient:
    """Get LLM client for investment analysis."""
    config = get_config()
    return LLMClient(model_name=config.analysis_model, provider=config.model_provider)


def get_qa_llm() -> LLMClient:
    """Get LLM client for Q&A."""
    config = get_config()
    return LLMClient(model_name=config.qa_model, provider=config.model_provider)


def get_classification_llm() -> LLMClient:
    """Get LLM client for classification."""
    config = get_config()
    return LLMClient(model_name=config.classification_model, provider=config.model_provider)
