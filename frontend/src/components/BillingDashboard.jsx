import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  LinearProgress,
  Chip,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  Stack
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  AttachMoney as MoneyIcon,
  Storage as StorageIcon,
  People as PeopleIcon,
  Description as DocumentIcon,
  Folder as FolderIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Download as DownloadIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import api from '../services/api';

const BillingDashboard = () => {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsRes, invoicesRes] = await Promise.all([
        api.get('/api/billing/firm-stats'),
        api.get('/api/billing/invoices?limit=5')
      ]);
      setStats(statsRes.data);
      setInvoices(invoicesRes.data.invoices || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load billing data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 4 }}>
        <LinearProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!stats) return null;

  const getStatusColor = (status) => {
    const colors = {
      active: 'success',
      expired: 'error',
      trial: 'warning',
      suspended: 'error'
    };
    return colors[status] || 'default';
  };

  const getInvoiceStatusColor = (status) => {
    const colors = {
      paid: 'success',
      pending: 'warning',
      overdue: 'error',
      cancelled: 'default'
    };
    return colors[status] || 'default';
  };

  const isNearExpiry = stats.days_remaining < 30 && stats.days_remaining > 0;
  const isExpired = stats.days_remaining <= 0;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight="bold">
          {t('billing.title')}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {stats.firm_name}
        </Typography>
      </Box>

      {/* Subscription Alert */}
      {(isNearExpiry || isExpired) && (
        <Alert 
          severity={isExpired ? 'error' : 'warning'} 
          icon={<WarningIcon />}
          sx={{ mb: 3 }}
        >
          {isExpired 
            ? t('billing.subscription_expired')
            : t('billing.subscription_expiring_soon', { days: stats.days_remaining })
          }
        </Alert>
      )}

      {/* Subscription Overview */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6} lg={3}>
          <Card 
            sx={{ 
              height: '100%',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white'
            }}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                    {t('billing.subscription_status')}
                  </Typography>
                  <Typography variant="h4" fontWeight="bold">
                    {stats.subscription_tier.toUpperCase()}
                  </Typography>
                  <Chip
                    label={stats.subscription_status.toUpperCase()}
                    size="small"
                    sx={{ 
                      mt: 2, 
                      bgcolor: 'rgba(255,255,255,0.2)',
                      color: 'white',
                      fontWeight: 'bold'
                    }}
                  />
                </Box>
                <CheckCircleIcon sx={{ fontSize: 40, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <ScheduleIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  {t('billing.days_remaining')}
                </Typography>
              </Box>
              <Typography variant="h3" fontWeight="bold" color={isNearExpiry ? 'error' : 'primary'}>
                {stats.days_remaining}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                {t('billing.expires_on')}: {new Date(stats.subscription_end).toLocaleDateString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MoneyIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  {t('billing.monthly_fee')}
                </Typography>
              </Box>
              <Typography variant="h3" fontWeight="bold" color="success.main">
                {stats.monthly_fee.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                MAD / {t('billing.month')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <TrendingUpIcon color="info" sx={{ mr: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  {t('billing.money_saved')}
                </Typography>
              </Box>
              <Typography variant="h3" fontWeight="bold" color="info.main">
                {stats.money_saved_mad.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                MAD {t('billing.total_roi')}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Usage Statistics */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            {t('billing.usage_statistics')}
          </Typography>
          <Divider sx={{ mb: 3 }} />
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Box>
                <Box display="flex" alignItems="center" mb={1}>
                  <PeopleIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {t('billing.active_users')}
                  </Typography>
                </Box>
                <Typography variant="h5" fontWeight="bold">
                  {stats.users_count} / {stats.max_users}
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={stats.users_percentage} 
                  sx={{ mt: 1, height: 8, borderRadius: 4 }}
                  color={stats.users_percentage > 80 ? 'warning' : 'primary'}
                />
                <Typography variant="caption" color="text.secondary">
                  {stats.users_percentage}% {t('billing.used')}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box>
                <Box display="flex" alignItems="center" mb={1}>
                  <DocumentIcon color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {t('billing.documents')}
                  </Typography>
                </Box>
                <Typography variant="h5" fontWeight="bold">
                  {stats.documents_count.toLocaleString()} / {stats.max_documents.toLocaleString()}
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={stats.documents_percentage} 
                  sx={{ mt: 1, height: 8, borderRadius: 4 }}
                  color={stats.documents_percentage > 80 ? 'warning' : 'secondary'}
                />
                <Typography variant="caption" color="text.secondary">
                  {stats.documents_percentage}% {t('billing.used')}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box>
                <Box display="flex" alignItems="center" mb={1}>
                  <StorageIcon color="info" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {t('billing.storage')}
                  </Typography>
                </Box>
                <Typography variant="h5" fontWeight="bold">
                  {stats.storage_used_gb} GB / {stats.max_storage_gb} GB
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={stats.storage_percentage} 
                  sx={{ mt: 1, height: 8, borderRadius: 4 }}
                  color={stats.storage_percentage > 80 ? 'error' : 'info'}
                />
                <Typography variant="caption" color="text.secondary">
                  {stats.storage_percentage}% {t('billing.used')}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box>
                <Box display="flex" alignItems="center" mb={1}>
                  <FolderIcon color="success" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {t('expedientes.title')}
                  </Typography>
                </Box>
                <Typography variant="h5" fontWeight="bold">
                  {stats.expedientes_count}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t('billing.active_cases')}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box>
                <Box display="flex" alignItems="center" mb={1}>
                  <ScheduleIcon color="warning" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {t('billing.time_saved')}
                  </Typography>
                </Box>
                <Typography variant="h5" fontWeight="bold">
                  {stats.time_saved_hours} {t('billing.hours')}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  ~{Math.round(stats.time_saved_hours / 8)} {t('billing.work_days')}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Recent Invoices */}
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" fontWeight="bold">
              {t('billing.recent_invoices')}
            </Typography>
            <Button variant="outlined" size="small">
              {t('billing.view_all')}
            </Button>
          </Box>
          <Divider sx={{ mb: 2 }} />
          
          {invoices.length === 0 ? (
            <Alert severity="info">{t('billing.no_invoices')}</Alert>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>{t('billing.invoice_number')}</TableCell>
                    <TableCell>{t('billing.date')}</TableCell>
                    <TableCell>{t('billing.amount')}</TableCell>
                    <TableCell>{t('billing.status')}</TableCell>
                    <TableCell>{t('billing.due_date')}</TableCell>
                    <TableCell align="right">{t('common.actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {invoices.map((invoice) => (
                    <TableRow key={invoice.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {invoice.invoice_number}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {new Date(invoice.invoice_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {invoice.amount.toLocaleString()} {invoice.currency}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={invoice.status.toUpperCase()}
                          size="small"
                          color={getInvoiceStatusColor(invoice.status)}
                        />
                      </TableCell>
                      <TableCell>
                        {new Date(invoice.due_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          startIcon={<DownloadIcon />}
                          variant="text"
                        >
                          {t('billing.download')}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default BillingDashboard;
