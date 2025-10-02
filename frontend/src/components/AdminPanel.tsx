import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  LinearProgress,
  Divider,
} from '@mui/material';
import {
  CloudUpload,
  Assessment,
  Description,
  Security,
  Refresh,
} from '@mui/icons-material';

import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/api';
import { DashboardStats, UploadResponse } from '../types';
import LoginForm from './LoginForm';

const AdminPanel: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [ticker, setTicker] = useState('AAPL');
  const [docType, setDocType] = useState('earnings');
  const [period, setPeriod] = useState('2025-Q3');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [uploadTime, setUploadTime] = useState<number | null>(null);

  useEffect(() => {
    if (isAuthenticated && user?.role === 'ADMIN') {
      fetchStats();
    }
  }, [isAuthenticated, user]);

  const fetchStats = async () => {
    try {
      const statsData = await apiService.getAdminStats();
      setStats(statsData);
    } catch (err: any) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError(null);
      } else {
        setError('Please select a PDF file');
        setFile(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!file || !ticker) {
      setError('Please select a file and enter a ticker');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadResult(null);
    setUploadTime(Date.now()); // Record upload time for latency tracking

    try {
      const result = await apiService.uploadDocument(
        file,
        ticker,
        docType,
        period || undefined,
        effectiveDate || undefined
      );
      
      setUploadResult(result);
      setFile(null);
      
      // Reset form
      const fileInput = document.getElementById('file-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      
      // Refresh stats
      await fetchStats();
      
    } catch (err: any) {
      setError(err.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  if (user?.role !== 'ADMIN') {
    return (
      <Alert severity="error">
        Admin access required. Please login with an admin API key.
      </Alert>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {uploadResult && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setUploadResult(null)}>
          Document uploaded successfully! Doc ID: {uploadResult.doc_id}
          <br />
          Status: {uploadResult.status} - {uploadResult.message}
        </Alert>
      )}

      {/* Upload Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CloudUpload />
          Document Upload
        </Typography>
        
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              fullWidth
              label="Ticker Symbol"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="AAPL"
              sx={{ mb: 2 }}
            />
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Document Type</InputLabel>
              <Select
                value={docType}
                label="Document Type"
                onChange={(e) => setDocType(e.target.value)}
              >
                <MenuItem value="earnings">Earnings</MenuItem>
                <MenuItem value="filing">Filing</MenuItem>
                <MenuItem value="press_release">Press Release</MenuItem>
                <MenuItem value="compliance">Compliance</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              fullWidth
              label="Period (optional)"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="2025-Q3"
              sx={{ mb: 2 }}
            />
            
            {docType === 'compliance' && (
              <TextField
                fullWidth
                label="Effective Date"
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ mb: 2 }}
              />
            )}
          </Grid>
          
          <Grid size={12}>
            <input
              id="file-upload"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-upload">
              <Button
                variant="outlined"
                component="span"
                startIcon={<Description />}
                sx={{ mr: 2 }}
              >
                Choose PDF File
              </Button>
            </label>
            
            {file && (
              <Typography variant="body2" component="span">
                Selected: {file.name}
              </Typography>
            )}
          </Grid>
          
          <Grid size={12}>
            <Button
              variant="contained"
              onClick={handleUpload}
              disabled={!file || uploading}
              startIcon={uploading ? <CircularProgress size={20} /> : <CloudUpload />}
              size="large"
            >
              {uploading ? 'Uploading & Processing...' : 'Upload & Process'}
            </Button>
            
            {uploading && (
              <Box sx={{ mt: 2 }}>
                <LinearProgress />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Processing document with AI extraction...
                </Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      </Paper>

      {/* System Statistics */}
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Assessment />
            System Statistics
          </Typography>
          <Button
            variant="outlined"
            size="small"
            onClick={fetchStats}
            startIcon={<Refresh />}
          >
            Refresh
          </Button>
        </Box>
        
        {stats ? (
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="primary">
                    {stats.totalDocuments || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Documents
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="secondary">
                    {stats.totalSignals || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Signals
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="info.main">
                    {stats.activeSubscriptions || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Subscriptions
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid size={{ xs: 12, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="warning.main">
                    {stats.processingQueue || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Processing Queue
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid size={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body2" color="text.secondary">
                System Uptime: {stats.systemUptime || 'N/A'}
              </Typography>
            </Grid>
          </Grid>
        ) : (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default AdminPanel;
