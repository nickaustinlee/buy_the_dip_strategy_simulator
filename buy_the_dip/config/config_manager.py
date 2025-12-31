"""
Configuration manager for loading and validating YAML configuration files.
"""

import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .models import StrategyConfig


logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Manages loading and validation of YAML configuration files."""
    
    DEFAULT_CONFIG_FILENAME = "config.yaml"
    
    def load_config(self, config_path: Optional[str] = None) -> StrategyConfig:
        """
        Load and validate configuration from YAML file.
        
        Args:
            config_path: Path to configuration file. If None, uses default.
            
        Returns:
            Validated StrategyConfig instance.
        """
        if config_path is None:
            config_path = self.get_default_config_path()
            
        try:
            config_dict = self._load_yaml_file(config_path)
            return self.validate_config(config_dict)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            logger.info("Using default configuration")
            return StrategyConfig()
    
    def validate_config(self, config: Dict[str, Any]) -> StrategyConfig:
        """
        Validate configuration dictionary using Pydantic.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Validated StrategyConfig instance.
        """
        try:
            return StrategyConfig(**config)
        except Exception as e:
            logger.warning(f"Configuration validation failed: {e}")
            logger.info("Using default configuration")
            return StrategyConfig()
    
    def get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        return self.DEFAULT_CONFIG_FILENAME
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Load YAML file and return as dictionary."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
            
        with open(path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file) or {}