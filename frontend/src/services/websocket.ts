import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '../store/authStore';
import { useActivityStore, ActivityItem, SystemStatus } from '../store/activityStore';

class WebSocketService {
  private static instance: WebSocketService | null = null;
  private socket: Socket | null = null;
  private isInitialized = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000; // 5 seconds
  private activityUpdateQueue: ActivityItem[] = [];
  private updateBatchTimeout: NodeJS.Timeout | null = null;
  private readonly BATCH_DELAY = 50; // ms - batch updates for better performance

  // Private constructor to enforce singleton pattern
  private constructor() {}

  // Singleton instance getter
  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  // Initialize the socket instance once and only once during app lifetime
  private initializeSocket(): void {
    if (this.isInitialized) {
      return; // Socket already created, never create another one
    }

    const wsUrl = process.env.REACT_APP_WS_URL || 'http://localhost:5000';
    
    console.log('WebSocket: Creating single socket instance for app lifetime:', wsUrl);
    this.socket = io(wsUrl, {
      auth: { token: '' }, // Will be updated dynamically
      autoConnect: false,
      reconnection: false,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectInterval,
      // Fix transport upgrade issues
      transports: ['polling'], // Start with polling only to avoid upgrade issues
      upgrade: false, // Disable automatic transport upgrade
      forceNew: false, // Reuse connection when possible
      timeout: 20000, // 20 second timeout
    });

    this.setupEventListeners();
    this.isInitialized = true;
  }

  // Idempotent connect method - safe to call multiple times
  connect(): void {
    const token = useAuthStore.getState().token;
    const isAuthenticated = useAuthStore.getState().isAuthenticated;
    
    console.log('WebSocket: connect() called - token present:', !!token, 'isAuthenticated:', isAuthenticated);
    
    if (!token) {
      console.warn('WebSocket: No auth token available during connect attempt');
      return;
    }

    // Initialize socket if not done yet (only happens once)
    if (!this.isInitialized) {
      console.log('WebSocket: Initializing socket for first time');
      this.initializeSocket();
    }

    // If already connected, do nothing
    if (this.socket && this.socket.connected) {
      console.log('WebSocket: Already connected, skipping duplicate connect');
      return;
    }

    // Update auth token for this connection attempt
    if (this.socket) {
      this.socket.auth = { token };
      console.log('WebSocket: Connecting with updated token, socket state:', this.socket.connected ? 'connected' : 'disconnected');
      this.socket.connect();
    }
  }

  // Idempotent disconnect method - safe to call multiple times
  disconnect(): void {
    if (this.socket && this.socket.connected) {
      console.log('WebSocket: Disconnecting');
      this.socket.disconnect();
    } else {
      console.log('WebSocket: Already disconnected or no socket');
    }
    
    useActivityStore.getState().setConnectionStatus(false);
    this.reconnectAttempts = 0;
    this.cleanup();
  }


  private setupEventListeners(): void {
    if (!this.socket) return;

    // Remove any existing listeners to prevent duplicates
    this.socket.removeAllListeners();

    this.socket.on('connect', () => {
      console.log('WebSocket: Connected successfully');
      useActivityStore.getState().setConnectionStatus(true);
      this.reconnectAttempts = 0;
      
      // Subscribe to activities
      this.socket?.emit('subscribe_activities');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket: Disconnected -', reason);
      useActivityStore.getState().setConnectionStatus(false);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket: Connection error -', error);
      useActivityStore.getState().setConnectionStatus(false);
      
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('WebSocket: Max reconnection attempts reached');
        this.disconnect();
      }
    });

    this.socket.on('connection_status', (data) => {
      console.log('Connection status:', data);
    });

    this.socket.on('subscription_status', (data) => {
      console.log('Subscription status:', data);
    });

    // Activity updates - batched for performance
    this.socket.on('activity_update', (activity: ActivityItem) => {
      console.log('Activity update received:', activity);
      this.queueActivityUpdate(activity);
    });

    this.socket.on('system_status_update', (status: SystemStatus) => {
      console.log('System status update:', status);
      useActivityStore.getState().updateSystemStatus(status);
    });

