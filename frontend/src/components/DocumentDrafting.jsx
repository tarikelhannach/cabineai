import React, { useState, useEffect } from 'react';
import {
  Box, Container, Typography, Paper, Button, TextField,
  Select, MenuItem, FormControl, InputLabel, Grid, Card, CardContent,
  Dialog, DialogTitle, DialogContent, DialogActions, Chip, CircularProgress,
  Alert
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

const DOCUMENT_TYPES = [
  { value: 'acta', label: 'Acta' },
  { value: 'demanda', label: 'Demanda' },
  { value: 'contrato', label: 'Contrato' },
  { value: 'poder', label: 'Poder' },
  { value: 'escrito', label: 'Escrito' },
  { value: 'dictamen', label: 'Dictamen' }
];

const STATUS_COLORS = {
  draft: 'default',
  reviewed: 'info',
  approved: 'success',
  rejected: 'error'
};

function DocumentDrafting() {
  const { t, i18n } = useTranslation();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [documentType, setDocumentType] = useState('acta');
  const [userPrompt, setUserPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/drafting/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(response.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error loading documents');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDocument = async () => {
    if (!userPrompt.trim()) {
      setError('Please enter a description for the document');
      return;
    }

    try {
      setGenerating(true);
      setError('');
      const token = localStorage.getItem('token');
      
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/drafting/generate/prompt`,
        {
          document_type: documentType,
          user_prompt: userPrompt,
          expediente_id: null,
          context: null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSuccess('Document generated successfully!');
      setGenerateDialogOpen(false);
      setUserPrompt('');
      await loadDocuments();
    } catch (err) {
      if (err.response?.status === 503) {
        setError('OpenAI API key not configured. Please contact your administrator.');
      } else {
        setError(err.response?.data?.detail || 'Error generating document');
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleViewDocument = (doc) => {
    setSelectedDocument(doc);
    setViewDialogOpen(true);
  };

  const handleUpdateStatus = async (documentId, newStatus) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/drafting/documents/${documentId}/status`,
        { status: newStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(`Status updated to ${newStatus}`);
      await loadDocuments();
      if (selectedDocument?.id === documentId) {
        setViewDialogOpen(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error updating status');
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4, direction: i18n.dir() }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {t('Legal Document Drafting Assistant')}
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          {t('Generate professional legal documents using AI')}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess('')} sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => setGenerateDialogOpen(true)}
        >
          {t('Generate New Document')}
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {documents.map((doc) => (
            <Grid item xs={12} md={6} lg={4} key={doc.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                    <Typography variant="h6" noWrap sx={{ flex: 1, mr: 1 }}>
                      {doc.title}
                    </Typography>
                    <Chip 
                      label={doc.status} 
                      color={STATUS_COLORS[doc.status]} 
                      size="small"
                    />
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {t('Type')}: {doc.document_type}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {t('Created')}: {new Date(doc.created_at).toLocaleDateString()}
                  </Typography>
                  
                  {doc.generation_time_seconds && (
                    <Typography variant="caption" color="text.secondary">
                      {t('Generated in')} {doc.generation_time_seconds.toFixed(2)}s
                    </Typography>
                  )}
                  
                  <Box sx={{ mt: 2 }}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => handleViewDocument(doc)}
                    >
                      {t('View Document')}
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {documents.length === 0 && !loading && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            {t('No documents generated yet. Click "Generate New Document" to start.')}
          </Typography>
        </Paper>
      )}

      <Dialog 
        open={generateDialogOpen} 
        onClose={() => setGenerateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{t('Generate New Legal Document')}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>{t('Document Type')}</InputLabel>
              <Select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                label={t('Document Type')}
              >
                {DOCUMENT_TYPES.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              multiline
              rows={6}
              label={t('Description')}
              placeholder={t('Describe the document you need in detail...')}
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              helperText={t('Example: Draft a sales contract for a property in Casablanca, including payment terms and delivery date.')}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGenerateDialogOpen(false)} disabled={generating}>
            {t('Cancel')}
          </Button>
          <Button 
            onClick={handleGenerateDocument}
            variant="contained"
            disabled={generating || !userPrompt.trim()}
          >
            {generating ? <CircularProgress size={24} /> : t('Generate with AI')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedDocument && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">{selectedDocument.title}</Typography>
                <Chip 
                  label={selectedDocument.status} 
                  color={STATUS_COLORS[selectedDocument.status]}
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Paper 
                sx={{ 
                  p: 3, 
                  mb: 2, 
                  maxHeight: '400px', 
                  overflow: 'auto',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace',
                  direction: 'rtl',
                  textAlign: 'right'
                }}
              >
                {selectedDocument.content}
              </Paper>
              
              <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                {t('Type')}: {selectedDocument.document_type} | {t('Model')}: {selectedDocument.model_used}
              </Typography>
              
              {selectedDocument.generation_time_seconds && (
                <Typography variant="caption" color="text.secondary" display="block">
                  {t('Generation time')}: {selectedDocument.generation_time_seconds.toFixed(2)}s
                </Typography>
              )}
            </DialogContent>
            <DialogActions>
              {selectedDocument.status === 'draft' && (
                <Button
                  onClick={() => handleUpdateStatus(selectedDocument.id, 'reviewed')}
                  color="info"
                >
                  {t('Mark as Reviewed')}
                </Button>
              )}
              {selectedDocument.status === 'reviewed' && (
                <>
                  <Button
                    onClick={() => handleUpdateStatus(selectedDocument.id, 'approved')}
                    color="success"
                  >
                    {t('Approve')}
                  </Button>
                  <Button
                    onClick={() => handleUpdateStatus(selectedDocument.id, 'rejected')}
                    color="error"
                  >
                    {t('Reject')}
                  </Button>
                </>
              )}
              <Button onClick={() => setViewDialogOpen(false)}>
                {t('Close')}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Container>
  );
}

export default DocumentDrafting;
