import React from 'react';
import { Bot, Archive, Calendar, CheckSquare } from 'lucide-react';
import { useSettingsStore } from '../../../store/settingsStore';
import CollapsibleCard from '../../ui/CollapsibleCard';
import { FormGroup, Switch, ConfidenceInput } from '../../ui/FormControls';

const AutonomousTasksSection: React.FC = () => {
  const { config, panel, updateSettings, toggleSection, validation } = useSettingsStore();
  
  if (!config) return null;
  
  const isExpanded = panel.expandedSections.has('autonomous_tasks');
  
  const updateTaskConfig = (taskKey: keyof typeof config.autonomous_tasks, updates: Partial<typeof config.autonomous_tasks[keyof typeof config.autonomous_tasks]>) => {
    const currentTask = config.autonomous_tasks[taskKey];
    updateSettings('autonomous_tasks', {
      [taskKey]: { ...currentTask, ...updates }
    });
  };

  return (
    <CollapsibleCard
      title="Autonomous Tasks"
      subtitle="Configure automated actions and their confidence thresholds"
      icon={<Bot className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={() => toggleSection('autonomous_tasks')}
      badge={undefined}
      variant="default"
    >
      <div className="space-y-6">
        {/* Auto Archive */}
        <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <Archive className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white">Auto Archive</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Automatically archive low-priority emails based on AI analysis
                </p>
              </div>
            </div>
            <Switch
              checked={config.autonomous_tasks.auto_archive.enabled}
              onChange={(checked) => updateTaskConfig('auto_archive', { enabled: checked })}
            />
          </div>
          
          {config.autonomous_tasks.auto_archive.enabled && (
            <div className="ml-8">
              <FormGroup
                label="Confidence Threshold"
                description="Minimum confidence required before auto-archiving emails"
                error={validation.validationErrors['autonomous_tasks.auto_archive.confidence_threshold']}
              >
                <ConfidenceInput
                  value={config.autonomous_tasks.auto_archive.confidence_threshold * 100}
                  onChange={(value) => updateTaskConfig('auto_archive', { confidence_threshold: value / 100 })}
                />
              </FormGroup>
            </div>
          )}
        </div>

        {/* Auto Meeting Prep */}
        <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <Calendar className="h-5 w-5 text-blue-600" />
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white">Auto Meeting Prep</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Automatically prepare meeting summaries and action items
                </p>
              </div>
            </div>
            <Switch
              checked={config.autonomous_tasks.auto_meeting_prep.enabled}
              onChange={(checked) => updateTaskConfig('auto_meeting_prep', { enabled: checked })}
            />
          </div>
          
          {config.autonomous_tasks.auto_meeting_prep.enabled && (
            <div className="ml-8">
              <FormGroup
                label="Confidence Threshold"
                description="Minimum confidence required for automated meeting preparation"
                error={validation.validationErrors['autonomous_tasks.auto_meeting_prep.confidence_threshold']}
              >
                <ConfidenceInput
                  value={config.autonomous_tasks.auto_meeting_prep.confidence_threshold * 100}
                  onChange={(value) => updateTaskConfig('auto_meeting_prep', { confidence_threshold: value / 100 })}
                />
              </FormGroup>
            </div>
          )}
        </div>

        {/* Auto Task Creation */}
        <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <CheckSquare className="h-5 w-5 text-green-600" />
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white">Auto Task Creation</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Automatically create tasks from action-required emails
                </p>
              </div>
            </div>
            <Switch
              checked={config.autonomous_tasks.auto_task_creation.enabled}
              onChange={(checked) => updateTaskConfig('auto_task_creation', { enabled: checked })}
            />
          </div>
          
          {config.autonomous_tasks.auto_task_creation.enabled && (
            <div className="ml-8">
              <FormGroup
                label="Confidence Threshold"
                description="Minimum confidence required for automatic task creation"
                error={validation.validationErrors['autonomous_tasks.auto_task_creation.confidence_threshold']}
              >
                <ConfidenceInput
                  value={config.autonomous_tasks.auto_task_creation.confidence_threshold * 100}
                  onChange={(value) => updateTaskConfig('auto_task_creation', { confidence_threshold: value / 100 })}
                />
              </FormGroup>
            </div>
          )}
        </div>

        {/* Global Settings */}
        <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-4">Global Autonomous Settings</h4>
          <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              <strong>Safety Note:</strong> Autonomous tasks are designed with conservative confidence thresholds 
              to prevent unwanted actions. You can adjust these thresholds based on your comfort level and 
              the agent's performance over time.
            </p>
          </div>
        </div>
      </div>
    </CollapsibleCard>
  );
};

export default AutonomousTasksSection;