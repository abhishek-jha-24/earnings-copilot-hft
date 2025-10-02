import React, { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Login } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const LoginForm: React.FC = () => {
  const [apiKey, setApiKey] = useState('');
  const [role, setRole] = useState<'ADMIN' | 'TRADER'>('TRADER');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!apiKey.trim()) {
      setError('API key is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const success = await login(apiKey, role);
      if (!success) {
        setError('Invalid API key or connection failed');
      }
    } catch (err: any) {
      setError(err.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (quickRole: 'ADMIN' | 'TRADER') => {
    const quickKey = quickRole === 'ADMIN' ? 'admin-secret' : 'trader-secret';
    setApiKey(quickKey);
    setRole(quickRole);
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="60vh"
    >
      <Paper sx={{ p: 4, maxWidth: 400, width: '100%' }}>
        <Box textAlign="center" mb={3}>
          <Login sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h4" gutterBottom>
            Login
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Enter your API key to access the system
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Role</InputLabel>
            <Select
              value={role}
              label="Role"
              onChange={(e) => setRole(e.target.value as 'ADMIN' | 'TRADER')}
            >
              <MenuItem value="TRADER">Trader</MenuItem>
              <MenuItem value="ADMIN">Admin</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="API Key"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            sx={{ mb: 3 }}
            placeholder="Enter your API key"
          />

          <Button
            type="submit"
            fullWidth
            variant="contained"
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <Login />}
            sx={{ mb: 2 }}
          >
            {loading ? 'Connecting...' : 'Login'}
          </Button>
        </form>

        <Box textAlign="center">
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Quick Login (Demo):
          </Typography>
          <Box display="flex" gap={1} justifyContent="center">
            <Button
              size="small"
              variant="outlined"
              onClick={() => handleQuickLogin('TRADER')}
            >
              Trader Demo
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={() => handleQuickLogin('ADMIN')}
            >
              Admin Demo
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default LoginForm;
