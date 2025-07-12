import { create } from 'zustand';

export interface Suggestion {
  type: string;
  title: string;
  description: string;
  action: string;
  action_params: Record<string, any>;
  priority: 'critical' | 'high' | 'medium' | 'low';
  rationale: string;
  relevance_score: number;
}

export interface QuickAction {
  type: string;
  label: string;
  icon?: React.ReactNode;
  description?: string;
}

export interface RichMessageData {
  suggestions?: string[];
  actions?: QuickAction[];
  context_hint?: string;
  email_count?: number;
  priority_breakdown?: { [key: string]: number };
  conversation_id?: string;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: string;
  action?: {
    type: string;
    data: any;
  };
  richData?: RichMessageData;
}

export interface ConversationContext {
  intent?: string;
  entities?: Record<string, any>;
  follow_up?: boolean;
  related_emails?: string[];
  conversation_id?: string;
}

interface AgentState {
  // Suggestion state
  suggestions: Suggestion[];
  dismissedSuggestions: Set<string>;
  suggestionsLoading: boolean;
  suggestionsError: string | null;
  
  // Chat state
  messages: ChatMessage[];
  isTyping: boolean;
  chatLoading: boolean;
  chatError: string | null;
  conversationContext: ConversationContext | null;
  
  // UI state
  showChat: boolean;
  showSuggestions: boolean;
  
  // Actions - Suggestions
  setSuggestions: (suggestions: Suggestion[]) => void;
  addSuggestion: (suggestion: Suggestion) => void;
  dismissSuggestion: (type: string) => void;
  undismissSuggestion: (type: string) => void;
  clearDismissedSuggestions: () => void;
  setSuggestionsLoading: (loading: boolean) => void;
  setSuggestionsError: (error: string | null) => void;
  
  // Actions - Chat
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearMessages: () => void;
  setIsTyping: (typing: boolean) => void;
  setChatLoading: (loading: boolean) => void;
  setChatError: (error: string | null) => void;
  setConversationContext: (context: ConversationContext | null) => void;
  
  // Actions - UI
  setShowChat: (show: boolean) => void;
  setShowSuggestions: (show: boolean) => void;
  toggleChat: () => void;
  toggleSuggestions: () => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  // Initial state - Suggestions
  suggestions: [],
  dismissedSuggestions: new Set<string>(),
  suggestionsLoading: false,
  suggestionsError: null,
  
  // Initial state - Chat
  messages: [],
  isTyping: false,
  chatLoading: false,
  chatError: null,
  conversationContext: null,
  
  // Initial state - UI
  showChat: false,
  showSuggestions: true,
  
  // Actions - Suggestions
  setSuggestions: (suggestions: Suggestion[]) => {
    set({ suggestions });
  },
  
  addSuggestion: (suggestion: Suggestion) => {
    set((state) => ({
      suggestions: [...state.suggestions, suggestion],
    }));
  },
  
  dismissSuggestion: (type: string) => {
    set((state) => {
      const newDismissed = new Set(state.dismissedSuggestions);
      newDismissed.add(type);
      return {
        dismissedSuggestions: newDismissed,
        suggestions: state.suggestions.filter(s => s.type !== type)
      };
    });
  },
  
  undismissSuggestion: (type: string) => {
    set((state) => {
      const newDismissed = new Set(state.dismissedSuggestions);
      newDismissed.delete(type);
      return { dismissedSuggestions: newDismissed };
    });
  },
  
  clearDismissedSuggestions: () => {
    set({ dismissedSuggestions: new Set<string>() });
  },
  
  setSuggestionsLoading: (loading: boolean) => {
    set({ suggestionsLoading: loading });
  },
  
  setSuggestionsError: (error: string | null) => {
    set({ suggestionsError: error });
  },
  
  // Actions - Chat
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
    };
    
    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },
  
  setMessages: (messages: ChatMessage[]) => {
    set({ messages });
  },
  
  clearMessages: () => {
    set({ messages: [], conversationContext: null });
  },
  
  setIsTyping: (typing: boolean) => {
    set({ isTyping: typing });
  },
  
  setChatLoading: (loading: boolean) => {
    set({ chatLoading: loading });
  },
  
  setChatError: (error: string | null) => {
    set({ chatError: error });
  },
  
  setConversationContext: (context: ConversationContext | null) => {
    set({ conversationContext: context });
  },
  
  // Actions - UI
  setShowChat: (show: boolean) => {
    set({ showChat: show });
  },
  
  setShowSuggestions: (show: boolean) => {
    set({ showSuggestions: show });
  },
  
  toggleChat: () => {
    set((state) => ({ showChat: !state.showChat }));
  },
  
  toggleSuggestions: () => {
    set((state) => ({ showSuggestions: !state.showSuggestions }));
  },
}));