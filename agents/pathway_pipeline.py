"""
Pathway integration for live memory/index and feature store.
Manages hybrid BM25 + vector search and KPI data storage.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MockPathwayPipeline:
    """
    Mock Pathway pipeline for development.
    In production, this would integrate with actual Pathway service.
    """
    
    def __init__(self):
        self.kpi_data = {}  # ticker -> period -> metric -> data
        self.document_index = {}  # doc_id -> content chunks
        self.vector_index = None
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.search_corpus = []
        self.search_metadata = []
    
    async def upsert_kpi_rows(self, kpi_rows: List[Dict[str, Any]]) -> bool:
        """
        Upsert KPI rows into the feature store.
        
        Args:
            kpi_rows: List of normalized KPI rows
            
        Returns:
            Success status
        """
        try:
            for row in kpi_rows:
                ticker = row["ticker"]
                period = row["period"]
                metric = row["metric"]
                
                # Initialize nested structure
                if ticker not in self.kpi_data:
                    self.kpi_data[ticker] = {}
                if period not in self.kpi_data[ticker]:
                    self.kpi_data[ticker][period] = {}
                
                # Store the KPI data
                self.kpi_data[ticker][period][metric] = row
                
                # Add to search corpus if it has textual content
                search_text = f"{ticker} {period} {metric} {row.get('value', '')} {row.get('unit', '')}"
                self.search_corpus.append(search_text)
                self.search_metadata.append({
                    "ticker": ticker,
                    "period": period,
                    "metric": metric,
                    "doc": row["provenance"]["doc"],
                    "page": row["provenance"]["page"],
                    "table": row["provenance"]["table"]
                })
            
            # Rebuild vector index
            await self._rebuild_vector_index()
            return True
            
        except Exception as e:
            print(f"Error upserting KPI rows: {e}")
            return False
    
    async def get_kpi(self, ticker: str, metric: str, period: str) -> Optional[Dict[str, Any]]:
        """Get specific KPI value."""
        try:
            return self.kpi_data.get(ticker, {}).get(period, {}).get(metric)
        except Exception as e:
            print(f"Error getting KPI: {e}")
            return None
    
    async def get_latest_kpis(self, ticker: str) -> Dict[str, Any]:
        """Get latest KPIs for a ticker."""
        if ticker not in self.kpi_data:
            return {}
        
        # Find the most recent period
        periods = list(self.kpi_data[ticker].keys())
        if not periods:
            return {}
        
        # Sort periods (simple string sort, in practice would be more sophisticated)
        latest_period = sorted(periods)[-1]
        return self.kpi_data[ticker][latest_period]
    
    async def get_deltas(self, ticker: str, period: str) -> List[Dict[str, Any]]:
        """Calculate deltas for a ticker and period."""
        deltas = []
        
        if ticker not in self.kpi_data:
            return deltas
        
        current_data = self.kpi_data[ticker].get(period, {})
        
        # Find previous periods for comparison
        periods = sorted(self.kpi_data[ticker].keys())
        current_idx = periods.index(period) if period in periods else -1
        
        if current_idx > 0:
            prev_period = periods[current_idx - 1]
            prev_data = self.kpi_data[ticker][prev_period]
            
            # Calculate deltas for common metrics
            for metric in current_data:
                if metric in prev_data:
                    current_val = current_data[metric]["value"]
                    prev_val = prev_data[metric]["value"]
                    
                    if prev_val and prev_val != 0:
                        delta_abs = current_val - prev_val
                        delta_pct = delta_abs / prev_val
                        
                        delta = {
                            "ticker": ticker,
                            "period": period,
                            "metric": metric,
                            "current_value": current_val,
                            "previous_value": prev_val,
                            "previous_period": prev_period,
                            "delta_abs": delta_abs,
                            "delta_pct": delta_pct,
                            "provenance": current_data[metric]["provenance"]
                        }
                        deltas.append(delta)
        
        return deltas
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search across indexed content.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of search results with scores
        """
        if not self.search_corpus or self.vector_index is None:
            return []
        
        try:
            # Vectorize the query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.vector_index).flatten()
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:limit]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:  # Only include relevant results
                    result = {
                        "text": self.search_corpus[idx],
                        "score": float(similarities[idx]),
                        "metadata": self.search_metadata[idx]
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error in search: {e}")
            return []
    
    async def _rebuild_vector_index(self):
        """Rebuild the vector index from search corpus."""
        if self.search_corpus:
            try:
                self.vector_index = self.vectorizer.fit_transform(self.search_corpus)
            except Exception as e:
                print(f"Error rebuilding vector index: {e}")
    
    async def add_document_chunks(self, doc_id: str, chunks: List[Dict[str, Any]]):
        """Add document chunks to the index."""
        self.document_index[doc_id] = chunks
        
        # Add chunks to search corpus
        for chunk in chunks:
            text = chunk.get("text", "")
            if text:
                self.search_corpus.append(text)
                self.search_metadata.append({
                    "doc": doc_id,
                    "page": chunk.get("page", 0),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "type": "document_chunk"
                })
        
        await self._rebuild_vector_index()
    
    async def get_kpi_history(self, ticker: str, metric: str) -> List[Dict[str, Any]]:
        """Get historical values for a specific KPI."""
        history = []
        
        if ticker in self.kpi_data:
            for period in sorted(self.kpi_data[ticker].keys()):
                if metric in self.kpi_data[ticker][period]:
                    kpi_data = self.kpi_data[ticker][period][metric]
                    history.append({
                        "period": period,
                        "value": kpi_data["value"],
                        "confidence": kpi_data["confidence"],
                        "provenance": kpi_data["provenance"]
                    })
        
        return history


class PathwayService:
    """Service wrapper for Pathway pipeline operations."""
    
    def __init__(self):
        # In production, this would connect to actual Pathway service
        self.pipeline = MockPathwayPipeline()
    
    async def upsert(self, kpi_rows: List[Dict[str, Any]]) -> bool:
        """Upsert KPI data into Pathway pipeline."""
        return await self.pipeline.upsert_kpi_rows(kpi_rows)
    
    async def get_kpi(self, ticker: str, metric: str, period: str) -> Optional[Dict[str, Any]]:
        """Get specific KPI."""
        return await self.pipeline.get_kpi(ticker, metric, period)
    
    async def get_latest_kpis(self, ticker: str) -> Dict[str, Any]:
        """Get latest KPIs for ticker."""
        return await self.pipeline.get_latest_kpis(ticker)
    
    async def get_deltas(self, ticker: str, period: str) -> List[Dict[str, Any]]:
        """Get deltas for ticker and period."""
        return await self.pipeline.get_deltas(ticker, period)
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search across indexed content."""
        return await self.pipeline.search(query, limit)
    
    async def add_document(self, doc_id: str, chunks: List[Dict[str, Any]]):
        """Add document chunks to index."""
        await self.pipeline.add_document_chunks(doc_id, chunks)
    
    async def get_kpi_history(self, ticker: str, metric: str) -> List[Dict[str, Any]]:
        """Get KPI history."""
        return await self.pipeline.get_kpi_history(ticker, metric)


# Global service instance
pathway_service = PathwayService()
