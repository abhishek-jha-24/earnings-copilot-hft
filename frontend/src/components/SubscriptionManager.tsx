import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material';
import {
  Add,
  Delete,
  Notifications,
  NotificationsActive,
  Refresh,
} from '@mui/icons-material';

import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { Subscription, SubscriptionCreate } from '../types';
import LoginForm from './LoginForm';

const SubscriptionManager: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [newTicker, setNewTicker] = useState('');
  const [newChannels, setNewChannels] = useState<string[]>(['ws']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchSubscriptions();
    }
  }, [isAuthenticated]);

  const fetchSubscriptions = async () => {
    setLoading(true);
    try {
      const data = await apiService.getSubscriptions();
      setSubscriptions(data);
    } catch (err: any) {
      setError(err.detail || 'Failed to fetch subscriptions');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSubscription = async () => {
    if (!newTicker.trim()) {
      setError('Ticker is required');
      return;
    }

    if (newChannels.length === 0) {
      setError('At least one notification channel must be selected');
      return;
    }

    try {
      const subscription: SubscriptionCreate = {
        ticker: newTicker.toUpperCase(),
        channels: newChannels as ('ws' | 'slack' | 'email')[],
      };

      await apiService.createSubscription(subscription);
      setSuccess(`Successfully subscribed to ${newTicker.toUpperCase()}`);
      setNewTicker('');
      setNewChannels(['ws']);
      await fetchSubscriptions();
    } catch (err: any) {
      setError(err.detail || 'Failed to create subscription');
    }
  };

  const handleDeleteSubscription = async (ticker: string) => {
    try {
      await apiService.deleteSubscription(ticker);
      setSuccess(`Unsubscribed from ${ticker}`);
      await fetchSubscriptions();
    } catch (err: any) {
      setError(err.detail || 'Failed to delete subscription');
    }
  };

  const getChannelColor = (channel: string) => {
    switch (channel) {
      case 'ws': return 'primary';
      case 'slack': return 'secondary';
      case 'email': return 'success';
      default: return 'default';
    }
  };

  const getChannelLabel = (channel: string) => {
    switch (channel) {
      case 'ws': return 'WebSocket';
      case 'slack': return 'Slack';
      case 'email': return 'Email';
      default: return channel;
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

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Create New Subscription */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Add />
          Subscribe to Ticker
        </Typography>
        
        <Grid container spacing={3} alignItems="center">
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth
              label="Ticker Symbol"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
              placeholder="AAPL"
            />
          </Grid>
          
          <Grid size={{ xs: 12, md: 6 }}>
            <FormControl fullWidth>
              <InputLabel>Notification Channels</InputLabel>
              <Select
                multiple
                value={newChannels}
                onChange={(e) => setNewChannels(e.target.value as string[])}
                label="Notification Channels"
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip
                        key={value}
                        label={getChannelLabel(value)}
                        size="small"
                        color={getChannelColor(value) as any}
                      />
                    ))}
                  </Box>
                )}
              >
                <MenuItem value="ws">WebSocket (Real-time)</MenuItem>
                <MenuItem value="slack">Slack</MenuItem>
                <MenuItem value="email">Email</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid size={{ xs: 12, md: 2 }}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleCreateSubscription}
              startIcon={<Add />}
            >
              Subscribe
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Current Subscriptions */}
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <NotificationsActive />
            Active Subscriptions ({subscriptions.length})
          </Typography>
          <Button
            variant="outlined"
            size="small"
            onClick={fetchSubscriptions}
            startIcon={loading ? <CircularProgress size={16} /> : <Refresh />}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
        
        {loading && subscriptions.length === 0 ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : subscriptions.length === 0 ? (
          <Box textAlign="center" py={4}>
            <Notifications sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              No subscriptions yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Subscribe to tickers above to receive real-time notifications
            </Typography>
          </Box>
        ) : (
          <Grid container spacing={2}>
            {subscriptions.map((subscription) => (
              <Grid size={{ xs: 12, md: 6, lg: 4 }} key={subscription.id}>
                <Card variant="outlined">
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Typography variant="h5" component="div">
                        {subscription.ticker}
                      </Typography>
                      <IconButton
                        color="error"
                        onClick={() => handleDeleteSubscription(subscription.ticker)}
                        size="small"
                      >
                        <Delete />
                      </IconButton>
                    </Box>
                    
                    <Box mb={2}>
                      {subscription.channels.map((channel) => (
                        <Chip
                          key={channel}
                          label={getChannelLabel(channel)}
                          size="small"
                          color={getChannelColor(channel) as any}
                          sx={{ mr: 0.5, mb: 0.5 }}
                        />
                      ))}
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary">
                      Subscribed: {new Date(subscription.created_at).toLocaleDateString()}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Paper>

      {/* Subscription Info */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Notification Types
        </Typography>
        <List>
          <ListItem>
            <ListItemText
              primary="NEW_DOC_INGESTED"
              secondary="Notifies when a new document is uploaded and processed for your subscribed tickers"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="NEW_SIGNAL_READY"
              secondary="Alerts when a new trading signal (BUY/SELL/HOLD) is generated with confidence score"
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="COMPLIANCE_ALERT"
              secondary="Warns about margin requirement changes and provides exposure guidance"
            />
          </ListItem>
        </List>
      </Paper>
    </Box>
  );
};

export default SubscriptionManager;
