import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Box,
  TextField,
  Button,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Refresh,
  Search,
  GetApp,
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { Signal, KpiData, SearchResponse, TickerSummary } from '../types';
import LoginForm from './LoginForm';
import SignalStrengthChart from './SignalStrengthChart';
import { useSubscriptions } from '../hooks/useSubscriptions';

const TraderDashboard: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const { subscriptions } = useSubscriptions();
  const [selectedTicker, setSelectedTicker] = useState('AAPL');
  const [signal, setSignal] = useState<Signal | null>(null);
  const [kpis, setKpis] = useState<KpiData[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [tickerSummary, setTickerSummary] = useState<TickerSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadTime, setUploadTime] = useState<number | null>(null);

  useEffect(() => {
    if (isAuthenticated && selectedTicker) {
      fetchTickerData();
    }
  }, [isAuthenticated, selectedTicker]);

  const fetchTickerData = async () => {
    if (!selectedTicker) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Fetch signal
      const signalData = await apiService.getSignal(selectedTicker);
      setSignal(signalData);
      
      // Calculate latency if we have upload time
      if (uploadTime && signalData.generated_at) {
        const signalTime = new Date(signalData.generated_at).getTime();
        const latency = (signalTime - uploadTime) / 1000;
        console.log(`Upload → Signal latency: ${latency}s`);
      }

      // Fetch KPIs for major metrics
      const metrics = ['revenue', 'eps', 'gross_margin'];
      const kpiPromises = metrics.map(metric =>
        apiService.getKpi(selectedTicker, metric).catch(() => null)
      );
      const kpiResults = await Promise.all(kpiPromises);
      setKpis(kpiResults.filter(Boolean) as KpiData[]);

      // Fetch ticker summary
      const summary = await apiService.getTickerSummary(selectedTicker);
      setTickerSummary(summary);

    } catch (err: any) {
      setError(err.detail || 'Failed to fetch ticker data');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      const results = await apiService.search(searchQuery);
      setSearchResults(results);
    } catch (err: any) {
      setError(err.detail || 'Search failed');
    }
  };

  const handleExportMemo = async () => {
    if (!selectedTicker) return;
    
    try {
      const blob = await apiService.exportMemo(selectedTicker, '2025-Q3');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedTicker}_memo.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.detail || 'Export failed');
    }
  };

  const getSignalColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'success';
      case 'SELL': return 'error';
      case 'HOLD': return 'warning';
      default: return 'default';
    }
  };

  const getSignalIcon = (action: string) => {
    switch (action) {
      case 'BUY': return <TrendingUp />;
      case 'SELL': return <TrendingDown />;
      case 'HOLD': return <TrendingFlat />;
      default: return <TrendingFlat />;
    }
  };

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Ticker Selection */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            fullWidth
            label="Analyze Ticker"
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value.toUpperCase())}
            variant="outlined"
            placeholder="Enter ticker symbol"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Button
            fullWidth
            variant="contained"
            onClick={fetchTickerData}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <Refresh />}
            sx={{ height: '56px' }}
          >
            Refresh Data
          </Button>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Button
            fullWidth
            variant="outlined"
            onClick={handleExportMemo}
            startIcon={<GetApp />}
            sx={{ height: '56px' }}
          >
            Export Memo
          </Button>
        </Grid>
      </Grid>

      {/* Signal Display */}
      {signal && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={3} alignItems="center">
            <Grid size={{ xs: 12, md: 4 }}>
              <Box display="flex" alignItems="center" gap={2}>
                {getSignalIcon(signal.action)}
                <Box>
                  <Typography variant="h4" component="div">
                    <Chip
                      label={signal.action}
                      color={getSignalColor(signal.action) as any}
                      size="medium"
                      sx={{ fontSize: '1.2rem', fontWeight: 'bold' }}
                    />
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedTicker} • {(signal.confidence * 100).toFixed(0)}% confidence
                  </Typography>
                </Box>
              </Box>
            </Grid>
            
            <Grid size={{ xs: 12, md: 8 }}>
              <Typography variant="h6" gutterBottom>
                Analysis Reasons:
              </Typography>
              {signal.reasons.map((reason, index) => (
                <Typography key={index} variant="body2" sx={{ mb: 0.5 }}>
                  • {reason}
                </Typography>
              ))}
              
              {signal.blocked_reason && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  Signal blocked: {signal.blocked_reason}
                </Alert>
              )}
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {kpis.map((kpi) => (
          <Grid size={{ xs: 12, md: 4 }} key={kpi.metric}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {kpi.metric.replace('_', ' ').toUpperCase()}
                </Typography>
                <Typography variant="h4" component="div">
                  {kpi.current_value} {kpi.unit}
                </Typography>
                
                {kpi.yoy_change !== undefined && (
                  <Box display="flex" alignItems="center" gap={1} mt={1}>
                    {kpi.yoy_change > 0 ? (
                      <TrendingUp color="success" />
                    ) : kpi.yoy_change < 0 ? (
                      <TrendingDown color="error" />
                    ) : (
                      <TrendingFlat />
                    )}
                    <Typography
                      variant="body2"
                      color={kpi.yoy_change > 0 ? 'success.main' : kpi.yoy_change < 0 ? 'error.main' : 'text.secondary'}
                    >
                      {(kpi.yoy_change * 100).toFixed(1)}% YoY
                    </Typography>
                  </Box>
                )}
                
                {kpi.surprise !== undefined && kpi.consensus !== undefined && (
                  <Typography variant="body2" color="text.secondary" mt={1}>
                    vs Consensus: {kpi.consensus} ({(kpi.surprise * 100).toFixed(1)}% surprise)
                  </Typography>
                )}
                
                <Typography variant="caption" display="block" mt={1}>
                  Confidence: {(kpi.confidence * 100).toFixed(0)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Search Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Document Search
        </Typography>
        <Grid container spacing={2} alignItems="center">
          <Grid size={{ xs: 12, md: 8 }}>
            <TextField
              fullWidth
              label="Search query"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search earnings documents..."
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleSearch}
              startIcon={<Search />}
            >
              Search
            </Button>
          </Grid>
        </Grid>

        {searchResults && (
          <Box mt={3}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {searchResults.total_results} results for "{searchResults.query}"
            </Typography>
            {searchResults.results.map((result, index) => (
              <Paper key={index} variant="outlined" sx={{ p: 2, mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  {result.doc} (Page {result.page})
                  {result.ticker && (
                    <Chip label={result.ticker} size="small" sx={{ ml: 1 }} />
                  )}
                </Typography>
                <Typography variant="body2">
                  {result.text}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Score: {result.score.toFixed(3)}
                </Typography>
              </Paper>
            ))}
          </Box>
        )}
      </Paper>

      {/* Signal Strength Chart */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <SignalStrengthChart 
          subscribedTickers={subscriptions.map(sub => sub.ticker)}
          className="signal-strength-chart"
        />
      </Paper>
    </Box>
  );
};

export default TraderDashboard;
