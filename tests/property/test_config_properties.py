"""
Property-based tests for configuration loading and validation.
"""

import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any

import pytest
from hypothesis import given, strategies as st, assume
from pydantic import ValidationError

from buy_the_dip.config.config_manager import ConfigurationManager
from buy_the_dip.config.models import StrategyConfig


class TestConfigurationProperties:
    """Property-based tests for configuration management."""

    @given(
        ticker=st.text(min_size=1, max_size=10).filter(lambda x: x.strip() and x.isalnum()),
        rolling_window_days=st.integers(min_value=1, max_value=365),
        percentage_trigger=st.floats(min_value=0.01, max_value=1.0, exclude_min=True),
        monthly_dca_amount=st.floats(min_value=0.01, max_value=100000.0, exclude_min=True),
        data_cache_days=st.integers(min_value=1, max_value=365)
    )
    def test_configuration_loading_and_validation_consistency(
        self,
        ticker: str,
        rolling_window_days: int,
        percentage_trigger: float,
        monthly_dca_amount: float,
        data_cache_days: int
    ):
        """
        Feature: buy-the-dip-strategy, Property 1: Configuration Loading and Validation Consistency
        
        For any YAML configuration file with valid structure, all required fields 
        (ticker, rolling_window_days, percentage_trigger, monthly_dca_amount, data_cache_days) 
        should be loaded correctly, and validation should accept values within defined ranges 
        while rejecting values outside those ranges.
        
        Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9
        """
        # Create valid configuration data
        config_data = {
            "ticker": ticker,
            "rolling_window_days": rolling_window_days,
            "percentage_trigger": percentage_trigger,
            "monthly_dca_amount": monthly_dca_amount,
            "data_cache_days": data_cache_days
        }
        
        # Test direct validation
        config_manager = ConfigurationManager()
        validated_config = config_manager.validate_config(config_data)
        
        # Verify all fields are loaded correctly
        assert validated_config.ticker == ticker
        assert validated_config.rolling_window_days == rolling_window_days
        assert validated_config.percentage_trigger == percentage_trigger
        assert validated_config.monthly_dca_amount == monthly_dca_amount
        assert validated_config.data_cache_days == data_cache_days
        
        # Test YAML file loading
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file.flush()
            
            # Load from file
            loaded_config = config_manager.load_config(temp_file.name)
            
            # Verify file loading produces same result as direct validation
            assert loaded_config.ticker == validated_config.ticker
            assert loaded_config.rolling_window_days == validated_config.rolling_window_days
            assert loaded_config.percentage_trigger == validated_config.percentage_trigger
            assert loaded_config.monthly_dca_amount == validated_config.monthly_dca_amount
            assert loaded_config.data_cache_days == validated_config.data_cache_days
            
            # Clean up
            Path(temp_file.name).unlink()

    @given(
        rolling_window_days=st.integers().filter(lambda x: x <= 0 or x > 365),
        percentage_trigger=st.floats().filter(lambda x: x <= 0.0 or x > 1.0),
        monthly_dca_amount=st.floats().filter(lambda x: x <= 0.0)
    )
    def test_configuration_validation_rejects_invalid_ranges(
        self,
        rolling_window_days: int,
        percentage_trigger: float,
        monthly_dca_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 1: Configuration Loading and Validation Consistency
        
        For any configuration with values outside defined ranges, validation should reject 
        the configuration and use defaults with warnings.
        
        Validates: Requirements 1.6, 1.7, 1.8, 1.9
        """
        # Skip NaN and infinite values as they cause different behavior
        assume(not (isinstance(percentage_trigger, float) and 
                   (percentage_trigger != percentage_trigger or 
                    percentage_trigger == float('inf') or 
                    percentage_trigger == float('-inf'))))
        assume(not (isinstance(monthly_dca_amount, float) and 
                   (monthly_dca_amount != monthly_dca_amount or 
                    monthly_dca_amount == float('inf') or 
                    monthly_dca_amount == float('-inf'))))
        
        config_manager = ConfigurationManager()
        
        # Test invalid rolling_window_days
        invalid_config = {
            "ticker": "SPY",
            "rolling_window_days": rolling_window_days,
            "percentage_trigger": 0.90,
            "monthly_dca_amount": 2000.0,
            "data_cache_days": 30
        }
        
        # Should return default config when validation fails
        result_config = config_manager.validate_config(invalid_config)
        assert isinstance(result_config, StrategyConfig)
        # Should use defaults when validation fails
        assert result_config.rolling_window_days == 90  # default value
        
        # Test invalid percentage_trigger
        invalid_config = {
            "ticker": "SPY",
            "rolling_window_days": 90,
            "percentage_trigger": percentage_trigger,
            "monthly_dca_amount": 2000.0,
            "data_cache_days": 30
        }
        
        result_config = config_manager.validate_config(invalid_config)
        assert isinstance(result_config, StrategyConfig)
        assert result_config.percentage_trigger == 0.90  # default value
        
        # Test invalid monthly_dca_amount
        invalid_config = {
            "ticker": "SPY",
            "rolling_window_days": 90,
            "percentage_trigger": 0.90,
            "monthly_dca_amount": monthly_dca_amount,
            "data_cache_days": 30
        }
        
        result_config = config_manager.validate_config(invalid_config)
        assert isinstance(result_config, StrategyConfig)
        assert result_config.monthly_dca_amount == 2000.0  # default value

    @given(
        config_dict=st.dictionaries(
            keys=st.sampled_from(["ticker", "rolling_window_days", "percentage_trigger", 
                                 "monthly_dca_amount", "data_cache_days"]),
            values=st.one_of(
                st.text(min_size=1, max_size=10).filter(lambda x: x.strip()),
                st.integers(min_value=1, max_value=365),
                st.floats(min_value=0.01, max_value=1.0, exclude_min=True),
                st.floats(min_value=0.01, max_value=100000.0, exclude_min=True)
            ),
            min_size=0,
            max_size=5
        )
    )
    def test_configuration_handles_missing_fields_with_defaults(self, config_dict: Dict[str, Any]):
        """
        Feature: buy-the-dip-strategy, Property 1: Configuration Loading and Validation Consistency
        
        For any configuration dictionary with missing required fields, the system should 
        use default values and produce a valid configuration.
        
        Validates: Requirements 1.6
        """
        config_manager = ConfigurationManager()
        result_config = config_manager.validate_config(config_dict)
        
        # Should always return a valid StrategyConfig
        assert isinstance(result_config, StrategyConfig)
        
        # Should have all required fields with either provided or default values
        assert hasattr(result_config, 'ticker')
        assert hasattr(result_config, 'rolling_window_days')
        assert hasattr(result_config, 'percentage_trigger')
        assert hasattr(result_config, 'monthly_dca_amount')
        assert hasattr(result_config, 'data_cache_days')
        
        # Values should be within valid ranges
        assert isinstance(result_config.ticker, str)
        assert 1 <= result_config.rolling_window_days <= 365
        assert 0.0 < result_config.percentage_trigger <= 1.0
        assert result_config.monthly_dca_amount > 0.0
        assert result_config.data_cache_days >= 1

    def test_configuration_handles_nonexistent_file_gracefully(self):
        """
        Feature: buy-the-dip-strategy, Property 1: Configuration Loading and Validation Consistency
        
        For any nonexistent configuration file path, the system should handle the error 
        gracefully and return a default configuration.
        
        Validates: Requirements 1.6
        """
        config_manager = ConfigurationManager()
        
        # Try to load from a nonexistent file
        nonexistent_path = "/path/that/does/not/exist/config.yaml"
        result_config = config_manager.load_config(nonexistent_path)
        
        # Should return default configuration
        assert isinstance(result_config, StrategyConfig)
        assert result_config.ticker == "SPY"
        assert result_config.rolling_window_days == 90
        assert result_config.percentage_trigger == 0.90
        assert result_config.monthly_dca_amount == 2000.0
        assert result_config.data_cache_days == 30

    def test_configuration_handles_invalid_yaml_gracefully(self):
        """
        Feature: buy-the-dip-strategy, Property 1: Configuration Loading and Validation Consistency
        
        For any invalid YAML file, the system should handle the error gracefully 
        and return a default configuration.
        
        Validates: Requirements 1.6
        """
        config_manager = ConfigurationManager()
        
        # Create a file with invalid YAML content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file.write("invalid: yaml: content: [unclosed bracket")
            temp_file.flush()
            
            # Try to load the invalid YAML
            result_config = config_manager.load_config(temp_file.name)
            
            # Should return default configuration
            assert isinstance(result_config, StrategyConfig)
            assert result_config.ticker == "SPY"
            assert result_config.rolling_window_days == 90
            assert result_config.percentage_trigger == 0.90
            assert result_config.monthly_dca_amount == 2000.0
            assert result_config.data_cache_days == 30
            
            # Clean up
            Path(temp_file.name).unlink()