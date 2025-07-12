import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings, 
  ToggleLeft, 
  ToggleRight, 
  Activity, 
  Clock, 
  Mail, 
  CheckCircle, 
  XCircle,
  Archive,
  Plus,
  ExternalLink
} from 'lucide-react';

// Store
import { useAutonomousStore } from '../../store/autonomousStore';

// UI Components
import { FormGroup, Switch, Slider } from '../ui/FormControls';
import CollapsibleCard from '../ui/CollapsibleCard';

const Autonomous: React.FC = () => {
  const {
    settings,
    logs,
    isLoading,
    isSaving,
    loadSettings,
    loadLogs,
    updateSetting,
    saveSettings
  } = useAutonomousStore();

  // State for managing collapsible sections
  const [expandedSections, setExpandedSections] = useState({
    masterControl: true,
    featureSettings: true,
    recentActions: true
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  useEffect(() => {
    // Load initial data
    loadSettings();
    loadLogs();
  }, [loadSettings, loadLogs]);

  const formatConfidence = (value: number): string => `${Math.round(value * 100)}%`;
  
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'auto_archive':
        return <Archive className="h-4 w-4" />;
      case 'auto_task_creation':
        return <Plus className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getActionColor = (actionType: string) => {
    switch (actionType) {
      case 'auto_archive':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900';
      case 'auto_task_creation':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900';
    }
  };

  const handleMasterToggle = (enabled: boolean) => {
    // Update all autonomous features
    updateSetting('auto_archive.enabled', enabled);
    updateSetting('auto_task_creation.enabled', enabled);
    updateSetting('auto_meeting_prep.enabled', enabled);
  };

  const masterEnabled = settings?.auto_archive?.enabled && 
                       settings?.auto_task_creation?.enabled && 
                       settings?.auto_meeting_prep?.enabled;

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600 dark:text-gray-400">Loading autonomous settings...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
            <Settings className="h-7 w-7 text-blue-600" />
            <span>Autonomous Controls</span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Monitor and control your AI agent's autonomous actions
          </p>
        </div>
        
        {/* Save Status */}
        {isSaving && (
          <div className="flex items-center space-x-2 text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm">Saving...</span>
          </div>
        )}
      </div>

      {/* Master Control */}
      <CollapsibleCard
        title="Master Control"
        icon={<ToggleLeft className="h-5 w-5" />}
        isExpanded={expandedSections.masterControl}
        onToggle={() => toggleSection('masterControl')}
      >
        <div className="space-y-4">
          <FormGroup
            label="Enable All Autonomous Features"
            description="Master toggle to enable or disable all autonomous functionality at once"
          >
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="flex items-center space-x-3">
                {masterEnabled ? (
                  <ToggleRight className="h-6 w-6 text-green-600" />
                ) : (
                  <ToggleLeft className="h-6 w-6 text-gray-400" />
                )}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    Autonomous Mode
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {masterEnabled ? 'All features enabled' : 'Autonomous features disabled'}
                  </p>
                </div>
              </div>
              <Switch
                checked={masterEnabled || false}
                onChange={handleMasterToggle}
                size="lg"
              />
            </div>
          </FormGroup>
        </div>
      </CollapsibleCard>

      {/* Individual Controls */}
      <CollapsibleCard
        title="Feature Settings"
        icon={<Settings className="h-5 w-5" />}
        isExpanded={expandedSections.featureSettings}
        onToggle={() => toggleSection('featureSettings')}
      >
        <div className="space-y-6">
          {/* Auto Archive */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <Archive className="h-5 w-5 text-blue-600" />
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">Auto-Archive</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Automatically archive low-priority emails
                  </p>
                </div>
              </div>
              <Switch
                checked={settings?.auto_archive?.enabled || false}
                onChange={(enabled) => updateSetting('auto_archive.enabled', enabled)}
              />
            </div>
            
            {settings?.auto_archive?.enabled && (
              <FormGroup
                label="Confidence Threshold"
                description="How confident the AI must be before auto-archiving (higher = more cautious)"
              >
                <Slider
                  value={Math.round((settings?.auto_archive?.confidence_threshold || 0.95) * 100)}
                  onChange={(value) => updateSetting('auto_archive.confidence_threshold', value / 100)}
                  min={50}
                  max={99}
                  step={1}
                  formatValue={(val) => `${val}%`}
                />
              </FormGroup>
            )}
          </div>

          {/* Auto Task Creation */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <Plus className="h-5 w-5 text-green-600" />
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">Auto-Task Creation</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Automatically create tasks from actionable emails
                  </p>
                </div>
              </div>
              <Switch
                checked={settings?.auto_task_creation?.enabled || false}
                onChange={(enabled) => updateSetting('auto_task_creation.enabled', enabled)}
              />
            </div>
            
            {settings?.auto_task_creation?.enabled && (
              <FormGroup
                label="Confidence Threshold"
                description="How confident the AI must be before creating tasks (higher = more cautious)"
              >
                <Slider
                  value={Math.round((settings?.auto_task_creation?.confidence_threshold || 0.90) * 100)}
                  onChange={(value) => updateSetting('auto_task_creation.confidence_threshold', value / 100)}
                  min={50}
                  max={99}
                  step={1}
                  formatValue={(val) => `${val}%`}
                />
              </FormGroup>
            )}
          </div>

          {/* Auto Meeting Prep */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <Clock className="h-5 w-5 text-purple-600" />
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">Auto-Meeting Prep</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Automatically prepare for meetings from calendar invites
                  </p>
                </div>
              </div>
              <Switch
                checked={settings?.auto_meeting_prep?.enabled || false}
                onChange={(enabled) => updateSetting('auto_meeting_prep.enabled', enabled)}
              />
            </div>
            
            {settings?.auto_meeting_prep?.enabled && (
              <FormGroup
                label="Confidence Threshold"
                description="How confident the AI must be before preparing meetings (higher = more cautious)"
              >
                <Slider
                  value={Math.round((settings?.auto_meeting_prep?.confidence_threshold || 0.90) * 100)}
                  onChange={(value) => updateSetting('auto_meeting_prep.confidence_threshold', value / 100)}
                  min={50}
                  max={99}
                  step={1}
                  formatValue={(val) => `${val}%`}
                />
              </FormGroup>
            )}
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={saveSettings}
            disabled={isSaving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isSaving ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <CheckCircle className="h-4 w-4" />
            )}
            <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </CollapsibleCard>

      {/* Recent Actions Log */}
      <CollapsibleCard
        title="Recent Autonomous Actions"
        icon={<Activity className="h-5 w-5" />}
        isExpanded={expandedSections.recentActions}
        onToggle={() => toggleSection('recentActions')}
      >
        <div className="space-y-4">
          {logs && logs.length > 0 ? (
            <div className="space-y-3">
              {logs.map((log, index) => (
                <motion.div
                  key={log.id || index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      <div className={`p-2 rounded-full ${getActionColor(log.action_type)}`}>
                        {getActionIcon(log.action_type)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="font-medium text-gray-900 dark:text-white">
                            {log.action_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {formatDate(log.timestamp)}
                          </span>
                        </div>
                        
                        <p className="text-sm text-gray-900 dark:text-white font-medium mb-1">
                          {log.email_subject}
                        </p>
                        
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {log.reasoning}
                        </p>
                        
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            Confidence: {formatConfidence(log.confidence)}
                          </span>
                          {log.email_id && (
                            <button
                              onClick={() => {
                                // Navigate to email detail or open email
                                console.log('Opening email:', log.email_id);
                              }}
                              className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              <span>View Email</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {log.success ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium mb-1">No autonomous actions yet</p>
              <p className="text-sm">
                When the AI agent takes autonomous actions, they will appear here
              </p>
            </div>
          )}
          
          {logs && logs.length > 0 && (
            <div className="mt-4 text-center">
              <button
                onClick={loadLogs}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Refresh logs
              </button>
            </div>
          )}
        </div>
      </CollapsibleCard>
    </div>
  );
};

export default Autonomous;