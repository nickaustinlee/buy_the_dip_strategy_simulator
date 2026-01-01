"""
Unit tests for state management and persistence functionality.
"""

import json
import pytest
import tempfile
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from buy_the_dip.persistence import StateManager
from buy_the_dip.models import StrategyState, Transaction
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.dca_controller.models import DCASession, DCAState


class TestStateManager:
    """Test StateManager class."""
    
    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0
        )
    
    @pytest.fixture
    def sample_state(self, config):
        """Create a sample strategy state for testing."""
        # Create sample DCA session
        session = DCASession(
            session_id="test-session-1",
            trigger_price=450.0,
            start_date=date.today(),
            state=DCAState.ACTIVE,
            total_invested=2000.0,
            shares_purchased=4.44
        )
        
        # Create sample transaction
        transaction = Transaction(
            transaction_id="test-tx-1",
            session_id="test-session-1",
            date=date.today(),
            price=450.0,
            shares=4.44,
            amount=2000.0
        )
        
        return StrategyState(
            config=config,
            active_sessions=[session],
            completed_sessions=[],
            all_transactions=[transaction],
            last_update=datetime.now(),
            price_cache={"SPY": [{"date": "2023-01-01", "close": 450.0}]}
        )
    
    def test_state_manager_initialization_default_dir(self):
        """Test StateManager initialization with default directory."""
        manager = StateManager()
        expected_path = Path.home() / ".buy_the_dip" / "state"
        assert manager._state_dir == expected_path
        assert manager._state_dir.exists()
    
    def test_state_manager_initialization_custom_dir(self, temp_state_dir):
        """Test StateManager initialization with custom directory."""
        manager = StateManager(state_dir=temp_state_dir)
        assert manager._state_dir == Path(temp_state_dir)
        assert manager._state_dir.exists()
    
    def test_get_file_paths(self, temp_state_dir):
        """Test file path generation methods."""
        manager = StateManager(state_dir=temp_state_dir)
        
        state_file = manager.get_state_file_path()
        backup_file = manager.get_backup_file_path()
        
        assert state_file == Path(temp_state_dir) / "strategy_state.json"
        assert backup_file == Path(temp_state_dir) / "strategy_state.json.backup"
    
    def test_save_state_success(self, temp_state_dir, sample_state):
        """Test successful state saving."""
        manager = StateManager(state_dir=temp_state_dir)
        
        result = manager.save_state(sample_state)
        
        assert result is True
        
        # Verify file was created
        state_file = manager.get_state_file_path()
        assert state_file.exists()
        
        # Verify content is valid JSON
        with open(state_file, 'r') as f:
            data = json.load(f)
        
        assert data['config']['ticker'] == 'SPY'
        assert len(data['active_sessions']) == 1
        assert len(data['all_transactions']) == 1
    
    def test_save_state_creates_backup(self, temp_state_dir, sample_state):
        """Test that saving state creates backup of existing file."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Save initial state
        manager.save_state(sample_state)
        
        # Modify state and save again
        sample_state.config.ticker = "AAPL"
        manager.save_state(sample_state)
        
        # Verify backup was created
        backup_file = manager.get_backup_file_path()
        assert backup_file.exists()
        
        # Verify backup contains original data
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        assert backup_data['config']['ticker'] == 'SPY'
        
        # Verify main file contains new data
        state_file = manager.get_state_file_path()
        with open(state_file, 'r') as f:
            current_data = json.load(f)
        assert current_data['config']['ticker'] == 'AAPL'
    
    def test_save_state_updates_timestamp(self, temp_state_dir, sample_state):
        """Test that saving state updates the last_update timestamp."""
        manager = StateManager(state_dir=temp_state_dir)
        
        original_timestamp = sample_state.last_update
        
        # Save state
        manager.save_state(sample_state)
        
        # Verify timestamp was updated
        assert sample_state.last_update > original_timestamp
    
    def test_save_state_atomic_write(self, temp_state_dir, sample_state):
        """Test that state saving uses atomic write (temp file then replace)."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Mock file operations to simulate failure during write
        original_open = open
        
        def mock_open(*args, **kwargs):
            if args[0].endswith('.tmp'):
                # Simulate failure when writing temp file
                raise IOError("Disk full")
            return original_open(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open):
            result = manager.save_state(sample_state)
        
        # Should return False on failure
        assert result is False
        
        # Main state file should not exist (atomic write failed)
        state_file = manager.get_state_file_path()
        assert not state_file.exists()
    
    def test_load_state_success(self, temp_state_dir, sample_state):
        """Test successful state loading."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Save state first
        manager.save_state(sample_state)
        
        # Load state
        loaded_state = manager.load_state()
        
        assert isinstance(loaded_state, StrategyState)
        assert loaded_state.config.ticker == sample_state.config.ticker
        assert len(loaded_state.active_sessions) == 1
        assert len(loaded_state.all_transactions) == 1
        assert loaded_state.active_sessions[0].session_id == "test-session-1"
    
    def test_load_state_no_file_creates_default(self, temp_state_dir, config):
        """Test loading state when no file exists creates default state."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Load state when no file exists
        loaded_state = manager.load_state(default_config=config)
        
        assert isinstance(loaded_state, StrategyState)
        assert loaded_state.config.ticker == config.ticker
        assert len(loaded_state.active_sessions) == 0
        assert len(loaded_state.all_transactions) == 0
        
        # Verify default state was saved
        state_file = manager.get_state_file_path()
        assert state_file.exists()
    
    def test_load_state_corrupted_file_uses_backup(self, temp_state_dir, sample_state):
        """Test loading state from backup when main file is corrupted."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Save valid state (creates backup)
        manager.save_state(sample_state)
        sample_state.config.ticker = "AAPL"
        manager.save_state(sample_state)
        
        # Corrupt main state file
        state_file = manager.get_state_file_path()
        with open(state_file, 'w') as f:
            f.write("invalid json content")
        
        # Load state should recover from backup
        loaded_state = manager.load_state()
        
        assert isinstance(loaded_state, StrategyState)
        assert loaded_state.config.ticker == "SPY"  # From backup, not corrupted file
        
        # Verify corrupted file was moved
        corrupted_files = list(manager._state_dir.glob("*.corrupted.*"))
        assert len(corrupted_files) == 1
    
    def test_load_state_both_files_corrupted(self, temp_state_dir, config):
        """Test loading state when both main and backup files are corrupted."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Create corrupted main file
        state_file = manager.get_state_file_path()
        with open(state_file, 'w') as f:
            f.write("invalid json")
        
        # Create corrupted backup file
        backup_file = manager.get_backup_file_path()
        with open(backup_file, 'w') as f:
            f.write("also invalid json")
        
        # Load state should create default
        loaded_state = manager.load_state(default_config=config)
        
        assert isinstance(loaded_state, StrategyState)
        assert loaded_state.config.ticker == config.ticker
        assert len(loaded_state.active_sessions) == 0
    
    def test_state_serialization_round_trip(self, temp_state_dir, sample_state):
        """Test that state can be serialized and deserialized without data loss."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Save and load state
        manager.save_state(sample_state)
        loaded_state = manager.load_state()
        
        # Verify all data is preserved
        assert loaded_state.config.ticker == sample_state.config.ticker
        assert loaded_state.config.rolling_window_days == sample_state.config.rolling_window_days
        assert loaded_state.config.percentage_trigger == sample_state.config.percentage_trigger
        assert loaded_state.config.monthly_dca_amount == sample_state.config.monthly_dca_amount
        
        # Verify sessions
        assert len(loaded_state.active_sessions) == len(sample_state.active_sessions)
        loaded_session = loaded_state.active_sessions[0]
        original_session = sample_state.active_sessions[0]
        assert loaded_session.session_id == original_session.session_id
        assert loaded_session.trigger_price == original_session.trigger_price
        assert loaded_session.state == original_session.state
        
        # Verify transactions
        assert len(loaded_state.all_transactions) == len(sample_state.all_transactions)
        loaded_tx = loaded_state.all_transactions[0]
        original_tx = sample_state.all_transactions[0]
        assert loaded_tx.transaction_id == original_tx.transaction_id
        assert loaded_tx.amount == original_tx.amount
        assert loaded_tx.price == original_tx.price
    
    def test_backup_state_success(self, temp_state_dir, sample_state):
        """Test manual backup creation."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Save state first
        manager.save_state(sample_state)
        
        # Create manual backup
        result = manager.backup_state()
        
        assert result is True
        
        # Verify backup file was created
        backup_files = list(manager._state_dir.glob("strategy_state_backup_*.json"))
        assert len(backup_files) == 1
        
        # Verify backup contains correct data
        with open(backup_files[0], 'r') as f:
            backup_data = json.load(f)
        assert backup_data['config']['ticker'] == 'SPY'
    
    def test_backup_state_no_file(self, temp_state_dir):
        """Test manual backup when no state file exists."""
        manager = StateManager(state_dir=temp_state_dir)
        
        result = manager.backup_state()
        
        assert result is False
    
    def test_cleanup_old_backups(self, temp_state_dir, sample_state):
        """Test cleanup of old backup files."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Create multiple backup files
        for i in range(7):
            backup_file = manager._state_dir / f"strategy_state_backup_2023010{i}_120000.json"
            with open(backup_file, 'w') as f:
                json.dump({"test": i}, f)
        
        # Cleanup keeping only 3 files
        manager.cleanup_old_backups(keep_count=3)
        
        # Verify only 3 files remain
        backup_files = list(manager._state_dir.glob("strategy_state_backup_*.json"))
        assert len(backup_files) == 3
    
    def test_handle_corrupted_file(self, temp_state_dir):
        """Test corrupted file handling."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Create a corrupted file
        corrupted_file = manager._state_dir / "test_corrupted.json"
        with open(corrupted_file, 'w') as f:
            f.write("invalid json")
        
        # Handle corruption
        manager._handle_corrupted_file(corrupted_file)
        
        # Verify original file was moved
        assert not corrupted_file.exists()
        
        # Verify corrupted backup was created
        corrupted_backups = list(manager._state_dir.glob("test_corrupted.corrupted.*"))
        assert len(corrupted_backups) == 1
    
    def test_state_to_dict_conversion(self, temp_state_dir, sample_state):
        """Test conversion of StrategyState to dictionary."""
        manager = StateManager(state_dir=temp_state_dir)
        
        state_dict = manager._state_to_dict(sample_state)
        
        assert isinstance(state_dict, dict)
        assert 'config' in state_dict
        assert 'active_sessions' in state_dict
        assert 'all_transactions' in state_dict
        assert 'last_update' in state_dict
        
        # Verify datetime serialization
        assert isinstance(state_dict['last_update'], str)
    
    def test_dict_to_state_conversion(self, temp_state_dir, sample_state):
        """Test conversion of dictionary to StrategyState."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Convert to dict and back
        state_dict = manager._state_to_dict(sample_state)
        restored_state = manager._dict_to_state(state_dict)
        
        assert isinstance(restored_state, StrategyState)
        assert restored_state.config.ticker == sample_state.config.ticker
        assert len(restored_state.active_sessions) == len(sample_state.active_sessions)
        assert len(restored_state.all_transactions) == len(sample_state.all_transactions)
    
    def test_state_manager_with_complex_state(self, temp_state_dir, config):
        """Test state manager with complex state containing multiple sessions and transactions."""
        manager = StateManager(state_dir=temp_state_dir)
        
        # Create complex state with multiple sessions and transactions
        sessions = []
        transactions = []
        
        for i in range(3):
            session = DCASession(
                session_id=f"session-{i}",
                trigger_price=400.0 + i * 10,
                start_date=date.today() - timedelta(days=i * 30),
                state=DCAState.ACTIVE if i < 2 else DCAState.COMPLETED,
                total_invested=2000.0 * (i + 1),
                shares_purchased=5.0 * (i + 1)
            )
            sessions.append(session)
            
            # Add transactions for each session
            for j in range(2):
                transaction = Transaction(
                    transaction_id=f"tx-{i}-{j}",
                    session_id=session.session_id,
                    date=date.today() - timedelta(days=i * 30 + j * 15),
                    price=400.0 + i * 10 + j * 5,
                    shares=2.5,
                    amount=1000.0
                )
                transactions.append(transaction)
        
        complex_state = StrategyState(
            config=config,
            active_sessions=sessions[:2],
            completed_sessions=sessions[2:],
            all_transactions=transactions,
            price_cache={
                "SPY": [
                    {"date": "2023-01-01", "close": 400.0},
                    {"date": "2023-01-02", "close": 405.0}
                ]
            }
        )
        
        # Save and load complex state
        result = manager.save_state(complex_state)
        assert result is True
        
        loaded_state = manager.load_state()
        
        # Verify all data is preserved
        assert len(loaded_state.active_sessions) == 2
        assert len(loaded_state.completed_sessions) == 1
        assert len(loaded_state.all_transactions) == 6
        assert len(loaded_state.price_cache["SPY"]) == 2
        
        # Verify session details
        for i, session in enumerate(loaded_state.active_sessions):
            assert session.session_id == f"session-{i}"
            assert session.trigger_price == 400.0 + i * 10
        
        # Verify transaction details
        assert len([tx for tx in loaded_state.all_transactions if tx.session_id == "session-0"]) == 2
        assert len([tx for tx in loaded_state.all_transactions if tx.session_id == "session-1"]) == 2
        assert len([tx for tx in loaded_state.all_transactions if tx.session_id == "session-2"]) == 2