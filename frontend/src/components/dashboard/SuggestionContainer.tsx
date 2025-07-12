import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Eye, EyeOff, Bot, AlertCircle } from 'lucide-react';
import { useAgentStore } from '../../store/agentStore';
import { useToastStore } from '../../store/toastStore';
import { apiService } from '../../services/api';
import SuggestionCard from './SuggestionCard';
import { Suggestion } from '../../store/agentStore';
import { successToast, errorToast, infoToast, warningToast } from '../../utils/toastHelpers';

interface SuggestionContainerProps {
  className?: string;
  maxSuggestions?: number;
  autoRefreshInterval?: number; // in milliseconds
}

const SuggestionContainer: React.FC<SuggestionContainerProps> = ({
  className = '',
  maxSuggestions = 3,
  autoRefreshInterval = 300000 // 5 minutes
}) => {
  const {
    suggestions,
    dismissedSuggestions,
    suggestionsLoading,
    suggestionsError,
    showSuggestions,
    setSuggestions,
    dismissSuggestion,
    setSuggestionsLoading,
    setSuggestionsError,
    setShowSuggestions
  } = useAgentStore();

  const addToast = useToastStore(state => state.addToast);
  const [lastFetch, setLastFetch] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Filter out dismissed suggestions
  const activeSuggestions = suggestions.filter(
    suggestion => !dismissedSuggestions.has(suggestion.type)
  ).slice(0, maxSuggestions);

  const fetchSuggestions = useCallback(async (showLoading = true) => {
    // Prevent duplicate requests
    if (suggestionsLoading || refreshing) {
      console.log('Suggestions already loading, skipping request');
      return;
    }

    // Rate limiting: don't fetch more than once every 30 seconds
    const now = new Date();
    if (lastFetch && (now.getTime() - lastFetch.getTime()) < 30000) {
      console.log('Rate limiting: too soon since last fetch, skipping request');
      return;
    }

    if (showLoading) {
      setSuggestionsLoading(true);
    } else {
      setRefreshing(true);
    }
    
    setSuggestionsError(null);

    try {
      console.log('Fetching AI suggestions...');
      const fetchedSuggestions = await apiService.getAgentSuggestions();
      setSuggestions(fetchedSuggestions);
      setLastFetch(new Date());
      console.log(`Fetched ${fetchedSuggestions.length} suggestions`);
    } catch (error: any) {
      console.error('Failed to fetch suggestions:', error);
      const errorMessage = error.message || 'Failed to load suggestions';
      setSuggestionsError(errorMessage);
      addToast(errorToast('Loading Failed', `Error loading suggestions: ${errorMessage}`));
    } finally {
      setSuggestionsLoading(false);
      setRefreshing(false);
    }
  }, [setSuggestions, setSuggestionsLoading, setSuggestionsError, addToast, suggestionsLoading, refreshing, lastFetch]);

  const handleAcceptSuggestion = async (suggestion: Suggestion) => {
    try {
      const response = await apiService.processAgentAction({
        action: suggestion.action,
        params: suggestion.action_params,
        type: suggestion.type
      });

      if (response.action_handled) {
        addToast(successToast('Success', 'Suggestion processed successfully!'));
        
        // Remove the processed suggestion from the list
        setSuggestions(suggestions.filter(s => s.type !== suggestion.type));
        
        // Show response if available
        if (response.response) {
          addToast(infoToast('Agent Response', response.response, 8000)); // Longer duration for detailed responses
        }
        
        // Refresh suggestions after a short delay
        setTimeout(() => {
          fetchSuggestions(false);
        }, 2000);
      } else {
        addToast(warningToast('Processing Issue', 'Suggestion could not be processed at this time.'));
      }
    } catch (error: any) {
      console.error('Failed to process suggestion:', error);
      const errorMessage = error.message || 'Failed to process suggestion';
      addToast(errorToast('Processing Error', errorMessage));
    }
  };

  const handleDismissSuggestion = async (suggestionType: string) => {
    try {
      await apiService.dismissSuggestion(suggestionType);
      dismissSuggestion(suggestionType);
    } catch (error: any) {
      console.error('Failed to dismiss suggestion:', error);
      const errorMessage = error.message || 'Failed to dismiss suggestion';
      addToast(errorToast('Dismiss Error', errorMessage));
    }
  };

  const handleManualRefresh = () => {
    fetchSuggestions(false);
  };

  const toggleVisibility = () => {
    setShowSuggestions(!showSuggestions);
  };

  // Initial fetch - only if we don't have suggestions yet
  useEffect(() => {
    if (suggestions.length === 0 && !suggestionsLoading) {
      fetchSuggestions();
    }
  }, [fetchSuggestions, suggestions.length, suggestionsLoading]);

  // Auto-refresh interval with tab visibility detection
  useEffect(() => {
    if (!autoRefreshInterval || autoRefreshInterval <= 0) return;

    const handleVisibilityChange = () => {
      // Don't fetch when tab becomes visible to prevent excessive requests
      // Only rely on the interval timer
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    const interval = setInterval(() => {
      // Only fetch if tab is visible and not already loading
      if (!document.hidden && !suggestionsLoading && !refreshing) {
        const now = new Date();
        // Additional check: only fetch if it's been at least 5 minutes since last fetch
        if (!lastFetch || (now.getTime() - lastFetch.getTime()) >= autoRefreshInterval) {
          fetchSuggestions(false);
        }
      }
    }, autoRefreshInterval);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [autoRefreshInterval, suggestionsLoading, refreshing, lastFetch, fetchSuggestions]);

  if (!showSuggestions) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`p-4 ${className}`}
      >
        <button
          onClick={toggleVisibility}
          className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
        >
          <Bot className="h-4 w-4" />
          <span>Show AI Suggestions</span>
          <Eye className="h-4 w-4" />
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`space-y-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Bot className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            AI Suggestions
          </h2>
          {activeSuggestions.length > 0 && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
              {activeSuggestions.length}
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {lastFetch && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Updated {lastFetch.toLocaleTimeString()}
            </span>
          )}
          
          <button
            onClick={handleManualRefresh}
            disabled={suggestionsLoading || refreshing}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh suggestions"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={toggleVisibility}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
            title="Hide suggestions"
          >
            <EyeOff className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Loading state */}
      {suggestionsLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-8"
        >
          <div className="flex items-center space-x-2 text-gray-600 dark:text-gray-400">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Loading suggestions...</span>
          </div>
        </motion.div>
      )}

      {/* Error state */}
      {suggestionsError && !suggestionsLoading && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
        >
          <div className="flex items-center space-x-2 text-red-800 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm font-medium">Failed to load suggestions</span>
          </div>
          <p className="text-red-700 dark:text-red-300 text-sm mt-1">{suggestionsError}</p>
          <button
            onClick={() => fetchSuggestions()}
            className="mt-2 text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 underline"
          >
            Try again
          </button>
        </motion.div>
      )}

      {/* Suggestions list */}
      {!suggestionsLoading && !suggestionsError && (
        <AnimatePresence mode="popLayout">
          {activeSuggestions.length === 0 ? (
            <motion.div
              key="no-suggestions"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="text-center py-8"
            >
              <Bot className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600 dark:text-gray-400">
                No suggestions available right now.
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
                I'll analyze your emails and provide helpful suggestions when ready.
              </p>
            </motion.div>
          ) : (
            <div className="space-y-3">
              {activeSuggestions.map((suggestion) => (
                <motion.div
                  key={suggestion.type}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <SuggestionCard
                    suggestion={suggestion}
                    onAccept={handleAcceptSuggestion}
                    onDismiss={handleDismissSuggestion}
                    disabled={suggestionsLoading || refreshing}
                  />
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>
      )}

      {/* Dismissal info */}
      {dismissedSuggestions.size > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-xs text-gray-500 dark:text-gray-400 text-center pt-2 border-t border-gray-200 dark:border-gray-700"
        >
          {dismissedSuggestions.size} suggestion{dismissedSuggestions.size !== 1 ? 's' : ''} dismissed this session.
          <br />
          You can reset dismissed suggestions in Settings.
        </motion.div>
      )}
    </motion.div>
  );
};

export default SuggestionContainer;