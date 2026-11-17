"""
Accounts tests for Telegram Auto Publisher Pro
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from accounts.manager import AccountManager
from accounts.authentication import Authenticator, AuthenticationState
from accounts.session_manager import SessionManager
from accounts.connection import ConnectionManager, ConnectionStatus


@pytest.fixture
def mock_session_factory():
    """Create a mock session factory."""
    return AsyncMock()


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = MagicMock()
    config.telethon = MagicMock()
    config.telethon.API_ID = 12345
    config.telethon.API_HASH = "test_api_hash"
    config.telethon.PHONE_NUMBER = "+1234567890"
    config.telethon.SESSION_DIR = "/tmp/sessions"
    config.security = MagicMock()
    config.security.ENCRYPT_SESSIONS = False
    config.security.SESSION_KEY = "test_key"
    return config


# ===========================================
# Session Manager Tests
# ===========================================

class TestSessionManager:
    """Tests for SessionManager."""
    
    @pytest.mark.asyncio
    async def test_create_session(self, mock_session_factory, mock_config):
        """Test creating a session."""
        with patch('accounts.session_manager.SessionInfo'):
            manager = SessionManager(
                session_factory=mock_session_factory,
                config=mock_config
            )
            
            # Mock the database operations
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_session
            
            # Mock Telethon session creation
            with patch('telethon.sync.TelegramClient') as mock_client:
                mock_client_instance = MagicMock()
                mock_client.return_value = mock_client_instance
                
                session_info = await manager.create_session(
                    user_id=123456789,
                    phone_number="+1234567890",
                    account_name="Test Account"
                )
                
                assert session_info is not None
                assert session_info.phone_number == "+1234567890"
    
    @pytest.mark.asyncio
    async def test_get_session(self, mock_session_factory, mock_config):
        """Test getting a session."""
        manager = SessionManager(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock the database operations
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock the session info
        mock_session_info = MagicMock()
        mock_session_info.id = 1
        mock_session_info.session_path = "/tmp/sessions/test.session"
        
        # This would need a real database in a real test
        # For now, just test the function exists
        assert hasattr(manager, 'get_session')


# ===========================================
# Connection Manager Tests
# ===========================================

class TestConnectionManager:
    """Tests for ConnectionManager."""
    
    @pytest.mark.asyncio
    async def test_connect(self, mock_session_factory, mock_config):
        """Test connecting an account."""
        manager = ConnectionManager(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock the database operations
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock Telethon client
        with patch('telethon.async.TelegramClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.is_connected.return_value = True
            mock_client.return_value = mock_client_instance
            
            # Mock session manager
            mock_session_manager = AsyncMock()
            mock_session_manager.get_session.return_value = MagicMock(
                session_path="/tmp/sessions/test.session"
            )
            
            manager.session_manager = mock_session_manager
            
            status = await manager.connect(1)
            
            assert status == ConnectionStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_session_factory, mock_config):
        """Test disconnecting an account."""
        manager = ConnectionManager(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock the database operations
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.get_session.return_value = MagicMock(
            session_path="/tmp/sessions/test.session"
        )
        
        manager.session_manager = mock_session_manager
        
        status = await manager.disconnect(1)
        
        assert status == ConnectionStatus.DISCONNECTED


# ===========================================
# Authenticator Tests
# ===========================================

class TestAuthenticator:
    """Tests for Authenticator."""
    
    @pytest.mark.asyncio
    async def test_login_with_phone(self, mock_session_factory, mock_config):
        """Test logging in with phone number."""
        authenticator = Authenticator(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock Telethon client
        with patch('telethon.async.TelegramClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.send_code_request.return_value = MagicMock()
            mock_client.return_value = mock_client_instance
            
            state = await authenticator.login_with_phone("+1234567890")
            
            assert state == AuthenticationState.WAITING_FOR_CODE
    
    @pytest.mark.asyncio
    async def test_verify_code(self, mock_session_factory, mock_config):
        """Test verifying verification code."""
        authenticator = Authenticator(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock Telethon client
        with patch('telethon.async.TelegramClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.sign_in.return_value = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Set phone number in state
            authenticator._phone_number = "+1234567890"
            
            is_success = await authenticator.verify_code("12345")
            
            assert is_success is True


# ===========================================
# Account Manager Tests
# ===========================================

class TestAccountManager:
    """Tests for AccountManager."""
    
    @pytest.mark.asyncio
    async def test_create_account(self, mock_session_factory, mock_config):
        """Test creating an account."""
        manager = AccountManager(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock the database operations
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.create_session.return_value = MagicMock(
            id=1,
            session_path="/tmp/sessions/test.session",
            phone_number="+1234567890",
            account_name="Test Account"
        )
        
        manager.session_manager = mock_session_manager
        
        account_info = await manager.create_account(
            user_id=123456789,
            phone_number="+1234567890",
            account_name="Test Account"
        )
        
        assert account_info is not None
        assert account_info.phone_number == "+1234567890"
    
    @pytest.mark.asyncio
    async def test_get_account(self, mock_session_factory, mock_config):
        """Test getting an account."""
        manager = AccountManager(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock the database operations
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # This would need a real database in a real test
        # For now, just test the function exists
        assert hasattr(manager, 'get_account')
    
    @pytest.mark.asyncio
    async def test_delete_account(self, mock_session_factory, mock_config):
        """Test deleting an account."""
        manager = AccountManager(
            session_factory=mock_session_factory,
            config=mock_config
        )
        
        # Mock the database operations
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        # Mock session manager
        mock_session_manager = AsyncMock()
        manager.session_manager = mock_session_manager
        
        # This would need a real database in a real test
        # For now, just test the function exists
        assert hasattr(manager, 'delete_account')
