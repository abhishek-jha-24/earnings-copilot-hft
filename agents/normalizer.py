"""
Data normalization and validation agent.
Validates extracted KPI data and marks items needing review.
"""

from typing import List, Dict, Any
from datetime import datetime
import re


class DataNormalizer:
    """Normalizes and validates extracted financial data."""
    
    def __init__(self):
        # Define validation rules for different metrics
        self.validation_rules = {
            "revenue": {
                "min_value": 0,
                "max_value": 1000,  # Billion USD
                "unit": "B",
                "confidence_threshold": 0.85
            },
            "eps": {
                "min_value": -10,
                "max_value": 50,
                "unit": "USD", 
                "confidence_threshold": 0.85
            },
            "gross_margin": {
                "min_value": 0,
                "max_value": 1,
                "unit": "ratio",
                "confidence_threshold": 0.80
            },
            "operating_margin": {
                "min_value": -1,
                "max_value": 1,
                "unit": "ratio",
                "confidence_threshold": 0.80
            },
            "net_margin": {
                "min_value": -1,
                "max_value": 1,
                "unit": "ratio",
                "confidence_threshold": 0.80
            }
        }
    
    def validate_kpi_row(self, kpi_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single KPI row and set needs_review flag.
        
        Args:
            kpi_row: KPI row dictionary
            
        Returns:
            Validated and potentially modified KPI row
        """
        metric = kpi_row.get("metric", "").lower()
        value = kpi_row.get("value")
        confidence = kpi_row.get("confidence", 0)
        
        # Start with original needs_review value
        needs_review = kpi_row.get("needs_review", False)
        review_reasons = []
        
        # Check if metric has validation rules
        if metric in self.validation_rules:
            rules = self.validation_rules[metric]
            
            # Check value range
            if value is not None:
                if value < rules["min_value"] or value > rules["max_value"]:
                    needs_review = True
                    review_reasons.append(f"Value {value} outside expected range [{rules['min_value']}, {rules['max_value']}]")
            
            # Check confidence threshold
            if confidence < rules["confidence_threshold"]:
                needs_review = True
                review_reasons.append(f"Confidence {confidence:.2f} below threshold {rules['confidence_threshold']}")
            
            # Check unit consistency
            expected_unit = rules["unit"]
            actual_unit = kpi_row.get("unit", "")
            if actual_unit != expected_unit:
                needs_review = True
                review_reasons.append(f"Unit mismatch: expected {expected_unit}, got {actual_unit}")
        
        # Check for missing required fields
        required_fields = ["ticker", "metric", "value", "provenance"]
        for field in required_fields:
            if not kpi_row.get(field):
                needs_review = True
                review_reasons.append(f"Missing required field: {field}")
        
        # Validate ticker format (should be uppercase letters)
        ticker = kpi_row.get("ticker", "")
        if ticker and not re.match(r"^[A-Z]{1,5}$", ticker):
            needs_review = True
            review_reasons.append(f"Invalid ticker format: {ticker}")
        
        # Update the row
        kpi_row["needs_review"] = needs_review
        if review_reasons:
            kpi_row["review_reasons"] = review_reasons
        
        return kpi_row
    
    def validate_and_mark(self, kpi_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate a list of KPI rows and mark those needing review.
        
        Args:
            kpi_rows: List of KPI row dictionaries
            
        Returns:
            List of validated KPI rows
        """
        validated_rows = []
        
        for row in kpi_rows:
            validated_row = self.validate_kpi_row(row.copy())
            validated_rows.append(validated_row)
        
        return validated_rows
    
    def normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker symbol to standard format."""
        if not ticker:
            return ""
        
        # Convert to uppercase and remove spaces
        normalized = ticker.upper().strip()
        
        # Remove common suffixes
        suffixes = [".US", ".N", ".O", ".A"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized
    
    def normalize_period(self, period: str) -> str:
        """Normalize period string to standard format."""
        if not period:
            return ""
        
        # Convert to standard format: YYYY-QX or YYYY
        period = period.upper().strip()
        
        # Handle various quarter formats
        quarter_patterns = [
            (r"(\d{4})\s*Q(\d)", r"\1-Q\2"),
            (r"Q(\d)\s*(\d{4})", r"\2-Q\1"),
            (r"(\d{4})\s*QUARTER\s*(\d)", r"\1-Q\2"),
        ]
        
        for pattern, replacement in quarter_patterns:
            match = re.match(pattern, period)
            if match:
                return re.sub(pattern, replacement, period)
        
        # Handle year formats
        if re.match(r"^\d{4}$", period):
            return period
        
        return period
    
    def calculate_deltas(self, current_kpis: List[Dict[str, Any]], 
                        historical_kpis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate year-over-year and quarter-over-quarter deltas.
        
        Args:
            current_kpis: Current period KPIs
            historical_kpis: Historical KPIs for comparison
            
        Returns:
            List of delta calculations
        """
        deltas = []
        
        # Group historical KPIs by ticker and metric
        hist_lookup = {}
        for kpi in historical_kpis:
            key = (kpi["ticker"], kpi["metric"])
            if key not in hist_lookup:
                hist_lookup[key] = []
            hist_lookup[key].append(kpi)
        
        for current_kpi in current_kpis:
            ticker = current_kpi["ticker"]
            metric = current_kpi["metric"]
            current_value = current_kpi["value"]
            current_period = current_kpi["period"]
            
            key = (ticker, metric)
            if key in hist_lookup:
                # Find comparable periods
                for hist_kpi in hist_lookup[key]:
                    hist_period = hist_kpi["period"]
                    hist_value = hist_kpi["value"]
                    
                    if hist_value and hist_value != 0:
                        delta_abs = current_value - hist_value
                        delta_pct = delta_abs / hist_value
                        
                        # Determine if this is YoY or QoQ comparison
                        comparison_type = self._determine_comparison_type(current_period, hist_period)
                        
                        if comparison_type:
                            delta = {
                                "ticker": ticker,
                                "period": current_period,
                                "metric": metric,
                                "current_value": current_value,
                                "previous_value": hist_value,
                                "previous_period": hist_period,
                                "delta_abs": delta_abs,
                                "delta_pct": delta_pct,
                                "comparison_type": comparison_type,
                                "significance": self._determine_significance(delta_pct, metric),
                                "provenance": current_kpi["provenance"]
                            }
                            deltas.append(delta)
        
        return deltas
    
    def _determine_comparison_type(self, current_period: str, hist_period: str) -> str:
        """Determine if comparison is YoY or QoQ."""
        # Simple logic - in practice would be more sophisticated
        if "Q" in current_period and "Q" in hist_period:
            # Extract years and quarters
            try:
                curr_year = int(current_period.split("-")[0])
                hist_year = int(hist_period.split("-")[0])
                
                if curr_year - hist_year == 1:
                    return "yoy"
                elif curr_year == hist_year:
                    return "qoq"
            except:
                pass
        
        return "other"
    
    def _determine_significance(self, delta_pct: float, metric: str) -> str:
        """Determine if delta is material, minor, or negligible."""
        abs_delta = abs(delta_pct)
        
        # Define thresholds by metric type
        thresholds = {
            "revenue": {"material": 0.05, "minor": 0.02},
            "eps": {"material": 0.10, "minor": 0.05},
            "margin": {"material": 0.03, "minor": 0.01}
        }
        
        # Determine metric category
        metric_category = "revenue"
        if "eps" in metric.lower():
            metric_category = "eps"
        elif "margin" in metric.lower():
            metric_category = "margin"
        
        thresh = thresholds[metric_category]
        
        if abs_delta >= thresh["material"]:
            return "material"
        elif abs_delta >= thresh["minor"]:
            return "minor"
        else:
            return "negligible"


# Global normalizer instance
normalizer = DataNormalizer()
