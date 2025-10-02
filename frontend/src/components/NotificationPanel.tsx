import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Button,
  Collapse,
  IconButton,
  Alert,
  Badge,
} from '@mui/material';
import {
  Notifications,
  NotificationsActive,
  Description,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Warning,
  ExpandMore,
  ExpandLess,
  Clear,
  Wifi,
  WifiOff,
} from '@mui/icons-material';
import { format } from 'date-fns';

import { useNotifications } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';
import { NotificationEvent } from '../types';

const NotificationPanel: React.FC = () => {
  const { notifications, isConnected, clearNotifications } = useNotifications();
  const { isAuthenticated } = useAuth();
  const [expanded, setExpanded] = useState(true);
  const [showAll, setShowAll] = useState(false);

  const getNotificationIcon = (event: string) => {
    switch (event) {
      case 'NEW_DOC_INGESTED':
        return <Description color="info" />;
      case 'NEW_SIGNAL_READY':
        return <TrendingUp color="success" />;
      case 'COMPLIANCE_ALERT':
        return <Warning color="warning" />;
      case 'connected':
        return <Wifi color="success" />;
      case 'ping':
        return <NotificationsActive color="action" />;
      default:
        return <Notifications />;
    }
  };

  const getNotificationTitle = (notification: NotificationEvent) => {
    switch (notification.event) {
      case 'NEW_DOC_INGESTED':
        return `New Document: ${notification.data.ticker} ${notification.data.doc_type}`;
      case 'NEW_SIGNAL_READY':
        return `Signal Ready: ${notification.data.ticker} ${notification.data.action}`;
      case 'COMPLIANCE_ALERT':
        return `Compliance Alert: ${notification.data.ticker}`;
      case 'connected':
        return 'Connected to notification stream';
      case 'ping':
        return 'Keepalive';
      default:
        return notification.event;
    }
  };

  const getNotificationDescription = (notification: NotificationEvent) => {
    switch (notification.event) {
      case 'NEW_DOC_INGESTED':
        return `${notification.data.doc_type} document processed for ${notification.data.ticker}${
          notification.data.period ? ` (${notification.data.period})` : ''
        }`;
      case 'NEW_SIGNAL_READY':
        const confidence = notification.data.confidence
          ? `${(notification.data.confidence * 100).toFixed(0)}% confidence`
          : '';
        return `${notification.data.action} recommendation for ${notification.data.ticker} ${confidence}`;
      case 'COMPLIANCE_ALERT':
        return notification.data.message;
      case 'connected':
        return `Connected as ${notification.data.user_id}`;
      case 'ping':
        return 'Connection active';
      default:
        return JSON.stringify(notification.data);
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY': return 'success';
      case 'SELL': return 'error';
      case 'HOLD': return 'warning';
      default: return 'default';
    }
  };

  const displayNotifications = showAll ? notifications : notifications.slice(0, 10);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Paper sx={{ borderRadius: 2 }}>
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box display="flex" alignItems="center" gap={2}>
          <Badge badgeContent={notifications.length} color="primary" max={99}>
            <Notifications />
          </Badge>
          <Typography variant="h6">
            Live Notifications
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {isConnected ? (
              <>
                <Wifi color="success" fontSize="small" />
                <Typography variant="body2" color="success.main">
                  Connected
                </Typography>
              </>
            ) : (
              <>
                <WifiOff color="error" fontSize="small" />
                <Typography variant="body2" color="error.main">
                  Disconnected
                </Typography>
              </>
            )}
          </Box>
        </Box>
        
        <Box display="flex" alignItems="center" gap={1}>
          {notifications.length > 0 && (
            <Button
              size="small"
              startIcon={<Clear />}
              onClick={(e) => {
                e.stopPropagation();
                clearNotifications();
              }}
            >
              Clear
            </Button>
          )}
          <IconButton size="small">
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
          {!isConnected && (
            <Alert severity="warning" sx={{ m: 2 }}>
              Not connected to notification stream. Please check your connection and API key.
            </Alert>
          )}

          {notifications.length === 0 ? (
            <Box textAlign="center" py={4}>
              <Notifications sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                No notifications yet
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {isConnected
                  ? 'Subscribe to tickers to receive real-time updates'
                  : 'Connect to the notification stream to see live updates'}
              </Typography>
            </Box>
          ) : (
            <>
              <List sx={{ py: 0 }}>
                {displayNotifications.map((notification, index) => (
                  <ListItem
                    key={index}
                    sx={{
                      borderBottom: index < displayNotifications.length - 1 ? 1 : 0,
                      borderColor: 'divider',
                    }}
                  >
                    <ListItemIcon>
                      {getNotificationIcon(notification.event)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="subtitle2">
                            {getNotificationTitle(notification)}
                          </Typography>
                          {notification.event === 'NEW_SIGNAL_READY' && (
                            <Chip
                              label={notification.data.action}
                              size="small"
                              color={getActionColor(notification.data.action) as any}
                            />
                          )}
                          <Typography variant="caption" color="text.secondary">
                            {format(new Date(notification.timestamp), 'HH:mm:ss')}
                          </Typography>
                        </Box>
                      }
                      secondary={getNotificationDescription(notification)}
                    />
                  </ListItem>
                ))}
              </List>

              {notifications.length > 10 && (
                <Box textAlign="center" p={2}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setShowAll(!showAll)}
                  >
                    {showAll ? 'Show Less' : `Show All (${notifications.length})`}
                  </Button>
                </Box>
              )}
            </>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default NotificationPanel;
