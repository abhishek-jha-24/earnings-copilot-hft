"""
Tests for confidence scoring and risk gating.
"""

import pytest
import asyncio
from datetime import datetime
from agents.normalizer import normalizer
from agents.signal_agent import signal_agent
from agents.risk_gate import risk_gate


class TestConfidence:
    """Test confidence scoring and risk management."""
    
    @pytest.fixture
    def high_confidence_kpi(self):
        """High confidence KPI data."""
        return {
            "ticker": "AAPL",
            "period": "2025-Q3",
            "metric": "revenue",
            "value": 123.45,
            "unit": "B",
            "confidence": 0.95,
            "needs_review": False,
            "provenance": {
                "doc": "aapl_10q_2025_q3.pdf",
                "page": 15,
                "table": "income_statement",
                "row": 1,
                "col": 2
            }
        }
    
    @pytest.fixture
    def low_confidence_kpi(self):
        """Low confidence KPI data."""
        return {
            "ticker": "AAPL",
            "period": "2025-Q3",
            "metric": "eps",
            "value": 1.72,
            "unit": "USD",
            "confidence": 0.65,  # Below threshold
            "needs_review": True,
            "provenance": {
                "doc": "aapl_10q_2025_q3.pdf",
                "page": 15,
                "table": "income_statement",
                "row": 8,
                "col": 3
            }
        }
    
    def test_validation_confidence_threshold(self, high_confidence_kpi, low_confidence_kpi):
        """Test confidence threshold validation."""
        # High confidence should pass validation
        validated_high = normalizer.validate_kpi_row(high_confidence_kpi.copy())
        assert not validated_high["needs_review"]
        
        # Low confidence should be marked for review
        validated_low = normalizer.validate_kpi_row(low_confidence_kpi.copy())
        assert validated_low["needs_review"]
        assert "Confidence" in str(validated_low.get("review_reasons", []))
    
    def test_data_quality_checks(self):
        """Test data quality validation rules."""
        # Valid revenue KPI
        valid_kpi = {
            "ticker": "AAPL",
            "metric": "revenue",
            "value": 123.45,
            "unit": "B",
            "confidence": 0.90,
            "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 1, "col": 1}
        }
        
        validated = normalizer.validate_kpi_row(valid_kpi)
        assert not validated["needs_review"]
        
        # Invalid revenue (too high)
        invalid_kpi = valid_kpi.copy()
        invalid_kpi["value"] = 2000.0  # > 1000B limit
        
        validated = normalizer.validate_kpi_row(invalid_kpi)
        assert validated["needs_review"]
        assert any("outside expected range" in reason for reason in validated.get("review_reasons", []))
        
        # Invalid EPS (too low)
        invalid_eps = {
            "ticker": "AAPL",
            "metric": "eps",
            "value": -15.0,  # < -10 limit
            "unit": "USD",
            "confidence": 0.90,
            "provenance": {"doc": "test.pdf", "page": 1, "table": "test", "row": 1, "col": 1}
        }
        
        validated = normalizer.validate_kpi_row(invalid_eps)
        assert validated["needs_review"]
    
    @pytest.mark.asyncio
    async def test_signal_confidence_calculation(self):
        """Test signal confidence calculation."""
        # Create a signal with mixed metric scores
        ticker = "AAPL"
        period = "2025-Q3"
        
        # Mock pathway service to return test data
        import unittest.mock
        
        mock_kpis = {
            "revenue": {
                "value": 123.45,
                "consensus": 120.0,
                "surprise": 0.0288,
                "confidence": 0.95,
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test"}
            },
            "eps": {
                "value": 1.85,
                "consensus": 1.80,
                "surprise": 0.028,
                "confidence": 0.92,
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test"}
            }
        }
        
        mock_deltas = [
            {
                "metric": "gross_margin",
                "delta_pct": 0.03,  # 3% improvement
                "provenance": {"doc": "test.pdf", "page": 1, "table": "test"}
            }
        ]
        
        with unittest.mock.patch('agents.pathway_pipeline.pathway_service.get_latest_kpis', return_value=mock_kpis):
            with unittest.mock.patch('agents.pathway_pipeline.pathway_service.get_deltas', return_value=mock_deltas):
                signal = await signal_agent.decide(ticker, period)
        
        # Should have high confidence due to good data quality and consistent signals
        assert signal["confidence"] > 0.7
        assert signal["action"] == "BUY"  # Positive surprises should lead to BUY
        assert len(signal["reasons"]) > 0
    
    @pytest.mark.asyncio
    async def test_risk_gate_confidence_threshold(self, high_confidence_kpi, low_confidence_kpi):
        """Test risk gate confidence threshold."""
        # High confidence signal should pass
        high_conf_signal = {
            "ticker": "AAPL",
            "period": "2025-Q3",
            "action": "BUY",
            "confidence": 0.85,
            "reasons": ["Strong earnings beat"],
            "citations": []
        }
        
        approved, reason = await risk_gate.gate(high_conf_signal, [high_confidence_kpi])
        assert approved
        assert reason is None
        
        # Low confidence signal should be blocked
        low_conf_signal = high_conf_signal.copy()
        low_conf_signal["confidence"] = 0.60
        
        approved, reason = await risk_gate.gate(low_conf_signal, [low_confidence_kpi])
        assert not approved
        assert "low_confidence" in reason
    
    @pytest.mark.asyncio
    async def test_risk_gate_data_quality(self, low_confidence_kpi):
        """Test risk gate data quality checks."""
        signal = {
            "ticker": "AAPL",
            "confidence": 0.80,
            "action": "BUY",
            "reasons": [],
            "citations": []
        }
        
        # Multiple low-quality KPIs should be blocked
        low_quality_kpis = [low_confidence_kpi] * 5  # 100% needs review
        
        approved, reason = await risk_gate.gate(signal, low_quality_kpis)
        assert not approved
        assert "review_ratio" in reason or "data_quality" in reason
    
    def test_confidence_factors_weighting(self):
        """Test confidence calculation with different factor weights."""
        # Test signal strength factor
        metric_scores = {"revenue": 1.0, "eps": 0.8}  # Strong positive signals
        data_quality_scores = [0.95, 0.90]  # High quality data
        
        confidence = signal_agent._calculate_confidence(0.9, metric_scores, data_quality_scores)
        assert confidence > 0.85  # Should be high
        
        # Test with conflicting signals (low consistency)
        conflicting_scores = {"revenue": 1.0, "eps": -0.8}  # Mixed signals
        
        confidence = signal_agent._calculate_confidence(0.1, conflicting_scores, data_quality_scores)
        assert confidence < 0.7  # Should be lower due to inconsistency
    
    def test_needs_review_ratio_calculation(self):
        """Test needs_review ratio calculation in risk gate."""
        # Create mixed quality KPIs
        kpis = []
        for i in range(10):
            kpi = {
                "ticker": "AAPL",
                "metric": f"metric_{i}",
                "confidence": 0.95 if i < 8 else 0.65,  # 20% low confidence
                "needs_review": i >= 8
            }
            kpis.append(kpi)
        
        # Should pass (20% = threshold)
        quality_check = risk_gate._check_data_quality(kpis)
        assert quality_check[0]  # Should pass at exactly 20%
        
        # Add one more low-quality KPI (>20%)
        kpis.append({
            "ticker": "AAPL",
            "metric": "metric_10",
            "confidence": 0.60,
            "needs_review": True
        })
        
        quality_check = risk_gate._check_data_quality(kpis)
        assert not quality_check[0]  # Should fail at >20%
        assert "review_ratio" in quality_check[1]
    
    def test_signal_consistency_validation(self):
        """Test signal consistency across multiple signals."""
        # Consistent signals
        consistent_signals = [
            {"ticker": "AAPL", "action": "BUY", "confidence": 0.85},
            {"ticker": "AAPL", "action": "BUY", "confidence": 0.80},
            {"ticker": "MSFT", "action": "SELL", "confidence": 0.75}
        ]
        
        validated = risk_gate.validate_signal_consistency(consistent_signals)
        assert len(validated) == 2  # One per ticker
        assert validated[0]["confidence"] == 0.85  # Higher confidence chosen
        
        # Conflicting signals for same ticker
        conflicting_signals = [
            {"ticker": "AAPL", "action": "BUY", "confidence": 0.70, "reasons": []},
            {"ticker": "AAPL", "action": "SELL", "confidence": 0.85, "reasons": []}
        ]
        
        validated = risk_gate.validate_signal_consistency(conflicting_signals)
        assert len(validated) == 1
        assert validated[0]["action"] == "SELL"  # Higher confidence wins
        assert "Conflicting signals resolved" in validated[0]["reasons"][0]


if __name__ == "__main__":
    pytest.main([__file__])
