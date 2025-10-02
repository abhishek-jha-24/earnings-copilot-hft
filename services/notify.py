"""
Server-Sent Events (SSE) notification hub and Slack integration.
Manages real-time notifications to subscribed users.
"""

import json
import asyncio
import os
from typing import Dict, List, Any, AsyncGenerator, Set
from datetime import datetime
from fastapi import Request
import httpx

from apps.api.schemas import DocEvent, ComplianceAlert, NewSignalReady
from services.storage import subscribers_for_ticker


class SSEManager:
    """Manages SSE connections and message broadcasting."""
    
    def __init__(self):
        # Store active connections per user
        self._connections: Dict[str, Set[asyncio.Queue]] = {}
        self._slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    async def add_connection(self, user_id: str) -> asyncio.Queue:
        """Add new SSE connection for user."""
        if user_id not in self._connections:
            self._connections[user_id] = set()
        
        queue = asyncio.Queue()
        self._connections[user_id].add(queue)
        return queue
    
    async def remove_connection(self, user_id: str, queue: asyncio.Queue):
        """Remove SSE connection."""
        if user_id in self._connections:
            self._connections[user_id].discard(queue)
            if not self._connections[user_id]:
                del self._connections[user_id]
    
    async def broadcast_to_user(self, user_id: str, event: str, data: Dict[str, Any]):
        """Broadcast message to all connections for a specific user."""
        if user_id not in self._connections:
            return
        
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all user's connections
        dead_queues = set()
        for queue in self._connections[user_id]:
            try:
                await asyncio.wait_for(queue.put(message), timeout=1.0)
            except (asyncio.TimeoutError, RuntimeError):
                dead_queues.add(queue)
        
        # Clean up dead connections
        for dead_queue in dead_queues:
            self._connections[user_id].discard(dead_queue)
    
    async def broadcast_to_multiple_users(self, user_ids: List[str], event: str, data: Dict[str, Any]):
        """Broadcast message to multiple users."""
        tasks = []
        for user_id in user_ids:
            tasks.append(self.broadcast_to_user(user_id, event, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_slack_notification(self, message: str, ticker: str = None):
        """Send notification to Slack webhook if configured."""
        if not self._slack_webhook_url:
            return
        
        try:
            payload = {
                "text": message,
                "username": "Earnings Copilot",
                "icon_emoji": ":chart_with_upwards_trend:"
            }
            
            if ticker:
                payload["attachments"] = [{
                    "color": "good",
                    "fields": [{
                        "title": "Ticker",
                        "value": ticker,
                        "short": True
                    }]
                }]
            
            async with httpx.AsyncClient() as client:
                await client.post(self._slack_webhook_url, json=payload, timeout=5.0)
                
        except Exception as e:
            print(f"Failed to send Slack notification: {e}")


# Global SSE manager instance
sse_manager = SSEManager()


async def sse_stream_for_user(user_id: str, request: Request) -> AsyncGenerator[Dict[str, Any], None]:
    """Generate SSE stream for a specific user."""
    queue = await sse_manager.add_connection(user_id)
    
    try:
        # Send initial connection confirmation
        yield {
            "event": "connected",
            "data": {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()}
        }
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            try:
                # Wait for new messages with timeout
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield message
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield {
                    "event": "ping",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                }
                
    except Exception as e:
        print(f"SSE stream error for user {user_id}: {e}")
    finally:
        await sse_manager.remove_connection(user_id, queue)


# Event publishing functions
async def publish_doc_event(doc_event: DocEvent):
    """Publish document ingestion event to subscribers."""
    # Get subscribers for this ticker
    subscribers = await subscribers_for_ticker(doc_event.ticker)
    
    if not subscribers:
        return
    
    # Prepare event data
    event_data = doc_event.dict()
    
    # Broadcast to all subscribers
    user_ids = [sub["user_id"] for sub in subscribers if "ws" in sub["channels"]]
    await sse_manager.broadcast_to_multiple_users(user_ids, "NEW_DOC_INGESTED", event_data)
    
    # Send Slack notifications for subscribers who want them
    slack_subscribers = [sub for sub in subscribers if "slack" in sub["channels"]]
    if slack_subscribers:
        message = f"📄 New {doc_event.doc_type} document ingested for {doc_event.ticker}"
        if doc_event.period:
            message += f" ({doc_event.period})"
        await sse_manager.send_slack_notification(message, doc_event.ticker)


async def publish_signal_ready(ticker: str, signal_data: Dict[str, Any]):
    """Publish signal ready event to subscribers."""
    # Get subscribers for this ticker
    subscribers = await subscribers_for_ticker(ticker)
    
    if not subscribers:
        return
    
    # Create signal event
    signal_event = NewSignalReady(
        event="NEW_SIGNAL_READY",
        ticker=ticker,
        action=signal_data["action"],
        confidence=signal_data["confidence"],
        citations=signal_data.get("citations", [])
    )
    
    # Broadcast to WebSocket subscribers
    user_ids = [sub["user_id"] for sub in subscribers if "ws" in sub["channels"]]
    await sse_manager.broadcast_to_multiple_users(user_ids, "NEW_SIGNAL_READY", signal_event.dict())
    
    # Send Slack notifications
    slack_subscribers = [sub for sub in subscribers if "slack" in sub["channels"]]
    if slack_subscribers:
        action_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal_data["action"], "⚪")
        message = f"{action_emoji} {signal_data['action']} signal for {ticker} (confidence: {signal_data['confidence']:.0%})"
        await sse_manager.send_slack_notification(message, ticker)


async def publish_compliance_alert(ticker: str, alert_data: Dict[str, Any]):
    """Publish compliance alert to subscribers."""
    # Get subscribers for this ticker
    subscribers = await subscribers_for_ticker(ticker)
    
    if not subscribers:
        return
    
    # Create compliance alert event
    alert_event = ComplianceAlert(
        event="COMPLIANCE_ALERT",
        ticker=ticker,
        message=alert_data["message"],
        effective_date=alert_data["effective_date"],
        citations=alert_data.get("citations", []),
        exposure_guidance=alert_data.get("exposure_guidance")
    )
    
    # Broadcast to WebSocket subscribers
    user_ids = [sub["user_id"] for sub in subscribers if "ws" in sub["channels"]]
    await sse_manager.broadcast_to_multiple_users(user_ids, "COMPLIANCE_ALERT", alert_event.dict())
    
    # Send Slack notifications
    slack_subscribers = [sub for sub in subscribers if "slack" in sub["channels"]]
    if slack_subscribers:
        message = f"⚠️ Compliance alert for {ticker}: {alert_data['message']}"
        if alert_data.get("exposure_guidance"):
            message += f"\n💡 {alert_data['exposure_guidance']}"
        await sse_manager.send_slack_notification(message, ticker)


# Utility functions
def format_sse_message(event: str, data: Dict[str, Any]) -> str:
    """Format message for SSE transmission."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
