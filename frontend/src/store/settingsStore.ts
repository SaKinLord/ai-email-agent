import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiService } from '../services/api';

// Configuration interfaces based on config.template.json structure
interface GmailSettings {
  scopes: string[];
  token_path: string;
  credentials_path: string;
  fetch_max_results: number;
  fetch_labels: string[];
}

interface LLMSettings {
  provider: string;
  api_key_env_var: string;
  model_name: string;
  analysis_max_input_chars: number;
  analysis_max_tokens: number;
  analysis_temperature: number;
  summary_max_input_chars: number;
  summary_max_tokens: number;
  summary_temperature: number;
  api_delay_seconds: number;
}

interface ClassificationSettings {
  important_senders: string[];
  subject_keywords_high: string[];
  subject_keywords_low: string[];
  sender_keywords_low: string[];
}

interface MLSettings {
  pipeline_filename: string;
  label_encoder_filename: string;
  min_feedback_for_retrain: number;
}

interface RetrainingSettings {
  enabled: boolean;
  trigger_feedback_count: number;
  state_filepath: string;
}

interface LLMModernSettings {
  model: string;
  max_tokens: number;
  hybrid_mode: boolean;
  gpt_budget_monthly: number;
  claude_budget_monthly: number;
}

interface AutonomousTaskConfig {
  enabled: boolean;
  confidence_threshold: number;
}

interface AutonomousTasksSettings {
  auto_archive: AutonomousTaskConfig;
  auto_meeting_prep: AutonomousTaskConfig;
  auto_task_creation: AutonomousTaskConfig;
}

interface ReplySuggestionsSettings {
  enabled: boolean;
  max_suggestions: number;
  exclude_purposes: string[];
}

interface WebhookSettings {
  timeout_seconds: number;
  verify_ssl: boolean;
}

interface IntegrationsSettings {
  task_webhook_url: string;
  reply_suggestions: ReplySuggestionsSettings;
  webhook_settings: WebhookSettings;
}

interface ReasoningSettings {
  enabled: boolean;
  explanation_detail_level: string;
  confidence_thresholds: { [key: string]: number };
}

interface AgendaSynthesisSettings {
  enabled: boolean;
  max_emails: number;
  max_tasks: number;
  max_events: number;
  refresh_interval_minutes: number;
  fallback_enabled: boolean;
}

// Complete configuration interface
interface Configuration {
  gmail: GmailSettings;
  llm: LLMSettings;
  classification: ClassificationSettings;
  database: { filepath: string };
  ml: MLSettings;
  retraining: RetrainingSettings;
  llm_settings: LLMModernSettings;
  autonomous_tasks: AutonomousTasksSettings;
  integrations: IntegrationsSettings;
  reasoning: ReasoningSettings;
  agenda_synthesis: AgendaSynthesisSettings;
}

// Settings panel UI state
interface SettingsPanelState {
  isExpanded: boolean;
  activeSection: string | null;
  hasUnsavedChanges: boolean;
  expandedSections: Set<string>;
}

// Validation state
interface ValidationState {
  isValidating: boolean;
  validationErrors: { [path: string]: string };
  lastValidated: Date | null;
}

// Store state interface
interface SettingsState {
  // Configuration data
  config: Configuration | null;
  originalConfig: Configuration | null;
  
  // Panel state
  panel: SettingsPanelState;
  
  // Validation state
  validation: ValidationState;
  
  // Loading states
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  
  // Actions for configuration management
  loadSettings: () => Promise<void>;
  updateSettings: <K extends keyof Configuration>(category: K, updates: Partial<Configuration[K]>) => void;
  updateSettingValue: (path: string, value: any) => void;
  saveSettings: (category?: keyof Configuration) => Promise<boolean>;
  resetCategory: <K extends keyof Configuration>(category: K) => Promise<void>;
  resetAllSettings: () => Promise<void>;
  validateSettings: (category?: keyof Configuration) => Promise<boolean>;
  
  // Actions for panel state
  togglePanel: () => void;
  setActiveSection: (section: string | null) => void;
  toggleSection: (section: string) => void;
  expandAllSections: () => void;
  collapseAllSections: () => void;
  
  // Actions for change management
  discardChanges: () => void;
  hasChanges: () => boolean;
  getChangedCategories: () => (keyof Configuration)[];
  
  // Utility actions
  clearValidationErrors: () => void;
  addValidationError: (path: string, message: string) => void;
}

