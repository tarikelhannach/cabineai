import React, { useState, useEffect } from 'react';
import {
    Box,
    Grid,
    Paper,
    Typography,
    Button,
    TextField,
    CircularProgress,
    Alert,
    IconButton,
    Divider,
    Tooltip
} from '@mui/material';
import {
    Save as SaveIcon,
    CheckCircle as CheckCircleIcon,
    Close as CloseIcon,
    ZoomIn as ZoomInIcon,
    ZoomOut as ZoomOutIcon,
    Refresh as RefreshIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { documentsAPI } from '../services/api';

const OCRVerification = ({ documentId, onClose, onVerified }) => {
    const { t, i18n } = useTranslation();
    const [document, setDocument] = useState(null);
    const [ocrText, setOcrText] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [zoom, setZoom] = useState(100);
    const [pdfUrl, setPdfUrl] = useState(null);

    const isRTL = i18n.language === 'ar';

    useEffect(() => {
        fetchDocument();
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        };
    }, [documentId]);

    const fetchDocument = async () => {
        try {
            setLoading(true);
            // Fetch document metadata
            const docData = await documentsAPI.getDocument(documentId);
            setDocument(docData);
            setOcrText(docData.ocr_text || '');

            // Fetch document file for preview
            const blob = await documentsAPI.downloadDocument(documentId);
            const url = URL.createObjectURL(blob);
            setPdfUrl(url);

        } catch (err) {
            setError(t('common.error'));
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await documentsAPI.updateDocumentOCR(documentId, ocrText);
            if (onVerified) onVerified();
            onClose();
        } catch (err) {
            setError(t('common.error'));
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Box sx={{ height: '85vh', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <Box p={2} borderBottom={1} borderColor="divider" display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">
                    {t('ocr.verificationTitle', 'Verificación de OCR')}
                </Typography>
                <Box display="flex" gap={1}>
                    <Button
                        variant="outlined"
                        color="inherit"
                        onClick={onClose}
                        startIcon={<CloseIcon />}
                    >
                        {t('common.cancel')}
                    </Button>
                    <Button
                        variant="contained"
                        color="success"
                        onClick={handleSave}
                        disabled={saving}
                        startIcon={saving ? <CircularProgress size={20} /> : <CheckCircleIcon />}
                    >
                        {t('ocr.verifyAndSave', 'Verificar y Guardar')}
                    </Button>
                </Box>
            </Box>

            {error && (
                <Alert severity="error" onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Content - Split Screen */}
            <Grid container sx={{ flexGrow: 1, overflow: 'hidden' }}>
                {/* Left Panel - Document Viewer */}
                <Grid item xs={12} md={6} sx={{ borderRight: 1, borderColor: 'divider', height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box p={1} bgcolor="grey.100" display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="subtitle2" color="textSecondary">
                            {t('ocr.originalDocument', 'Documento Original')}
                        </Typography>
                        <Box>
                            <IconButton size="small" onClick={() => setZoom(z => Math.max(50, z - 10))}>
                                <ZoomOutIcon />
                            </IconButton>
                            <Typography variant="caption" sx={{ mx: 1 }}>{zoom}%</Typography>
                            <IconButton size="small" onClick={() => setZoom(z => Math.min(200, z + 10))}>
                                <ZoomInIcon />
                            </IconButton>
                        </Box>
                    </Box>
                    <Box sx={{ flexGrow: 1, bgcolor: 'grey.200', overflow: 'auto', position: 'relative' }}>
                        {pdfUrl && (
                            <iframe
                                src={`${pdfUrl}#zoom=${zoom}`}
                                width="100%"
                                height="100%"
                                style={{ border: 'none' }}
                                title="Document Preview"
                            />
                        )}
                    </Box>
                </Grid>

                {/* Right Panel - Text Editor */}
                <Grid item xs={12} md={6} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box p={1} bgcolor="grey.50" borderBottom={1} borderColor="divider">
                        <Typography variant="subtitle2" color="textSecondary">
                            {t('ocr.extractedText', 'Texto Extraído (Editable)')}
                        </Typography>
                    </Box>
                    <TextField
                        multiline
                        fullWidth
                        variant="standard"
                        value={ocrText}
                        onChange={(e) => setOcrText(e.target.value)}
                        InputProps={{
                            disableUnderline: true,
                            sx: {
                                height: '100%',
                                p: 2,
                                fontSize: '1rem',
                                fontFamily: isRTL ? 'Amiri, serif' : 'inherit',
                                lineHeight: 1.8,
                                direction: isRTL ? 'rtl' : 'ltr'
                            }
                        }}
                        sx={{
                            flexGrow: 1,
                            overflow: 'auto',
                            '& .MuiInputBase-root': { height: '100%', alignItems: 'flex-start' }
                        }}
                    />
                </Grid>
            </Grid>
        </Box>
    );
};

export default OCRVerification;
