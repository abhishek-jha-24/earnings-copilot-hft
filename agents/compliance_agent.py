"""
Compliance agent for processing regulatory documents.
Extracts margin requirements and generates compliance alerts.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from agents.ade_ingest import ade_service
from agents.risk_gate import risk_gate
from services.storage import add_compliance_rule, get_compliance_rules_for_ticker


class ComplianceAgent:
    """Agent for processing compliance-related documents and rules."""
    
    def __init__(self):
        self.supported_doc_types = ["compliance", "regulatory", "margin_update"]
    
    async def process(self, file_path: str, ticker: str, doc_type: str, 
                     effective_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process compliance document and extract rules.
        
        Args:
            file_path: Path to compliance document
            ticker: Ticker symbol (may be None for broad rules)
            doc_type: Type of compliance document
            effective_date: When rules become effective
            
        Returns:
            List of compliance alert dictionaries
        """
        try:
            # Extract compliance rules using ADE
            extracted_rules = await ade_service.extract_compliance_rules(file_path)
            
            if not extracted_rules:
                print(f"No compliance rules extracted from {file_path}")
                return []
            
            alerts = []
            
            for rule_data in extracted_rules:
                # Store the rule
                success = await self._store_compliance_rule(rule_data, effective_date)
                
                if success:
                    # Generate alerts for affected tickers
                    rule_alerts = await self._generate_compliance_alerts(rule_data)
                    alerts.extend(rule_alerts)
            
            return alerts
            
        except Exception as e:
            print(f"Error processing compliance document {file_path}: {e}")
            return []
    
    async def _store_compliance_rule(self, rule_data: Dict[str, Any], 
                                   effective_date: Optional[str] = None) -> bool:
        """Store compliance rule in database."""
        try:
            # Use provided effective date or extract from rule data
            if effective_date:
                rule_data["effective_date"] = effective_date
            elif "effective_date" not in rule_data:
                rule_data["effective_date"] = datetime.utcnow().isoformat()[:10]
            
            success = await add_compliance_rule(
                rule_id=rule_data["rule_id"],
                scope_class=rule_data.get("scope_class"),
                scope_tickers=rule_data.get("scope_tickers", []),
                initial_margin=rule_data["initial_margin"],
                maintenance_margin=rule_data["maintenance_margin"],
                effective_date=rule_data["effective_date"],
                provenance=rule_data["provenance"],
                confidence=rule_data["confidence"]
            )
            
            return success
            
        except Exception as e:
            print(f"Error storing compliance rule: {e}")
            return False
    
    async def _generate_compliance_alerts(self, rule_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate compliance alerts for affected tickers."""
        alerts = []
        
        try:
            affected_tickers = rule_data.get("scope_tickers", [])
            scope_class = rule_data.get("scope_class")
            
            # If no specific tickers, determine from scope class
            if not affected_tickers and scope_class:
                affected_tickers = self._get_tickers_for_scope_class(scope_class)
            
            for ticker in affected_tickers:
                alert = await self._create_compliance_alert(ticker, rule_data)
                if alert:
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            print(f"Error generating compliance alerts: {e}")
            return []
    
    async def _create_compliance_alert(self, ticker: str, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create compliance alert for a specific ticker."""
        try:
            # Get current rules for comparison
            current_rules = await get_compliance_rules_for_ticker(ticker)
            current_rule = current_rules[0] if current_rules else None
            
            # Generate exposure guidance
            exposure_guidance = risk_gate.get_exposure_guidance(ticker, rule_data, current_rule)
            
            # Create alert message
            new_initial = rule_data["initial_margin"]
            new_maintenance = rule_data["maintenance_margin"]
            effective_date = rule_data["effective_date"]
            
            if current_rule:
                old_initial = current_rule["initial_margin"]
                old_maintenance = current_rule["maintenance_margin"]
                
                if new_maintenance > old_maintenance:
                    message = f"Margin requirements increased: maintenance {old_maintenance:.1%} → {new_maintenance:.1%}"
                elif new_maintenance < old_maintenance:
                    message = f"Margin requirements decreased: maintenance {old_maintenance:.1%} → {new_maintenance:.1%}"
                else:
                    message = f"Margin requirements updated: maintenance {new_maintenance:.1%}"
            else:
                message = f"New margin requirements: initial {new_initial:.1%}, maintenance {new_maintenance:.1%}"
            
            # Create citation
            provenance = rule_data.get("provenance", {})
            citation = {
                "doc": provenance.get("doc", ""),
                "page": provenance.get("page", 0),
                "table": provenance.get("table", ""),
                "text": f"Initial margin: {new_initial:.1%}, Maintenance margin: {new_maintenance:.1%}"
            }
            
            alert = {
                "ticker": ticker,
                "message": message,
                "effective_date": effective_date,
                "citations": [citation],
                "exposure_guidance": exposure_guidance,
                "rule_id": rule_data["rule_id"],
                "confidence": rule_data["confidence"]
            }
            
            return alert
            
        except Exception as e:
            print(f"Error creating compliance alert for {ticker}: {e}")
            return None
    
    def _get_tickers_for_scope_class(self, scope_class: str) -> List[str]:
        """Get tickers that belong to a scope class."""
        # In practice, this would query a ticker classification system
        scope_mappings = {
            "TECH-LARGE": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"],
            "TECH-MID": ["CRM", "ADBE", "NFLX", "NVDA"],
            "FINANCE-LARGE": ["JPM", "BAC", "WFC", "GS"],
            "HEALTHCARE": ["JNJ", "PFE", "UNH", "ABBV"],
            "ENERGY": ["XOM", "CVX", "COP", "EOG"]
        }
        
        return scope_mappings.get(scope_class, [])
    
    async def check_compliance_for_signal(self, ticker: str, signal: Dict[str, Any]) -> Optional[str]:
        """
        Check if a signal violates any compliance rules.
        
        Args:
            ticker: Stock ticker symbol
            signal: Trading signal to check
            
        Returns:
            Compliance violation message or None
        """
        try:
            rules = await get_compliance_rules_for_ticker(ticker)
            
            for rule in rules:
                # Check if rule is effective
                effective_date = rule.get("effective_date")
                if effective_date:
                    try:
                        rule_date = datetime.fromisoformat(effective_date).date()
                        if rule_date > datetime.now().date():
                            continue  # Rule not yet effective
                    except ValueError:
                        continue
                
                # Check margin compliance for BUY signals
                if signal.get("action") == "BUY":
                    maintenance_margin = rule.get("maintenance_margin")
                    if maintenance_margin:
                        # Simulate position check (in practice, would query position system)
                        current_exposure = risk_gate._get_simulated_exposure(ticker)
                        
                        if current_exposure >= maintenance_margin * 0.9:  # 90% of limit
                            return f"Near margin limit: {current_exposure:.1%} of {maintenance_margin:.1%} allowed"
            
            return None
            
        except Exception as e:
            print(f"Error checking compliance for {ticker}: {e}")
            return None
    
    async def get_compliance_summary(self, ticker: str) -> Dict[str, Any]:
        """Get compliance summary for a ticker."""
        try:
            rules = await get_compliance_rules_for_ticker(ticker)
            
            summary = {
                "ticker": ticker,
                "active_rules": len(rules),
                "rules": [],
                "current_exposure": risk_gate._get_simulated_exposure(ticker),
                "compliance_status": "compliant"
            }
            
            for rule in rules:
                rule_summary = {
                    "rule_id": rule["rule_id"],
                    "scope_class": rule.get("scope_class"),
                    "initial_margin": rule["initial_margin"],
                    "maintenance_margin": rule["maintenance_margin"],
                    "effective_date": rule["effective_date"],
                    "confidence": rule["confidence"]
                }
                summary["rules"].append(rule_summary)
                
                # Check compliance status
                if summary["current_exposure"] >= rule["maintenance_margin"]:
                    summary["compliance_status"] = "at_risk"
            
            return summary
            
        except Exception as e:
            print(f"Error getting compliance summary for {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}


# Global compliance agent instance
compliance_agent = ComplianceAgent()
