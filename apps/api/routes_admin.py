"""
Admin API routes for document ingestion and management.
Handles file uploads, document processing, and admin operations.
"""

import os
import tempfile
import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse

from apps.api.auth import require_admin_role
from apps.api.schemas import UploadResponse, DocEvent
from services.storage import add_document
from services.notify import publish_doc_event, publish_signal_ready, publish_compliance_alert
from agents.ade_ingest import ade_service
from agents.normalizer import normalizer
from agents.pathway_pipeline import pathway_service
from agents.signal_agent import signal_agent
from agents.risk_gate import risk_gate
from agents.compliance_agent import compliance_agent


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest", response_model=UploadResponse)
async def ingest_document(
    file: UploadFile = File(...),
    ticker: str = Form(...),
    period: Optional[str] = Form(None),
    doc_type: str = Form(...),
    effective_date: Optional[str] = Form(None),
    admin_role: str = Depends(require_admin_role)
):
    """
    Ingest a financial document for processing.
    
    Supports document types: earnings, filing, press_release, compliance
    """
    try:
        # Validate inputs
        if doc_type not in ["earnings", "filing", "press_release", "compliance"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid doc_type. Must be one of: earnings, filing, press_release, compliance"
            )
        
        ticker = ticker.upper().strip()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticker is required"
            )
        
        # Generate document ID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        doc_id = f"{ticker}_{doc_type}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Store document record
            success = await add_document(
                doc_id=doc_id,
                ticker=ticker,
                period=period,
                doc_type=doc_type,
                path=temp_file_path,
                uploader="admin_user"
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store document record"
                )
            
            # Publish document ingestion event
            doc_event = DocEvent(
                event="NEW_DOC_INGESTED",
                doc_id=doc_id,
                ticker=ticker,
                period=period,
                doc_type=doc_type,
                received_at=datetime.utcnow().isoformat()
            )
            await publish_doc_event(doc_event)
            
            # Process document based on type
            if doc_type == "compliance":
                await _process_compliance_document(temp_file_path, ticker, doc_type, effective_date)
            else:
                await _process_financial_document(temp_file_path, ticker, period, doc_type, doc_id)
            
            return UploadResponse(
                doc_id=doc_id,
                ticker=ticker,
                period=period,
                doc_type=doc_type,
                status="success",
                message="Document ingested and processing started"
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error ingesting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )


async def _process_financial_document(file_path: str, ticker: str, period: Optional[str], 
                                    doc_type: str, doc_id: str):
    """Process financial documents (earnings, filings, etc.)."""
    try:
        # Extract KPIs using ADE
        kpi_rows = await ade_service.extract_and_normalize(file_path, ticker, period, doc_type)
        
        if not kpi_rows:
            print(f"No KPIs extracted from {file_path}")
            return
        
        # Validate and normalize KPIs
        validated_kpis = normalizer.validate_and_mark(kpi_rows)
        
        # Enrich with consensus data
        from agents.benchmarks import benchmark_service
        enriched_kpis = benchmark_service.enrich_kpi_list(validated_kpis)
        
        # Write to JSONL file for persistence
        await _write_kpis_to_jsonl(enriched_kpis, doc_id)
        
        # Upsert into Pathway pipeline
        success = await pathway_service.upsert(enriched_kpis)
        
        if success:
            # Generate trading signal
            signal = await signal_agent.decide(ticker, period or "latest")
            
            # Apply risk gate
            gate_result = await risk_gate.gate(signal, enriched_kpis)
            
            if gate_result[0]:  # Signal approved
                # Cache signal
                from services.storage import upsert_signal
                await upsert_signal(ticker, signal)
                
                # Publish signal ready event
                await publish_signal_ready(ticker, signal)
                
                print(f"Signal generated for {ticker}: {signal['action']} ({signal['confidence']:.2f})")
            else:
                # Signal blocked
                blocked_signal = signal.copy()
                blocked_signal["blocked_reason"] = gate_result[1]
                await upsert_signal(ticker, blocked_signal)
                
                print(f"Signal blocked for {ticker}: {gate_result[1]}")
        
    except Exception as e:
        print(f"Error processing financial document: {e}")


async def _process_compliance_document(file_path: str, ticker: str, doc_type: str, 
                                     effective_date: Optional[str]):
    """Process compliance documents."""
    try:
        # Process compliance rules
        alerts = await compliance_agent.process(file_path, ticker, doc_type, effective_date)
        
        if alerts:
            print(f"Generated {len(alerts)} compliance alerts")
            
            # Publish compliance alerts
            for alert in alerts:
                await publish_compliance_alert(alert["ticker"], alert)
        
    except Exception as e:
        print(f"Error processing compliance document: {e}")


async def _write_kpis_to_jsonl(kpi_rows: list, doc_id: str):
    """Write KPIs to JSONL file for persistence."""
    try:
        import json
        
        # Ensure normalized directory exists
        os.makedirs("data/normalized", exist_ok=True)
        
        # Write to JSONL file
        filename = f"data/normalized/{doc_id}.jsonl"
        with open(filename, 'w') as f:
            for kpi in kpi_rows:
                f.write(json.dumps(kpi) + '\n')
        
        print(f"Wrote {len(kpi_rows)} KPIs to {filename}")
        
    except Exception as e:
        print(f"Error writing KPIs to JSONL: {e}")


@router.get("/documents")
async def list_documents(
    ticker: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 50,
    admin_role: str = Depends(require_admin_role)
):
    """List ingested documents with optional filtering."""
    try:
        # This would query the database for documents
        # For now, return a placeholder response
        return {
            "documents": [],
            "total": 0,
            "filters": {
                "ticker": ticker,
                "doc_type": doc_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    admin_role: str = Depends(require_admin_role)
):
    """Delete a document and its associated data."""
    try:
        # This would remove the document from database and clean up files
        # For now, return a placeholder response
        return {
            "doc_id": doc_id,
            "status": "deleted",
            "message": "Document and associated data removed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/stats")
async def get_admin_stats(admin_role: str = Depends(require_admin_role)):
    """Get admin statistics and system health."""
    try:
        # Gather system statistics
        stats = {
            "documents": {
                "total": 0,
                "by_type": {
                    "earnings": 0,
                    "filing": 0,
                    "compliance": 0,
                    "press_release": 0
                }
            },
            "signals": {
                "total": 0,
                "by_action": {
                    "BUY": 0,
                    "SELL": 0,
                    "HOLD": 0
                }
            },
            "subscriptions": {
                "total": 0,
                "active_tickers": 0
            },
            "system": {
                "uptime": "0h 0m",
                "last_document": None,
                "processing_queue": 0
            }
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get admin stats: {str(e)}"
        )


@router.post("/reprocess/{doc_id}")
async def reprocess_document(
    doc_id: str,
    admin_role: str = Depends(require_admin_role)
):
    """Reprocess a previously ingested document."""
    try:
        # This would reload the document and rerun the processing pipeline
        # For now, return a placeholder response
        return {
            "doc_id": doc_id,
            "status": "reprocessing",
            "message": "Document reprocessing started"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess document: {str(e)}"
        )
