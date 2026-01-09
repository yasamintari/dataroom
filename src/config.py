"""
Configuration management for the data room.

Loads settings from config.yaml and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml (default: config/config.yaml)
        """
        if config_path is None:
            # Find config.yaml relative to this file
            base_path = Path(__file__).parent.parent
            config_path = base_path / "config" / "config.yaml"

        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

        # Load environment variables
        self._load_env()

    def _load_env(self):
        """Load environment variables from .env if available."""
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Path to config value (e.g., "models.primary_model")
            default: Default value if not found

        Returns:
            Configuration value

        Example:
            config.get("models.primary_model")  # Returns "databricks-gpt-oss-20b"
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    @property
    def databricks_catalog(self) -> str:
        """Get Databricks catalog name."""
        return self.get("databricks.catalog", "main")

    @property
    def databricks_schema(self) -> str:
        """Get Databricks schema name."""
        return self.get("databricks.schema", "dataroom")

    @property
    def primary_model(self) -> str:
        """Get primary LLM model name."""
        return self.get("models.primary_model", "databricks-gpt-oss-20b")

    @property
    def model_provider(self) -> str:
        """Get model provider (databricks, openai, anthropic, google)."""
        return self.get("models.provider", "databricks")

    @property
    def analysis_model(self) -> str:
        """Get analysis model (falls back to primary_model if not set)."""
        model = self.get("models.analysis_model")
        return model if model else self.primary_model

    @property
    def qa_model(self) -> str:
        """Get Q&A model (falls back to primary_model if not set)."""
        model = self.get("models.qa_model")
        return model if model else self.primary_model

    @property
    def classification_model(self) -> str:
        """Get classification model (falls back to primary_model if not set)."""
        model = self.get("models.classification_model")
        return model if model else self.primary_model

    @property
    def temperature(self) -> float:
        """Get model temperature."""
        return self.get("models.temperature", 0.1)

    @property
    def max_tokens(self) -> int:
        """Get max tokens."""
        return self.get("models.max_tokens", 500)

    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        return self.get("models.embedding_model", "BAAI/bge-large-en-v1.5")

    @property
    def chunk_size(self) -> int:
        """Get chunk size for document processing."""
        return self.get("vector_search.chunk_size", 800)

    @property
    def chunk_overlap(self) -> int:
        """Get chunk overlap."""
        return self.get("vector_search.chunk_overlap", 200)


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global config instance.

    Args:
        config_path: Optional path to config file

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
