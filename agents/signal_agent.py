"""
Signal generation agent.
Makes BUY/SELL/HOLD decisions based on KPI deltas and consensus surprises.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import math

from agents.pathway_pipeline import pathway_service
from agents.benchmarks import benchmark_service


class SignalAgent:
    """Agent that generates trading signals based on financial data analysis."""
    
    def __init__(self):
        # Define signal generation rules
        self.signal_rules = {
            "eps": {
                "weight": 0.4,
                "surprise_threshold": {"strong_beat": 0.05, "beat": 0.02, "miss": -0.02, "strong_miss": -0.05}
            },
            "revenue": {
                "weight": 0.3,
                "surprise_threshold": {"strong_beat": 0.03, "beat": 0.01, "miss": -0.01, "strong_miss": -0.03}
            },
            "gross_margin": {
                "weight": 0.2,
                "delta_threshold": {"improvement": 0.02, "deterioration": -0.02}
            },
            "operating_margin": {
                "weight": 0.1,
                "delta_threshold": {"improvement": 0.02, "deterioration": -0.02}
            }
        }
        
        self.confidence_factors = {
            "data_quality": 0.3,
            "signal_strength": 0.4,
            "consistency": 0.3
        }
    
    async def decide(self, ticker: str, period: str) -> Dict[str, Any]:
        """
        Generate trading signal for a ticker and period.
        
        Args:
            ticker: Stock ticker symbol
            period: Financial period
            
        Returns:
            Signal dictionary with action, confidence, reasons, and citations
        """
        try:
            # Get latest KPIs and deltas
            latest_kpis = await pathway_service.get_latest_kpis(ticker)
            deltas = await pathway_service.get_deltas(ticker, period)
            
            if not latest_kpis:
                return self._create_no_data_signal(ticker, period)
            
            # Analyze each metric
            metric_scores = {}
            reasons = []
            citations = []
            data_quality_scores = []
            
            for metric, kpi_data in latest_kpis.items():
                if metric in self.signal_rules:
                    score, reason, citation, quality = await self._analyze_metric(
                        ticker, period, metric, kpi_data, deltas
                    )
                    
                    metric_scores[metric] = score
                    if reason:
                        reasons.append(reason)
                    if citation:
                        citations.append(citation)
                    
                    data_quality_scores.append(quality)
            
            # Calculate overall signal
            overall_score = self._calculate_weighted_score(metric_scores)
            action = self._score_to_action(overall_score)
            confidence = self._calculate_confidence(overall_score, metric_scores, data_quality_scores)
            
            # Create signal response
            signal = {
                "ticker": ticker,
                "period": period,
                "action": action,
                "confidence": confidence,
                "reasons": reasons[:5],  # Limit to top 5 reasons
                "citations": citations[:3],  # Limit to top 3 citations
                "blocked_reason": None,
                "generated_at": datetime.utcnow().isoformat(),
                "metric_scores": metric_scores,
                "overall_score": overall_score
            }
            
            return signal
            
        except Exception as e:
            print(f"Error generating signal for {ticker}: {e}")
            return self._create_error_signal(ticker, period, str(e))
    
    async def _analyze_metric(self, ticker: str, period: str, metric: str, 
                            kpi_data: Dict[str, Any], deltas: List[Dict[str, Any]]) -> Tuple[float, str, Dict[str, Any], float]:
        """
        Analyze a specific metric and return score, reason, citation, and quality.
        
        Returns:
            Tuple of (score, reason, citation, data_quality)
        """
        score = 0.0
        reason = ""
        citation = {}
        data_quality = kpi_data.get("confidence", 0.5)
        
        value = kpi_data.get("value")
        consensus = kpi_data.get("consensus")
        surprise = kpi_data.get("surprise")
        
        # Create citation
        provenance = kpi_data.get("provenance", {})
        citation = {
            "doc": provenance.get("doc", ""),
            "page": provenance.get("page", 0),
            "table": provenance.get("table", ""),
            "text": f"{metric.title()}: {value} {kpi_data.get('unit', '')}"
        }
        
        # Analyze based on metric type
        if metric in ["eps", "revenue"]:
            score, reason = self._analyze_earnings_metric(metric, value, consensus, surprise)
        elif "margin" in metric:
            score, reason = self._analyze_margin_metric(metric, kpi_data, deltas)
        
        return score, reason, citation, data_quality
    
    def _analyze_earnings_metric(self, metric: str, value: float, consensus: Optional[float], 
                               surprise: Optional[float]) -> Tuple[float, str]:
        """Analyze EPS or Revenue metric."""
        if surprise is None or consensus is None:
            return 0.0, f"{metric.upper()} data incomplete"
        
        thresholds = self.signal_rules[metric]["surprise_threshold"]
        
        if surprise >= thresholds["strong_beat"]:
            return 1.0, f"{metric.upper()} strong beat vs consensus ({surprise:.1%})"
        elif surprise >= thresholds["beat"]:
            return 0.5, f"{metric.upper()} beat vs consensus ({surprise:.1%})"
        elif surprise <= thresholds["strong_miss"]:
            return -1.0, f"{metric.upper()} strong miss vs consensus ({surprise:.1%})"
        elif surprise <= thresholds["miss"]:
            return -0.5, f"{metric.upper()} miss vs consensus ({surprise:.1%})"
        else:
            return 0.0, f"{metric.upper()} in line with consensus"
    
    def _analyze_margin_metric(self, metric: str, kpi_data: Dict[str, Any], 
                             deltas: List[Dict[str, Any]]) -> Tuple[float, str]:
        """Analyze margin metrics using deltas."""
        # Find delta for this metric
        metric_delta = None
        for delta in deltas:
            if delta["metric"] == metric:
                metric_delta = delta
                break
        
        if not metric_delta:
            return 0.0, f"{metric.title()} delta not available"
        
        delta_pct = metric_delta["delta_pct"]
        thresholds = self.signal_rules.get(metric, {}).get("delta_threshold", {})
        
        improvement_threshold = thresholds.get("improvement", 0.02)
        deterioration_threshold = thresholds.get("deterioration", -0.02)
        
        if delta_pct >= improvement_threshold:
            return 0.5, f"{metric.title()} improved by {delta_pct:.1%}"
        elif delta_pct <= deterioration_threshold:
            return -0.5, f"{metric.title()} declined by {delta_pct:.1%}"
        else:
            return 0.0, f"{metric.title()} stable"
    
    def _calculate_weighted_score(self, metric_scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        total_score = 0.0
        total_weight = 0.0
        
        for metric, score in metric_scores.items():
            if metric in self.signal_rules:
                weight = self.signal_rules[metric]["weight"]
                total_score += score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return total_score / total_weight
    
    def _score_to_action(self, score: float) -> str:
        """Convert numeric score to action."""
        if score >= 0.3:
            return "BUY"
        elif score <= -0.3:
            return "SELL"
        else:
            return "HOLD"
    
    def _calculate_confidence(self, overall_score: float, metric_scores: Dict[str, float], 
                            data_quality_scores: List[float]) -> float:
        """Calculate confidence in the signal."""
        # Signal strength factor
        signal_strength = min(abs(overall_score), 1.0)
        
        # Data quality factor
        avg_data_quality = sum(data_quality_scores) / len(data_quality_scores) if data_quality_scores else 0.5
        
        # Consistency factor (how aligned are the metrics)
        if len(metric_scores) > 1:
            scores = list(metric_scores.values())
            score_variance = sum((s - overall_score) ** 2 for s in scores) / len(scores)
            consistency = max(0, 1 - score_variance)
        else:
            consistency = 1.0
        
        # Weighted confidence
        confidence = (
            signal_strength * self.confidence_factors["signal_strength"] +
            avg_data_quality * self.confidence_factors["data_quality"] +
            consistency * self.confidence_factors["consistency"]
        )
        
        return min(max(confidence, 0.0), 1.0)
    
    def _create_no_data_signal(self, ticker: str, period: str) -> Dict[str, Any]:
        """Create signal for case with no data."""
        return {
            "ticker": ticker,
            "period": period,
            "action": "HOLD",
            "confidence": 0.0,
            "reasons": ["Insufficient data for analysis"],
            "citations": [],
            "blocked_reason": "no_data",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _create_error_signal(self, ticker: str, period: str, error: str) -> Dict[str, Any]:
        """Create signal for error case."""
        return {
            "ticker": ticker,
            "period": period,
            "action": "HOLD",
            "confidence": 0.0,
            "reasons": [f"Analysis error: {error}"],
            "citations": [],
            "blocked_reason": "analysis_error",
            "generated_at": datetime.utcnow().isoformat()
        }


# Global signal agent instance
signal_agent = SignalAgent()
