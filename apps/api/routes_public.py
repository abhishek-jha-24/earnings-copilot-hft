"""
Public API routes for KPIs, search, signals, exports, and SSE.
Available to traders and admins.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from fastapi.responses import StreamingResponse, Response
from datetime import datetime
import json

from apps.api.auth import require_trader_role, get_current_user_id
from apps.api.schemas import (
    KpiResponse, SignalResponse, SearchResponse, SearchResult, 
    MemoRequest, ErrorResponse
)
from agents.pathway_pipeline import pathway_service
from agents.benchmarks import benchmark_service
from agents.explainability import explainability_agent
from services.storage import get_signal as get_cached_signal
from services.notify import sse_stream_for_user


router = APIRouter(tags=["public"])


@router.get("/kpi", response_model=KpiResponse)
async def get_kpi(
    ticker: str = Query(..., description="Stock ticker symbol"),
    metric: str = Query(..., description="KPI metric name"),
    period: Optional[str] = Query(None, description="Financial period"),
    trader_role: str = Depends(require_trader_role)
):
    """
    Get latest KPI data with deltas, consensus, and provenance.
    
    Example: /kpi?ticker=AAPL&metric=revenue&period=2025-Q3
    """
    try:
        ticker = ticker.upper().strip()
        
        # Get KPI data from Pathway
        if period:
            kpi_data = await pathway_service.get_kpi(ticker, metric, period)
        else:
            # Get latest KPIs and find the metric
            latest_kpis = await pathway_service.get_latest_kpis(ticker)
            kpi_data = latest_kpis.get(metric)
        
        if not kpi_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"KPI not found: {ticker} {metric} {period or 'latest'}"
            )
        
        # Enrich with consensus data
        enriched_kpi = benchmark_service.enrich_kpi_with_consensus(kpi_data)
        
        # Calculate deltas if period specified
        yoy_change = enriched_kpi.get("yoy_change")
        qoq_change = enriched_kpi.get("qoq_change")
        
        if period and not yoy_change and not qoq_change:
            deltas = await pathway_service.get_deltas(ticker, period)
            metric_delta = next((d for d in deltas if d["metric"] == metric), None)
            if metric_delta:
                if metric_delta.get("comparison_type") == "yoy":
                    yoy_change = metric_delta["delta_pct"]
                elif metric_delta.get("comparison_type") == "qoq":
                    qoq_change = metric_delta["delta_pct"]
        
        return KpiResponse(
            ticker=ticker,
            period=enriched_kpi["period"],
            metric=metric,
            current_value=enriched_kpi["value"],
            unit=enriched_kpi["unit"],
            yoy_change=yoy_change,
            qoq_change=qoq_change,
            consensus=enriched_kpi.get("consensus"),
            surprise=enriched_kpi.get("surprise"),
            provenance=enriched_kpi["provenance"],
            confidence=enriched_kpi["confidence"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting KPI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get KPI: {str(e)}"
        )


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    trader_role: str = Depends(require_trader_role)
):
    """
    Search across indexed documents and KPI data.
    
    Example: /search?q=revenue growth&limit=10
    """
    try:
        # Search using Pathway pipeline
        results = await pathway_service.search(q, limit)
        
        # Convert to response format
        search_results = []
        for result in results:
            metadata = result.get("metadata", {})
            
            search_result = SearchResult(
                doc=metadata.get("doc", ""),
                page=metadata.get("page", 0),
                text=result.get("text", ""),
                score=result.get("score", 0.0),
                ticker=metadata.get("ticker")
            )
            search_results.append(search_result)
        
        return SearchResponse(
            query=q,
            results=search_results,
            total_results=len(search_results)
        )
        
    except Exception as e:
        print(f"Error in search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/signal", response_model=SignalResponse)
async def get_signal(
    ticker: str = Query(..., description="Stock ticker symbol"),
    period: Optional[str] = Query(None, description="Financial period"),
    trader_role: str = Depends(require_trader_role)
):
    """
    Get latest trading signal for a ticker.
    
    Example: /signal?ticker=AAPL&period=2025-Q3
    """
    try:
        ticker = ticker.upper().strip()
        # Ensure period is a proper string or None
        period_str = period if period else "latest"
        
        # Get cached signal first
        cached_signal = await get_cached_signal(ticker)
        
        if cached_signal:
            # Check if period matches (if specified)
            if not period or cached_signal.get("period") == period:
                return SignalResponse(**cached_signal)
        
        # If no cached signal or period mismatch, generate new one
        from agents.signal_agent import signal_agent
        from agents.risk_gate import risk_gate
        
        signal = await signal_agent.decide(ticker, period_str)
        
        # Apply risk gate
        gate_result = await risk_gate.gate(signal)
        if not gate_result[0]:
            signal["blocked_reason"] = gate_result[1]
        
        return SignalResponse(**signal)
        
    except Exception as e:
        print(f"Error getting signal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get signal: {str(e)}"
        )


@router.get("/events/stream")
async def events_stream(
    request: Request,
    api_key: Optional[str] = Query(None, description="API key for authentication"),
    user_id: Optional[str] = Query(None, description="User ID (if API key provided)")
):
    """
    Server-Sent Events stream for real-time notifications.
    
    Events: NEW_DOC_INGESTED, NEW_SIGNAL_READY, COMPLIANCE_ALERT
    """
    # Authenticate user
    if api_key:
        from apps.api.auth import get_user_id_from_api_key
        authenticated_user_id = get_user_id_from_api_key(api_key)
        if not authenticated_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        user_id = authenticated_user_id
    elif not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key or user_id required"
        )
    
    async def event_generator():
        try:
            async for message in sse_stream_for_user(user_id, request):
                event_type = message.get("event", "message")
                data = message.get("data", {})
                
                # Format as SSE
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(data)}\n\n"
                
        except Exception as e:
            print(f"SSE stream error for user {user_id}: {e}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/export/memo")
async def export_memo(
    ticker: str = Query(..., description="Stock ticker symbol"),
    period: str = Query(..., description="Financial period"),
    format: str = Query("pdf", regex="^(pdf|markdown)$", description="Export format"),
    include_citations: bool = Query(True, description="Include citations"),
    include_compliance: bool = Query(True, description="Include compliance info"),
    trader_role: str = Depends(require_trader_role)
):
    """
    Export investment memo as PDF or Markdown.
    
    Example: /export/memo?ticker=AAPL&period=2025-Q3&format=pdf
    """
    try:
        ticker = ticker.upper().strip()
        
        if format == "pdf":
            # Generate PDF
            pdf_bytes = await explainability_agent.generate_pdf(
                ticker, period, include_citations, include_compliance
            )
            
            if pdf_bytes is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF generation failed"
                )
            
            filename = f"{ticker}_{period}_memo.pdf"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
        else:  # markdown
            # Generate markdown memo
            memo = await explainability_agent.generate_memo(
                ticker, period, include_citations, include_compliance
            )
            
            if memo.get("error"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Memo generation failed: {memo['error']}"
                )
            
            filename = f"{ticker}_{period}_memo.md"
            return Response(
                content=memo["markdown"],
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error exporting memo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export memo: {str(e)}"
        )


@router.get("/tickers")
async def list_available_tickers(
    trader_role: str = Depends(require_trader_role)
):
    """Get list of tickers with available data."""
    try:
        # This would query the database for available tickers
        # For now, return a static list
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "CRM"]
        
        return {
            "tickers": sorted(tickers),
            "total": len(tickers),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"Error listing tickers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tickers: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/ticker/{ticker}/summary")
async def get_ticker_summary(
    ticker: str,
    trader_role: str = Depends(require_trader_role)
):
    """Get comprehensive summary for a ticker."""
    try:
        ticker = ticker.upper().strip()
        
        # Get latest KPIs
        latest_kpis = await pathway_service.get_latest_kpis(ticker)
        
        # Get latest signal
        signal = await get_cached_signal(ticker)
        
        # Get compliance summary
        from agents.compliance_agent import compliance_agent
        compliance = await compliance_agent.get_compliance_summary(ticker)
        
        return {
            "ticker": ticker,
            "last_updated": datetime.utcnow().isoformat(),
            "signal": signal,
            "kpis": latest_kpis,
            "compliance": compliance,
            "available_periods": []  # Would be populated from actual data
        }
        
    except Exception as e:
        print(f"Error getting ticker summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticker summary: {str(e)}"
        )
