import React from 'react';
import { Filter, UserCheck, AlertTriangle } from 'lucide-react';
import { useSettingsStore } from '../../../store/settingsStore';
import CollapsibleCard from '../../ui/CollapsibleCard';
import { FormGroup, ArrayInput } from '../../ui/FormControls';

const ClassificationSection: React.FC = () => {
  const { config, panel, updateSettings, toggleSection, validation } = useSettingsStore();
  
  if (!config) return null;
  
  const isExpanded = panel.expandedSections.has('classification');

  return (
    <CollapsibleCard
      title="Email Classification"
      subtitle="Configure priority and classification rules"
      icon={<Filter className="h-4 w-4" />}
      isExpanded={isExpanded}
      onToggle={() => toggleSection('classification')}
      badge={undefined}
      variant="default"
    >
      <div className="space-y-6">
        {/* Important Senders */}
        <div className="border border-green-200 dark:border-green-700 bg-green-50/50 dark:bg-green-900/10 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <UserCheck className="h-4 w-4 text-green-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">Important Senders</h4>
          </div>
          
          <FormGroup
            label=""
            description="Email addresses and domains that should always be prioritized (e.g., boss@company.com, @important-client.com)"
            error={validation.validationErrors['classification.important_senders']}
          >
            <ArrayInput
              values={config.classification.important_senders}
              onChange={(values) => updateSettings('classification', { important_senders: values })}
              placeholder="Enter email or domain..."
              addButtonText="Add Sender"
              maxItems={20}
            />
          </FormGroup>
        </div>

        {/* High Priority Keywords */}
        <div className="border border-red-200 dark:border-red-700 bg-red-50/50 dark:bg-red-900/10 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <h4 className="font-medium text-gray-900 dark:text-white">High Priority Keywords</h4>
          </div>
          
          <FormGroup
            label=""
            description="Subject line keywords that indicate high priority emails (case-insensitive)"
            error={validation.validationErrors['classification.subject_keywords_high']}
          >
            <ArrayInput
              values={config.classification.subject_keywords_high}
              onChange={(values) => updateSettings('classification', { subject_keywords_high: values })}
              placeholder="Enter keyword..."
              addButtonText="Add Keyword"
              maxItems={30}
            />
          </FormGroup>
        </div>

        {/* Low Priority Keywords */}
        <div className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">Low Priority Keywords</h4>
          
          <div className="space-y-4">
            <FormGroup
              label="Subject Keywords"
              description="Subject line keywords that indicate low priority emails"
              error={validation.validationErrors['classification.subject_keywords_low']}
            >
              <ArrayInput
                values={config.classification.subject_keywords_low}
                onChange={(values) => updateSettings('classification', { subject_keywords_low: values })}
                placeholder="Enter keyword..."
                addButtonText="Add Keyword"
                maxItems={30}
              />
            </FormGroup>

            <FormGroup
              label="Sender Keywords"
              description="Sender patterns that indicate automated or low-priority emails"
              error={validation.validationErrors['classification.sender_keywords_low']}
            >
              <ArrayInput
                values={config.classification.sender_keywords_low}
                onChange={(values) => updateSettings('classification', { sender_keywords_low: values })}
                placeholder="Enter pattern..."
                addButtonText="Add Pattern"
                maxItems={30}
              />
            </FormGroup>
          </div>
        </div>

        {/* Classification Tips */}
        <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Classification Tips</h4>
          <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
            <li>• Use @domain.com format to match entire domains</li>
            <li>• Keywords are case-insensitive and match partial words</li>
            <li>• Important senders override other classification rules</li>
            <li>• The AI model learns from your feedback to improve accuracy</li>
          </ul>
        </div>
      </div>
    </CollapsibleCard>
  );
};

export default ClassificationSection;