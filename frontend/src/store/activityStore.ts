import { create } from 'zustand';

export interface ChartData {
  label: string;
  value: number;
  color: string;
}

export interface Charts {
  pie_chart?: {
    title: string;
    data: ChartData[];
  };
  bar_chart?: {
    title: string;
    data: ChartData[];
  };
}

export interface ThreatDetails {
  email_id: string;
  subject: string;
  sender: string;
  flags: string[];
  llm_analysis?: string;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface ActivityItem {
  id: string;
  type: 'email_processing' | 'autonomous_task' | 'autonomous_action' | 'ml_training' | 'report_generation' | 'security_scan';
  stage: 'fetch' | 'analyze' | 'classify' | 'suggest' | 'execute' | 'execution' | 'initialize' | 'complete' | 'error' | 'processing' | 'scanning' | 'gathering_data' | 'analyzing_patterns' | 'generating_insights';
  status: 'started' | 'in_progress' | 'completed' | 'error' | 'failed';
  title: string;
  description?: string;
  progress?: number; // 0-100
  confidence?: number; // 0-1
  email_id?: string;
  charts?: Charts; // Chart data for report generation
  scan_details?: ThreatDetails[]; // Security scan threat details
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface SystemStatus {
  is_processing: boolean;
  last_email_check: string;
  active_tasks: string[];
  ml_training_status?: {
    is_training: boolean;
    progress: number;
    estimated_completion?: string;
  };
  autonomous_mode: boolean;
  last_updated: string;
}

interface ActivityState {
  activities: ActivityItem[];
  systemStatus: SystemStatus | null;
  isConnected: boolean;
  
  // Actions
  addActivity: (activity: ActivityItem) => void;
  updateActivity: (id: string, updates: Partial<ActivityItem>) => void;
  removeActivity: (id: string) => void;
  clearActivities: () => void;
  updateSystemStatus: (status: SystemStatus) => void;
  setConnectionStatus: (connected: boolean) => void;
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  activities: [],
  systemStatus: null,
  isConnected: false,
  
  addActivity: (activity: ActivityItem) => {
    set((state) => {
      // Check for duplicates to prevent unnecessary re-renders
      const existingIndex = state.activities.findIndex(a => a.id === activity.id);
      if (existingIndex >= 0) {
        // Update existing activity instead of adding duplicate
        const updatedActivities = [...state.activities];
        updatedActivities[existingIndex] = { ...updatedActivities[existingIndex], ...activity };
        return { activities: updatedActivities };
      }
      
      return {
        activities: [activity, ...state.activities].slice(0, 50), // Keep last 50 activities
      };
    });
  },
  
  updateActivity: (id: string, updates: Partial<ActivityItem>) => {
    set((state) => {
      const existingIndex = state.activities.findIndex(a => a.id === id);
      if (existingIndex === -1) return state; // No change if activity doesn't exist
      
      const existingActivity = state.activities[existingIndex];
      
      // Check if updates actually change anything to prevent unnecessary re-renders
      const hasChanges = Object.keys(updates).some(key => 
        (updates as any)[key] !== (existingActivity as any)[key]
      );
      
      if (!hasChanges) return state;
      
      const updatedActivities = [...state.activities];
      updatedActivities[existingIndex] = { ...existingActivity, ...updates };
      
      return { activities: updatedActivities };
    });
  },
  
  removeActivity: (id: string) => {
    set((state) => {
      const newActivities = state.activities.filter((activity) => activity.id !== id);
      // Only update if something was actually removed
      return newActivities.length !== state.activities.length 
        ? { activities: newActivities }
        : state;
    });
  },
  
  clearActivities: () => {
    set((state) => state.activities.length > 0 ? { activities: [] } : state);
  },
  
  updateSystemStatus: (status: SystemStatus) => {
    set((state) => {
      // Shallow comparison to prevent unnecessary updates
      if (JSON.stringify(state.systemStatus) === JSON.stringify(status)) {
        return state;
      }
      return { systemStatus: status };
    });
  },
  
  setConnectionStatus: (connected: boolean) => {
    set((state) => state.isConnected !== connected ? { isConnected: connected } : state);
  },
}));