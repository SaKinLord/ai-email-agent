import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, X, HelpCircle, Lightbulb, AlertTriangle, Info } from 'lucide-react';
import { Suggestion } from '../../store/agentStore';
import { useToastStore } from '../../store/toastStore';
import { successToast, errorToast, infoToast } from '../../utils/toastHelpers';

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept: (suggestion: Suggestion) => void;
  onDismiss: (suggestionType: string) => void;
  disabled?: boolean;
}

const priorityStyles = {
  critical: {
    border: 'border-red-200 dark:border-red-700',
    bg: 'bg-red-50/50 dark:bg-red-900/10',
    indicator: 'bg-red-500',
    icon: AlertTriangle,
    iconColor: 'text-red-600 dark:text-red-400'
  },
  high: {
    border: 'border-orange-200 dark:border-orange-700',
    bg: 'bg-orange-50/50 dark:bg-orange-900/10',
    indicator: 'bg-orange-500',
    icon: Lightbulb,
    iconColor: 'text-orange-600 dark:text-orange-400'
  },
  medium: {
    border: 'border-blue-200 dark:border-blue-700',
    bg: 'bg-blue-50/50 dark:bg-blue-900/10',
    indicator: 'bg-blue-500',
    icon: Info,
    iconColor: 'text-blue-600 dark:text-blue-400'
  },
  low: {
    border: 'border-gray-200 dark:border-gray-700',
    bg: 'bg-gray-50/50 dark:bg-gray-900/10',
    indicator: 'bg-gray-500',
    icon: Info,
    iconColor: 'text-gray-600 dark:text-gray-400'
  }
};

const actionButtonLabels: Record<string, string> = {
  create_sender_rule: "Create Rule",
  create_domain_filter: "Add Filter",
  summarize_action_items: "Summarize Actions",
  summarize_questions: "Review Questions",
  summarize_high_priority: "Summarize Priority",
  schedule_email_time: "Schedule Time",
  manage_meetings: "Organize Meetings",
  scheduled_send_setup: "Setup Send Times",
  cleanup_inbox: "Archive Low Priority",
  organize_inbox: "Suggest Organization",
  setup_daily_summary: "Enable Daily Summary",
  setup_follow_up: "Setup Follow-ups"
};

const SuggestionCard: React.FC<SuggestionCardProps> = ({
  suggestion,
  onAccept,
  onDismiss,
  disabled = false
}) => {
  const [showRationale, setShowRationale] = useState(false);
  const [processing, setProcessing] = useState(false);
  const addToast = useToastStore(state => state.addToast);

  const priorityStyle = priorityStyles[suggestion.priority];
  const PriorityIcon = priorityStyle.icon;
  const actionLabel = actionButtonLabels[suggestion.action] || 'Accept';

  const handleAccept = async () => {
    if (disabled || processing) return;
    
    setProcessing(true);
    try {
      await onAccept(suggestion);
      addToast(infoToast('Processing Suggestion', 'Your suggestion is being processed...'));
    } catch (error) {
      addToast(errorToast('Processing Failed', 'Failed to process suggestion. Please try again.'));
    } finally {
      setProcessing(false);
    }
  };

  const handleDismiss = async () => {
    if (disabled || processing) return;
    
    try {
      await onDismiss(suggestion.type);
      addToast(successToast('Suggestion Dismissed', 'This suggestion type has been dismissed.'));
    } catch (error) {
      addToast(errorToast('Dismiss Failed', 'Failed to dismiss suggestion. Please try again.'));
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className={`relative border rounded-lg overflow-hidden ${priorityStyle.border} ${priorityStyle.bg} ${
        disabled ? 'opacity-60' : ''
      }`}
    >
      {/* Priority indicator */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${priorityStyle.indicator}`} />
      
      {/* Card content */}
      <div className="p-4 pl-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start space-x-3 flex-1">
            <div className={`flex-shrink-0 ${priorityStyle.iconColor} mt-0.5`}>
              <PriorityIcon className="h-5 w-5" />
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="font-semibold text-gray-900 dark:text-white text-sm leading-tight">
                  {suggestion.title}
                </h3>
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                  suggestion.priority === 'critical' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                  suggestion.priority === 'high' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' :
                  suggestion.priority === 'medium' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                  'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
                }`}>
                  {suggestion.priority}
                </span>
              </div>
              
              <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                {suggestion.description}
              </p>
            </div>
          </div>
          
          {/* Info button */}
          <button
            onClick={() => setShowRationale(!showRationale)}
            className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            title="Why this suggestion?"
          >
            <HelpCircle className="h-4 w-4" />
          </button>
        </div>

        {/* Rationale (expandable) */}
        {showRationale && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mb-4 p-3 bg-white/50 dark:bg-gray-800/50 rounded border border-gray-200 dark:border-gray-700"
          >
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              <strong>Why this suggestion:</strong> {suggestion.rationale}
            </p>
          </motion.div>
        )}

        {/* Action buttons */}
        <div className="flex items-center space-x-2">
          <motion.button
            onClick={handleAccept}
            disabled={disabled || processing}
            whileHover={disabled ? {} : { scale: 1.02 }}
            whileTap={disabled ? {} : { scale: 0.98 }}
            className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              disabled || processing
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600'
                : 'bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
            }`}
          >
            <CheckCircle className="h-4 w-4" />
            <span>{processing ? 'Processing...' : actionLabel}</span>
          </motion.button>
          
          <motion.button
            onClick={handleDismiss}
            disabled={disabled || processing}
            whileHover={disabled ? {} : { scale: 1.02 }}
            whileTap={disabled ? {} : { scale: 0.98 }}
            className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              disabled || processing
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            <X className="h-4 w-4" />
            <span>Dismiss</span>
          </motion.button>
        </div>

        {/* Relevance score indicator (optional) */}
        {suggestion.relevance_score !== undefined && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Relevance</span>
              <div className="flex items-center space-x-2">
                <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 rounded-full transition-all duration-300"
                    style={{ width: `${Math.round(suggestion.relevance_score * 100)}%` }}
                  />
                </div>
                <span>{Math.round(suggestion.relevance_score * 100)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default SuggestionCard;