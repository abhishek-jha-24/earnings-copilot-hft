"""
Streamlit UI for the earnings copilot system.
Provides admin upload interface and trader dashboard with SSE notifications.
"""

import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio
import threading
import queue


# Configuration
API_BASE_URL = "http://localhost:8000"
SSE_ENDPOINT = f"{API_BASE_URL}/events/stream"


class SSEClient:
    """Simple SSE client for receiving real-time notifications."""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.message_queue = queue.Queue()
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the SSE client in a background thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop the SSE client."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _listen(self):
        """Listen for SSE events."""
        try:
            headers = {"X-API-Key": self.api_key}
            params = {"user_id": self.user_id}
            
            response = requests.get(
                SSE_ENDPOINT,
                headers=headers,
                params=params,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for line in response.iter_lines(decode_unicode=True):
                    if not self.running:
                        break
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            self.message_queue.put(data)
                        except json.JSONDecodeError:
                            pass
                            
        except Exception as e:
            print(f"SSE error: {e}")
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all pending messages."""
        messages = []
        while not self.message_queue.empty():
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
        return messages


def make_api_request(endpoint: str, method: str = "GET", data: Any = None, 
                    files: Any = None, api_key: str = None) -> Dict[str, Any]:
    """Make API request with error handling."""
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=data)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, data=data, files=files)
            else:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"error": str(e)}


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Earnings Copilot HFT",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📈 Earnings Copilot HFT")
    st.markdown("*AI-powered earnings analysis and trading signals*")
    
    # Initialize session state
    if "sse_client" not in st.session_state:
        st.session_state.sse_client = None
    if "notifications" not in st.session_state:
        st.session_state.notifications = []
    if "upload_time" not in st.session_state:
        st.session_state.upload_time = None
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Role selection
        role = st.selectbox("Role", ["TRADER", "ADMIN"])
        
        # API key input
        if role == "ADMIN":
            api_key = st.text_input("Admin API Key", type="password", value="admin-secret")
            user_id = "admin_user"
        else:
            api_key = st.text_input("Trader API Key", type="password", value="trader-secret")
            user_id = "trader_user"
        
        # SSE connection
        if st.button("Connect Notifications"):
            if api_key:
                if st.session_state.sse_client:
                    st.session_state.sse_client.stop()
                
                st.session_state.sse_client = SSEClient(api_key, user_id)
                st.session_state.sse_client.start()
                st.success("Connected to notification stream")
            else:
                st.error("API key required")
        
        if st.button("Disconnect Notifications"):
            if st.session_state.sse_client:
                st.session_state.sse_client.stop()
                st.session_state.sse_client = None
                st.success("Disconnected from notification stream")
    
    # Main content area
    if role == "ADMIN":
        show_admin_interface(api_key)
    else:
        show_trader_interface(api_key, user_id)
    
    # Live notifications panel (always visible)
    show_notifications_panel()


def show_admin_interface(api_key: str):
    """Show admin interface for document upload."""
    st.header("🔒 Admin Interface")
    
    # Document upload form
    with st.expander("📄 Upload Document", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            ticker = st.text_input("Ticker Symbol", value="AAPL").upper()
            doc_type = st.selectbox("Document Type", 
                                   ["earnings", "filing", "press_release", "compliance"])
        
        with col2:
            period = st.text_input("Period (optional)", placeholder="2025-Q3")
            effective_date = st.text_input("Effective Date (optional)", 
                                         placeholder="2025-12-01")
        
        uploaded_file = st.file_uploader("Choose PDF file", type="pdf")
        
        if st.button("Upload & Process", type="primary"):
            if uploaded_file and ticker and api_key:
                # Record upload time for latency tracking
                st.session_state.upload_time = time.time()
                
                # Prepare form data
                files = {"file": uploaded_file}
                data = {
                    "ticker": ticker,
                    "doc_type": doc_type
                }
                if period:
                    data["period"] = period
                if effective_date:
                    data["effective_date"] = effective_date
                
                # Upload document
                with st.spinner("Uploading and processing document..."):
                    result = make_api_request("/admin/ingest", "POST", 
                                            data=data, files=files, api_key=api_key)
                
                if "error" in result:
                    st.error(f"Upload failed: {result['error']}")
                else:
                    st.success(f"Document uploaded successfully! Doc ID: {result['doc_id']}")
                    st.json(result)
            else:
                st.error("Please provide ticker, API key, and select a file")
    
    # Admin statistics
    with st.expander("📊 System Statistics"):
        if api_key:
            stats = make_api_request("/admin/stats", api_key=api_key)
            
            if "error" not in stats:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Documents", stats["documents"]["total"])
                    st.metric("Total Signals", stats["signals"]["total"])
                
                with col2:
                    st.metric("Active Subscriptions", stats["subscriptions"]["total"])
                    st.metric("Processing Queue", stats["system"]["processing_queue"])
                
                with col3:
                    st.metric("System Uptime", stats["system"]["uptime"])
            else:
                st.error("Failed to load statistics")


def show_trader_interface(api_key: str, user_id: str):
    """Show trader interface with signals and KPIs."""
    st.header("💼 Trader Dashboard")
    
    # Subscription management
    with st.expander("🔔 Manage Subscriptions"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_ticker = st.text_input("Subscribe to Ticker", placeholder="AAPL").upper()
            channels = st.multiselect("Notification Channels", 
                                    ["ws", "slack", "email"], default=["ws"])
            
            if st.button("Subscribe"):
                if new_ticker and channels and api_key:
                    data = {"ticker": new_ticker, "channels": channels}
                    result = make_api_request("/subscriptions", "POST", 
                                            data=data, api_key=api_key)
                    
                    if "error" in result:
                        st.error(f"Subscription failed: {result['error']}")
                    else:
                        st.success(f"Subscribed to {new_ticker}")
                        st.rerun()
        
        with col2:
            # List current subscriptions
            if api_key:
                subs = make_api_request("/subscriptions", api_key=api_key)
                
                if "error" not in subs and subs:
                    st.write("**Current Subscriptions:**")
                    for sub in subs:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.write(f"• {sub['ticker']} ({', '.join(sub['channels'])})")
                        with col_b:
                            if st.button("🗑️", key=f"unsub_{sub['ticker']}"):
                                result = make_api_request(f"/subscriptions/{sub['ticker']}", 
                                                        "DELETE", api_key=api_key)
                                if "error" not in result:
                                    st.success(f"Unsubscribed from {sub['ticker']}")
                                    st.rerun()
    
    # Ticker analysis
    with st.expander("📊 Ticker Analysis", expanded=True):
        analysis_ticker = st.text_input("Analyze Ticker", value="AAPL").upper()
        
        if analysis_ticker:
            col1, col2 = st.columns(2)
            
            with col1:
                # Get signal
                if api_key:
                    signal = make_api_request(f"/signal?ticker={analysis_ticker}", 
                                            api_key=api_key)
                    
                    if "error" not in signal:
                        # Signal banner
                        action = signal.get("action", "HOLD")
                        confidence = signal.get("confidence", 0)
                        
                        if action == "BUY":
                            st.success(f"🟢 {action} - {confidence:.0%} confidence")
                        elif action == "SELL":
                            st.error(f"🔴 {action} - {confidence:.0%} confidence")
                        else:
                            st.warning(f"🟡 {action} - {confidence:.0%} confidence")
                        
                        # Reasons
                        if signal.get("reasons"):
                            st.write("**Reasons:**")
                            for reason in signal["reasons"]:
                                st.write(f"• {reason}")
                        
                        # Check for latency tracking
                        if (st.session_state.upload_time and 
                            st.session_state.upload_time > 0):
                            signal_time = time.time()
                            latency = signal_time - st.session_state.upload_time
                            st.metric("Upload → Signal Latency", f"{latency:.1f}s")
                            st.session_state.upload_time = None  # Reset
                    else:
                        st.error("Failed to get signal")
            
            with col2:
                # KPI data
                metrics = ["revenue", "eps", "gross_margin"]
                for metric in metrics:
                    kpi = make_api_request(f"/kpi?ticker={analysis_ticker}&metric={metric}", 
                                         api_key=api_key)
                    
                    if "error" not in kpi:
                        value = kpi.get("current_value", 0)
                        unit = kpi.get("unit", "")
                        yoy_change = kpi.get("yoy_change")
                        
                        delta = f"{yoy_change:+.1%}" if yoy_change else None
                        st.metric(f"{metric.title()}", f"{value} {unit}", delta)
    
    # Export memo
    with st.expander("📄 Export Memo"):
        export_ticker = st.text_input("Ticker for Memo", value="AAPL").upper()
        export_period = st.text_input("Period for Memo", value="2025-Q3")
        export_format = st.selectbox("Format", ["pdf", "markdown"])
        
        if st.button("Generate Memo"):
            if export_ticker and export_period and api_key:
                url = f"/export/memo?ticker={export_ticker}&period={export_period}&format={export_format}"
                
                # Make direct request to get file
                headers = {"X-API-Key": api_key}
                response = requests.get(f"{API_BASE_URL}{url}", headers=headers)
                
                if response.status_code == 200:
                    filename = f"{export_ticker}_{export_period}_memo.{export_format}"
                    st.download_button(
                        label=f"Download {export_format.upper()}",
                        data=response.content,
                        file_name=filename,
                        mime="application/pdf" if export_format == "pdf" else "text/markdown"
                    )
                else:
                    st.error("Failed to generate memo")


def show_notifications_panel():
    """Show live notifications panel."""
    st.header("🔔 Live Notifications")
    
    # Get new messages from SSE client
    if st.session_state.sse_client:
        new_messages = st.session_state.sse_client.get_messages()
        
        for msg in new_messages:
            # Add timestamp
            msg["ui_timestamp"] = datetime.now().strftime("%H:%M:%S")
            st.session_state.notifications.insert(0, msg)
        
        # Limit to last 20 notifications
        st.session_state.notifications = st.session_state.notifications[:20]
    
    # Display notifications
    if st.session_state.notifications:
        for i, notification in enumerate(st.session_state.notifications):
            with st.container():
                timestamp = notification.get("ui_timestamp", "")
                event_type = notification.get("event", "message")
                data = notification.get("data", {})
                
                if event_type == "NEW_DOC_INGESTED":
                    st.info(f"[{timestamp}] 📄 New document: {data.get('ticker')} {data.get('doc_type')}")
                
                elif event_type == "NEW_SIGNAL_READY":
                    action = data.get("action", "HOLD")
                    ticker = data.get("ticker", "")
                    confidence = data.get("confidence", 0)
                    
                    if action == "BUY":
                        st.success(f"[{timestamp}] 🟢 {ticker} {action} ({confidence:.0%})")
                    elif action == "SELL":
                        st.error(f"[{timestamp}] 🔴 {ticker} {action} ({confidence:.0%})")
                    else:
                        st.warning(f"[{timestamp}] 🟡 {ticker} {action} ({confidence:.0%})")
                
                elif event_type == "COMPLIANCE_ALERT":
                    ticker = data.get("ticker", "")
                    message = data.get("message", "")
                    st.warning(f"[{timestamp}] ⚠️ {ticker}: {message}")
                
                elif event_type == "connected":
                    st.success(f"[{timestamp}] ✅ Connected to notification stream")
                
                elif event_type == "ping":
                    st.text(f"[{timestamp}] 📡 Keepalive")
                
                else:
                    st.text(f"[{timestamp}] {event_type}: {json.dumps(data, indent=2)}")
    else:
        st.info("No notifications yet. Connect to the notification stream to see live updates.")
    
    # Auto-refresh every 2 seconds
    time.sleep(2)
    st.rerun()


if __name__ == "__main__":
    main()
