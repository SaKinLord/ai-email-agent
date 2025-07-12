import { create } from 'zustand';

export interface Email {
  id: string;
  subject: string;
  sender: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  purpose?: string; // Optional since some emails might not have purpose classified yet
  received_date: string;
  unread: boolean;
  summary: string;
  content: string;
  
  // UI state fields - guaranteed by backend defensive transformation
  isRead: boolean;
  isStarred: boolean;
  isArchived: boolean;
  labels: string[];
  
  // Optional fields
  confidence?: number;
  threadId?: string;
  user_id?: string;
  processed_timestamp?: string;
}

export interface DashboardData {
  total_emails: number;
  unread_count: number;
  priority_counts: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  last_updated: string;
  
  // Enhanced AI Performance Metrics
  ai_performance?: {
    classification_accuracy: number;
    auto_actions_today: number;
    time_saved: string;
    security_score: number;
  };
  
  // Additional performance details
  performance_details?: {
    total_feedback_count: number;
    action_breakdown: {
      auto_archive?: number;
      auto_summary?: number;
      auto_task?: number;
      auto_reply?: number;
      auto_label?: number;
    };
    security_risks: {
      suspicious_senders?: number;
      suspicious_links?: number;
      urgent_language?: number;
      unverified_senders?: number;
    };
    calculation_timestamp: string;
  };
  
  // Legacy fields for backward compatibility
  email_change_24h?: number;
  unread_change_24h?: number;
  priority_change_24h?: number;
  ml_accuracy?: number;
  ml_model_version?: string;
  autonomous_actions_today?: number;
  time_saved_minutes?: number;
  security_score?: number;
}

interface EmailState {
  emails: Email[];
  dashboardData: DashboardData | null;
  currentEmail: Email | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  setEmails: (emails: Email[]) => void;
  addEmail: (email: Email) => void;
  updateEmail: (id: string, updates: Partial<Email>) => void;
  setCurrentEmail: (email: Email | null) => void;
  setDashboardData: (data: DashboardData) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useEmailStore = create<EmailState>((set) => ({
  emails: [],
  dashboardData: null,
  currentEmail: null,
  loading: false,
  error: null,
  
  setEmails: (emails: Email[]) => {
    set({ emails });
  },
  
  addEmail: (email: Email) => {
    set((state) => ({
      emails: [email, ...state.emails],
    }));
  },
  
  updateEmail: (id: string, updates: Partial<Email>) => {
    set((state) => ({
      emails: state.emails.map((email) =>
        email.id === id ? { ...email, ...updates } : email
      ),
    }));
  },
  
  setCurrentEmail: (email: Email | null) => {
    set({ currentEmail: email });
  },
  
  setDashboardData: (data: DashboardData) => {
    set({ dashboardData: data });
  },
  
  setLoading: (loading: boolean) => {
    set({ loading });
  },
  
  setError: (error: string | null) => {
    set({ error });
  },
}));