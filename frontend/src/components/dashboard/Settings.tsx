import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, Cog, Zap, Activity, Settings as SettingsIcon, TestTube, Mail, Bot, RefreshCw } from 'lucide-react';
import { useSettingsStore } from '../../store/settingsStore';
import { useActivityStore } from '../../store/activityStore';
import { useAgentStore } from '../../store/agentStore';
import { apiService } from '../../services/api';
import { toast } from '../../store/toastStore';

// Import individual setting sections
import LLMSettingsSection from '../settings/sections/LLMSettingsSection';
import ClassificationSection from '../settings/sections/ClassificationSection';
import ReasoningSection from '../settings/sections/ReasoningSection';
import IntegrationsSection from '../settings/sections/IntegrationsSection';
import EmailManagementSection from '../settings/sections/EmailManagementSection';
import StickyActionBar from '../settings/StickyActionBar';

const Settings: React.FC = () => {
  const { loadSettings, config, isLoading } = useSettingsStore();
  const { isConnected } = useActivityStore();
  const { dismissedSuggestions, clearDismissedSuggestions } = useAgentStore();
  const [testing, setTesting] = useState(false);

  // Load settings on component mount
  useEffect(() => {
    if (!config) {
      loadSettings().then(() => {
        toast.success('Settings loaded successfully');
      }).catch(() => {
        toast.error('Failed to load settings');
      });
    }
  }, [config, loadSettings]);

  const handleTestActivity = async () => {
    try {
      setTesting(true);
      await apiService.testActivityBroadcast();
      toast.success(
        'Activity test completed', 
        'Real-time activity broadcast test was successful.',
        {
          label: 'View Activity',
          onClick: () => window.location.href = '/dashboard/activity'
        }
      );
    } catch (error) {
      console.error('Test activity failed:', error);
      toast.error(
        'Activity test failed', 
        'There was an error testing the activity broadcast system.'
      );
    } finally {
      setTesting(false);
    }
  };

  const handleTestSystemStatus = async () => {
    try {
      setTesting(true);
      await apiService.testSystemStatusBroadcast();
      toast.success(
        'System status test completed', 
        'System status broadcast test was successful.'
      );
    } catch (error) {
      console.error('Test system status failed:', error);
      toast.error(
        'System status test failed', 
        'There was an error testing the system status broadcast.'
      );
    } finally {
      setTesting(false);
    }
  };

  const handleTestEmailProcessing = async () => {
    try {
      setTesting(true);
      await apiService.testEmailProcessingSimulation({
        subject: 'Test Email - Real-time Processing Demo',
        sender: 'demo@maia-agent.com',
        body: 'This is a demonstration of real-time email processing with live WebSocket updates.'
      });
      toast.success(
        'Email processing test started', 
        'Watch the Activity Feed for real-time updates.',
        {
          label: 'View Pipeline',
          onClick: () => window.location.href = '/dashboard/pipeline'
        }
      );
    } catch (error) {
      console.error('Test email processing failed:', error);
      toast.error(
        'Email processing test failed', 
        'There was an error starting the email processing simulation.'
      );
    } finally {
      setTesting(false);
    }
  };

  const handleProcessRealEmails = async () => {
    try {
      setTesting(true);
      await apiService.processRealGmailEmails({
        max_emails: 3,
        use_enhanced_reasoning: true
      });
      toast.info(
        'Real email processing started', 
        'Processing up to 3 emails from your Gmail inbox with enhanced AI reasoning.',
        {
          label: 'View Activity',
          onClick: () => window.location.href = '/dashboard/activity'
        }
      );
    } catch (error) {
      console.error('Real Gmail processing failed:', error);
      toast.error(
        'Gmail processing failed', 
        'There was an error processing your Gmail emails. Please check your connection.'
      );
    } finally {
      setTesting(false);
    }
  };

  const handleResetDismissedSuggestions = () => {
    clearDismissedSuggestions();
    toast.success(
      'Suggestions Reset',
      'All dismissed suggestions have been reset and will appear again.',
      {
        label: 'View Dashboard',
        onClick: () => window.location.href = '/dashboard'
      }
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full"
        />
      </div>
    );
  }

  return (
    <>
      <div className="space-y-8 pb-24"> {/* Added bottom padding for sticky action bar */}
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Agent Configuration
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Configure your AI email agent's behavior, intelligence settings, and system preferences
          </p>
        </motion.div>

        {/* AI & Agent Behavior Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-6"
        >
          <div className="flex items-center space-x-3 border-b border-gray-200 dark:border-gray-700 pb-3">
            <Brain className="h-6 w-6 text-blue-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                AI & Agent Behavior
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configure language models, classification rules, and reasoning
              </p>
            </div>
          </div>
          
          <div className="space-y-4">
            <LLMSettingsSection />
            <ClassificationSection />
            <ReasoningSection />
          </div>
        </motion.div>

        {/* System & Data Management Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          <div className="flex items-center space-x-3 border-b border-gray-200 dark:border-gray-700 pb-3">
            <Cog className="h-6 w-6 text-green-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                System & Data Management
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configure integrations, email processing, and system-level settings
              </p>
            </div>
          </div>
          
          <div className="space-y-4">
            <IntegrationsSection />
            <EmailManagementSection />
          </div>
        </motion.div>

        {/* AI Agent Preferences Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="space-y-6"
        >
          <div className="flex items-center space-x-3 border-b border-gray-200 dark:border-gray-700 pb-3">
            <Bot className="h-6 w-6 text-purple-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                AI Agent Preferences
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Manage AI suggestions, chat interface, and agent behavior
              </p>
            </div>
          </div>
          
          <div className="card">
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Suggestion Management
              </h3>
              
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      Dismissed Suggestions
                    </span>
                    {dismissedSuggestions.size > 0 && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400">
                        {dismissedSuggestions.size} dismissed
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {dismissedSuggestions.size > 0 
                      ? `You have ${dismissedSuggestions.size} dismissed suggestion type(s). Reset to see them again.`
                      : 'No suggestions have been dismissed. Dismissed suggestions will appear here.'
                    }
                  </p>
                </div>
                
                <button
                  onClick={handleResetDismissedSuggestions}
                  disabled={dismissedSuggestions.size === 0}
                  className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Reset All</span>
                </button>
              </div>
              
              {dismissedSuggestions.size > 0 && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                  <div className="flex items-start space-x-2">
                    <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                        Dismissed suggestion types:
                      </p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {Array.from(dismissedSuggestions).map((type) => (
                          <span
                            key={type}
                            className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                          >
                            {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Real-time Testing Card - At Bottom */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="flex items-center space-x-3 mb-6">
            <TestTube className="h-5 w-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Real-time Testing
            </h2>
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <button
              onClick={handleTestActivity}
              disabled={testing || !isConnected}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Activity className="h-6 w-6 text-blue-600 mb-2" />
              <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                Test Activity
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Send a test activity notification
              </p>
            </button>

            <button
              onClick={handleTestSystemStatus}
              disabled={testing || !isConnected}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <SettingsIcon className="h-6 w-6 text-green-600 mb-2" />
              <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                Test Status
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Send a test system status update
              </p>
            </button>

            <button
              onClick={handleTestEmailProcessing}
              disabled={testing || !isConnected}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Zap className="h-6 w-6 text-purple-600 mb-2" />
              <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                Test Processing
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Simulate complete email processing flow
              </p>
            </button>

            <button
              onClick={handleProcessRealEmails}
              disabled={testing || !isConnected}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Mail className="h-6 w-6 text-orange-600 mb-2" />
              <h3 className="font-medium text-gray-900 dark:text-white mb-1">
                Process Real Emails
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Process actual Gmail emails with real-time updates
              </p>
            </button>
          </div>

          {testing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
            >
              <p className="text-sm text-blue-700 dark:text-blue-300">
                Testing real-time communication... Check the Activity Feed for updates!
              </p>
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* Sticky Action Bar */}
      <StickyActionBar />
    </>
  );
};

export default Settings;