    // Email processing events - Enhanced to match backend broadcasts
    this.socket.on('email_processing_started', (data) => {
      console.log('Email processing started:', data);
      const activity: ActivityItem = {
        id: `email_${data.email_id}_start`,
        type: 'email_processing',
        stage: 'fetch',
        status: 'started',
        title: `Processing: ${data.subject || 'New Email'}`,
        description: `From: ${data.sender || 'Unknown'}`,
        email_id: data.email_id,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('llm_analysis_complete', (data) => {
      console.log('LLM analysis complete:', data);
      const activity: ActivityItem = {
        id: `email_${data.email_id}_llm`,
        type: 'email_processing',
        stage: 'analyze',
        status: 'completed',
        title: `LLM Analysis Complete`,
        description: `Purpose: ${data.purpose}, Priority: ${data.priority}, Urgency: ${data.urgency}`,
        confidence: data.confidence,
        email_id: data.email_id,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('classification_complete', (data) => {
      console.log('Classification complete:', data);
      const activity: ActivityItem = {
        id: `email_${data.email_id}_classify`,
        type: 'email_processing',
        stage: 'classify',
        status: 'completed',
        title: `ML Classification Complete`,
        description: `Priority: ${data.priority}${data.confidence && data.confidence > 0 ? ` (${(data.confidence * 100).toFixed(0)}% confidence)` : ''}`,
        confidence: data.confidence,
        email_id: data.email_id,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('suggestion_generated', (data) => {
      console.log('Suggestion generated:', data);
      const activity: ActivityItem = {
        id: `suggestion_${data.email_id}_${Date.now()}`,
        type: 'email_processing',
        stage: 'suggest',
        status: 'completed',
        title: 'Suggestion Generated',
        description: data.suggestion || 'New suggestion available',
        email_id: data.email_id,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('autonomous_action_executed', (data) => {
      console.log('Autonomous action executed:', data);
      const activity: ActivityItem = {
        id: `autonomous_${data.email_id}_${Date.now()}`,
        type: 'autonomous_action',
        stage: 'execution',
        status: 'completed',
        title: `Autonomous Action: ${data.action}`,
        description: data.details || 'Action completed successfully',
        email_id: data.email_id,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('training_progress', (data) => {
      console.log('Training progress:', data);
      const activity: ActivityItem = {
        id: `training_${Date.now()}`,
        type: 'ml_training',
        stage: 'execute',
        status: data.progress === 100 ? 'completed' : 'in_progress',
        title: 'ML Model Training',
        description: `Training progress: ${data.progress}% - ${data.details || ''}`,
        progress: data.progress,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('ml_training_started', (data) => {
      console.log('ML training started:', data);
      const activity: ActivityItem = {
        id: `ml_training_${Date.now()}`,
        type: 'ml_training',
        stage: 'initialize',
        status: 'in_progress',
        title: '🧠 AI Model Retraining',
        description: 'Starting model retraining with your feedback...',
        progress: 0,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('ml_training_progress', (data) => {
      console.log('ML training progress:', data);
      const activity: ActivityItem = {
        id: `ml_training_${data.step || 'progress'}`,
        type: 'ml_training',
        stage: data.step || 'training',
        status: 'in_progress',
        title: '🧠 AI Model Retraining',
        description: data.message || 'Training in progress...',
        progress: data.progress || 0,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('ml_training_complete', (data) => {
      console.log('ML training complete:', data);
      const activity: ActivityItem = {
        id: `ml_training_complete_${Date.now()}`,
        type: 'ml_training',
        stage: 'complete',
        status: 'completed',
        title: '✅ AI Model Retrained Successfully',
        description: data.message || `Model trained with ${data.training_samples || 0} feedback entries`,
        progress: 100,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('ml_training_error', (data) => {
      console.log('ML training error:', data);
      const activity: ActivityItem = {
        id: `ml_training_error_${Date.now()}`,
        type: 'ml_training',
        stage: 'error',
        status: 'failed',
        title: '❌ AI Model Training Failed',
        description: data.error || 'Training failed. Please try again.',
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    // Report Generation Events
    this.socket.on('report_generation_started', (data) => {
      console.log('Report generation started:', data);
      const activity: ActivityItem = {
        id: `report_generation_${Date.now()}`,
        type: 'report_generation',
        stage: 'initialize',
        status: 'in_progress',
        title: '📊 Generating Email Report',
        description: 'Starting email insights report generation...',
        progress: 0,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('report_generation_progress', (data) => {
      console.log('Report generation progress:', data);
      const activity: ActivityItem = {
        id: `report_generation_${data.step || 'progress'}`,
        type: 'report_generation',
        stage: data.step || 'processing',
        status: 'in_progress',
        title: '📊 Generating Email Report',
        description: data.message || 'Generating report...',
        progress: data.progress || 0,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('report_generation_complete', (data) => {
      console.log('Report generation complete:', data);
      const activity: ActivityItem = {
        id: `report_generation_complete_${Date.now()}`,
        type: 'report_generation',
        stage: 'complete',
        status: 'completed',
        title: '✅ Email Report Generated',
        description: data.message || `Report generated with insights from ${data.total_emails || 0} emails`,
        progress: 100,
        charts: data.charts || undefined,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    // Security Scan Events
    this.socket.on('security_scan_started', (data) => {
      console.log('Security scan started:', data);
      const activity: ActivityItem = {
        id: `security_scan_${Date.now()}`,
        type: 'security_scan',
        stage: 'initialize',
        status: 'in_progress',
        title: '🛡️ Security Scan Started',
        description: data.message || `Starting security scan of emails from last ${data.hours_back || 24} hours...`,
        progress: 0,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('security_scan_progress', (data) => {
      console.log('Security scan progress:', data);
      const activity: ActivityItem = {
        id: `security_scan_${data.step || 'progress'}`,
        type: 'security_scan',
        stage: data.step || 'scanning',
        status: 'in_progress',
        title: '🛡️ Security Scan in Progress',
        description: data.message || 'Scanning emails for security threats...',
        progress: data.progress || 0,
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });

    this.socket.on('security_scan_complete', (data) => {
      console.log('Security scan complete:', data);
      const threats_found = data.threats_found || 0;
      const activity: ActivityItem = {
        id: `security_scan_complete_${Date.now()}`,
        type: 'security_scan',
        stage: 'complete',
        status: 'completed',
        title: threats_found > 0 ? '⚠️ Security Threats Found' : '✅ Security Scan Complete',
        description: data.message || `Scan complete: ${threats_found} threats found in ${data.emails_scanned || 0} emails`,
        progress: 100,
        scan_details: data.scan_details || [],
        created_at: data.timestamp || new Date().toISOString(),
        updated_at: data.timestamp || new Date().toISOString(),
      };
      
      this.queueActivityUpdate(activity);
    });
  }


  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  // Manual subscription methods
  subscribeToActivities(): void {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_activities');
    }
  }

  unsubscribeFromActivities(): void {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_activities');
    }
  }

  // Performance optimization: batch activity updates
  private queueActivityUpdate(activity: ActivityItem): void {
    // Add to queue, removing duplicates based on ID
    const existingIndex = this.activityUpdateQueue.findIndex(a => a.id === activity.id);
    if (existingIndex >= 0) {
      this.activityUpdateQueue[existingIndex] = activity;
    } else {
      this.activityUpdateQueue.push(activity);
    }

    // Clear existing timeout
    if (this.updateBatchTimeout) {
      clearTimeout(this.updateBatchTimeout);
    }

    // Set new timeout to process batch
    this.updateBatchTimeout = setTimeout(() => {
      this.processBatchedUpdates();
    }, this.BATCH_DELAY);
  }

  private processBatchedUpdates(): void {
    if (this.activityUpdateQueue.length === 0) return;

    const activityStore = useActivityStore.getState();
    
    // Process all queued updates
    this.activityUpdateQueue.forEach(activity => {
      const existingActivity = activityStore.activities.find(a => a.id === activity.id);
      
      if (existingActivity) {
        activityStore.updateActivity(activity.id, activity);
      } else {
        activityStore.addActivity(activity);
      }
    });

    // Clear the queue
    this.activityUpdateQueue = [];
    this.updateBatchTimeout = null;
  }

  // Cleanup on disconnect
  private cleanup(): void {
    if (this.updateBatchTimeout) {
      clearTimeout(this.updateBatchTimeout);
      this.updateBatchTimeout = null;
    }
    this.activityUpdateQueue = [];
  }
}

export const websocketService = WebSocketService.getInstance();