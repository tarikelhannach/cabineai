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
  Grid
} from '@mui/material';
import {
  Send as SendIcon,
  Add as AddIcon,
  Chat as ChatIcon,
  SmartToy as AIIcon,
  Description as DocumentIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import api from '../services/api';

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
  
  const messagesEndRef = useRef(null);
  
  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);
  
  // Load messages when conversation selected
  useEffect(() => {
    if (selectedConversation) {
      loadMessages(selectedConversation.id);
    }
  }, [selectedConversation]);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
  
  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;
    
    const userMessage = newMessage.trim();
    setNewMessage('');
    
    // Add user message to UI immediately
    const tempUserMessage = {
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages([...messages, tempUserMessage]);
    
    try {
      setSending(true);
      const response = await api.post('/chat/messages', {
        conversation_id: selectedConversation.id,
        message: userMessage,
        language: i18n.language
      });
      
      // Add AI response to messages
      const aiMessage = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.content,
        sources: response.data.sources,
        created_at: new Date().toISOString()
      };
      
      // Reload messages to get both user and AI messages from server
      await loadMessages(selectedConversation.id);
      
    } catch (err) {
      console.error('Error sending message:', err);
      if (err.response?.status === 503) {
        setError(t('chat.api_key_not_configured'));
      } else {
        setError(t('chat.error_sending_message'));
      }
      // Remove the temporary user message
      setMessages(messages);
    } finally {
      setSending(false);
    }
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
            {isUser ? <ChatIcon sx={{ mr: 1, fontSize: 20 }} /> : <AIIcon sx={{ mr: 1, fontSize: 20 }} />}
            <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
              {isUser ? t('chat.you') : t('chat.ai_assistant')}
            </Typography>
          </Box>
          
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', mb: sources.length > 0 ? 2 : 0 }}>
            {message.content}
          </Typography>
          
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
            <Paper elevation={2} sx={{ p: 2 }}>
              <Typography variant="h6">{selectedConversation.title}</Typography>
            </Paper>
            
            {/* Messages */}
            <Box sx={{ flex: 1, overflow: 'auto', p: 3, bgcolor: 'grey.50' }}>
              {loading && messages.length === 0 ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : messages.length === 0 ? (
                <Box sx={{ textAlign: 'center', p: 4 }}>
                  <AIIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    {t('chat.start_conversation')}
                  </Typography>
                </Box>
              ) : (
                messages.map((message, index) => renderMessage(message, index))
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
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={t('chat.type_message')}
                  disabled={sending}
                  dir={isRTL ? 'rtl' : 'ltr'}
                />
                <IconButton
                  color="primary"
                  onClick={sendMessage}
                  disabled={!newMessage.trim() || sending}
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
