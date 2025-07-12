import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Save, RotateCcw, AlertTriangle } from 'lucide-react';
import { useSettingsStore } from '../../store/settingsStore';
import { toast } from '../../store/toastStore';

const StickyActionBar: React.FC = () => {
  const {
    hasChanges,
    getChangedCategories,
    isSaving,
    saveSettings,
    discardChanges,
    validateSettings
  } = useSettingsStore();

  const hasUnsavedChanges = hasChanges();
  const changedCategories = getChangedCategories();

  const handleSaveAll = async () => {
    const isValid = await validateSettings();
    if (!isValid) {
      toast.error(
        'Validation failed',
        'Please fix the errors before saving settings.'
      );
      return;
    }

    const success = await saveSettings();
    if (success) {
      toast.success(
        'Settings saved',
        'All configuration changes have been saved successfully.'
      );
    } else {
      toast.error(
        'Save failed',
        'There was an error saving your settings. Please try again.'
      );
    }
  };

  const handleDiscardChanges = () => {
    discardChanges();
    toast.info(
      'Changes discarded',
      'All unsaved changes have been reverted.'
    );
  };

  return (
    <AnimatePresence>
      {hasUnsavedChanges && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-2xl"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between py-4">
              <div className="flex items-center space-x-3">
                <motion.div
                  animate={{ rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
                >
                  <AlertTriangle className="h-5 w-5 text-orange-600" />
                </motion.div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    You have unsaved changes
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {changedCategories.length} section{changedCategories.length !== 1 ? 's' : ''} modified: {' '}
                    {changedCategories.map(cat => 
                      cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                    ).join(', ')}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleDiscardChanges}
                  disabled={isSaving}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <RotateCcw className="h-4 w-4 mr-2 inline" />
                  Discard Changes
                </button>
                
                <button
                  onClick={handleSaveAll}
                  disabled={isSaving}
                  className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
                >
                  {isSaving ? (
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"
                    />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  {isSaving ? 'Saving...' : 'Save All Changes'}
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default StickyActionBar;