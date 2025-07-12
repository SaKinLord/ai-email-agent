import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Check } from 'lucide-react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (correctedPriority: string, correctedIntent: string) => void;
  emailSubject: string;
  currentPriority: string;
  currentIntent: string;
}

const PRIORITY_OPTIONS = [
  { value: 'CRITICAL', label: 'Critical', color: 'text-red-600' },
  { value: 'HIGH', label: 'High', color: 'text-orange-600' },
  { value: 'MEDIUM', label: 'Medium', color: 'text-yellow-600' },
  { value: 'LOW', label: 'Low', color: 'text-green-600' },
];

const INTENT_OPTIONS = [
  { value: 'action_request', label: 'Action Request' },
  { value: 'meeting_invite', label: 'Meeting Invite' },
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'promotion', label: 'Promotion' },
  { value: 'social', label: 'Social' },
  { value: 'task_related', label: 'Task Related' },
];

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  emailSubject,
  currentPriority,
  currentIntent,
}) => {
  const [selectedPriority, setSelectedPriority] = useState(currentPriority);
  const [selectedIntent, setSelectedIntent] = useState(currentIntent);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await onSubmit(selectedPriority, selectedIntent);
      onClose();
    } catch (error) {
      console.error('Error submitting feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setSelectedPriority(currentPriority);
      setSelectedIntent(currentIntent);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="absolute inset-0 bg-black bg-opacity-50"
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-md bg-white rounded-lg shadow-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Provide Feedback
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  Help improve classification accuracy
                </p>
              </div>
              <button
                onClick={handleClose}
                disabled={isSubmitting}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* Email Subject */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Subject
                </label>
                <div className="p-3 bg-gray-50 rounded-md text-sm text-gray-900 border">
                  {emailSubject}
                </div>
              </div>

              {/* Current Classification */}
              <div className="bg-blue-50 p-4 rounded-md">
                <h4 className="text-sm font-medium text-blue-900 mb-2">
                  Current Classification
                </h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-blue-700">Priority:</span>
                    <span className={`font-medium ${PRIORITY_OPTIONS.find(p => p.value === currentPriority)?.color || 'text-gray-900'}`}>
                      {PRIORITY_OPTIONS.find(p => p.value === currentPriority)?.label || currentPriority}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-blue-700">Intent:</span>
                    <span className="font-medium text-blue-900">
                      {INTENT_OPTIONS.find(i => i.value === currentIntent)?.label || currentIntent}
                    </span>
                  </div>
                </div>
              </div>

              {/* Priority Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Correct Priority
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {PRIORITY_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedPriority(option.value)}
                      className={`p-3 text-left border rounded-md transition-colors ${
                        selectedPriority === option.value
                          ? 'border-blue-500 bg-blue-50 text-blue-900'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-medium ${selectedPriority === option.value ? 'text-blue-900' : option.color}`}>
                          {option.label}
                        </span>
                        {selectedPriority === option.value && (
                          <Check className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Intent Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Correct Intent
                </label>
                <div className="space-y-2">
                  {INTENT_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedIntent(option.value)}
                      className={`w-full p-3 text-left border rounded-md transition-colors ${
                        selectedIntent === option.value
                          ? 'border-blue-500 bg-blue-50 text-blue-900'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`font-medium ${selectedIntent === option.value ? 'text-blue-900' : 'text-gray-700'}`}>
                          {option.label}
                        </span>
                        {selectedIntent === option.value && (
                          <Check className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};