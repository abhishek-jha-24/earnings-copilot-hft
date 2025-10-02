"""
Tests for subscription management and notifications.
"""

import pytest
import asyncio
from datetime import datetime
from services.subscriptions import (
    create_subscription,
    delete_subscription,
    get_user_subscriptions,
    is_user_subscribed
)
from services.notify import sse_manager, publish_doc_event, publish_signal_ready
from apps.api.schemas import DocEvent


class TestSubscriptions:
    """Test subscription management functionality."""
    
    @pytest.mark.asyncio
    async def test_create_subscription(self):
        """Test creating a new subscription."""
        user_id = "test_user_1"
        ticker = "AAPL"
        channels = ["ws", "slack"]
        
        success = await create_subscription(user_id, ticker, channels)
        assert success
        
        # Verify subscription exists
        is_subscribed = await is_user_subscribed(user_id, ticker)
        assert is_subscribed
        
        # Verify subscription details
        subscriptions = await get_user_subscriptions(user_id)
        assert len(subscriptions) >= 1
        
        sub = next((s for s in subscriptions if s["ticker"] == ticker), None)
        assert sub is not None
        assert set(sub["channels"]) == set(channels)
        assert sub["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_update_subscription(self):
        """Test updating an existing subscription."""
        user_id = "test_user_2"
        ticker = "MSFT"
        
        # Create initial subscription
        initial_channels = ["ws"]
        await create_subscription(user_id, ticker, initial_channels)
        
        # Update with different channels
        updated_channels = ["ws", "slack", "email"]
        success = await create_subscription(user_id, ticker, updated_channels)
        assert success
        
        # Verify update
        subscriptions = await get_user_subscriptions(user_id)
        sub = next((s for s in subscriptions if s["ticker"] == ticker), None)
        assert sub is not None
        assert set(sub["channels"]) == set(updated_channels)
    
    @pytest.mark.asyncio
    async def test_delete_subscription(self):
        """Test deleting a subscription."""
        user_id = "test_user_3"
        ticker = "GOOGL"
        channels = ["ws"]
        
        # Create subscription
        await create_subscription(user_id, ticker, channels)
        assert await is_user_subscribed(user_id, ticker)
        
        # Delete subscription
        success = await delete_subscription(user_id, ticker)
        assert success
        
        # Verify deletion
        is_subscribed = await is_user_subscribed(user_id, ticker)
        assert not is_subscribed
    
    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self):
        """Test managing multiple subscriptions for a user."""
        user_id = "test_user_4"
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        channels = ["ws", "slack"]
        
        # Create multiple subscriptions
        for ticker in tickers:
            await create_subscription(user_id, ticker, channels)
        
        # Verify all subscriptions
        subscriptions = await get_user_subscriptions(user_id)
        subscribed_tickers = [s["ticker"] for s in subscriptions]
        
        for ticker in tickers:
            assert ticker in subscribed_tickers
        
        # Delete one subscription
        await delete_subscription(user_id, "MSFT")
        
        # Verify remaining subscriptions
        remaining_subs = await get_user_subscriptions(user_id)
        remaining_tickers = [s["ticker"] for s in remaining_subs]
        
        assert "MSFT" not in remaining_tickers
        assert len(remaining_tickers) == len(tickers) - 1
    
    def test_invalid_channels(self):
        """Test validation of invalid channels."""
        with pytest.raises(ValueError, match="Invalid channels"):
            asyncio.run(create_subscription("user", "AAPL", ["invalid_channel"]))
    
    @pytest.mark.asyncio
    async def test_sse_connection_management(self):
        """Test SSE connection management."""
        user_id = "test_sse_user"
        
        # Add connection
        queue = await sse_manager.add_connection(user_id)
        assert queue is not None
        assert user_id in sse_manager._connections
        assert len(sse_manager._connections[user_id]) == 1
        
        # Add another connection for same user
        queue2 = await sse_manager.add_connection(user_id)
        assert len(sse_manager._connections[user_id]) == 2
        
        # Remove connection
        await sse_manager.remove_connection(user_id, queue)
        assert len(sse_manager._connections[user_id]) == 1
        
        # Remove last connection
        await sse_manager.remove_connection(user_id, queue2)
        assert user_id not in sse_manager._connections
    
    @pytest.mark.asyncio
    async def test_broadcast_to_user(self):
        """Test broadcasting messages to specific user."""
        user_id = "test_broadcast_user"
        
        # Add connection
        queue = await sse_manager.add_connection(user_id)
        
        # Broadcast message
        test_event = "test_event"
        test_data = {"message": "hello", "timestamp": datetime.utcnow().isoformat()}
        
        await sse_manager.broadcast_to_user(user_id, test_event, test_data)
        
        # Check message received
        message = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert message["event"] == test_event
        assert message["data"] == test_data
        assert "timestamp" in message
        
        # Clean up
        await sse_manager.remove_connection(user_id, queue)
    
    @pytest.mark.asyncio
    async def test_document_event_notification(self):
        """Test document ingestion event notification."""
        user_id = "test_doc_user"
        ticker = "AAPL"
        
        # Create subscription
        await create_subscription(user_id, ticker, ["ws"])
        
        # Add SSE connection
        queue = await sse_manager.add_connection(user_id)
        
        # Publish document event
        doc_event = DocEvent(
            event="NEW_DOC_INGESTED",
            doc_id="test_doc_123",
            ticker=ticker,
            period="2025-Q3",
            doc_type="earnings",
            received_at=datetime.utcnow().isoformat()
        )
        
        await publish_doc_event(doc_event)
        
        # Check notification received
        try:
            message = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert message["event"] == "NEW_DOC_INGESTED"
            assert message["data"]["ticker"] == ticker
            assert message["data"]["doc_id"] == "test_doc_123"
        except asyncio.TimeoutError:
            pytest.fail("Did not receive document event notification")
        
        # Clean up
        await sse_manager.remove_connection(user_id, queue)
    
    @pytest.mark.asyncio
    async def test_signal_ready_notification(self):
        """Test signal ready event notification."""
        user_id = "test_signal_user"
        ticker = "MSFT"
        
        # Create subscription
        await create_subscription(user_id, ticker, ["ws"])
        
        # Add SSE connection
        queue = await sse_manager.add_connection(user_id)
        
        # Publish signal ready event
        signal_data = {
            "ticker": ticker,
            "action": "BUY",
            "confidence": 0.85,
            "reasons": ["Strong earnings beat"],
            "citations": [{
                "doc": "msft_10q.pdf",
                "page": 10,
                "table": "income_statement",
                "text": "Revenue exceeded expectations"
            }]
        }
        
        await publish_signal_ready(ticker, signal_data)
        
        # Check notification received
        try:
            message = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert message["event"] == "NEW_SIGNAL_READY"
            assert message["data"]["ticker"] == ticker
            assert message["data"]["action"] == "BUY"
            assert message["data"]["confidence"] == 0.85
        except asyncio.TimeoutError:
            pytest.fail("Did not receive signal ready notification")
        
        # Clean up
        await sse_manager.remove_connection(user_id, queue)
    
    @pytest.mark.asyncio
    async def test_notification_filtering(self):
        """Test that notifications are only sent to subscribed users."""
        subscribed_user = "subscribed_user"
        unsubscribed_user = "unsubscribed_user"
        ticker = "AAPL"
        
        # Only one user subscribes
        await create_subscription(subscribed_user, ticker, ["ws"])
        
        # Both users connect to SSE
        sub_queue = await sse_manager.add_connection(subscribed_user)
        unsub_queue = await sse_manager.add_connection(unsubscribed_user)
        
        # Publish event for the ticker
        doc_event = DocEvent(
            event="NEW_DOC_INGESTED",
            doc_id="test_filtering",
            ticker=ticker,
            period="2025-Q3",
            doc_type="earnings",
            received_at=datetime.utcnow().isoformat()
        )
        
        await publish_doc_event(doc_event)
        
        # Subscribed user should receive notification
        try:
            message = await asyncio.wait_for(sub_queue.get(), timeout=1.0)
            assert message["event"] == "NEW_DOC_INGESTED"
        except asyncio.TimeoutError:
            pytest.fail("Subscribed user did not receive notification")
        
        # Unsubscribed user should NOT receive notification
        try:
            await asyncio.wait_for(unsub_queue.get(), timeout=0.5)
            pytest.fail("Unsubscribed user received notification")
        except asyncio.TimeoutError:
            pass  # Expected - no notification should be received
        
        # Clean up
        await sse_manager.remove_connection(subscribed_user, sub_queue)
        await sse_manager.remove_connection(unsubscribed_user, unsub_queue)
    
    @pytest.mark.asyncio
    async def test_subscription_channel_validation(self):
        """Test subscription channel validation."""
        user_id = "test_channel_user"
        ticker = "AAPL"
        
        # Valid channels
        valid_channels = ["ws", "slack", "email"]
        success = await create_subscription(user_id, ticker, valid_channels)
        assert success
        
        # Invalid channel should raise error
        with pytest.raises(ValueError):
            await create_subscription(user_id, ticker, ["invalid"])
        
        # Empty channels should raise error
        with pytest.raises(ValueError):
            await create_subscription(user_id, ticker, [])
    
    @pytest.mark.asyncio
    async def test_concurrent_subscriptions(self):
        """Test concurrent subscription operations."""
        user_id = "concurrent_user"
        tickers = [f"STOCK{i}" for i in range(10)]
        
        # Create subscriptions concurrently
        tasks = []
        for ticker in tickers:
            task = create_subscription(user_id, ticker, ["ws"])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        assert all(result is True for result in results if not isinstance(result, Exception))
        
        # Verify all subscriptions exist
        subscriptions = await get_user_subscriptions(user_id)
        subscribed_tickers = [s["ticker"] for s in subscriptions]
        
        for ticker in tickers:
            assert ticker in subscribed_tickers


if __name__ == "__main__":
    pytest.main([__file__])
