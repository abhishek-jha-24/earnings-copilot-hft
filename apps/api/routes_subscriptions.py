"""
Subscription management API routes.
Handles user subscriptions to ticker notifications.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from apps.api.auth import require_trader_role, get_current_user_id
from apps.api.schemas import SubscriptionCreate, SubscriptionResponse
from services.subscriptions import (
    create_subscription,
    delete_subscription,
    get_user_subscriptions,
    is_user_subscribed
)


router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionResponse)
async def create_user_subscription(
    subscription: SubscriptionCreate,
    trader_role: str = Depends(require_trader_role),
    user_id: str = Depends(get_current_user_id)
):
    """
    Create or update a subscription to ticker notifications.
    
    Channels supported: ws (WebSocket/SSE), slack, email
    """
    try:
        # Validate ticker format
        ticker = subscription.ticker.upper().strip()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticker cannot be empty"
            )
        
        # Validate channels
        valid_channels = {"ws", "slack", "email"}
        if not all(channel in valid_channels for channel in subscription.channels):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channels. Supported: {valid_channels}"
            )
        
        if not subscription.channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one notification channel must be specified"
            )
        
        # Create subscription
        success = await create_subscription(user_id, ticker, subscription.channels)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create subscription"
            )
        
        # Get the created subscription to return
        user_subscriptions = await get_user_subscriptions(user_id)
        created_sub = next((sub for sub in user_subscriptions if sub["ticker"] == ticker), None)
        
        if not created_sub:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Subscription created but could not be retrieved"
            )
        
        return SubscriptionResponse(**created_sub)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.get("", response_model=List[SubscriptionResponse])
async def list_user_subscriptions(
    trader_role: str = Depends(require_trader_role),
    user_id: str = Depends(get_current_user_id)
):
    """Get all subscriptions for the current user."""
    try:
        subscriptions = await get_user_subscriptions(user_id)
        return [SubscriptionResponse(**sub) for sub in subscriptions]
        
    except Exception as e:
        print(f"Error listing subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list subscriptions: {str(e)}"
        )


@router.delete("/{ticker}")
async def delete_user_subscription(
    ticker: str,
    trader_role: str = Depends(require_trader_role),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a subscription for a specific ticker."""
    try:
        ticker = ticker.upper().strip()
        
        # Check if subscription exists
        is_subscribed = await is_user_subscribed(user_id, ticker)
        if not is_subscribed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No subscription found for ticker {ticker}"
            )
        
        # Delete subscription
        success = await delete_subscription(user_id, ticker)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete subscription"
            )
        
        return {
            "ticker": ticker,
            "status": "deleted",
            "message": f"Subscription to {ticker} removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete subscription: {str(e)}"
        )


@router.get("/{ticker}/status")
async def get_subscription_status(
    ticker: str,
    trader_role: str = Depends(require_trader_role),
    user_id: str = Depends(get_current_user_id)
):
    """Check if user is subscribed to a specific ticker."""
    try:
        ticker = ticker.upper().strip()
        is_subscribed = await is_user_subscribed(user_id, ticker)
        
        if is_subscribed:
            # Get subscription details
            user_subscriptions = await get_user_subscriptions(user_id)
            subscription = next((sub for sub in user_subscriptions if sub["ticker"] == ticker), None)
            
            return {
                "ticker": ticker,
                "subscribed": True,
                "channels": subscription["channels"] if subscription else [],
                "created_at": subscription["created_at"] if subscription else None
            }
        else:
            return {
                "ticker": ticker,
                "subscribed": False,
                "channels": [],
                "created_at": None
            }
        
    except Exception as e:
        print(f"Error checking subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check subscription status: {str(e)}"
        )


@router.put("/{ticker}")
async def update_subscription_channels(
    ticker: str,
    subscription: SubscriptionCreate,
    trader_role: str = Depends(require_trader_role),
    user_id: str = Depends(get_current_user_id)
):
    """Update notification channels for an existing subscription."""
    try:
        ticker = ticker.upper().strip()
        
        # Check if subscription exists
        is_subscribed = await is_user_subscribed(user_id, ticker)
        if not is_subscribed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No subscription found for ticker {ticker}"
            )
        
        # Validate channels
        valid_channels = {"ws", "slack", "email"}
        if not all(channel in valid_channels for channel in subscription.channels):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channels. Supported: {valid_channels}"
            )
        
        if not subscription.channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one notification channel must be specified"
            )
        
        # Update subscription (create_subscription handles updates too)
        success = await create_subscription(user_id, ticker, subscription.channels)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription"
            )
        
        # Get updated subscription
        user_subscriptions = await get_user_subscriptions(user_id)
        updated_sub = next((sub for sub in user_subscriptions if sub["ticker"] == ticker), None)
        
        if not updated_sub:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Subscription updated but could not be retrieved"
            )
        
        return SubscriptionResponse(**updated_sub)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )


@router.get("/stats/summary")
async def get_subscription_stats(
    trader_role: str = Depends(require_trader_role),
    user_id: str = Depends(get_current_user_id)
):
    """Get subscription statistics for the current user."""
    try:
        subscriptions = await get_user_subscriptions(user_id)
        
        # Calculate stats
        total_subscriptions = len(subscriptions)
        channel_counts = {"ws": 0, "slack": 0, "email": 0}
        tickers = []
        
        for sub in subscriptions:
            tickers.append(sub["ticker"])
            for channel in sub["channels"]:
                if channel in channel_counts:
                    channel_counts[channel] += 1
        
        return {
            "user_id": user_id,
            "total_subscriptions": total_subscriptions,
            "subscribed_tickers": sorted(tickers),
            "channel_distribution": channel_counts,
            "most_recent": subscriptions[0]["created_at"] if subscriptions else None
        }
        
    except Exception as e:
        print(f"Error getting subscription stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription stats: {str(e)}"
        )
