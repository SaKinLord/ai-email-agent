import React from 'react';
import { Link, Webhook } from 'lucide-react';
import { useSettingsStore } from '../../../store/settingsStore';
import CollapsibleCard from '../../ui/CollapsibleCard';
import { FormGroup, TextInput, Switch, NumberInput, ArrayInput } from '../../ui/FormControls';

const IntegrationsSection: React.FC = () => {
  const { config, panel, updateSettings, toggleSection, validation } = useSettingsStore();
  
  if (!config) return null;
  
  const isExpanded = panel.expandedSections.has('integrations');

  return (
    <CollapsibleCard
      title="Integrations & Webhooks"
      subtitle="Configure external service integrations and webhook settings"
      icon={<Link className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={() => toggleSection('integrations')}
      badge={undefined}
      variant="default"
    >
      <div className="space-y-6">
        {/* Task Webhook */}
        <div className="border border-blue-200 dark:border-blue-700 bg-blue-50/50 dark:bg-blue-900/10 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <Webhook className="h-4 w-4 text-blue-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">Task Webhook</h4>
          </div>
          
          <FormGroup
            label="Webhook URL"
            description="URL to send task notifications to external systems (leave empty to disable)"
            error={validation.validationErrors['integrations.task_webhook_url']}
          >
            <TextInput
              value={config.integrations.task_webhook_url}
              onChange={(value) => updateSettings('integrations', { task_webhook_url: value })}
              placeholder="https://your-webhook-endpoint.com/tasks"
              type="url"
            />
          </FormGroup>
        </div>

        {/* Reply Suggestions */}
        <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white">Reply Suggestions</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                AI-generated reply suggestions for emails
              </p>
            </div>
            <Switch
              checked={config.integrations.reply_suggestions.enabled}
              onChange={(checked) => updateSettings('integrations', {
                reply_suggestions: { ...config.integrations.reply_suggestions, enabled: checked }
              })}
            />
          </div>
          
          {config.integrations.reply_suggestions.enabled && (
            <div className="space-y-4 ml-2">
              <FormGroup
                label="Max Suggestions"
                description="Maximum number of reply suggestions to generate per email"
                error={validation.validationErrors['integrations.reply_suggestions.max_suggestions']}
              >
                <NumberInput
                  value={config.integrations.reply_suggestions.max_suggestions}
                  onChange={(value) => updateSettings('integrations', {
                    reply_suggestions: { ...config.integrations.reply_suggestions, max_suggestions: value }
                  })}
                  min={1}
                  max={10}
                  step={1}
                />
              </FormGroup>

              <FormGroup
                label="Excluded Purposes"
                description="Email purposes to exclude from reply suggestions"
                error={validation.validationErrors['integrations.reply_suggestions.exclude_purposes']}
              >
                <ArrayInput
                  values={config.integrations.reply_suggestions.exclude_purposes}
                  onChange={(values) => updateSettings('integrations', {
                    reply_suggestions: { ...config.integrations.reply_suggestions, exclude_purposes: values }
                  })}
                  placeholder="Enter purpose (e.g., promotion, newsletter)..."
                  addButtonText="Add Purpose"
                  maxItems={10}
                />
              </FormGroup>
            </div>
          )}
        </div>

        {/* Webhook Settings */}
        <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-4">Webhook Configuration</h4>
          
          <div className="grid grid-cols-2 gap-4">
            <FormGroup
              label="Timeout (seconds)"
              description="HTTP timeout for webhook requests"
              error={validation.validationErrors['integrations.webhook_settings.timeout_seconds']}
            >
              <NumberInput
                value={config.integrations.webhook_settings.timeout_seconds}
                onChange={(value) => updateSettings('integrations', {
                  webhook_settings: { ...config.integrations.webhook_settings, timeout_seconds: value }
                })}
                min={5}
                max={120}
                step={5}
              />
            </FormGroup>

            <FormGroup
              label="SSL Verification"
              description="Verify SSL certificates for webhook URLs"
            >
              <div className="flex items-center space-x-3 pt-2">
                <Switch
                  checked={config.integrations.webhook_settings.verify_ssl}
                  onChange={(checked) => updateSettings('integrations', {
                    webhook_settings: { ...config.integrations.webhook_settings, verify_ssl: checked }
                  })}
                />
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {config.integrations.webhook_settings.verify_ssl ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </FormGroup>
          </div>
        </div>

        {/* Integration Tips */}
        <div className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">Integration Tips</h4>
          <ul className="text-sm text-green-700 dark:text-green-300 space-y-1">
            <li>• Webhooks send POST requests with JSON payloads</li>
            <li>• Test your webhook endpoint before enabling integrations</li>
            <li>• Use HTTPS URLs for webhook endpoints when possible</li>
            <li>• Monitor webhook delivery success in the activity feed</li>
          </ul>
        </div>
      </div>
    </CollapsibleCard>
  );
};

export default IntegrationsSection;