// Default configuration values
const defaultConfig: Configuration = {
  gmail: {
    scopes: [
      "https://www.googleapis.com/auth/gmail.readonly",
      "https://www.googleapis.com/auth/gmail.modify"
    ],
    token_path: "token.json",
    credentials_path: "credentials.json",
    fetch_max_results: 150,
    fetch_labels: ["INBOX", "UNREAD"]
  },
  llm: {
    provider: "anthropic",
    api_key_env_var: "ANTHROPIC_API_KEY",
    model_name: "claude-3-haiku-20240307",
    analysis_max_input_chars: 4500,
    analysis_max_tokens: 100,
    analysis_temperature: 0.6,
    summary_max_input_chars: 9000,
    summary_max_tokens: 150,
    summary_temperature: 0.5,
    api_delay_seconds: 2
  },
  classification: {
    important_senders: [],
    subject_keywords_high: ["urgent", "action required", "important", "meeting request", "deadline"],
    subject_keywords_low: ["newsletter", "promotion", "update", "social", "notification", "digest"],
    sender_keywords_low: ["noreply", "newsletter", "notifications", "support", "marketing"]
  },
  database: {
    filepath: "email_agent_memory.db"
  },
  ml: {
    pipeline_filename: "feature_pipeline.joblib",
    label_encoder_filename: "label_encoder.joblib",
    min_feedback_for_retrain: 5
  },
  retraining: {
    enabled: true,
    trigger_feedback_count: 10,
    state_filepath: "retrain_state.json"
  },
  llm_settings: {
    model: "claude-3-haiku-20240307",
    max_tokens: 1000,
    hybrid_mode: true,
    gpt_budget_monthly: 120.0,
    claude_budget_monthly: 5.0
  },
  autonomous_tasks: {
    auto_archive: { enabled: true, confidence_threshold: 0.95 },
    auto_meeting_prep: { enabled: true, confidence_threshold: 0.90 },
    auto_task_creation: { enabled: true, confidence_threshold: 0.90 }
  },
  integrations: {
    task_webhook_url: "",
    reply_suggestions: {
      enabled: true,
      max_suggestions: 3,
      exclude_purposes: ["promotion", "social", "newsletter"]
    },
    webhook_settings: {
      timeout_seconds: 30,
      verify_ssl: true
    }
  },
  reasoning: {
    enabled: true,
    explanation_detail_level: "standard",
    confidence_thresholds: { archive: 95, priority_adjust: 80 }
  },
  agenda_synthesis: {
    enabled: true,
    max_emails: 5,
    max_tasks: 10,
    max_events: 8,
    refresh_interval_minutes: 30,
    fallback_enabled: true
  }
};

// Utility function to deep clone object
const deepClone = <T>(obj: T): T => JSON.parse(JSON.stringify(obj));

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

