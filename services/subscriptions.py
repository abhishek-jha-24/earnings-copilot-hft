"""
Subscription management service.
Thin layer over storage for subscription CRUD operations.
"""

from typing import List, Dict, Any
from services.storage import (
    add_subscription as storage_add_subscription,
    remove_subscription as storage_remove_subscription,
    list_subscriptions as storage_list_subscriptions,
    subscribers_for_ticker as storage_subscribers_for_ticker
)


async def create_subscription(user_id: str, ticker: str, channels: List[str]) -> bool:
    """Create or update a subscription."""
    # Validate channels
    valid_channels = {"ws", "slack", "email"}
    if not all(channel in valid_channels for channel in channels):
        raise ValueError(f"Invalid channels. Must be subset of: {valid_channels}")
    
    return await storage_add_subscription(user_id, ticker, channels)


async def delete_subscription(user_id: str, ticker: str) -> bool:
    """Delete a subscription."""
    return await storage_remove_subscription(user_id, ticker)


async def get_user_subscriptions(user_id: str) -> List[Dict[str, Any]]:
    """Get all subscriptions for a user."""
    return await storage_list_subscriptions(user_id)


async def get_ticker_subscribers(ticker: str) -> List[Dict[str, Any]]:
    """Get all subscribers for a ticker."""
    return await storage_subscribers_for_ticker(ticker)


async def is_user_subscribed(user_id: str, ticker: str) -> bool:
    """Check if user is subscribed to a ticker."""
    subscriptions = await get_user_subscriptions(user_id)
    return any(sub["ticker"] == ticker for sub in subscriptions)


async def get_subscription_stats() -> Dict[str, Any]:
    """Get subscription statistics."""
    # This would require additional queries in a real implementation
    # For now, return basic stats
    return {
        "total_subscriptions": 0,
        "active_tickers": [],
        "channel_distribution": {
            "ws": 0,
            "slack": 0,
            "email": 0
        }
    }
