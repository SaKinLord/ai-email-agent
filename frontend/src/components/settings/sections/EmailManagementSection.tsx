import React from 'react';
import { Mail, RefreshCw, Database } from 'lucide-react';
import { useSettingsStore } from '../../../store/settingsStore';
import CollapsibleCard from '../../ui/CollapsibleCard';
import { FormGroup, NumberInput, Switch, ArrayInput } from '../../ui/FormControls';

const EmailManagementSection: React.FC = () => {
  const { config, panel, updateSettings, toggleSection, validation } = useSettingsStore();
  
  if (!config) return null;
  
  const isExpanded = panel.expandedSections.has('email_management');

  return (
    <CollapsibleCard
      title="Email Management"
      subtitle="Configure email fetching, processing, and storage settings"
      icon={<Mail className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={() => toggleSection('email_management')}
      badge={undefined}
      variant="default"
    >
      <div className="space-y-6">
        {/* Gmail Fetch Settings */}
        <div className="border border-blue-200 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <Mail className="h-4 w-4 text-blue-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">Gmail Fetch Settings</h4>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <FormGroup
              label="Max Results"
              description="Maximum emails to fetch per request"
              error={validation.validationErrors['gmail.fetch_max_results']}
            >
              <NumberInput
                value={config.gmail.fetch_max_results}
                onChange={(value) => updateSettings('gmail', { fetch_max_results: value })}
                min={10}
                max={500}
                step={10}
              />
            </FormGroup>

            <FormGroup
              label="Fetch Labels"
              description="Gmail labels to include when fetching emails"
              error={validation.validationErrors['gmail.fetch_labels']}
            >
              <ArrayInput
                values={config.gmail.fetch_labels}
                onChange={(values) => updateSettings('gmail', { fetch_labels: values })}
                placeholder="Enter label (e.g., INBOX, UNREAD)..."
                addButtonText="Add Label"
                maxItems={10}
              />
            </FormGroup>
          </div>
        </div>

        {/* ML Model Settings */}
        <div className="border border-purple-200 dark:border-purple-700 bg-purple-50/50 dark:bg-purple-900/10 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <Database className="h-4 w-4 text-purple-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">Machine Learning</h4>
          </div>
          
          <FormGroup
            label="Min Feedback for Retrain"
            description="Minimum feedback entries required before triggering model retraining"
            error={validation.validationErrors['ml.min_feedback_for_retrain']}
          >
            <NumberInput
              value={config.ml.min_feedback_for_retrain}
              onChange={(value) => updateSettings('ml', { min_feedback_for_retrain: value })}
              min={1}
              max={100}
              step={1}
            />
          </FormGroup>
        </div>

        {/* Retraining Settings */}
        <div className="border border-green-200 dark:border-green-700 bg-green-50/50 dark:bg-green-900/10 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-4">
            <RefreshCw className="h-4 w-4 text-green-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">Auto Retraining</h4>
          </div>
          
          <div className="space-y-4">
            <FormGroup
              label="Enable Auto Retraining"
              description="Automatically retrain the ML model when enough feedback is collected"
            >
              <div className="flex items-center space-x-3">
                <Switch
                  checked={config.retraining.enabled}
                  onChange={(checked) => updateSettings('retraining', { enabled: checked })}
                />
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {config.retraining.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </FormGroup>

            {config.retraining.enabled && (
              <FormGroup
                label="Trigger Feedback Count"
                description="Number of new feedback entries that triggers automatic retraining"
                error={validation.validationErrors['retraining.trigger_feedback_count']}
              >
                <NumberInput
                  value={config.retraining.trigger_feedback_count}
                  onChange={(value) => updateSettings('retraining', { trigger_feedback_count: value })}
                  min={5}
                  max={100}
                  step={5}
                />
              </FormGroup>
            )}
          </div>
        </div>

        {/* Agenda Synthesis */}
        <div className="border border-orange-200 dark:border-orange-700 bg-orange-50/50 dark:bg-orange-900/10 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white">Agenda Synthesis</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Generate daily summaries combining emails, tasks, and calendar events
              </p>
            </div>
            <Switch
              checked={config.agenda_synthesis.enabled}
              onChange={(checked) => updateSettings('agenda_synthesis', { enabled: checked })}
            />
          </div>
          
          {config.agenda_synthesis.enabled && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <FormGroup
                  label="Max Emails"
                  description="Max emails to include"
                  error={validation.validationErrors['agenda_synthesis.max_emails']}
                >
                  <NumberInput
                    value={config.agenda_synthesis.max_emails}
                    onChange={(value) => updateSettings('agenda_synthesis', { max_emails: value })}
                    min={1}
                    max={20}
                    step={1}
                  />
                </FormGroup>

                <FormGroup
                  label="Max Tasks"
                  description="Max tasks to include"
                  error={validation.validationErrors['agenda_synthesis.max_tasks']}
                >
                  <NumberInput
                    value={config.agenda_synthesis.max_tasks}
                    onChange={(value) => updateSettings('agenda_synthesis', { max_tasks: value })}
                    min={1}
                    max={30}
                    step={1}
                  />
                </FormGroup>

                <FormGroup
                  label="Max Events"
                  description="Max calendar events"
                  error={validation.validationErrors['agenda_synthesis.max_events']}
                >
                  <NumberInput
                    value={config.agenda_synthesis.max_events}
                    onChange={(value) => updateSettings('agenda_synthesis', { max_events: value })}
                    min={1}
                    max={20}
                    step={1}
                  />
                </FormGroup>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormGroup
                  label="Refresh Interval (minutes)"
                  description="How often to regenerate the synthesis"
                  error={validation.validationErrors['agenda_synthesis.refresh_interval_minutes']}
                >
                  <NumberInput
                    value={config.agenda_synthesis.refresh_interval_minutes}
                    onChange={(value) => updateSettings('agenda_synthesis', { refresh_interval_minutes: value })}
                    min={5}
                    max={240}
                    step={5}
                  />
                </FormGroup>

                <FormGroup
                  label="Fallback Mode"
                  description="Enable fallback if synthesis fails"
                >
                  <div className="flex items-center space-x-3 pt-2">
                    <Switch
                      checked={config.agenda_synthesis.fallback_enabled}
                      onChange={(checked) => updateSettings('agenda_synthesis', { fallback_enabled: checked })}
                    />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {config.agenda_synthesis.fallback_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </FormGroup>
              </div>
            </div>
          )}
        </div>

        {/* Email Management Tips */}
        <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Email Management Tips</h4>
          <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
            <li>• Higher fetch limits provide more comprehensive analysis but increase processing time</li>
            <li>• Auto-retraining improves accuracy but requires computational resources</li>
            <li>• Agenda synthesis combines multiple data sources for comprehensive daily overviews</li>
            <li>• Monitor system performance when adjusting these settings</li>
          </ul>
        </div>
      </div>
    </CollapsibleCard>
  );
};

export default EmailManagementSection;