"""
Benchmark and consensus data management.
Loads consensus expectations and calculates surprises.
"""

import pandas as pd
from typing import Dict, Optional, List, Any
import os


class BenchmarkService:
    """Service for managing consensus benchmarks and surprise calculations."""
    
    def __init__(self):
        self.consensus_data = {}
        self._load_consensus_data()
    
    def _load_consensus_data(self):
        """Load consensus data from CSV file."""
        consensus_file = "data/consensus_seed.csv"
        
        if os.path.exists(consensus_file):
            try:
                df = pd.read_csv(consensus_file)
                
                # Convert to nested dictionary structure
                for _, row in df.iterrows():
                    ticker = row["ticker"]
                    period = row["period"]
                    metric = row["metric"]
                    consensus_value = row["consensus_value"]
                    unit = row["unit"]
                    
                    if ticker not in self.consensus_data:
                        self.consensus_data[ticker] = {}
                    if period not in self.consensus_data[ticker]:
                        self.consensus_data[ticker][period] = {}
                    
                    self.consensus_data[ticker][period][metric] = {
                        "consensus": consensus_value,
                        "unit": unit
                    }
                
                print(f"Loaded consensus data for {len(self.consensus_data)} tickers")
                
            except Exception as e:
                print(f"Error loading consensus data: {e}")
                self._create_default_consensus()
        else:
            print("Consensus file not found, creating default data")
            self._create_default_consensus()
    
    def _create_default_consensus(self):
        """Create default consensus data for major tickers."""
        default_data = {
            "AAPL": {
                "2025-Q3": {
                    "revenue": {"consensus": 120.0, "unit": "B"},
                    "eps": {"consensus": 1.80, "unit": "USD"},
                    "gross_margin": {"consensus": 0.45, "unit": "ratio"}
                }
            },
            "MSFT": {
                "2025-Q3": {
                    "revenue": {"consensus": 65.0, "unit": "B"},
                    "eps": {"consensus": 2.95, "unit": "USD"},
                    "gross_margin": {"consensus": 0.68, "unit": "ratio"}
                }
            },
            "GOOGL": {
                "2025-Q3": {
                    "revenue": {"consensus": 85.0, "unit": "B"},
                    "eps": {"consensus": 1.45, "unit": "USD"},
                    "gross_margin": {"consensus": 0.56, "unit": "ratio"}
                }
            }
        }
        self.consensus_data = default_data
    
    def consensus_for(self, ticker: str, period: str, metric: str) -> Optional[float]:
        """
        Get consensus expectation for a specific ticker, period, and metric.
        
        Args:
            ticker: Stock ticker symbol
            period: Financial period (e.g., "2025-Q3")
            metric: Metric name (e.g., "revenue", "eps")
            
        Returns:
            Consensus value or None if not found
        """
        try:
            return self.consensus_data.get(ticker, {}).get(period, {}).get(metric, {}).get("consensus")
        except Exception:
            return None
    
    def calculate_surprise(self, ticker: str, period: str, metric: str, actual_value: float) -> Optional[float]:
        """
        Calculate surprise (actual vs consensus) as percentage.
        
        Args:
            ticker: Stock ticker symbol
            period: Financial period
            metric: Metric name
            actual_value: Actual reported value
            
        Returns:
            Surprise percentage or None if consensus not available
        """
        consensus = self.consensus_for(ticker, period, metric)
        
        if consensus is None or consensus == 0:
            return None
        
        surprise = (actual_value - consensus) / consensus
        return surprise
    
    def enrich_kpi_with_consensus(self, kpi_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a KPI row with consensus and surprise data.
        
        Args:
            kpi_row: KPI row dictionary
            
        Returns:
            Enriched KPI row
        """
        ticker = kpi_row.get("ticker")
        period = kpi_row.get("period")
        metric = kpi_row.get("metric")
        actual_value = kpi_row.get("value")
        
        if all([ticker, period, metric, actual_value is not None]):
            consensus = self.consensus_for(ticker, period, metric)
            if consensus is not None:
                surprise = self.calculate_surprise(ticker, period, metric, actual_value)
                
                kpi_row["consensus"] = consensus
                kpi_row["surprise"] = surprise
        
        return kpi_row
    
    def enrich_kpi_list(self, kpi_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich a list of KPI rows with consensus data.
        
        Args:
            kpi_rows: List of KPI row dictionaries
            
        Returns:
            List of enriched KPI rows
        """
        return [self.enrich_kpi_with_consensus(row.copy()) for row in kpi_rows]
    
    def get_all_consensus_for_ticker(self, ticker: str, period: str) -> Dict[str, Any]:
        """
        Get all consensus data for a ticker and period.
        
        Args:
            ticker: Stock ticker symbol
            period: Financial period
            
        Returns:
            Dictionary of consensus data by metric
        """
        return self.consensus_data.get(ticker, {}).get(period, {})
    
    def add_consensus_data(self, ticker: str, period: str, metric: str, 
                          consensus_value: float, unit: str) -> bool:
        """
        Add new consensus data point.
        
        Args:
            ticker: Stock ticker symbol
            period: Financial period
            metric: Metric name
            consensus_value: Consensus expectation
            unit: Value unit
            
        Returns:
            Success status
        """
        try:
            if ticker not in self.consensus_data:
                self.consensus_data[ticker] = {}
            if period not in self.consensus_data[ticker]:
                self.consensus_data[ticker][period] = {}
            
            self.consensus_data[ticker][period][metric] = {
                "consensus": consensus_value,
                "unit": unit
            }
            
            return True
            
        except Exception as e:
            print(f"Error adding consensus data: {e}")
            return False
    
    def get_surprise_summary(self, ticker: str, period: str) -> Dict[str, Any]:
        """
        Get surprise summary for a ticker and period.
        
        Args:
            ticker: Stock ticker symbol
            period: Financial period
            
        Returns:
            Summary of surprises
        """
        summary = {
            "ticker": ticker,
            "period": period,
            "surprises": {},
            "beat_count": 0,
            "miss_count": 0,
            "in_line_count": 0
        }
        
        consensus_data = self.get_all_consensus_for_ticker(ticker, period)
        
        for metric in consensus_data:
            # This would need actual values to calculate surprises
            # For now, just return the structure
            summary["surprises"][metric] = {
                "consensus": consensus_data[metric]["consensus"],
                "actual": None,
                "surprise": None,
                "beat": None
            }
        
        return summary


# Global benchmark service instance
benchmark_service = BenchmarkService()
