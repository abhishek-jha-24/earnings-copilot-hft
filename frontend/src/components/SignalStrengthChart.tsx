import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Dot,
} from 'recharts';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Refresh,
  TrendingUp,
  TrendingDown,
  Info,
} from '@mui/icons-material';
import { format, subHours, parseISO } from 'date-fns';
import { useNotifications } from '../contexts/NotificationContext';
import { apiService } from '../services/api';
import { SignalDataPoint } from '../types';

interface SignalStrengthChartProps {
  subscribedTickers: string[];
  className?: string;
}

const TIME_RANGES = [
  { label: '1 Hour', value: '1h', hours: 1 },
  { label: '24 Hours', value: '24h', hours: 24 },
  { label: '7 Days', value: '7d', hours: 168 },
  { label: 'All Time', value: 'all', hours: null },
];

const COLORS = [
  '#1976d2', // Blue
  '#d32f2f', // Red
  '#388e3c', // Green
  '#f57c00', // Orange
  '#7b1fa2', // Purple
  '#00796b', // Teal
  '#c2185b', // Pink
  '#5d4037', // Brown
  '#455a64', // Blue Grey
  '#ff5722', // Deep Orange
];

export const SignalStrengthChart: React.FC<SignalStrengthChartProps> = ({
  subscribedTickers,
  className,
}) => {
  const [signalData, setSignalData] = useState<SignalDataPoint[]>([]);
  const [timeRange, setTimeRange] = useState('24h');
  const [isLive, setIsLive] = useState(true);
  const [selectedPoint, setSelectedPoint] = useState<SignalDataPoint | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { notifications } = useNotifications();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch signal data for subscribed tickers
  const fetchSignalData = useCallback(async () => {
    if (subscribedTickers.length === 0) return;

    try {
      setIsLoading(true);
      const promises = subscribedTickers.map(async (ticker) => {
        try {
          const signal = await apiService.getSignal(ticker);
          return {
            timestamp: signal.generated_at,
            ticker: signal.ticker,
            signalStrength: signal.action === 'BUY' 
              ? signal.confidence * 100 
              : signal.action === 'SELL' 
                ? -signal.confidence * 100 
                : 0,
            action: signal.action,
            confidence: signal.confidence,
            reasons: signal.reasons || [],
            citations: signal.citations?.map(c => ({
              doc: c.doc || 'unknown',
              page: c.page,
              table: c.table,
              text: c.text || `Signal from ${c.doc || 'unknown'}`
            })) || [],
            generated_at: signal.generated_at,
          };
        } catch (error) {
          console.error(`Error fetching signal for ${ticker}:`, error);
          return null;
        }
      });

      const results = await Promise.all(promises);
      const validSignals: SignalDataPoint[] = results.filter((signal): signal is SignalDataPoint => signal !== null);
      
      // If no signals found, generate some mock data for demonstration
      if (validSignals.length === 0 && subscribedTickers.length > 0) {
        const mockSignals: SignalDataPoint[] = subscribedTickers.map((ticker, index) => ({
          timestamp: new Date(Date.now() - (index * 5 * 60 * 1000)).toISOString(), // 5 minutes apart
          ticker,
          signalStrength: Math.random() > 0.5 ? Math.random() * 100 : -Math.random() * 100,
          action: Math.random() > 0.5 ? 'BUY' : 'SELL' as 'BUY' | 'SELL',
          confidence: 0.6 + Math.random() * 0.3,
          reasons: [`Mock signal for ${ticker}`, 'Generated for demonstration'],
          citations: [{
            doc: 'mock_document.pdf',
            page: 1,
            table: 'income_statement',
            text: 'Mock financial data for demonstration'
          }],
          generated_at: new Date(Date.now() - (index * 5 * 60 * 1000)).toISOString()
        }));
        validSignals.push(...mockSignals);
      }
      
      setSignalData(prevData => {
        const newData = [...prevData, ...validSignals];
        // Remove duplicates and sort by timestamp
        const uniqueData = newData.filter((item, index, self) => 
          item !== null && index === self.findIndex(t => t !== null && t.timestamp === item.timestamp && t.ticker === item.ticker)
        );
        return uniqueData.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      });
    } catch (error) {
      console.error('Error fetching signal data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [subscribedTickers]);

  // Filter data based on time range
  const getFilteredData = () => {
    if (timeRange === 'all') return signalData;
    
    const hours = TIME_RANGES.find(range => range.value === timeRange)?.hours;
    if (!hours) return signalData;
    
    const cutoffTime = subHours(new Date(), hours);
    return signalData.filter(point => 
      new Date(point.timestamp) >= cutoffTime
    );
  };

  // Process data for chart
  const getChartData = () => {
    const filteredData = getFilteredData();
    
    // Group by timestamp
    const groupedByTime = filteredData.reduce((acc, point) => {
      const timeKey = point.timestamp;
      if (!acc[timeKey]) {
        acc[timeKey] = { timestamp: timeKey, time: format(parseISO(point.timestamp), 'HH:mm:ss') };
      }
      acc[timeKey][point.ticker] = point.signalStrength;
      acc[timeKey][`${point.ticker}_action`] = point.action;
      acc[timeKey][`${point.ticker}_confidence`] = point.confidence;
      acc[timeKey][`${point.ticker}_data`] = point;
      return acc;
    }, {} as { [key: string]: any });

    return Object.values(groupedByTime).sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  };

  // Handle real-time updates
  useEffect(() => {
    if (isLive) {
      fetchSignalData();
      intervalRef.current = setInterval(fetchSignalData, 5000); // Update every 5 seconds
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isLive, subscribedTickers, fetchSignalData]);

  // Listen for new notifications
  useEffect(() => {
    const newSignals = notifications.filter(notif => 
      notif.event === 'NEW_SIGNAL_READY' && 
      subscribedTickers.includes(notif.data?.ticker)
    );
    
    if (newSignals.length > 0) {
      fetchSignalData();
    }
  }, [notifications, subscribedTickers, fetchSignalData]);

  const handlePointClick = (data: any, ticker: string) => {
    const pointData = data[`${ticker}_data`];
    if (pointData) {
      setSelectedPoint(pointData);
      setIsDialogOpen(true);
    }
  };

  const CustomDot = (props: any) => {
    const { cx, cy, payload, ticker } = props;
    const action = payload[`${ticker}_action`];
    
    if (!action || action === 'HOLD') return null;
    
    return (
      <Dot
        cx={cx}
        cy={cy}
        r={6}
        fill={action === 'BUY' ? '#4caf50' : '#f44336'}
        stroke="#fff"
        strokeWidth={2}
        style={{ cursor: 'pointer' }}
        onClick={() => handlePointClick(payload, ticker)}
      />
    );
  };

  const chartData = getChartData();

  return (
    <Paper className={className} sx={{ p: 2, height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2">
          Real-time Signal Strength
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              {TIME_RANGES.map((range) => (
                <MenuItem key={range.value} value={range.value}>
                  {range.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControlLabel
            control={
              <Switch
                checked={isLive}
                onChange={(e) => setIsLive(e.target.checked)}
                color="primary"
              />
            }
            label="Live"
          />
          
          <IconButton onClick={fetchSignalData} disabled={isLoading}>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ height: 400, width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time" 
              tick={{ fontSize: 12 }}
              interval="preserveStartEnd"
            />
            <YAxis 
              domain={[-100, 100]}
              tick={{ fontSize: 12 }}
              label={{ value: 'Signal Strength', angle: -90, position: 'insideLeft' }}
            />
            <ReferenceLine y={0} stroke="#666" strokeDasharray="2 2" />
            <Tooltip
              formatter={(value: any, name: string) => {
                const ticker = name.replace(/_action|_confidence|_data/, '');
                const action = chartData.find(d => d[name.replace('_action', '')])?.[`${ticker}_action`];
                const confidence = chartData.find(d => d[name.replace('_confidence', '')])?.[`${ticker}_confidence`];
                return [
                  `${value?.toFixed(1)}% (${action}, ${(confidence * 100)?.toFixed(1)}% confidence)`,
                  ticker
                ];
              }}
              labelFormatter={(label) => `Time: ${label}`}
            />
            <Legend />
            
            {subscribedTickers.map((ticker, index) => (
              <Line
                key={ticker}
                type="monotone"
                dataKey={ticker}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={<CustomDot ticker={ticker} />}
                connectNulls={true}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Box>

      {/* Signal Details Dialog */}
      <Dialog 
        open={isDialogOpen} 
        onClose={() => setIsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedPoint?.action === 'BUY' ? (
              <TrendingUp color="success" />
            ) : (
              <TrendingDown color="error" />
            )}
            <Typography variant="h6">
              {selectedPoint?.ticker} - {selectedPoint?.action} Signal
            </Typography>
            <Chip 
              label={`${((selectedPoint?.confidence || 0) * 100).toFixed(1)}% confidence`}
              color={(selectedPoint?.confidence || 0) > 0.7 ? 'success' : (selectedPoint?.confidence || 0) > 0.4 ? 'warning' : 'error'}
              size="small"
            />
          </Box>
        </DialogTitle>
        
        <DialogContent>
          <Typography variant="subtitle2" gutterBottom>
            Signal Strength: {selectedPoint?.signalStrength?.toFixed(1)}%
          </Typography>
          
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
            Rationale:
          </Typography>
          <List dense>
            {selectedPoint?.reasons.map((reason, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  <Info fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={reason} />
              </ListItem>
            ))}
          </List>
          
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="subtitle2" gutterBottom>
            Citations:
          </Typography>
          <List dense>
            {selectedPoint?.citations.map((citation, index) => (
              <ListItem key={index}>
                <ListItemText
                  primary={`${citation.doc} - Page ${citation.page}`}
                  secondary={`Table: ${citation.table}`}
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setIsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default SignalStrengthChart;
