import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Alert,
  alpha,
  useTheme,
  LinearProgress,
  Paper,
} from '@mui/material';
import {
  People as PeopleIcon,
  Gavel as GavelIcon,
  Description as DescriptionIcon,
  Security as SecurityIcon,
  TrendingUp as TrendingUpIcon,
  CheckCircle as CheckCircleIcon,
  HourglassEmpty as PendingIcon,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import api from '../services/api'; // Use default export for generic API client
import { useAuth } from '../context/AuthContext';
import DocumentUpload from './DocumentUpload';
import SearchBar from './SearchBar';
import { useTranslation } from 'react-i18next';

const AdminDashboard = () => {
  const theme = useTheme();
  const { user } = useAuth();
  const { t } = useTranslation();

  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch aggregated metrics from new endpoint
      const response = await api.get('/metrics/dashboard');
      setMetrics(response.data);

    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const COLORS = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    theme.palette.success.main,
    theme.palette.warning.main,
    theme.palette.error.main,
  ];

  const StatCard = ({ title, value, icon: Icon, color = 'primary' }) => (
    <Card
      sx={{
        position: 'relative',
        overflow: 'visible',
        background: alpha(theme.palette[color].main, 0.05),
        border: `1px solid ${alpha(theme.palette[color].main, 0.1)}`,
        height: '100%',
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontWeight: 600 }}>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700 }}>
              {loading ? '...' : value?.toLocaleString() || 0}
            </Typography>
          </Box>
          <Box
            sx={{
              bgcolor: alpha(theme.palette[color].main, 0.1),
              borderRadius: 2,
              p: 1.5,
            }}
          >
            <Icon sx={{ fontSize: 32, color: theme.palette[color].main }} />
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  if (loading && !metrics) {
    return (
      <Box sx={{ width: '100%', mt: 4 }}>
        <LinearProgress />
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
            {t('dashboard.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {t('common.welcome')} {user?.name}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<DescriptionIcon />}
          onClick={() => setUploadDialogOpen(true)}
        >
          {t('dashboard.uploadDocument')}
        </Button>
      </Box>

      {/* Error Alert */}
      {error && (
        <Box mb={4}>
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        </Box>
      )}

      {/* KPI Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title={t('dashboard.totalCases')}
            value={metrics?.kpi?.total_cases}
            icon={GavelIcon}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title={t('dashboard.activeCases')}
            value={metrics?.kpi?.active_cases}
            icon={TrendingUpIcon}
            color="warning"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title={t('dashboard.totalDocuments')}
            value={metrics?.kpi?.total_documents}
            icon={DescriptionIcon}
            color="info"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title={t('dashboard.totalUsers')}
            value={metrics?.kpi?.total_users}
            icon={PeopleIcon}
            color="success"
          />
        </Grid>
      </Grid>

      {/* Charts Section */}
      <Grid container spacing={3} mb={4}>
        {/* Document Upload Trend */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              {t('dashboard.documentsUploadedTrend')}
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics?.charts?.documents_trend || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill={theme.palette.primary.main} name={t('dashboard.documents')} />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Cases by Status */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom fontWeight={600}>
              {t('dashboard.casesByStatus')}
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={metrics?.charts?.cases_by_status || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  fill="#8884d8"
                  paddingAngle={5}
                  dataKey="value"
                >
                  {(metrics?.charts?.cases_by_status || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Activity */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 2 }}>
            {t('dashboard.recentActivity')}
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>{t('common.user')}</TableCell>
                  <TableCell>{t('dashboard.action')}</TableCell>
                  <TableCell>{t('dashboard.details')}</TableCell>
                  <TableCell>{t('dashboard.date')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(metrics?.recent_activity || []).map((log, index) => (
                  <TableRow key={index} hover>
                    <TableCell>{log.user}</TableCell>
                    <TableCell>
                      <Chip
                        label={log.action}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>{JSON.stringify(log.details)}</TableCell>
                    <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
                {(!metrics?.recent_activity || metrics.recent_activity.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      {t('dashboard.noActivity')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <DocumentUpload
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        onUploadSuccess={() => {
          setUploadDialogOpen(false);
          fetchDashboardData(); // Refresh data
        }}
      />
    </Box>
  );
};

export default AdminDashboard;
