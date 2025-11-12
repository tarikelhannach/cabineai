import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Grid,
  Divider,
  Stack
} from '@mui/material';
import {
  AutoAwesome,
  Description,
  Gavel,
  People,
  DateRange,
  PriorityHigh,
  Subject,
  Tag
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import api from '../services/api';

const DocumentClassification = ({ documentId }) => {
  const { t } = useTranslation();
  const [classification, setClassification] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [classifying, setClassifying] = useState(false);

  useEffect(() => {
    fetchClassification();
  }, [documentId]);

  const fetchClassification = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/documents/${documentId}/classification`);
      setClassification(response.data);
    } catch (err) {
      console.log('No classification found yet');
    } finally {
      setLoading(false);
    }
  };

  const handleClassify = async () => {
    try {
      setClassifying(true);
      setError(null);
      const response = await api.post(`/documents/${documentId}/classify`, {
        force_reclassify: classification ? true : false
      });
      setClassification(response.data);
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(t('classification.error'));
      }
    } finally {
      setClassifying(false);
    }
  };

  const getUrgencyColor = (level) => {
    const colors = {
      'normal': 'success',
      'medium': 'warning',
      'urgent': 'error',
      'very_urgent': 'error',
      'عادي': 'success',
      'متوسط': 'warning',
      'عاجل': 'error',
      'عاجل جدا': 'error'
    };
    return colors[level] || 'default';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" display="flex" alignItems="center" gap={1}>
            <AutoAwesome color="primary" />
            {t('classification.title', 'Clasificación Automática')}
          </Typography>
          
          <Button
            variant="contained"
            startIcon={classifying ? <CircularProgress size={20} /> : <AutoAwesome />}
            onClick={handleClassify}
            disabled={classifying}
          >
            {classification 
              ? t('classification.reclassify', 'Reclasificar')
              : t('classification.classify', 'Clasificar Documento')
            }
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!classification && !error && (
          <Alert severity="info">
            {t('classification.no_classification', 'Este documento aún no ha sido clasificado. Haz clic en "Clasificar Documento" para analizar automáticamente su contenido con IA.')}
          </Alert>
        )}

        {classification && (
          <Box>
            <Grid container spacing={2}>
              {/* Document Type */}
              {classification.document_type && (
                <Grid item xs={12} sm={6}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <Description color="primary" />
                    <Typography variant="subtitle2" color="textSecondary">
                      {t('classification.document_type', 'Tipo de Documento')}
                    </Typography>
                  </Box>
                  <Typography variant="body1" fontWeight="medium">
                    {classification.document_type}
                  </Typography>
                </Grid>
              )}

              {/* Legal Area */}
              {classification.legal_area && (
                <Grid item xs={12} sm={6}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <Gavel color="primary" />
                    <Typography variant="subtitle2" color="textSecondary">
                      {t('classification.legal_area', 'Área Legal')}
                    </Typography>
                  </Box>
                  <Typography variant="body1" fontWeight="medium">
                    {classification.legal_area}
                  </Typography>
                </Grid>
              )}

              {/* Urgency Level */}
              {classification.urgency_level && (
                <Grid item xs={12} sm={6}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <PriorityHigh color="primary" />
                    <Typography variant="subtitle2" color="textSecondary">
                      {t('classification.urgency', 'Nivel de Urgencia')}
                    </Typography>
                  </Box>
                  <Chip 
                    label={classification.urgency_level}
                    color={getUrgencyColor(classification.urgency_level)}
                    size="medium"
                  />
                </Grid>
              )}

              {/* Processing Time */}
              {classification.processing_time_seconds && (
                <Grid item xs={12} sm={6}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <AutoAwesome color="primary" />
                    <Typography variant="subtitle2" color="textSecondary">
                      {t('classification.processing_time', 'Tiempo de Procesamiento')}
                    </Typography>
                  </Box>
                  <Typography variant="body1" fontWeight="medium">
                    {classification.processing_time_seconds.toFixed(2)}s
                  </Typography>
                </Grid>
              )}
            </Grid>

            <Divider sx={{ my: 2 }} />

            {/* Parties Involved */}
            {classification.parties_involved && classification.parties_involved.length > 0 && (
              <Box mb={2}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <People color="primary" />
                  <Typography variant="subtitle2" color="textSecondary">
                    {t('classification.parties', 'Partes Involucradas')}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                  {classification.parties_involved.map((party, index) => (
                    <Chip key={index} label={party} variant="outlined" />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Important Dates */}
            {classification.important_dates && classification.important_dates.length > 0 && (
              <Box mb={2}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <DateRange color="primary" />
                  <Typography variant="subtitle2" color="textSecondary">
                    {t('classification.dates', 'Fechas Importantes')}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                  {classification.important_dates.map((date, index) => (
                    <Chip key={index} label={date} variant="outlined" color="primary" />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Keywords */}
            {classification.keywords && classification.keywords.length > 0 && (
              <Box mb={2}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <Tag color="primary" />
                  <Typography variant="subtitle2" color="textSecondary">
                    {t('classification.keywords', 'Palabras Clave')}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
                  {classification.keywords.map((keyword, index) => (
                    <Chip key={index} label={keyword} size="small" />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Summary */}
            {classification.summary && (
              <Box>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <Subject color="primary" />
                  <Typography variant="subtitle2" color="textSecondary">
                    {t('classification.summary', 'Resumen')}
                  </Typography>
                </Box>
                <Typography variant="body2" color="textSecondary">
                  {classification.summary}
                </Typography>
              </Box>
            )}

            {/* Model Info */}
            <Box mt={2}>
              <Typography variant="caption" color="textSecondary">
                {t('classification.model', 'Clasificado con')} {classification.model_used}
                {classification.confidence_score && ` • ${(classification.confidence_score * 100).toFixed(0)}% ${t('classification.confidence', 'confianza')}`}
              </Typography>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default DocumentClassification;
