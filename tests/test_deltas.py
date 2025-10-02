"""
Tests for delta calculations and KPI comparisons.
"""

import pytest
import asyncio
from datetime import datetime
from agents.normalizer import normalizer
from agents.pathway_pipeline import pathway_service
from agents.benchmarks import benchmark_service


class TestDeltas:
    """Test delta calculation functionality."""
    
    @pytest.fixture
    def sample_kpi_current(self):
        """Current period KPI data."""
        return {
            "ticker": "AAPL",
            "period": "2025-Q3",
            "metric": "revenue",
            "value": 123.45,
            "unit": "B",
            "provenance": {
                "doc": "aapl_10q_2025_q3.pdf",
                "page": 15,
                "table": "income_statement",
                "row": 1,
                "col": 2
            },
            "confidence": 0.95,
            "needs_review": False,
            "extracted_at": datetime.utcnow().isoformat()
        }
    
    @pytest.fixture
    def sample_kpi_previous(self):
        """Previous period KPI data."""
        return {
            "ticker": "AAPL",
            "period": "2024-Q3",
            "metric": "revenue",
            "value": 115.0,
            "unit": "B",
            "provenance": {
                "doc": "aapl_10q_2024_q3.pdf",
                "page": 12,
                "table": "income_statement",
                "row": 1,
                "col": 2
            },
            "confidence": 0.92,
            "needs_review": False,
            "extracted_at": datetime.utcnow().isoformat()
        }
    
    def test_calculate_deltas(self, sample_kpi_current, sample_kpi_previous):
        """Test delta calculation between periods."""
        current_kpis = [sample_kpi_current]
        historical_kpis = [sample_kpi_previous]
        
        deltas = normalizer.calculate_deltas(current_kpis, historical_kpis)
        
        assert len(deltas) == 1
        delta = deltas[0]
        
        assert delta["ticker"] == "AAPL"
        assert delta["metric"] == "revenue"
        assert delta["current_value"] == 123.45
        assert delta["previous_value"] == 115.0
        assert abs(delta["delta_abs"] - 8.45) < 0.01
        assert abs(delta["delta_pct"] - 0.0735) < 0.001  # ~7.35% increase
        assert delta["significance"] == "material"  # > 5% for revenue
    
    def test_determine_comparison_type(self):
        """Test comparison type determination (YoY vs QoQ)."""
        # Test YoY comparison
        yoy_type = normalizer._determine_comparison_type("2025-Q3", "2024-Q3")
        assert yoy_type == "yoy"
        
        # Test QoQ comparison
        qoq_type = normalizer._determine_comparison_type("2025-Q3", "2025-Q2")
        assert qoq_type == "qoq"
        
        # Test other comparison
        other_type = normalizer._determine_comparison_type("2025-Q3", "2023-Q1")
        assert other_type == "other"
    
    def test_determine_significance(self):
        """Test significance classification."""
        # Material revenue change (>5%)
        assert normalizer._determine_significance(0.08, "revenue") == "material"
        
        # Minor revenue change (2-5%)
        assert normalizer._determine_significance(0.03, "revenue") == "minor"
        
        # Negligible revenue change (<2%)
        assert normalizer._determine_significance(0.01, "revenue") == "negligible"
        
        # Material EPS change (>10%)
        assert normalizer._determine_significance(0.12, "eps") == "material"
        
        # Material margin change (>3%)
        assert normalizer._determine_significance(0.04, "gross_margin") == "material"
    
    @pytest.mark.asyncio
    async def test_pathway_delta_integration(self, sample_kpi_current, sample_kpi_previous):
        """Test delta calculation through Pathway service."""
        # Upsert both KPIs
        kpis = [sample_kpi_previous, sample_kpi_current]
        success = await pathway_service.upsert(kpis)
        assert success
        
        # Get deltas
        deltas = await pathway_service.get_deltas("AAPL", "2025-Q3")
        
        assert len(deltas) >= 1
        revenue_delta = next((d for d in deltas if d["metric"] == "revenue"), None)
        assert revenue_delta is not None
        assert revenue_delta["delta_pct"] > 0  # Positive growth
    
    def test_consensus_surprise_calculation(self, sample_kpi_current):
        """Test consensus surprise calculation."""
        # Add consensus data
        benchmark_service.add_consensus_data("AAPL", "2025-Q3", "revenue", 120.0, "B")
        
        # Enrich KPI with consensus
        enriched = benchmark_service.enrich_kpi_with_consensus(sample_kpi_current)
        
        assert enriched["consensus"] == 120.0
        assert abs(enriched["surprise"] - 0.0288) < 0.001  # (123.45-120)/120 ≈ 2.88%
    
    def test_delta_edge_cases(self):
        """Test edge cases in delta calculations."""
        # Zero previous value
        current_kpis = [{
            "ticker": "TEST",
            "period": "2025-Q3",
            "metric": "revenue",
            "value": 100.0,
            "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 1, "col": 1}
        }]
        
        historical_kpis = [{
            "ticker": "TEST",
            "period": "2024-Q3",
            "metric": "revenue",
            "value": 0.0,
            "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 1, "col": 1}
        }]
        
        deltas = normalizer.calculate_deltas(current_kpis, historical_kpis)
        assert len(deltas) == 0  # Should skip zero division
        
        # Negative values
        current_kpis[0]["value"] = -50.0
        historical_kpis[0]["value"] = -100.0
        
        deltas = normalizer.calculate_deltas(current_kpis, historical_kpis)
        assert len(deltas) == 1
        assert deltas[0]["delta_pct"] == 0.5  # (-50 - (-100)) / (-100) = 0.5
    
    def test_multiple_metrics_deltas(self):
        """Test delta calculation for multiple metrics."""
        current_kpis = [
            {
                "ticker": "AAPL",
                "period": "2025-Q3",
                "metric": "revenue",
                "value": 123.45,
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 1, "col": 1}
            },
            {
                "ticker": "AAPL",
                "period": "2025-Q3",
                "metric": "eps",
                "value": 1.85,
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 2, "col": 1}
            }
        ]
        
        historical_kpis = [
            {
                "ticker": "AAPL",
                "period": "2024-Q3",
                "metric": "revenue",
                "value": 115.0,
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 1, "col": 1}
            },
            {
                "ticker": "AAPL",
                "period": "2024-Q3",
                "metric": "eps",
                "value": 1.72,
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 2, "col": 1}
            }
        ]
        
        deltas = normalizer.calculate_deltas(current_kpis, historical_kpis)
        
        assert len(deltas) == 2
        
        revenue_delta = next((d for d in deltas if d["metric"] == "revenue"), None)
        eps_delta = next((d for d in deltas if d["metric"] == "eps"), None)
        
        assert revenue_delta is not None
        assert eps_delta is not None
        
        assert revenue_delta["significance"] == "material"  # > 5%
        assert eps_delta["significance"] == "material"  # > 10%


if __name__ == "__main__":
    pytest.main([__file__])
