import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageCircle, 
  Send, 
  X, 
  Minimize2, 
  Maximize2, 
  Bot, 
  User, 
  Loader2,
  Trash2,
  Copy,
  ExternalLink,
  Mail,
  Clock,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  Sparkles,
  Brain
} from 'lucide-react';
import { useAgentStore } from '../../store/agentStore';
import { useToastStore } from '../../store/toastStore';
import { apiService } from '../../services/api';
import { errorToast, successToast } from '../../utils/toastHelpers';

interface ChatInterfaceProps {
  className?: string;
  defaultMinimized?: boolean;
  position?: 'floating' | 'sidebar' | 'inline';
}

interface QuickAction {
  type: string;
  label: string;
  icon?: React.ReactNode;
  description?: string;
}

interface RichMessageData {
  suggestions?: string[];
  actions?: QuickAction[];
  context_hint?: string;
  email_count?: number;
  priority_breakdown?: { [key: string]: number };
  conversation_id?: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  className = '',
  defaultMinimized = false,
  position = 'floating'
}) => {
  const {
    messages,
    isTyping,
    chatLoading,
    chatError,
    showChat,
    conversationContext,
    addMessage,
    clearMessages,
    setIsTyping,
    setChatLoading,
    setChatError,
    setShowChat,
    setConversationContext
  } = useAgentStore();

  const addToast = useToastStore(state => state.addToast);
  
  const [inputValue, setInputValue] = useState('');
  const [isMinimized, setIsMinimized] = useState(defaultMinimized);
  const [isExpanded, setIsExpanded] = useState(false);
  const [quickSuggestions, setQuickSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Enhanced quick suggestions for better UX
  const enhancedSuggestions = [
    "What's important in my inbox?",
    "Summarize today's emails",
    "Show me high priority emails",
    "Any urgent messages?",
    "Help me organize my inbox",
    "Find emails from this week",
    "What patterns do you see in my emails?",
    "Set up filters for me"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Auto-focus input when chat opens
  useEffect(() => {
    if (showChat && !isMinimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showChat, isMinimized]);

  // Listen for external message sending (from quick actions)
  useEffect(() => {
    const handleExternalMessage = (event: CustomEvent) => {
      const message = event.detail;
      if (message && typeof message === 'string') {
        handleSendMessage(message);
      }
    };

    window.addEventListener('sendChatMessage', handleExternalMessage as EventListener);
    return () => {
      window.removeEventListener('sendChatMessage', handleExternalMessage as EventListener);
    };
  }, []);

  const handleSendMessage = async (messageText?: string) => {
    const message = (messageText || inputValue).trim();
    if (!message || chatLoading) return;

    // Add user message to chat
    addMessage({
      type: 'user',
      content: message
    });

    setInputValue('');
    setShowSuggestions(false);
    setChatLoading(true);
    setChatError(null);
    setIsTyping(true);

    try {
      const response = await apiService.sendChatMessage(message, conversationContext);
      
      // Enhanced response handling for rich conversations
      const agentMessage = {
        type: 'agent' as const,
        content: response.response,
        action: response.actions?.[0],
        richData: {
          suggestions: response.follow_up ? generateContextualSuggestions(response) : [],
          actions: response.actions || [],
          conversation_id: response.conversation_id,
          context_hint: response.intent === 'conversational' ? 'I can provide more details or help with related tasks.' : undefined
        } as RichMessageData
      };

      addMessage(agentMessage);

      // Update conversation context with enhanced data
      if (response.intent || response.entities || response.follow_up) {
        setConversationContext({
          intent: response.intent,
          entities: response.entities,
          follow_up: response.follow_up,
          related_emails: response.entities?.email_ids,
          conversation_id: response.conversation_id
        });
      }

      // Set dynamic quick suggestions based on response
      if (response.follow_up) {
        setQuickSuggestions(generateContextualSuggestions(response));
      }

    } catch (error: any) {
      console.error('Enhanced chat error:', error);
      
      // Handle different types of errors gracefully
      let errorResponse;
      
      if (error.data?.chat_specific) {
        // Chat-specific errors that should be handled gracefully
        if (error.data.error_type === 'rate_limit_exceeded') {
          errorResponse = {
            type: 'agent' as const,
            content: error.message,
            richData: {
              actions: [
                {
                  type: 'wait',
                  label: 'Wait 1 minute',
                  icon: '⏰',
                  description: 'Wait before sending another message'
                }
              ],
              context_hint: 'Rate limiting helps maintain system performance'
            }
          };
        } else {
          errorResponse = {
            type: 'agent' as const,
            content: error.message,
            richData: {
              actions: [
                {
                  type: 'retry',
                  label: 'Try Again',
                  icon: '🔄',
                  description: 'Retry your message'
                }
              ]
            }
          };
        }
      } else if (error.data?.error_handled) {
        // Server already handled the error gracefully, treat as normal response
        errorResponse = {
          type: 'agent' as const,
          content: error.data.response || error.message,
          richData: {
            actions: error.data.actions || [],
            context_hint: 'I encountered an issue but I\'m still here to help'
          }
        };
      } else {
        // Unexpected errors
        const errorMessage = error.message || 'Failed to send message';
        setChatError(errorMessage);
        addToast(errorToast('Chat Error', errorMessage));
        
        errorResponse = {
          type: 'agent' as const,
          content: `I encountered an unexpected error: ${errorMessage}. Please try again or refresh the page.`,
          richData: {
            actions: [
              {
                type: 'retry',
                label: 'Try Again',
                icon: '🔄',
                description: 'Retry your message'
              },
              {
                type: 'refresh',
                label: 'Refresh Page',
                icon: '↻',
                description: 'Refresh the page'
              }
            ]
          }
        };
      }
      
      addMessage(errorResponse);
    } finally {
      setChatLoading(false);
      setIsTyping(false);
    }
  };

  // Generate contextual suggestions based on AI response
  const generateContextualSuggestions = (response: any): string[] => {
    const suggestions: string[] = [];
    
    if (response.intent === 'conversational') {
      suggestions.push("Tell me more about this", "What else should I know?", "Any other insights?");
    }
    
    if (response.entities?.priority_filter) {
      suggestions.push("Show me other priorities", "What about low priority emails?", "Help me prioritize");
    }
    
    if (response.entities?.sender_filter) {
      suggestions.push("Show emails from other senders", "Block notifications from this sender", "Create filter for this sender");
    }
    
    // Add contextual suggestions based on response content
    if (response.response.includes('high priority') || response.response.includes('urgent')) {
      suggestions.push("Help me handle urgent emails", "Set up urgent email alerts", "Archive old urgent emails");
    }
    
    if (response.response.includes('summarize') || response.response.includes('summary')) {
      suggestions.push("Get detailed analysis", "Find patterns in these emails", "Export this summary");
    }
    
    // Always include some general helpful suggestions
    suggestions.push("What else can you help with?", "Show me suggestions", "Help me organize");
    
    return suggestions.slice(0, 3); // Return max 3 suggestions
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    setShowSuggestions(false);
    handleSendMessage(suggestion);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    clearMessages();
    setConversationContext(null);
    addToast(successToast('Chat Cleared', 'Conversation history has been cleared.'));
  };

  const copyMessageToClipboard = (content: string) => {
    navigator.clipboard.writeText(content);
    addToast(successToast('Message Copied', 'Message copied to clipboard.'));
  };

  const formatMessageContent = (content: string) => {
    // Convert markdown-like formatting to JSX
    return content.split('\n').map((line, i) => (
      <React.Fragment key={i}>
        {line.split('**').map((part, j) => 
          j % 2 === 1 ? <strong key={j}>{part}</strong> : part
        )}
        {i < content.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };

  // For inline mode, always show the chat interface
  if (!showChat && position !== 'inline') {
    return (
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        onClick={() => setShowChat(true)}
        className={`fixed bottom-6 right-6 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition-colors z-50 ${className}`}
      >
        <MessageCircle className="h-6 w-6" />
      </motion.button>
    );
  }

  const containerClasses = {
    floating: `fixed ${isExpanded ? 'inset-4' : 'bottom-6 right-6 w-96 h-[500px]'} z-50`,
    sidebar: 'h-full',
    inline: 'w-full h-96'
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ 
        opacity: 1, 
        y: 0, 
        scale: 1,
        height: isMinimized ? 'auto' : undefined
      }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden ${containerClasses[position]} ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-750">
        <div className="flex items-center space-x-2">
          <Bot className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {position === 'inline' ? 'Chat Interface' : 'Maia Assistant'}
          </h3>
          {conversationContext?.intent && (
            <span className={`text-xs px-2 py-1 rounded ${
              conversationContext.intent === 'conversational' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400' :
              conversationContext.intent === 'fallback' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400' :
              conversationContext.intent === 'error_fallback' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400' :
              conversationContext.intent === 'system_unavailable' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400' :
              'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400'
            }`}>
              {conversationContext.intent === 'conversational' ? '🟢 Full AI' :
               conversationContext.intent === 'fallback' ? '🟡 Limited' :
               conversationContext.intent === 'error_fallback' ? '🔴 Error Mode' :
               conversationContext.intent === 'system_unavailable' ? '🟠 Basic Mode' :
               conversationContext.intent}
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-1">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              title="Clear chat"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          
          {position === 'floating' && (
            <>
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                title={isMinimized ? 'Expand' : 'Minimize'}
              >
                {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
              </button>
              
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                title={isExpanded ? 'Restore' : 'Expand'}
              >
                <ExternalLink className="h-4 w-4" />
              </button>
              
              <button
                onClick={() => setShowChat(false)}
                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                title="Close chat"
              >
                <X className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Minimized state */}
      {isMinimized && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="p-4"
        >
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Chat minimized. Click the expand button to continue.
          </p>
        </motion.div>
      )}

      {/* Full chat interface */}
      {!isMinimized && (
        <>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <AnimatePresence>
              {messages.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-8"
                >
                  <div className="mb-4">
                    <Bot className="h-16 w-16 text-blue-500 mx-auto mb-3" />
                    <div className="flex items-center justify-center space-x-1 mb-2">
                      <Sparkles className="h-4 w-4 text-blue-500" />
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-white">
                        Hi! I'm Maia
                      </h3>
                      <Sparkles className="h-4 w-4 text-blue-500" />
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                      Your intelligent email assistant. I can help you understand, organize, and manage your emails with natural conversation.
                    </p>
                  </div>
                  
                  {/* Quick start suggestions */}
                  <div className="space-y-2">
                    <p className="text-sm text-gray-500 dark:text-gray-500 mb-3">Try asking me:</p>
                    <div className="grid grid-cols-1 gap-2 max-w-sm mx-auto">
                      {enhancedSuggestions.slice(0, 4).map((suggestion, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSuggestionClick(suggestion)}
                          className="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-lg text-sm hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors text-left"
                        >
                          <div className="flex items-center space-x-2">
                            <MessageCircle className="h-3 w-3" />
                            <span>"{suggestion}"</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ) : (
                messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className={`flex items-start space-x-3 ${
                      message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                    }`}
                  >
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                      message.type === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                    }`}>
                      {message.type === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </div>
                    
                    <div className={`flex-1 max-w-xs sm:max-w-md ${
                      message.type === 'user' ? 'text-right' : ''
                    }`}>
                      <div className={`relative inline-block px-4 py-2 rounded-lg ${
                        message.type === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                      }`}>
                        <div className="text-sm leading-relaxed">
                          {formatMessageContent(message.content)}
                        </div>
                        
                        {/* Enhanced rich content for agent messages */}
                        {message.type === 'agent' && message.richData && (
                          <div className="mt-3 space-y-2">
                            {/* Context hint */}
                            {message.richData.context_hint && (
                              <div className="flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
                                <Brain className="h-3 w-3" />
                                <span>{message.richData.context_hint}</span>
                              </div>
                            )}
                            
                            {/* Quick action buttons */}
                            {message.richData.actions && message.richData.actions.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {message.richData.actions.slice(0, 3).map((action, idx) => (
                                  <button
                                    key={idx}
                                    onClick={() => handleSuggestionClick(action.label)}
                                    className="inline-flex items-center space-x-1 px-2 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                                  >
                                    {action.icon && <span className="h-3 w-3">{action.icon}</span>}
                                    <span>{action.label}</span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Message actions */}
                        <button
                          onClick={() => copyMessageToClipboard(message.content)}
                          className={`absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity ${
                            message.type === 'user' 
                              ? 'bg-blue-700 text-white hover:bg-blue-800' 
                              : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-300 dark:hover:bg-gray-500'
                          }`}
                          title="Copy message"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                      
                      {/* Quick suggestions below agent messages */}
                      {message.type === 'agent' && message.richData?.suggestions && message.richData.suggestions.length > 0 && (
                        <div className="mt-2 space-y-1">
                          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Suggestions:</div>
                          <div className="flex flex-wrap gap-1">
                            {message.richData.suggestions.map((suggestion, idx) => (
                              <button
                                key={idx}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="inline-flex items-center space-x-1 px-2 py-1 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full text-xs hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                              >
                                <ArrowRight className="h-2 w-2" />
                                <span>{suggestion}</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div className={`text-xs text-gray-500 dark:text-gray-400 mt-1 ${
                        message.type === 'user' ? 'text-right' : ''
                      }`}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>

            {/* Typing indicator */}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start space-x-3"
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
                <div className="bg-gray-100 dark:bg-gray-700 px-4 py-2 rounded-lg">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            {chatError && (
              <div className="mb-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-700 dark:text-red-400">
                {chatError}
              </div>
            )}
            
            {/* Quick suggestions bar - show when input is focused or has quick suggestions */}
            {(showSuggestions || quickSuggestions.length > 0) && (
              <div className="mb-3 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">Quick suggestions:</div>
                <div className="flex flex-wrap gap-1">
                  {(quickSuggestions.length > 0 ? quickSuggestions : enhancedSuggestions.slice(0, 3)).map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="inline-flex items-center space-x-1 px-2 py-1 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400 transition-colors border border-gray-200 dark:border-gray-600"
                    >
                      <Sparkles className="h-2 w-2" />
                      <span>{suggestion}</span>
                    </button>
                  ))}
                  {showSuggestions && (
                    <button
                      onClick={() => setShowSuggestions(false)}
                      className="inline-flex items-center px-2 py-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs"
                    >
                      <X className="h-2 w-2" />
                    </button>
                  )}
                </div>
              </div>
            )}
            
            <div className="flex items-end space-x-2">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  onFocus={() => quickSuggestions.length === 0 && setShowSuggestions(true)}
                  placeholder="Ask me anything about your emails... (try natural language!)"
                  disabled={chatLoading}
                  rows={1}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ minHeight: '40px', maxHeight: '120px' }}
                />
                {!inputValue && !chatLoading && (
                  <button
                    onClick={() => setShowSuggestions(!showSuggestions)}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 text-gray-400 hover:text-blue-500 transition-colors"
                    title="Show suggestions"
                  >
                    <Brain className="h-4 w-4" />
                  </button>
                )}
              </div>
              
              <button
                onClick={() => handleSendMessage()}
                disabled={!inputValue.trim() || chatLoading}
                className="p-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Send message"
              >
                {chatLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
            
            {/* Enhanced conversation context hints */}
            {conversationContext?.follow_up && (
              <div className="mt-2 flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
                <Brain className="h-3 w-3" />
                <span>I can provide more details about this topic if needed.</span>
              </div>
            )}
            
            {conversationContext?.conversation_id && (
              <div className="mt-1 text-xs text-gray-400">
                Conversation continues • {messages.length} messages
              </div>
            )}
          </div>
        </>
      )}
    </motion.div>
  );
};

export default ChatInterface;