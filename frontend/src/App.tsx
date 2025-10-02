import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Grid,
  Paper,
  Tabs,
  Tab,
  Button,
  Chip,
} from '@mui/material';
import { TrendingUp, Dashboard, Settings, Notifications, Logout } from '@mui/icons-material';

import AdminPanel from './components/AdminPanel';
import TraderDashboard from './components/TraderDashboard';
import SubscriptionManager from './components/SubscriptionManager';
import NotificationPanel from './components/NotificationPanel';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00b4d8',
    },
    secondary: {
      main: '#90e0ef',
    },
    background: {
      default: '#0d1117',
      paper: '#161b22',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
});

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function AppContent() {
  const [tabValue, setTabValue] = useState(0);
  const { user, logout, isAuthenticated } = useAuth();

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleLogout = () => {
    logout();
    setTabValue(0); // Reset to first tab
  };

  return (
    <>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <TrendingUp sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            📈 Earnings Copilot HFT
          </Typography>
          <Typography variant="body2" color="inherit" sx={{ mr: 2 }}>
            AI-powered earnings analysis and trading signals
          </Typography>
          
          {isAuthenticated && user && (
            <>
              <Chip
                label={`${user.role} User`}
                color="primary"
                variant="outlined"
                sx={{ mr: 2 }}
              />
              <Button
                color="inherit"
                onClick={handleLogout}
                startIcon={<Logout />}
                variant="outlined"
                size="small"
              >
                Logout
              </Button>
            </>
          )}
        </Toolbar>
      </AppBar>

          <Container maxWidth="xl" sx={{ mt: 2 }}>
            <Paper sx={{ borderRadius: 2 }}>
              <Tabs
                value={tabValue}
                onChange={handleTabChange}
                variant="scrollable"
                scrollButtons="auto"
                sx={{ borderBottom: 1, borderColor: 'divider' }}
              >
                <Tab
                  icon={<Dashboard />}
                  label="Trading Dashboard"
                  iconPosition="start"
                />
                <Tab
                  icon={<Settings />}
                  label="Admin Panel"
                  iconPosition="start"
                />
                <Tab
                  icon={<Notifications />}
                  label="Subscriptions"
                  iconPosition="start"
                />
              </Tabs>

              <TabPanel value={tabValue} index={0}>
                <TraderDashboard />
              </TabPanel>
              
              <TabPanel value={tabValue} index={1}>
                <AdminPanel />
              </TabPanel>
              
              <TabPanel value={tabValue} index={2}>
                <SubscriptionManager />
              </TabPanel>
            </Paper>

            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid size={12}>
                <NotificationPanel />
              </Grid>
            </Grid>
          </Container>
    </>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <NotificationProvider>
          <AppContent />
        </NotificationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
