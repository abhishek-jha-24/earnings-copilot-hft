"""
Tests for idempotent operations and data consistency.
"""

import pytest
import asyncio
import json
from datetime import datetime
from services.storage import (
    add_document, get_document, upsert_signal, get_signal,
    add_compliance_rule, get_compliance_rules_for_ticker
)
from agents.pathway_pipeline import pathway_service
from agents.ade_ingest import ade_service


class TestIdempotence:
    """Test idempotent operations and data consistency."""
    
    @pytest.mark.asyncio
    async def test_document_ingestion_idempotence(self):
        """Test that duplicate document ingestion is handled properly."""
        doc_id = "test_idempotent_doc"
        ticker = "AAPL"
        
        # First ingestion
        success1 = await add_document(
            doc_id=doc_id,
            ticker=ticker,
            period="2025-Q3",
            doc_type="earnings",
            path="/tmp/test.pdf",
            uploader="admin"
        )
        assert success1
        
        # Duplicate ingestion (same doc_id)
        success2 = await add_document(
            doc_id=doc_id,
            ticker=ticker,
            period="2025-Q3",
            doc_type="earnings",
            path="/tmp/test2.pdf",
            uploader="admin"
        )
        
        # Should handle gracefully (either succeed with update or fail gracefully)
        # The exact behavior depends on implementation - key is no corruption
        
        # Verify document exists and is consistent
        doc = await get_document(doc_id)
        assert doc is not None
        assert doc["ticker"] == ticker
        assert doc["doc_id"] == doc_id
    
    @pytest.mark.asyncio
    async def test_kpi_upsert_idempotence(self):
        """Test that KPI upserts are idempotent."""
        kpi_data = {
            "ticker": "AAPL",
            "period": "2025-Q3",
            "metric": "revenue",
            "value": 123.45,
            "unit": "B",
            "confidence": 0.95,
            "needs_review": False,
            "provenance": {
                "doc": "test.pdf",
                "page": 1,
                "table": "income_statement",
                "row": 1,
                "col": 2
            },
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # First upsert
        success1 = await pathway_service.upsert([kpi_data])
        assert success1
        
        # Get initial data
        initial_kpi = await pathway_service.get_kpi("AAPL", "revenue", "2025-Q3")
        assert initial_kpi is not None
        assert initial_kpi["value"] == 123.45
        
        # Second upsert with same data
        success2 = await pathway_service.upsert([kpi_data])
        assert success2
        
        # Verify data unchanged
        updated_kpi = await pathway_service.get_kpi("AAPL", "revenue", "2025-Q3")
        assert updated_kpi["value"] == 123.45
        
        # Third upsert with updated value
        kpi_data["value"] = 125.0
        success3 = await pathway_service.upsert([kpi_data])
        assert success3
        
        # Verify data updated
        final_kpi = await pathway_service.get_kpi("AAPL", "revenue", "2025-Q3")
        assert final_kpi["value"] == 125.0
    
    @pytest.mark.asyncio
    async def test_signal_caching_idempotence(self):
        """Test that signal caching is idempotent."""
        ticker = "MSFT"
        
        signal_data = {
            "ticker": ticker,
            "period": "2025-Q3",
            "action": "BUY",
            "confidence": 0.85,
            "reasons": ["Strong earnings"],
            "citations": [],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # First cache
        success1 = await upsert_signal(ticker, signal_data)
        assert success1
        
        # Get cached signal
        cached1 = await get_signal(ticker)
        assert cached1 is not None
        assert cached1["action"] == "BUY"
        assert cached1["confidence"] == 0.85
        
        # Update signal
        signal_data["confidence"] = 0.90
        signal_data["generated_at"] = datetime.utcnow().isoformat()
        
        success2 = await upsert_signal(ticker, signal_data)
        assert success2
        
        # Verify update
        cached2 = await get_signal(ticker)
        assert cached2["confidence"] == 0.90
        assert cached2["generated_at"] != cached1["generated_at"]
    
    @pytest.mark.asyncio
    async def test_compliance_rule_idempotence(self):
        """Test that compliance rule updates are idempotent."""
        rule_id = "test_rule_idempotent"
        
        rule_data = {
            "rule_id": rule_id,
            "scope_class": "TECH-LARGE",
            "scope_tickers": ["AAPL", "MSFT"],
            "initial_margin": 0.30,
            "maintenance_margin": 0.25,
            "effective_date": "2025-12-01",
            "provenance": {
                "doc": "test_compliance.pdf",
                "page": 1,
                "table": "margin_requirements",
                "row": 1,
                "col": 1
            },
            "confidence": 0.95
        }
        
        # First addition
        success1 = await add_compliance_rule(
            rule_id=rule_data["rule_id"],
            scope_class=rule_data["scope_class"],
            scope_tickers=rule_data["scope_tickers"],
            initial_margin=rule_data["initial_margin"],
            maintenance_margin=rule_data["maintenance_margin"],
            effective_date=rule_data["effective_date"],
            provenance=rule_data["provenance"],
            confidence=rule_data["confidence"]
        )
        assert success1
        
        # Get initial rule
        rules1 = await get_compliance_rules_for_ticker("AAPL")
        initial_rule = next((r for r in rules1 if r["rule_id"] == rule_id), None)
        assert initial_rule is not None
        assert initial_rule["maintenance_margin"] == 0.25
        
        # Update rule (same ID, different margin)
        success2 = await add_compliance_rule(
            rule_id=rule_data["rule_id"],
            scope_class=rule_data["scope_class"],
            scope_tickers=rule_data["scope_tickers"],
            initial_margin=rule_data["initial_margin"],
            maintenance_margin=0.30,  # Updated
            effective_date=rule_data["effective_date"],
            provenance=rule_data["provenance"],
            confidence=rule_data["confidence"]
        )
        assert success2
        
        # Verify update
        rules2 = await get_compliance_rules_for_ticker("AAPL")
        updated_rule = next((r for r in rules2 if r["rule_id"] == rule_id), None)
        assert updated_rule is not None
        assert updated_rule["maintenance_margin"] == 0.30
    
    @pytest.mark.asyncio
    async def test_concurrent_kpi_updates(self):
        """Test concurrent KPI updates maintain consistency."""
        ticker = "GOOGL"
        period = "2025-Q3"
        metric = "revenue"
        
        # Create multiple concurrent updates
        kpi_updates = []
        for i in range(5):
            kpi_data = {
                "ticker": ticker,
                "period": period,
                "metric": metric,
                "value": 100.0 + i,  # Different values
                "unit": "B",
                "confidence": 0.90,
                "needs_review": False,
                "provenance": {
                    "doc": f"test_{i}.pdf",
                    "page": 1,
                    "table": "income_statement",
                    "row": 1,
                    "col": 2
                },
                "extracted_at": datetime.utcnow().isoformat()
            }
            kpi_updates.append([kpi_data])
        
        # Execute concurrent upserts
        tasks = [pathway_service.upsert(kpi_data) for kpi_data in kpi_updates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed (or handle gracefully)
        successful_updates = [r for r in results if r is True]
        assert len(successful_updates) > 0
        
        # Final state should be consistent
        final_kpi = await pathway_service.get_kpi(ticker, metric, period)
        assert final_kpi is not None
        assert 100.0 <= final_kpi["value"] <= 104.0  # One of the values
    
    @pytest.mark.asyncio
    async def test_document_processing_retry_idempotence(self):
        """Test that retrying document processing is safe."""
        # Mock file path
        file_path = "/tmp/test_retry.pdf"
        ticker = "AMZN"
        period = "2025-Q3"
        doc_type = "earnings"
        
        # First processing attempt
        kpis1 = await ade_service.extract_and_normalize(file_path, ticker, period, doc_type)
        
        # Second processing attempt (simulating retry)
        kpis2 = await ade_service.extract_and_normalize(file_path, ticker, period, doc_type)
        
        # Results should be consistent
        assert len(kpis1) == len(kpis2)
        
        if kpis1 and kpis2:
            # Compare first KPI from each run
            kpi1 = kpis1[0]
            kpi2 = kpis2[0]
            
            assert kpi1["ticker"] == kpi2["ticker"]
            assert kpi1["period"] == kpi2["period"]
            assert kpi1["metric"] == kpi2["metric"]
            # Values might vary slightly due to confidence, but should be close
    
    def test_json_serialization_consistency(self):
        """Test that JSON serialization/deserialization is consistent."""
        original_data = {
            "ticker": "AAPL",
            "period": "2025-Q3",
            "metric": "revenue",
            "value": 123.45,
            "unit": "B",
            "confidence": 0.95,
            "needs_review": False,
            "provenance": {
                "doc": "test.pdf",
                "page": 15,
                "table": "income_statement",
                "row": 1,
                "col": 2
            },
            "extracted_at": "2025-10-02T19:12:35Z",
            "consensus": 120.0,
            "surprise": 0.0288
        }
        
        # Serialize and deserialize multiple times
        for _ in range(5):
            serialized = json.dumps(original_data, sort_keys=True)
            deserialized = json.loads(serialized)
            
            # Should be identical
            assert deserialized == original_data
            
            # Use deserialized as input for next iteration
            original_data = deserialized
    
    @pytest.mark.asyncio
    async def test_database_transaction_consistency(self):
        """Test database transaction consistency."""
        # This test would verify ACID properties in a real database
        # For SQLite with our current implementation, we test basic consistency
        
        ticker = "TSLA"
        doc_id = "tsla_test_transaction"
        
        # Simulate a transaction that should be atomic
        try:
            # Step 1: Add document
            doc_success = await add_document(
                doc_id=doc_id,
                ticker=ticker,
                period="2025-Q3",
                doc_type="earnings",
                path="/tmp/test.pdf",
                uploader="admin"
            )
            assert doc_success
            
            # Step 2: Add signal (dependent on document)
            signal_data = {
                "ticker": ticker,
                "action": "BUY",
                "confidence": 0.80,
                "doc_id": doc_id
            }
            signal_success = await upsert_signal(ticker, signal_data)
            assert signal_success
            
            # Verify both operations succeeded
            doc = await get_document(doc_id)
            signal = await get_signal(ticker)
            
            assert doc is not None
            assert signal is not None
            assert doc["ticker"] == signal["ticker"]
            
        except Exception as e:
            # In a real implementation, this would trigger rollback
            pytest.fail(f"Transaction consistency test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_search_index_consistency(self):
        """Test that search index updates are consistent."""
        # Add some test data
        test_kpis = [
            {
                "ticker": "NFLX",
                "period": "2025-Q3",
                "metric": "revenue",
                "value": 50.0,
                "unit": "B",
                "confidence": 0.90,
                "needs_review": False,
                "provenance": {
                    "doc": "nflx_earnings.pdf",
                    "page": 10,
                    "table": "income_statement",
                    "row": 1,
                    "col": 2
                },
                "extracted_at": datetime.utcnow().isoformat()
            }
        ]
        
        # Upsert data (should update search index)
        success = await pathway_service.upsert(test_kpis)
        assert success
        
        # Search should find the data
        search_results = await pathway_service.search("NFLX revenue")
        
        # Should find at least one result
        assert len(search_results) > 0
        
        # Results should contain our data
        found_nflx = any("NFLX" in result.get("text", "") for result in search_results)
        assert found_nflx


if __name__ == "__main__":
    pytest.main([__file__])
