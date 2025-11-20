import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Button,
  IconButton,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  MenuItem,
} from '@mui/material';
import {
  Add as AddIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  CloudUpload as UploadIcon,
  AutoAwesome as ClassifyIcon,
  CheckCircle as VerifyIcon,
  Verified as VerifiedBadgeIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { usePermissions } from '../hooks/usePermissions';
import api from '../services/api';
import DocumentClassification from './DocumentClassification';
import OCRVerification from './OCRVerification';

const DocumentsList = () => {
  const { t } = useTranslation();
  const { canUploadDocument, canDeleteDocument } = usePermissions();

  const [documents, setDocuments] = useState([]);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const [openDialog, setOpenDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedCaseId, setSelectedCaseId] = useState('');

  const [openClassificationDialog, setOpenClassificationDialog] = useState(false);
  const [openVerificationDialog, setOpenVerificationDialog] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);

  const fetchDocuments = React.useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/documents/');
      setDocuments(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const fetchCases = React.useCallback(async () => {
    try {
      const response = await api.get('/cases/');
      setCases(response.data);
    } catch (err) {
      console.error('Error fetching cases:', err);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
    fetchCases();
  }, [fetchDocuments, fetchCases]);

  const handleUpload = async () => {
    if (!selectedFile || !selectedCaseId) {
      setError(t('documents.selectFileAndCase', 'Selecciona un archivo y un caso'));
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      await api.post(`/documents/${selectedCaseId}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setOpenDialog(false);
      setSelectedFile(null);
      setSelectedCaseId('');
      fetchDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    }
  };

  const handleDownload = async (documentId, filename) => {
    try {
      const response = await api.get(`/documents/${documentId}/download`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'));
    }
  };

  const handleDelete = async (documentId) => {
    if (window.confirm(t('documents.confirmDelete', '¿Confirmar eliminación?'))) {
      try {
        await api.delete(`/documents/${documentId}`);
        fetchDocuments();
      } catch (err) {
        setError(err.response?.data?.detail || t('common.error'));
      }
    }
  };

  const paginatedDocuments = documents.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={700}>
          {t('navigation.documents')}
        </Typography>
        {canUploadDocument && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            {t('documents.upload', 'Subir Documento')}
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('documents.filename', 'Nombre')}</TableCell>
                <TableCell>{t('documents.case', 'Caso')}</TableCell>
                <TableCell>{t('documents.uploadedBy', 'Subido por')}</TableCell>
                <TableCell>{t('documents.uploadedAt', 'Fecha')}</TableCell>
                <TableCell>{t('documents.size', 'Tamaño')}</TableCell>
                <TableCell align="right">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedDocuments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary" py={3}>
                      {t('documents.noDocuments', 'No hay documentos')}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedDocuments.map((doc) => (
                  <TableRow key={doc.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600} display="flex" alignItems="center" gap={1}>
                        {doc.filename}
                        {doc.is_verified && (
                          <VerifiedBadgeIcon color="success" fontSize="small" titleAccess={t('ocr.verified', 'Verificado')} />
                        )}
                      </Typography>
                    </TableCell>
                    <TableCell>{doc.case?.case_number || 'N/A'}</TableCell>
                    <TableCell>{doc.uploaded_by?.name || 'N/A'}</TableCell>
                    <TableCell>
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {(doc.file_size / 1024).toFixed(2)} KB
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedDocumentId(doc.id);
                          setOpenClassificationDialog(true);
                        }}
                        title={t('classification.title', 'Clasificación Automática')}
                      >
                        <ClassifyIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setSelectedDocumentId(doc.id);
                          setOpenVerificationDialog(true);
                        }}
                        title={t('ocr.verify', 'Verificar OCR')}
                        color={doc.is_verified ? "success" : "default"}
                      >
                        <VerifyIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDownload(doc.id, doc.filename)}
                        title={t('documents.download', 'Descargar')}
                      >
                        <DownloadIcon />
                      </IconButton>
                      {canDeleteDocument(doc) && (
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(doc.id)}
                          title={t('common.delete', 'Eliminar')}
                        >
                          <DeleteIcon />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={documents.length}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          labelRowsPerPage={t('common.rowsPerPage', 'Filas por página')}
        />
      </Paper>

      {/* Upload Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('documents.upload', 'Subir Documento')}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              select
              label={t('documents.selectCase', 'Seleccionar Caso')}
              value={selectedCaseId}
              onChange={(e) => setSelectedCaseId(e.target.value)}
              fullWidth
              required
            >
              <MenuItem value="">{t('documents.selectCase', 'Seleccionar Caso')}</MenuItem>
              {cases.map((caseItem) => (
                <MenuItem key={caseItem.id} value={caseItem.id}>
                  {caseItem.case_number} - {caseItem.title}
                </MenuItem>
              ))}
            </TextField>

            <Button
              variant="outlined"
              component="label"
              startIcon={<UploadIcon />}
              fullWidth
            >
              {selectedFile ? selectedFile.name : t('documents.selectFile', 'Seleccionar Archivo')}
              <input
                type="file"
                hidden
                onChange={(e) => setSelectedFile(e.target.files[0])}
              />
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>{t('common.cancel')}</Button>
          <Button onClick={handleUpload} variant="contained">
            {t('documents.upload', 'Subir')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Classification Dialog */}
      <Dialog
        open={openClassificationDialog}
        onClose={() => setOpenClassificationDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{t('classification.title', 'Clasificación Automática')}</DialogTitle>
        <DialogContent>
          {selectedDocumentId && (
            <DocumentClassification documentId={selectedDocumentId} />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenClassificationDialog(false)}>
            {t('common.close', 'Cerrar')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Verification Dialog */}
      <Dialog
        open={openVerificationDialog}
        onClose={() => setOpenVerificationDialog(false)}
        maxWidth="xl"
        fullWidth
        PaperProps={{
          sx: { height: '90vh' }
        }}
      >
        <DialogContent sx={{ p: 0 }}>
          {selectedDocumentId && (
            <OCRVerification
              documentId={selectedDocumentId}
              onClose={() => setOpenVerificationDialog(false)}
              onVerified={() => {
                fetchDocuments();
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default DocumentsList;
