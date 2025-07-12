import { useAuthStore } from '../store/authStore';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

class ApiService {
  private getAuthHeaders(): HeadersInit {
    const token = useAuthStore.getState().token;
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    skipAutoLogout = false
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: this.getAuthHeaders(),
      ...options,
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid
        if (!skipAutoLogout) {
          console.warn('API: Received 401 - token may be expired or invalid');
          // Only auto-logout for critical auth endpoints, not dashboard data
          const isCriticalEndpoint = endpoint.includes('/auth/') || endpoint.includes('/logout');
          if (isCriticalEndpoint) {
            useAuthStore.getState().logout();
          }
        }
        throw new ApiError('Authentication required', 401);
      }
      
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { error: response.statusText };
      }
      
      throw new ApiError(
        errorData.error || 'An error occurred',
        response.status,
        errorData
      );
    }

    const data: ApiResponse<T> = await response.json();
    
    if (!data.success) {
      throw new ApiError(data.error || 'Request failed', response.status, data);
    }

    return data.data as T;
  }

  // Authentication
  async googleSignIn(): Promise<{ authorization_url: string; state: string }> {
    return this.request('/api/auth/google-signin', {
      method: 'POST',
    });
  }

  async authCallback(code: string, state: string): Promise<{
    token: string;
    user: { id: string; email: string; name: string };
  }> {
    return this.request('/api/auth/callback', {
      method: 'POST',
      body: JSON.stringify({ code, state }),
    });
  }

  async refreshToken(): Promise<{ token: string }> {
    return this.request('/api/auth/refresh', {
      method: 'POST',
    });
  }

  async logout(): Promise<{ message: string }> {
    return this.request('/api/auth/logout', {
      method: 'POST',
    });
  }

  // Dashboard
  async getDashboardOverview(): Promise<{
    total_emails: number;
    unread_count: number;
    priority_counts: {
      CRITICAL: number;
      HIGH: number;
      MEDIUM: number;
      LOW: number;
    };
    last_updated: string;
  }> {
    return this.request('/api/dashboard/overview', {}, true); // Skip auto-logout for dashboard calls
  }

  async getDashboardInsights(): Promise<{
    daily_email_trend: any[];
    classification_accuracy: number;
    autonomous_actions_count: number;
    feedback_count: number;
  }> {
    return this.request('/api/dashboard/insights', {}, true); // Skip auto-logout for dashboard calls
  }

  // Emails
  async getEmails(params?: {
    page?: number;
    limit?: number;
    priority?: string;
  }): Promise<{
    emails: Array<{
      id: string;
      subject: string;
      sender: string;
      priority: string;
      purpose: string;
      received_date: string;
      unread: boolean;
      summary: string;
    }>;
    page: number;
    total: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.priority) queryParams.append('priority', params.priority);

    const query = queryParams.toString();
    return this.request(`/api/emails${query ? `?${query}` : ''}`);
  }

  async getEmailDetails(emailId: string): Promise<any> {
    return this.request(`/api/emails/${emailId}`);
  }

  async submitEmailFeedback(
    emailId: string,
    feedback: { corrected_priority: string; corrected_intent: string }
  ): Promise<{ message: string }> {
    return this.request(`/api/emails/${emailId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(feedback),
    });
  }

  async executeEmailAction(
    emailId: string,
    action: { type: string; params?: any }
  ): Promise<{ message: string }> {
    return this.request(`/api/emails/${emailId}/action`, {
      method: 'POST',
      body: JSON.stringify(action),
    });
  }

  // Activity
  async getRecentActivity(): Promise<Array<{
    id: string;
    type: string;
    stage: string;
    status: string;
    details: any;
    created_at: string;
    updated_at: string;
  }>> {
    return this.request('/api/activity/recent');
  }

  // Health check
  async healthCheck(): Promise<{
    status: string;
    timestamp: string;
    active_connections: number;
  }> {
    return this.request('/api/health');
  }

  // Test WebSocket functionality
  async testActivityBroadcast(): Promise<{ message: string; activity: any }> {
    return this.request('/api/test/activity', {
      method: 'POST',
    });
  }

  async testSystemStatusBroadcast(): Promise<{ message: string; status: any }> {
    return this.request('/api/test/system-status', {
      method: 'POST',
    });
  }

  async testEmailProcessingSimulation(emailData?: {
    subject?: string;
    sender?: string;
    body?: string;
  }): Promise<{ message: string; email_data: any }> {
    return this.request('/api/test/email-processing', {
      method: 'POST',
      body: JSON.stringify(emailData || {}),
    });
  }

  async processRealGmailEmails(options?: {
    max_emails?: number;
    use_enhanced_reasoning?: boolean;
  }): Promise<{ message: string; max_emails: number; use_enhanced_reasoning: boolean }> {
    return this.request('/api/email/process-real', {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  }

  // Settings
  async getSettings(): Promise<any> {
    return this.request('/api/settings');
  }

  async updateSettings(config: any): Promise<{ message: string; backup_file: string }> {
    return this.request('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getSettingsCategory(category: string): Promise<any> {
    return this.request(`/api/settings/${category}`);
  }

  async updateSettingsCategory(category: string, data: any): Promise<{ message: string }> {
    return this.request(`/api/settings/${category}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async validateSettings(config: any): Promise<{ message: string }> {
    return this.request('/api/settings/validate', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async resetAllSettings(): Promise<{ message: string; backup_file: string }> {
    return this.request('/api/settings/reset', {
      method: 'POST',
    });
  }

  async resetSettingsCategory(category: string): Promise<{ message: string }> {
    return this.request(`/api/settings/reset/${category}`, {
      method: 'POST',
    });
  }

  // Autonomous settings
  async getAutonomousSettings(): Promise<any> {
    return this.request('/api/autonomous/settings');
  }

  async updateAutonomousSettings(settings: any): Promise<{ message: string; settings: any }> {
    return this.request('/api/autonomous/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  async getAutonomousLogs(): Promise<any[]> {
    return this.request('/api/autonomous/logs');
  }

  // Quick Actions
  async retrainModel(): Promise<{ message: string; user_id: string }> {
    return this.request('/api/ml/retrain', {
      method: 'POST',
    });
  }

  async generateReport(): Promise<{
    report: string;
    stats: {
      total_emails: number;
      priority_breakdown: any;
      top_senders: Array<{ sender: string; count: number }>;
      common_purposes: Array<{ purpose: string; count: number }>;
    };
    generated_at: string;
  }> {
    return this.request('/api/reports/generate');
  }

  async performSecurityScan(options?: {
    hours_back?: number;
  }): Promise<{
    threats_found: number;
    summary: string;
    scan_details: Array<{
      email_id: string;
      subject: string;
      sender: string;
      flags: string[];
      llm_analysis?: string;
      risk_level: string;
    }>;
    emails_scanned: number;
    scan_timestamp: string;
  }> {
    return this.request('/api/security/scan', {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  }

  async getAIPerformanceMetrics(options?: {
    days_back?: number;
  }): Promise<{
    classification_accuracy: number;
    total_emails_processed: number;
    total_feedback_received: number;
    average_confidence: number;
    processing_speed_per_day: number;
    autonomous_actions_taken: number;
    average_response_time_seconds: number;
    priority_distribution: any;
    purpose_distribution: any;
    daily_trends: any[];
    time_period_days: number;
    last_updated: string;
  }> {
    const queryParams = new URLSearchParams();
    if (options?.days_back) queryParams.append('days_back', options.days_back.toString());
    
    const query = queryParams.toString();
    return this.request(`/api/ai/performance${query ? `?${query}` : ''}`);
  }

  // ============================================================================
  // Agent API Methods
  // ============================================================================

  async getAgentSuggestions(): Promise<Array<{
    type: string;
    title: string;
    description: string;
    action: string;
    action_params: Record<string, any>;
    priority: 'critical' | 'high' | 'medium' | 'low';
    rationale: string;
    relevance_score: number;
  }>> {
    return this.request('/api/agent/suggestions');
  }

  async processAgentAction(actionData: {
    action: string;
    params: Record<string, any>;
    type?: string;
  }): Promise<{
    response: string;
    action_handled: boolean;
    download_data?: any;
  }> {
    return this.request('/api/agent/actions', {
      method: 'POST',
      body: JSON.stringify(actionData),
    });
  }

  async dismissSuggestion(suggestionType: string): Promise<{
    message: string;
  }> {
    return this.request(`/api/agent/suggestions/${suggestionType}/dismiss`, {
      method: 'POST',
    });
  }

  async sendChatMessage(message: string, context?: any): Promise<{
    response: string;
    intent?: string;
    entities?: Record<string, any>;
    follow_up?: boolean;
    actions?: Array<{
      type: string;
      label: string;
      icon?: string;
      description?: string;
      data: any;
    }>;
    conversation_id?: string;
    processing_time?: number;
    status?: string;
    error_handled?: boolean;
  }> {
    try {
      return await this.request('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message, context }),
      });
    } catch (error) {
      // Enhanced error handling for chat-specific errors
      if (error instanceof ApiError) {
        // Check for specific error types from the enhanced backend
        if (error.data?.error_type) {
          switch (error.data.error_type) {
            case 'validation_error':
              throw new ApiError('Please provide a valid message', error.status, {
                ...error.data,
                chat_specific: true
              });
            case 'message_too_long':
              throw new ApiError('Message is too long. Please shorten your message and try again.', error.status, {
                ...error.data,
                chat_specific: true
              });
            case 'rate_limit_exceeded':
              throw new ApiError('You\'re sending messages too quickly. Please wait a moment before trying again.', error.status, {
                ...error.data,
                chat_specific: true,
                retry_after: 60
              });
            default:
              // For other errors, return a user-friendly chat response
              return {
                response: error.message || 'I\'m having trouble processing your message right now. Please try again.',
                intent: 'error_fallback',
                entities: {},
                actions: [
                  {
                    type: 'retry',
                    label: 'Try Again',
                    icon: '🔄',
                    description: 'Retry your message',
                    data: { action: 'retry' }
                  }
                ],
                follow_up: true,
                status: 'error_handled',
                error_handled: true
              };
          }
        }
      }
      
      // For network errors or other unexpected errors
      return {
        response: 'I\'m having trouble connecting right now. Please check your internet connection and try again.',
        intent: 'connection_error',
        entities: {},
        actions: [
          {
            type: 'retry',
            label: 'Try Again',
            icon: '🔄',
            description: 'Retry your message',
            data: { action: 'retry' }
          },
          {
            type: 'refresh',
            label: 'Refresh Page',
            icon: '↻',
            description: 'Refresh the page and try again',
            data: { action: 'refresh' }
          }
        ],
        follow_up: true,
        status: 'connection_error',
        error_handled: true
      };
    }
  }
}

export const apiService = new ApiService();
export { ApiError };