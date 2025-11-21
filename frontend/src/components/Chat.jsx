import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  CircularProgress,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  Badge
} from '@mui/material';
import {
  Send as SendIcon,
  Add as AddIcon,
  Chat as ChatIcon,
  SmartToy as AIIcon,
  Description as DocumentIcon,
  ExpandMore as ExpandMoreIcon,
  Image as ImageIcon,
  Close as CloseIcon,
  AutoAwesome as GeminiIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import api from '../services/api';
import GeminiChatService, { SYSTEM_PROMPTS } from '../services/geminiService';

const Chat = () => {
  const { t, i18n } = useTranslation();
  const isRTL = i18n.language === 'ar';

  // State
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [newConversationDialog, setNewConversationDialog] = useState(false);
  const [newConversationTitle, setNewConversationTitle] = useState('');

  // Gemini-specific state
  const [geminiService, setGeminiService] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [useGemini, setUseGemini] = useState(true); // Toggle for Gemini vs backend

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Initialize Gemini service
  useEffect(() => {
    const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
    if (apiKey) {
      const service = new GeminiChatService(apiKey);
      setGeminiService(service);
      console.log('✅ Gemini service initialized');
    } else {
      console.warn('⚠️ Gemini API key not configured, using backend fallback');
      setUseGemini(false);
    }
  }, []);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load messages when conversation selected
  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id);

      // Initialize Gemini chat for this conversation
      if (geminiService && useGemini) {
        initializeGeminiChat();
      }
    }
  }, [selectedConversation]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeGeminiChat = async () => {
    if (!geminiService) return;

    try {
      // Get document context if available
      const documentContext = await getDocumentContext();
      await geminiService.startChat(SYSTEM_PROMPTS.general, documentContext);
      console.log('✅ Gemini chat initialized for conversation');
    } catch (error) {
      console.error('Failed to initialize Gemini chat:', error);
    }
  };

  const getDocumentContext = async () => {
    // TODO: Fetch relevant documents for this conversation
    // For now, return null
    return null;
  };

  const loadConversations = async () => {
    try {
      setLoading(true);
      const response = await api.get('/chat/conversations');
      setConversations(response.data);
      if (response.data.length > 0 && !selectedConversation) {
        setSelectedConversation(response.data[0]);
      }
    } catch (err) {
      console.error('Error loading conversations:', err);
      setError(t('chat.error_loading_conversations'));
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (conversationId) => {
    try {
      setLoading(true);
      const response = await api.get(`/chat/conversations/${conversationId}/messages`);
      setMessages(response.data);
    } catch (err) {
      console.error('Error loading messages:', err);
      setError(t('chat.error_loading_messages'));
    } finally {
      setLoading(false);
    }
  };

  const createConversation = async () => {
    if (!newConversationTitle.trim()) return;

    try {
      const response = await api.post('/chat/conversations', {
        title: newConversationTitle
      });
      setConversations([response.data, ...conversations]);
      setSelectedConversation(response.data);
      setNewConversationDialog(false);
      setNewConversationTitle('');
    } catch (err) {
      console.error('Error creating conversation:', err);
      setError(t('chat.error_creating_conversation'));
    }
  };

  const handleImageSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('يرجى اختيار ملف صورة');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('حجم الصورة يجب أن يكون أقل من 10 ميجابايت');
      return;
    }

    setSelectedImage(file);

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const sendMessage = async () => {
    if ((!newMessage.trim() && !selectedImage) || !selectedConversation) return;

    const userMessage = newMessage.trim();
    setNewMessage('');

    // Add user message to UI immediately
    const tempUserMessage = {
      role: 'user',
      content: selectedImage ? `[صورة] ${userMessage}` : userMessage,
      created_at: new Date().toISOString(),
      temp: true
    };
    setMessages([...messages, tempUserMessage]);

    try {
      setSending(true);

      // Use Gemini if available and enabled
      if (geminiService && useGemini && geminiService.isEnabled()) {
        await sendMessageWithGemini(userMessage);
      } else {
        // Fallback to backend
        await sendMessageWithBackend(userMessage);
      }

      // Clear image after sending
      clearImage();

    } catch (err) {
      console.error('Error sending message:', err);

      // Try fallback if Gemini fails
      if (useGemini && geminiService) {
        console.log('Gemini failed, trying backend fallback...');
        try {
          await sendMessageWithBackend(userMessage);
        } catch (backendErr) {
          setError(t('chat.error_sending_message'));
          setMessages(messages); // Remove temp message
        }
      } else {
        setError(t('chat.error_sending_message'));
        setMessages(messages); // Remove temp message
      }
    } finally {
      setSending(false);
      setIsStreaming(false);
      setStreamingText('');
    }
  };

  const sendMessageWithGemini = async (userMessage) => {
    setIsStreaming(true);
    setStreamingText('');

    try {
      let responseText = '';

      // Handle image analysis
      if (selectedImage) {
        const reader = new FileReader();
        const imageData = await new Promise((resolve, reject) => {
          reader.onloadend = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
          };
          reader.onerror = reject;
          reader.readAsDataURL(selectedImage);
        });

        const prompt = userMessage || 'حلل هذا المستند واستخرج المعلومات المهمة';
        responseText = await geminiService.analyzeImage(
          imageData,
          selectedImage.type,
          prompt
        );

        setStreamingText(responseText);
      } else {
        // Regular text chat with streaming
        responseText = await geminiService.sendMessage(userMessage, (chunk) => {
          setStreamingText(prev => prev + chunk);
        });
      }

      // Save to backend for persistence
      try {
        await api.post('/chat/messages', {
          conversation_id: selectedConversation.id,
          message: userMessage,
          response: responseText,
          language: i18n.language,
          source: 'gemini'
        });
      } catch (saveError) {
        console.warn('Failed to save message to backend:', saveError);
      }

      // Reload messages from backend
      await loadMessages(selectedConversation.id);

    } catch (error) {
      console.error('Gemini error:', error);
      throw error;
    }
  };

  const sendMessageWithBackend = async (userMessage) => {
    const response = await api.post('/chat/messages', {
      conversation_id: selectedConversation.id,
      message: userMessage,
      language: i18n.language
    });

    // Reload messages to get both user and AI messages from server
    await loadMessages(selectedConversation.id);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renderMessage = (message, index) => {
    const isUser = message.role === 'user';
    const sources = message.sources ? (typeof message.sources === 'string' ? JSON.parse(message.sources) : message.sources) : [];
    const isGemini = message.source === 'gemini';

    return (
      <Box
        key={index}
        sx={{
          display: 'flex',
          justifyContent: isUser ? (isRTL ? 'flex-start' : 'flex-end') : (isRTL ? 'flex-end' : 'flex-start'),
          mb: 2
        }}
      >
        <Paper
          elevation={1}
          sx={{
            p: 2,
            maxWidth: '70%',
            bgcolor: isUser ? 'primary.light' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
            borderRadius: 2
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            {isUser ? (
              <ChatIcon sx={{ mr: 1, fontSize: 20 }} />
            ) : (
              <Tooltip title={isGemini ? 'Gemini AI' : 'Backend AI'}>
                {isGemini ? (
                  <GeminiIcon sx={{ mr: 1, fontSize: 20, color: 'secondary.main' }} />
                ) : (
                  <AIIcon sx={{ mr: 1, fontSize: 20 }} />
                )}
              </Tooltip>
            )}
            <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
              {isUser ? t('chat.you') : (isGemini ? 'Gemini' : t('chat.ai_assistant'))}
            </Typography>
          </Box>

          {/* Render markdown for AI responses */}
          {!isUser ? (
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <Typography variant="body1" sx={{ mb: 1, direction: isRTL ? 'rtl' : 'ltr' }}>
                    {children}
                  </Typography>
                ),
                ul: ({ children }) => (
                  <Box component="ul" sx={{ direction: isRTL ? 'rtl' : 'ltr', pr: isRTL ? 2 : 0, pl: isRTL ? 0 : 2 }}>
                    {children}
                  </Box>
                ),
                code: ({ children }) => (
                  <Box
                    component="code"
                    sx={{
                      bgcolor: 'grey.100',
                      p: 0.5,
                      borderRadius: 0.5,
                      fontFamily: 'monospace'
                    }}
                  >
                    {children}
                  </Box>
                )
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', direction: isRTL ? 'rtl' : 'ltr' }}>
              {message.content}
            </Typography>
          )}

          {sources.length > 0 && (
            <Accordion sx={{ mt: 1, bgcolor: 'transparent', boxShadow: 'none' }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="caption">
                  <DocumentIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                  {t('chat.sources')} ({sources.length})
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box>
                  {sources.map((source, idx) => (
                    <Chip
                      key={idx}
                      label={`${source.document_name} (${Math.round(source.similarity * 100)}%)`}
                      size="small"
                      sx={{ m: 0.5 }}
                      icon={<DocumentIcon />}
                    />
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}
        </Paper>
      </Box>
    );
  };

  return (
    <Box sx={{ height: 'calc(100vh - 120px)', display: 'flex' }}>
      {/* Conversations List */}
      <Paper
        elevation={3}
        sx={{
          width: 300,
          display: 'flex',
          flexDirection: 'column',
          borderRight: 1,
          borderColor: 'divider'
        }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">{t('chat.conversations')}</Typography>
          <IconButton color="primary" onClick={() => setNewConversationDialog(true)}>
            <AddIcon />
          </IconButton>
        </Box>
        <Divider />

        <List sx={{ flex: 1, overflow: 'auto' }}>
          {conversations.map((conv) => (
            <ListItemButton
              key={conv.id}
              selected={selectedConversation?.id === conv.id}
              onClick={() => setSelectedConversation(conv)}
            >
              <ListItemText
                primary={conv.title}
                secondary={`${conv.message_count || 0} ${t('chat.messages')}`}
              />
            </ListItemButton>
          ))}
        </List>
      </Paper>

      {/* Chat Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {selectedConversation ? (
          <>
            {/* Header */}
            <Paper elevation={2} sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="h6">{selectedConversation.title}</Typography>
              {geminiService && geminiService.isEnabled() && (
                <Chip
                  icon={<GeminiIcon />}
                  label="Gemini AI"
                  size="small"
                  color="secondary"
                  variant="outlined"
                />
              )}
            </Paper>

            {/* Messages */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 3, bgcolor: 'grey.50' }}>
              {loading && messages.length === 0 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : messages.length === 0 ? (
                <Box sx={{ textAlign: 'center', p: 4 }}>
                  <GeminiIcon sx={{ fontSize: 64, color: 'secondary.main', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    {t('chat.start_conversation')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    مدعوم بتقنية Gemini 2.0 Flash للغة العربية
                  </Typography>
                </Box>
              ) : (
                messages.filter(m => !m.temp).map((message, index) => renderMessage(message, index))
              )}

              {/* Streaming message */}
              {isStreaming && streamingText && (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: isRTL ? 'flex-end' : 'flex-start',
                    mb: 2
                  }}
                >
                  <Paper
                    elevation={1}
                    sx={{
                      p: 2,
                      maxWidth: '70%',
                      bgcolor: 'background.paper',
                      borderRadius: 2
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <GeminiIcon sx={{ mr: 1, fontSize: 20, color: 'secondary.main' }} />
                      <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
                        Gemini
                      </Typography>
                      <CircularProgress size={12} sx={{ ml: 1 }} />
                    </Box>
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => (
                          <Typography variant="body1" sx={{ direction: isRTL ? 'rtl' : 'ltr' }}>
                            {children}
                          </Typography>
                        )
                      }}
                    >
                      {streamingText}
                    </ReactMarkdown>
                  </Paper>
                </Box>
              )}

              <div ref={messagesEndRef} />
            </Box>

            {/* Input */}
            <Paper elevation={3} sx={{ p: 2 }}>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              {/* Image preview */}
              {imagePreview && (
                <Box sx={{ mb: 2, position: 'relative', display: 'inline-block' }}>
                  <img
                    src={imagePreview}
                    alt="Preview"
                    style={{
                      maxWidth: '200px',
                      maxHeight: '200px',
                      borderRadius: '8px',
                      border: '2px solid #e0e0e0'
                    }}
                  />
                  <IconButton
                    size="small"
                    sx={{
                      position: 'absolute',
                      top: -8,
                      right: -8,
                      bgcolor: 'background.paper',
                      '&:hover': { bgcolor: 'error.light' }
                    }}
                    onClick={clearImage}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              )}

              <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  style={{ display: 'none' }}
                  onChange={handleImageSelect}
                />
                <Tooltip title="إرفاق صورة">
                  <IconButton
                    color="primary"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={sending || !geminiService?.isEnabled()}
                  >
                    <Badge color="secondary" variant="dot" invisible={!selectedImage}>
                      <ImageIcon />
                    </Badge>
                  </IconButton>
                </Tooltip>

                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={selectedImage ? "وصف الصورة (اختياري)" : t('chat.type_message')}
                  disabled={sending}
                  dir={isRTL ? 'rtl' : 'ltr'}
                />
                <IconButton
                  color="primary"
                  onClick={sendMessage}
                  disabled={(!newMessage.trim() && !selectedImage) || sending}
                >
                  {sending ? <CircularProgress size={24} /> : <SendIcon />}
                </IconButton>
              </Box>
            </Paper>
          </>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Typography variant="h6" color="text.secondary">
              {t('chat.select_conversation')}
            </Typography>
          </Box>
        )}
      </Box>

      {/* New Conversation Dialog */}
      <Dialog open={newConversationDialog} onClose={() => setNewConversationDialog(false)}>
        <DialogTitle>{t('chat.new_conversation')}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t('chat.conversation_title')}
            fullWidth
            value={newConversationTitle}
            onChange={(e) => setNewConversationTitle(e.target.value)}
            dir={isRTL ? 'rtl' : 'ltr'}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewConversationDialog(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={createConversation} variant="contained">
            {t('common.create')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Chat;
