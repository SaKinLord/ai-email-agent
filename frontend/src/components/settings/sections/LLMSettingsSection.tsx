import React from 'react';
import { Brain, DollarSign } from 'lucide-react';
import { useSettingsStore } from '../../../store/settingsStore';
import CollapsibleCard from '../../ui/CollapsibleCard';
import { FormGroup, NumberInput, Select, Switch } from '../../ui/FormControls';

const LLMSettingsSection: React.FC = () => {
  const { config, panel, updateSettings, toggleSection, validation } = useSettingsStore();
  
  if (!config) return null;
  
  const isExpanded = panel.expandedSections.has('llm_settings');
  
  const modelOptions = [
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (Fast & Cost-effective)' },
    { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet (Balanced)' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (Most Capable)' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (Fast)' },
    { value: 'gpt-4', label: 'GPT-4 (High Quality)' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo (Latest)' }
  ];

  return (
    <CollapsibleCard
      title="LLM & AI Configuration"
      subtitle="Configure language model settings and budget management"
      icon={<Brain className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={() => toggleSection('llm_settings')}
      badge={undefined}
      variant="default"
    >
      <div className="space-y-6">
        {/* Primary Model Selection */}
        <FormGroup
          label="Primary Model"
          description="The main language model used for email analysis and processing"
          error={validation.validationErrors['llm_settings.model']}
        >
          <Select
            value={config.llm_settings.model}
            onChange={(value) => updateSettings('llm_settings', { model: value })}
            options={modelOptions}
          />
        </FormGroup>

        {/* Hybrid Mode */}
        <FormGroup
          label="Hybrid Mode"
          description="Automatically route tasks to cost-effective models when appropriate"
        >
          <div className="flex items-center space-x-3">
            <Switch
              checked={config.llm_settings.hybrid_mode}
              onChange={(checked) => updateSettings('llm_settings', { hybrid_mode: checked })}
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {config.llm_settings.hybrid_mode ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </FormGroup>

        {/* Budget Management */}
        <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
          <div className="flex items-center space-x-2 mb-4">
            <DollarSign className="h-4 w-4 text-green-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">Monthly Budget</h4>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <FormGroup
              label="GPT Budget"
              description="Monthly budget for GPT models (USD)"
              error={validation.validationErrors['llm_settings.gpt_budget_monthly']}
            >
              <NumberInput
                value={config.llm_settings.gpt_budget_monthly}
                onChange={(value) => updateSettings('llm_settings', { gpt_budget_monthly: value })}
                min={0}
                max={1000}
                step={5}
                placeholder="120.00"
              />
            </FormGroup>

            <FormGroup
              label="Claude Budget"
              description="Monthly budget for Claude models (USD)"
              error={validation.validationErrors['llm_settings.claude_budget_monthly']}
            >
              <NumberInput
                value={config.llm_settings.claude_budget_monthly}
                onChange={(value) => updateSettings('llm_settings', { claude_budget_monthly: value })}
                min={0}
                max={1000}
                step={5}
                placeholder="5.00"
              />
            </FormGroup>
          </div>
        </div>

        {/* Token Limits */}
        <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-4">Response Limits</h4>
          
          <FormGroup
            label="Max Tokens"
            description="Maximum tokens per response (higher = longer responses, higher cost)"
            error={validation.validationErrors['llm_settings.max_tokens']}
          >
            <NumberInput
              value={config.llm_settings.max_tokens}
              onChange={(value) => updateSettings('llm_settings', { max_tokens: value })}
              min={100}
              max={4000}
              step={100}
            />
          </FormGroup>
        </div>

        {/* Legacy LLM Settings */}
        <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-4">Legacy Settings</h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
            These settings are maintained for backward compatibility with existing email processing workflows.
          </p>
          
          <div className="grid grid-cols-2 gap-4">
            <FormGroup
              label="Analysis Temperature"
              description="Creativity level for analysis (0.0-1.0)"
              error={validation.validationErrors['llm.analysis_temperature']}
            >
              <NumberInput
                value={config.llm.analysis_temperature}
                onChange={(value) => updateSettings('llm', { analysis_temperature: value })}
                min={0}
                max={1}
                step={0.1}
              />
            </FormGroup>

            <FormGroup
              label="Summary Temperature"
              description="Creativity level for summaries (0.0-1.0)"
              error={validation.validationErrors['llm.summary_temperature']}
            >
              <NumberInput
                value={config.llm.summary_temperature}
                onChange={(value) => updateSettings('llm', { summary_temperature: value })}
                min={0}
                max={1}
                step={0.1}
              />
            </FormGroup>

            <FormGroup
              label="Analysis Max Tokens"
              description="Token limit for email analysis"
              error={validation.validationErrors['llm.analysis_max_tokens']}
            >
              <NumberInput
                value={config.llm.analysis_max_tokens}
                onChange={(value) => updateSettings('llm', { analysis_max_tokens: value })}
                min={50}
                max={500}
                step={10}
              />
            </FormGroup>

            <FormGroup
              label="Summary Max Tokens"
              description="Token limit for email summaries"
              error={validation.validationErrors['llm.summary_max_tokens']}
            >
              <NumberInput
                value={config.llm.summary_max_tokens}
                onChange={(value) => updateSettings('llm', { summary_max_tokens: value })}
                min={50}
                max={500}
                step={10}
              />
            </FormGroup>

            <FormGroup
              label="API Delay"
              description="Delay between API calls (seconds)"
              error={validation.validationErrors['llm.api_delay_seconds']}
            >
              <NumberInput
                value={config.llm.api_delay_seconds}
                onChange={(value) => updateSettings('llm', { api_delay_seconds: value })}
                min={0}
                max={10}
                step={0.5}
              />
            </FormGroup>
          </div>
        </div>
      </div>
    </CollapsibleCard>
  );
};

export default LLMSettingsSection;