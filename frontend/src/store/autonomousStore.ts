import { create } from 'zustand';
import { apiService } from '../services/api';

// Interfaces for autonomous settings
interface AutonomousTaskConfig {
  enabled: boolean;
  confidence_threshold: number;
}

interface AutonomousSettings {
  auto_archive: AutonomousTaskConfig;
  auto_task_creation: AutonomousTaskConfig;
  auto_meeting_prep: AutonomousTaskConfig;
}

// Interface for autonomous action logs
interface AutonomousActionLog {
  id: string;
  timestamp: string;
  action_type: string;
  email_id: string;
  email_subject: string;
  reasoning: string;
  confidence: number;
  success: boolean;
  result_data?: any;
}

// Store state interface
interface AutonomousState {
  // Settings data
  settings: AutonomousSettings | null;
  originalSettings: AutonomousSettings | null;
  
  // Logs data
  logs: AutonomousActionLog[];
  
  // Loading states
  isLoading: boolean;
  isSaving: boolean;
  isLoadingLogs: boolean;
  
  // Error states
  error: string | null;
  logsError: string | null;
  
  // Actions for settings management
  loadSettings: () => Promise<void>;
  updateSetting: (path: string, value: any) => void;
  saveSettings: () => Promise<boolean>;
  resetSettings: () => void;
  
  // Actions for logs management
  loadLogs: () => Promise<void>;
  clearLogs: () => void;
  
  // Utility actions
  hasUnsavedChanges: () => boolean;
  clearErrors: () => void;
}

// Utility function to set nested property by path
const setNestedProperty = (obj: any, path: string, value: any): void => {
  const keys = path.split('.');
  let current = obj;
  
  for (let i = 0; i < keys.length - 1; i++) {
    if (!(keys[i] in current)) {
      current[keys[i]] = {};
    }
    current = current[keys[i]];
  }
  
  current[keys[keys.length - 1]] = value;
};

// Deep clone utility
const deepClone = <T>(obj: T): T => JSON.parse(JSON.stringify(obj));

// Settings comparison utility
const settingsEqual = (settings1: AutonomousSettings | null, settings2: AutonomousSettings | null): boolean => {
  if (!settings1 || !settings2) return settings1 === settings2;
  return JSON.stringify(settings1) === JSON.stringify(settings2);
};

export const useAutonomousStore = create<AutonomousState>((set, get) => ({
  // Initial state
  settings: null,
  originalSettings: null,
  logs: [],
  isLoading: false,
  isSaving: false,
  isLoadingLogs: false,
  error: null,
  logsError: null,
  
  // Settings management actions
  loadSettings: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const settings = await apiService.getAutonomousSettings();
      
      set({
        settings,
        originalSettings: deepClone(settings),
        isLoading: false
      });
    } catch (error: any) {
      console.error('Failed to load autonomous settings:', error);
      set({
        error: error.message || 'Failed to load settings',
        isLoading: false
      });
    }
  },
  
  updateSetting: (path: string, value: any) => {
    const { settings } = get();
    if (!settings) return;
    
    const newSettings = deepClone(settings);
    setNestedProperty(newSettings, path, value);
    
    set({ settings: newSettings });
  },
  
  saveSettings: async () => {
    const { settings } = get();
    if (!settings) return false;
    
    set({ isSaving: true, error: null });
    
    try {
      await apiService.updateAutonomousSettings(settings);
      
      set({
        originalSettings: deepClone(settings),
        isSaving: false
      });
      
      return true;
    } catch (error: any) {
      console.error('Failed to save autonomous settings:', error);
      set({
        error: error.message || 'Failed to save settings',
        isSaving: false
      });
      return false;
    }
  },
  
  resetSettings: () => {
    const { originalSettings } = get();
    if (originalSettings) {
      set({
        settings: deepClone(originalSettings),
        error: null
      });
    }
  },
  
  // Logs management actions
  loadLogs: async () => {
    set({ isLoadingLogs: true, logsError: null });
    
    try {
      const logs = await apiService.getAutonomousLogs();
      
      set({
        logs,
        isLoadingLogs: false
      });
    } catch (error: any) {
      console.error('Failed to load autonomous logs:', error);
      set({
        logsError: error.message || 'Failed to load logs',
        isLoadingLogs: false
      });
    }
  },
  
  clearLogs: () => {
    set({ logs: [], logsError: null });
  },
  
  // Utility actions
  hasUnsavedChanges: () => {
    const { settings, originalSettings } = get();
    return !settingsEqual(settings, originalSettings);
  },
  
  clearErrors: () => {
    set({ error: null, logsError: null });
  }
}));

// Export types for use in components
export type {
  AutonomousSettings,
  AutonomousTaskConfig,
  AutonomousActionLog
};