"""
Risk gate agent.
Gates signals based on data quality and compliance rules.
"""

from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, date
from services.storage import get_compliance_rules_for_ticker


class RiskGate:
    """Risk management gate for trading signals."""
    
    def __init__(self):
        # Define risk thresholds
        self.risk_thresholds = {
            "min_confidence": 0.70,
            "min_data_quality": 0.80,
            "max_needs_review_ratio": 0.20,
            "margin_breach_threshold": 0.05  # 5% buffer above maintenance margin
        }
    
    async def gate(self, signal: Dict[str, Any], kpi_rows: List[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Gate a trading signal based on risk criteria.
        
        Args:
            signal: Signal dictionary from signal agent
            kpi_rows: Optional KPI rows for additional validation
            
        Returns:
            Tuple of (is_approved, block_reason)
        """
        try:
            ticker = signal.get("ticker")
            confidence = signal.get("confidence", 0.0)
            
            # Check minimum confidence threshold
            if confidence < self.risk_thresholds["min_confidence"]:
                return False, f"low_confidence: {confidence:.2f} < {self.risk_thresholds['min_confidence']}"
            
            # Check data quality if KPI rows provided
            if kpi_rows:
                data_quality_check = self._check_data_quality(kpi_rows)
                if not data_quality_check[0]:
                    return False, data_quality_check[1]
            
            # Check compliance rules
            compliance_check = await self._check_compliance_rules(ticker, signal)
            if not compliance_check[0]:
                return False, compliance_check[1]
            
            # Check for any explicit blocking reasons in the signal
            if signal.get("blocked_reason"):
                return False, signal["blocked_reason"]
            
            # All checks passed
            return True, None
            
        except Exception as e:
            return False, f"risk_gate_error: {str(e)}"
    
    def _check_data_quality(self, kpi_rows: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """Check data quality of KPI rows."""
        if not kpi_rows:
            return False, "no_kpi_data"
        
        # Calculate quality metrics
        total_rows = len(kpi_rows)
        needs_review_count = sum(1 for row in kpi_rows if row.get("needs_review", False))
        low_confidence_count = sum(1 for row in kpi_rows if row.get("confidence", 1.0) < self.risk_thresholds["min_data_quality"])
        
        # Check needs review ratio
        needs_review_ratio = needs_review_count / total_rows
        if needs_review_ratio > self.risk_thresholds["max_needs_review_ratio"]:
            return False, f"high_review_ratio: {needs_review_ratio:.1%} > {self.risk_thresholds['max_needs_review_ratio']:.1%}"
        
        # Check low confidence ratio
        low_confidence_ratio = low_confidence_count / total_rows
        if low_confidence_ratio > self.risk_thresholds["max_needs_review_ratio"]:
            return False, f"low_data_quality: {low_confidence_ratio:.1%} of data below quality threshold"
        
        return True, None
    
    async def _check_compliance_rules(self, ticker: str, signal: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check compliance rules for ticker."""
        try:
            # Get applicable compliance rules
            rules = await get_compliance_rules_for_ticker(ticker)
            
            if not rules:
                return True, None  # No rules to check
            
            # Check each rule
            for rule in rules:
                effective_date_str = rule.get("effective_date")
                if effective_date_str:
                    try:
                        effective_date = datetime.fromisoformat(effective_date_str).date()
                        today = date.today()
                        
                        # Only check rules that are effective
                        if effective_date <= today:
                            rule_check = self._check_individual_rule(ticker, signal, rule)
                            if not rule_check[0]:
                                return rule_check
                    except ValueError:
                        # Skip rules with invalid dates
                        continue
            
            return True, None
            
        except Exception as e:
            return False, f"compliance_check_error: {str(e)}"
    
    def _check_individual_rule(self, ticker: str, signal: Dict[str, Any], rule: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check an individual compliance rule."""
        # Check if rule applies to this ticker
        scope_tickers = rule.get("scope_tickers", [])
        scope_class = rule.get("scope_class")
        
        if scope_tickers and ticker not in scope_tickers:
            return True, None  # Rule doesn't apply
        
        # For now, implement basic margin checks
        # In practice, this would be more sophisticated
        maintenance_margin = rule.get("maintenance_margin")
        if maintenance_margin:
            # Simulate current position exposure (in practice, would query position management system)
            current_exposure = self._get_simulated_exposure(ticker)
            
            # Check if signal would breach margin requirements
            if signal.get("action") == "BUY" and current_exposure > (maintenance_margin + self.risk_thresholds["margin_breach_threshold"]):
                return False, f"margin_breach_risk: exposure {current_exposure:.1%} near limit {maintenance_margin:.1%}"
        
        return True, None
    
    def _get_simulated_exposure(self, ticker: str) -> float:
        """Simulate current position exposure for a ticker."""
        # In practice, this would query the position management system
        # For now, return a simulated value
        ticker_exposures = {
            "AAPL": 0.15,
            "MSFT": 0.12,
            "GOOGL": 0.18,
            "AMZN": 0.10
        }
        return ticker_exposures.get(ticker, 0.05)
    
    def get_exposure_guidance(self, ticker: str, new_rule: Dict[str, Any], current_rule: Dict[str, Any] = None) -> Optional[str]:
        """
        Generate exposure guidance when compliance rules change.
        
        Args:
            ticker: Stock ticker symbol
            new_rule: New compliance rule
            current_rule: Previous compliance rule (if any)
            
        Returns:
            Exposure guidance string or None
        """
        try:
            current_exposure = self._get_simulated_exposure(ticker)
            new_maintenance_margin = new_rule.get("maintenance_margin")
            
            if not new_maintenance_margin:
                return None
            
            # Calculate recommended exposure change
            if current_rule:
                old_maintenance_margin = current_rule.get("maintenance_margin", new_maintenance_margin)
                margin_change = new_maintenance_margin - old_maintenance_margin
                
                if abs(margin_change) > 0.01:  # 1% threshold for guidance
                    if margin_change > 0:
                        # Margin increased - recommend reducing exposure
                        reduction_pct = margin_change / old_maintenance_margin
                        return f"Reduce exposure by ~{reduction_pct:.0%} due to increased margin requirements"
                    else:
                        # Margin decreased - can increase exposure
                        increase_pct = abs(margin_change) / new_maintenance_margin
                        return f"Can increase exposure by ~{increase_pct:.0%} due to reduced margin requirements"
            else:
                # New rule - check if current exposure is compliant
                if current_exposure > new_maintenance_margin:
                    reduction_needed = (current_exposure - new_maintenance_margin) / current_exposure
                    return f"Reduce exposure by ~{reduction_needed:.0%} to comply with new margin requirements"
            
            return None
            
        except Exception as e:
            print(f"Error generating exposure guidance: {e}")
            return None
    
    def validate_signal_consistency(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate consistency across multiple signals for the same ticker.
        
        Args:
            signals: List of signals to validate
            
        Returns:
            List of validated signals with potential adjustments
        """
        if len(signals) <= 1:
            return signals
        
        # Group by ticker
        ticker_signals = {}
        for signal in signals:
            ticker = signal.get("ticker")
            if ticker:
                if ticker not in ticker_signals:
                    ticker_signals[ticker] = []
                ticker_signals[ticker].append(signal)
        
        validated_signals = []
        
        for ticker, ticker_signal_list in ticker_signals.items():
            if len(ticker_signal_list) == 1:
                validated_signals.extend(ticker_signal_list)
                continue
            
            # Check for conflicting signals
            actions = [s.get("action") for s in ticker_signal_list]
            if len(set(actions)) > 1:
                # Conflicting actions - choose highest confidence or default to HOLD
                best_signal = max(ticker_signal_list, key=lambda s: s.get("confidence", 0))
                best_signal["reasons"].append("Conflicting signals resolved by confidence")
                validated_signals.append(best_signal)
            else:
                # Consistent actions - take the highest confidence
                best_signal = max(ticker_signal_list, key=lambda s: s.get("confidence", 0))
                validated_signals.append(best_signal)
        
        return validated_signals


# Global risk gate instance
risk_gate = RiskGate()
