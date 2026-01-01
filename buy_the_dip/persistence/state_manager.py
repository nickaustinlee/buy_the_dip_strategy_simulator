"""
State manager for persisting and loading strategy state.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from ..models import StrategyState
from ..config.models import StrategyConfig

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistence of strategy state with corruption recovery."""
    
    DEFAULT_STATE_FILENAME = "strategy_state.json"
    BACKUP_SUFFIX = ".backup"
    
    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize state manager with specified directory.
        
        Args:
            state_dir: Directory for state files. If None, uses default location.
        """
        if state_dir is None:
            state_dir = os.path.join(os.path.expanduser("~"), ".buy_the_dip", "state")
        
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"StateManager initialized with directory: {self._state_dir}")
    
    def get_state_file_path(self) -> Path:
        """Get the path to the main state file."""
        return self._state_dir / self.DEFAULT_STATE_FILENAME
    
    def get_backup_file_path(self) -> Path:
        """Get the path to the backup state file."""
        return self._state_dir / (self.DEFAULT_STATE_FILENAME + self.BACKUP_SUFFIX)
    
    def save_state(self, state: StrategyState) -> bool:
        """
        Save strategy state to persistent storage.
        
        Args:
            state: The strategy state to save
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        state_file = self.get_state_file_path()
        backup_file = self.get_backup_file_path()
        
        try:
            # Update last_update timestamp
            state.last_update = datetime.now()
            
            # Convert state to JSON-serializable format
            state_dict = self._state_to_dict(state)
            
            # Create backup of existing state file if it exists
            if state_file.exists():
                shutil.copy2(state_file, backup_file)
                logger.debug(f"Created backup of existing state file")
            
            # Write new state to temporary file first
            temp_file = state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, default=str)
            
            # Atomically replace the state file
            temp_file.replace(state_file)
            
            logger.info(f"Successfully saved strategy state to {state_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save strategy state: {e}")
            return False
    
    def load_state(self, default_config: Optional[StrategyConfig] = None) -> StrategyState:
        """
        Load strategy state from persistent storage.
        
        Args:
            default_config: Default configuration to use if no state exists
            
        Returns:
            StrategyState: The loaded state or a new default state
        """
        state_file = self.get_state_file_path()
        backup_file = self.get_backup_file_path()
        
        # Try to load from main state file first
        state = self._load_state_from_file(state_file)
        
        if state is None and backup_file.exists():
            logger.warning("Main state file corrupted or missing, attempting to load from backup")
            state = self._load_state_from_file(backup_file)
            
            if state is not None:
                logger.info("Successfully recovered state from backup file")
                # Save the recovered state as the new main state
                self.save_state(state)
        
        if state is None:
            logger.info("No valid state found, initializing with default state")
            config = default_config or StrategyConfig()
            state = StrategyState(config=config)
            
            # Save the initial state
            self.save_state(state)
        
        return state
    
    def _load_state_from_file(self, file_path: Path) -> Optional[StrategyState]:
        """
        Load state from a specific file.
        
        Args:
            file_path: Path to the state file
            
        Returns:
            StrategyState or None if loading failed
        """
        if not file_path.exists():
            logger.debug(f"State file does not exist: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            state = self._dict_to_state(state_dict)
            logger.info(f"Successfully loaded strategy state from {file_path}")
            return state
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in state file {file_path}: {e}")
            self._handle_corrupted_file(file_path)
            return None
            
        except Exception as e:
            logger.error(f"Failed to load state from {file_path}: {e}")
            self._handle_corrupted_file(file_path)
            return None
    
    def _handle_corrupted_file(self, file_path: Path) -> None:
        """
        Handle a corrupted state file by creating a backup.
        
        Args:
            file_path: Path to the corrupted file
        """
        try:
            corrupted_backup = file_path.with_suffix(f'.corrupted.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.move(file_path, corrupted_backup)
            logger.warning(f"Moved corrupted state file to {corrupted_backup}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted file {file_path}: {e}")
    
    def _state_to_dict(self, state: StrategyState) -> Dict[str, Any]:
        """
        Convert StrategyState to JSON-serializable dictionary.
        
        Args:
            state: The strategy state to convert
            
        Returns:
            Dictionary representation of the state
        """
        # Use Pydantic's model_dump method for serialization
        state_dict = state.model_dump(mode='json')
        
        # Convert datetime objects to ISO format strings
        if 'last_update' in state_dict:
            if isinstance(state_dict['last_update'], datetime):
                state_dict['last_update'] = state_dict['last_update'].isoformat()
        
        # Handle any nested datetime objects in transactions
        for transaction in state_dict.get('all_transactions', []):
            if 'date' in transaction and isinstance(transaction['date'], str):
                # Date is already serialized by Pydantic
                pass
        
        return state_dict
    
    def _dict_to_state(self, state_dict: Dict[str, Any]) -> StrategyState:
        """
        Convert dictionary to StrategyState object.
        
        Args:
            state_dict: Dictionary representation of the state
            
        Returns:
            StrategyState object
        """
        # Pydantic will handle the conversion from dict to model
        return StrategyState.model_validate(state_dict)
    
    def backup_state(self) -> bool:
        """
        Create a manual backup of the current state file.
        
        Returns:
            bool: True if backup was successful, False otherwise
        """
        state_file = self.get_state_file_path()
        
        if not state_file.exists():
            logger.warning("No state file exists to backup")
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self._state_dir / f"strategy_state_backup_{timestamp}.json"
            shutil.copy2(state_file, backup_file)
            
            logger.info(f"Created manual backup: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create manual backup: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 5) -> None:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backup files to keep
        """
        try:
            # Find all backup files
            backup_pattern = "strategy_state_backup_*.json"
            backup_files = list(self._state_dir.glob(backup_pattern))
            
            if len(backup_files) <= keep_count:
                return
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
            
            logger.info(f"Cleaned up {len(backup_files) - keep_count} old backup files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")