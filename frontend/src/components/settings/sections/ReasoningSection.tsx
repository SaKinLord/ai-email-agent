import React from 'react';
import { Lightbulb } from 'lucide-react';
import { useSettingsStore } from '../../../store/settingsStore';
import CollapsibleCard from '../../ui/CollapsibleCard';
import { FormGroup, Switch, Select, ConfidenceInput } from '../../ui/FormControls';

const ReasoningSection: React.FC = () => {
  const { config, panel, updateSettings, toggleSection, validation } = useSettingsStore();
  
  if (!config) return null;
  
  const isExpanded = panel.expandedSections.has('reasoning');
  
  const detailLevelOptions = [
    { value: 'minimal', label: 'Minimal - Brief explanations' },
    { value: 'standard', label: 'Standard - Balanced detail' },
    { value: 'detailed', label: 'Detailed - Comprehensive explanations' },
    { value: 'verbose', label: 'Verbose - Maximum detail' }
  ];

  const updateConfidenceThreshold = (action: string, value: number) => {
    updateSettings('reasoning', {
      confidence_thresholds: {
        ...config.reasoning.confidence_thresholds,
        [action]: value
      }
    });
  };

  return (
    <CollapsibleCard
      title="AI Reasoning Engine"
      subtitle="Configure explainable AI and decision transparency"
      icon={<Lightbulb className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={() => toggleSection('reasoning')}
      badge={undefined}
      variant="default"
    >
      <div className="space-y-6">
        {/* Reasoning Engine Toggle */}
        <FormGroup
          label="Enable Reasoning Engine"
          description="Provides step-by-step explanations for AI decisions and actions"
        >
          <div className="flex items-center space-x-3">
            <Switch
              checked={config.reasoning.enabled}
              onChange={(checked) => updateSettings('reasoning', { enabled: checked })}
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {config.reasoning.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </FormGroup>

        {config.reasoning.enabled && (
          <>
            {/* Explanation Detail Level */}
            <FormGroup
              label="Explanation Detail Level"
              description="How much detail to include in AI reasoning explanations"
              error={validation.validationErrors['reasoning.explanation_detail_level']}
            >
              <Select
                value={config.reasoning.explanation_detail_level}
                onChange={(value) => updateSettings('reasoning', { explanation_detail_level: value })}
                options={detailLevelOptions}
              />
            </FormGroup>

            {/* Confidence Thresholds */}
            <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
              <h4 className="font-medium text-gray-900 dark:text-white mb-4">Confidence Thresholds</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Minimum confidence levels required for the AI to take autonomous actions
              </p>
              
              <div className="space-y-4">
                <FormGroup
                  label="Auto Archive Threshold"
                  description="Confidence required to automatically archive emails"
                  error={validation.validationErrors['reasoning.confidence_thresholds.archive']}
                >
                  <ConfidenceInput
                    value={config.reasoning.confidence_thresholds.archive || 95}
                    onChange={(value) => updateConfidenceThreshold('archive', value)}
                  />
                </FormGroup>

                <FormGroup
                  label="Priority Adjustment Threshold"
                  description="Confidence required to automatically adjust email priority"
                  error={validation.validationErrors['reasoning.confidence_thresholds.priority_adjust']}
                >
                  <ConfidenceInput
                    value={config.reasoning.confidence_thresholds.priority_adjust || 80}
                    onChange={(value) => updateConfidenceThreshold('priority_adjust', value)}
                  />
                </FormGroup>
              </div>
            </div>

            {/* Reasoning Features */}
            <div className="bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
              <h4 className="font-medium text-purple-900 dark:text-purple-100 mb-2">Reasoning Features</h4>
              <ul className="text-sm text-purple-700 dark:text-purple-300 space-y-1">
                <li>• <strong>Decision Transparency:</strong> See why the AI made specific classifications</li>
                <li>• <strong>Confidence Scoring:</strong> Understand how certain the AI is about its decisions</li>
                <li>• <strong>Step-by-Step Analysis:</strong> Follow the AI's reasoning process</li>
                <li>• <strong>Action Justification:</strong> Explanations for autonomous actions taken</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </CollapsibleCard>
  );
};

export default ReasoningSection;