// Utility function to compare configurations
const configsEqual = (config1: Configuration | null, config2: Configuration | null): boolean => {
  if (!config1 || !config2) return config1 === config2;
  return JSON.stringify(config1) === JSON.stringify(config2);
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      // Initial state
      config: null,
      originalConfig: null,
      
      panel: {
        isExpanded: false,
        activeSection: null,
        hasUnsavedChanges: false,
        expandedSections: new Set() // All sections collapsed by default
      },
      
      validation: {
        isValidating: false,
        validationErrors: {},
        lastValidated: null
      },
      
      isLoading: false,
      isSaving: false,
      lastSaved: null,
      
      // Configuration management actions
      loadSettings: async () => {
        set({ isLoading: true });
        
        try {
          const config = await apiService.getSettings();
          
          set({
            config,
            originalConfig: deepClone(config),
            isLoading: false
          });
        } catch (error) {
          console.error('Failed to load settings:', error);
          // Fallback to default config if API fails
          set({
            config: deepClone(defaultConfig),
            originalConfig: deepClone(defaultConfig),
            isLoading: false
          });
        }
      },
      
      updateSettings: <K extends keyof Configuration>(category: K, updates: Partial<Configuration[K]>) => {
        const { config } = get();
        if (!config) return;
        
        const newConfig = deepClone(config);
        newConfig[category] = { ...newConfig[category], ...updates } as Configuration[K];
        
        set({
          config: newConfig,
          panel: { ...get().panel, hasUnsavedChanges: true }
        });
      },
      
      updateSettingValue: (path, value) => {
        const { config } = get();
        if (!config) return;
        
        const newConfig = deepClone(config);
        setNestedProperty(newConfig, path, value);
        
        set({
          config: newConfig,
          panel: { ...get().panel, hasUnsavedChanges: true }
        });
      },
      
      saveSettings: async (category) => {
        const { config } = get();
        if (!config) return false;
        
        set({ isSaving: true });
        
        try {
          if (category) {
            await apiService.updateSettingsCategory(category, config[category]);
          } else {
            await apiService.updateSettings(config);
          }
          
          set({
            originalConfig: deepClone(config),
            panel: { ...get().panel, hasUnsavedChanges: false },
            lastSaved: new Date(),
            isSaving: false
          });
          
          return true;
        } catch (error) {
          console.error('Failed to save settings:', error);
          set({ isSaving: false });
          return false;
        }
      },
      
      resetCategory: async <K extends keyof Configuration>(category: K) => {
        try {
          await apiService.resetSettingsCategory(category as string);
          
          // Reload settings after reset
          await get().loadSettings();
        } catch (error) {
          console.error('Failed to reset category:', error);
        }
      },
      
      resetAllSettings: async () => {
        try {
          await apiService.resetAllSettings();
          
          // Reload settings after reset
          await get().loadSettings();
          
          set({
            panel: { ...get().panel, hasUnsavedChanges: false },
            validation: { ...get().validation, validationErrors: {} }
          });
        } catch (error) {
          console.error('Failed to reset all settings:', error);
        }
      },
      
      validateSettings: async (category) => {
        const { config } = get();
        if (!config) return false;
        
        set({
          validation: { ...get().validation, isValidating: true }
        });
        
        try {
          const dataToValidate = category ? config[category] : config;
          await apiService.validateSettings(dataToValidate);
          
          set({
            validation: {
              isValidating: false,
              validationErrors: {},
              lastValidated: new Date()
            }
          });
          
          return true;
        } catch (error: any) {
          console.error('Validation failed:', error);
          
          // Extract validation errors from API response if available
          const validationErrors = error.data?.validation_errors 
            ? error.data.validation_errors.reduce((acc: any, msg: string) => {
                acc[msg] = msg;
                return acc;
              }, {})
            : { general: error.message || 'Validation failed' };
          
          set({
            validation: {
              ...get().validation,
              isValidating: false,
              validationErrors
            }
          });
          return false;
        }
      },
      
      // Panel state actions
      togglePanel: () => {
        set({
          panel: { ...get().panel, isExpanded: !get().panel.isExpanded }
        });
      },
      
      setActiveSection: (section) => {
        set({
          panel: { ...get().panel, activeSection: section }
        });
      },
      
      toggleSection: (section) => {
        const { expandedSections } = get().panel;
        const newExpanded = new Set(expandedSections);
        
        if (newExpanded.has(section)) {
          newExpanded.delete(section);
        } else {
          newExpanded.add(section);
        }
        
        set({
          panel: { ...get().panel, expandedSections: newExpanded }
        });
      },
      
      expandAllSections: () => {
        const allSections = Object.keys(defaultConfig) as (keyof Configuration)[];
        set({
          panel: {
            ...get().panel,
            expandedSections: new Set(allSections)
          }
        });
      },
      
      collapseAllSections: () => {
        set({
          panel: { ...get().panel, expandedSections: new Set() }
        });
      },
      
      // Change management actions
      discardChanges: () => {
        const { originalConfig } = get();
        if (originalConfig) {
          set({
            config: deepClone(originalConfig),
            panel: { ...get().panel, hasUnsavedChanges: false },
            validation: { ...get().validation, validationErrors: {} }
          });
        }
      },
      
      hasChanges: () => {
        const { config, originalConfig } = get();
        if (!config || !originalConfig) return false;
        return !configsEqual(config, originalConfig);
      },
      
      getChangedCategories: () => {
        const { config, originalConfig } = get();
        if (!config || !originalConfig) return [];
        
        const categories: (keyof Configuration)[] = [];
        for (const key in config) {
          const categoryKey = key as keyof Configuration;
          if (JSON.stringify(config[categoryKey]) !== JSON.stringify(originalConfig[categoryKey])) {
            categories.push(categoryKey);
          }
        }
        return categories;
      },
      
      // Utility actions
      clearValidationErrors: () => {
        set({
          validation: { ...get().validation, validationErrors: {} }
        });
      },
      
      addValidationError: (path, message) => {
        set({
          validation: {
            ...get().validation,
            validationErrors: {
              ...get().validation.validationErrors,
              [path]: message
            }
          }
        });
      }
    }),
    {
      name: 'settings-storage',
      partialize: (state) => ({
        panel: {
          isExpanded: state.panel.isExpanded,
          expandedSections: Array.from(state.panel.expandedSections)
        }
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.panel?.expandedSections) {
          // Convert array back to Set after rehydration
          const expandedArray = state.panel.expandedSections as unknown as string[];
          state.panel.expandedSections = new Set(expandedArray);
        }
      }
    }
  )
);

// Export types for use in components
export type {
  Configuration,
  GmailSettings,
  LLMSettings,
  ClassificationSettings,
  MLSettings,
  RetrainingSettings,
  LLMModernSettings,
  AutonomousTasksSettings,
  IntegrationsSettings,
  ReasoningSettings,
  AgendaSynthesisSettings,
  SettingsPanelState,
  ValidationState
};