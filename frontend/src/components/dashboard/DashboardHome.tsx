import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Mail, AlertTriangle, CheckCircle, Clock, TrendingUp, 
  BarChart3, Zap, Shield, Brain, Target, Loader2 
} from 'lucide-react';
import { useEmailStore } from '../../store/emailStore';
import { useActivityStore } from '../../store/activityStore';
import { apiService } from '../../services/api';
import { toast } from '../../store/toastStore';
import LoadingSpinner from '../common/LoadingSpinner';
import SuggestionContainer from './SuggestionContainer';
import ChatInterface from './ChatInterface';

const DashboardHome: React.FC = () => {
  const { dashboardData, loading } = useEmailStore();
  const { activities, systemStatus } = useActivityStore();

  // Loading states for Quick Actions
  const [actionLoading, setActionLoading] = useState<{
    'process-emails': boolean;
    'retrain-model': boolean;
    'generate-report': boolean;
    'security-scan': boolean;
  }>({
    'process-emails': false,
    'retrain-model': false,
    'generate-report': false,
    'security-scan': false,
  });

  const recentActivities = activities.slice(0, 5);

  // Quick Actions handlers
  const handleQuickAction = async (actionType: keyof typeof actionLoading) => {
    // Set loading state for this specific action
    setActionLoading(prev => ({ ...prev, [actionType]: true }));

    try {
      switch (actionType) {
        case 'process-emails':
          await apiService.processRealGmailEmails({ max_emails: 10 });
          toast.success(
            'Email Processing Started',
            'Started processing new emails. Check the activity feed for updates.'
          );
          break;

        case 'retrain-model':
          await apiService.retrainModel();
          toast.success(
            'AI Model Retraining Started',
            'The AI model is being retrained with your feedback. This may take a few minutes.'
          );
          break;

        case 'generate-report':
          const reportData = await apiService.generateReport();
          toast.success(
            'Report Generated Successfully',
            `Generated report with insights from ${reportData.stats.total_emails} emails.`,
            {
              label: 'View Report',
              onClick: () => {
                // Create a modal or navigate to report view
                alert(reportData.report); // Temporary - should be replaced with proper modal
              }
            }
          );
          break;

        case 'security-scan':
          const scanResults = await apiService.performSecurityScan({ hours_back: 24 });
          if (scanResults.threats_found > 0) {
            toast.warning(
              'Security Threats Found',
              `Found ${scanResults.threats_found} potential threats in ${scanResults.emails_scanned} emails.`,
              {
                label: 'View Details',
                onClick: () => {
                  // Navigate to security details view
                  console.log('Security scan results:', scanResults);
                  alert(scanResults.summary); // Temporary - should be replaced with proper modal
                }
              }
            );
          } else {
            toast.success(
              'No Security Threats Found',
              `Scanned ${scanResults.emails_scanned} emails - all clear!`
            );
          }
          break;

        default:
          throw new Error(`Unknown action type: ${actionType}`);
      }
    } catch (error: any) {
      console.error(`Error executing ${actionType}:`, error);
      toast.error(
        'Action Failed',
        error.message || `Failed to execute ${actionType.replace('-', ' ')}`
      );
    } finally {
      // Always reset loading state
      setActionLoading(prev => ({ ...prev, [actionType]: false }));
    }
  };

  // Primary stats for main dashboard
  const primaryStats = [
    {
      label: 'Total Emails',
      value: dashboardData?.total_emails || 0,
      change: dashboardData?.email_change_24h || 0,
      icon: Mail,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    },
    {
      label: 'Unread',
      value: dashboardData?.unread_count || 0,
      change: dashboardData?.unread_change_24h || 0,
      icon: AlertTriangle,
      color: 'text-warning-600',
      bgColor: 'bg-warning-100 dark:bg-warning-900/20',
    },
    {
      label: 'High Priority',
      value: (dashboardData?.priority_counts?.HIGH || 0) + (dashboardData?.priority_counts?.CRITICAL || 0),
      change: dashboardData?.priority_change_24h || 0,
      icon: CheckCircle,
      color: 'text-red-600',
      bgColor: 'bg-red-100 dark:bg-red-900/20',
    },
    {
      label: 'Processing',
      value: systemStatus?.active_tasks?.length || 0,
      change: 0,
      icon: Clock,
      color: 'text-green-600',
      bgColor: 'bg-green-100 dark:bg-green-900/20',
    },
  ];

  // AI performance stats using dynamic data from enhanced endpoint
  const aiPerformance = dashboardData?.ai_performance;
  const aiStats = [
    {
      label: 'Classification Accuracy',
      value: `${aiPerformance?.classification_accuracy || 85.0}%`,
      icon: Brain,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100 dark:bg-purple-900/20',
    },
    {
      label: 'Auto-Actions Today',
      value: aiPerformance?.auto_actions_today || 0,
      icon: Zap,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100 dark:bg-indigo-900/20',
    },
    {
      label: 'Time Saved',
      value: aiPerformance?.time_saved || '0m',
      icon: Target,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-100 dark:bg-emerald-900/20',
    },
    {
      label: 'Security Score',
      value: `${aiPerformance?.security_score || 95}/100`,
      icon: Shield,
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-100 dark:bg-cyan-900/20',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Good morning! 👋
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Here's what's happening with your emails today.
        </p>
      </motion.div>

      {/* Primary Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {primaryStats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card hover:shadow-lg transition-shadow duration-200"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {stat.value}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {stat.label}
                  </p>
                </div>
              </div>
              {stat.change !== 0 && (
                <div className="flex items-center space-x-1">
                  <TrendingUp className={`h-4 w-4 ${
                    stat.change > 0 ? 'text-green-500' : 'text-red-500'
                  } ${stat.change > 0 ? '' : 'rotate-180'}`} />
                  <span className={`text-sm font-medium ${
                    stat.change > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {Math.abs(stat.change)}
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {/* AI Performance Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="card"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            AI Performance
          </h2>
          <BarChart3 className="h-5 w-5 text-gray-400" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {aiStats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6 + index * 0.1 }}
              className="flex items-center space-x-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  {stat.label}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* AI Suggestions Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="card"
      >
        <SuggestionContainer maxSuggestions={3} autoRefreshInterval={300000} />
      </motion.div>

      {/* Recent Activity & Quick Actions Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Activity
            </h2>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Live updates
            </span>
          </div>

          {recentActivities.length > 0 ? (
            <div className="space-y-3">
              {recentActivities.map((activity, index) => (
                <motion.div
                  key={activity.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + index * 0.1 }}
                  className="flex items-start space-x-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className={`mt-1 h-2 w-2 rounded-full ${
                    activity.status === 'completed' ? 'bg-green-500' :
                    activity.status === 'error' ? 'bg-red-500' :
                    'bg-blue-500 animate-pulse'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {activity.title}
                    </p>
                    {activity.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {activity.description}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {new Date(activity.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Clock className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                No recent activity
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Activity will appear here as emails are processed
              </p>
            </div>
          )}
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="card"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Quick Actions
            </h2>
            <Zap className="h-5 w-5 text-gray-400" />
          </div>

          <div className="space-y-3">
            <motion.button
              whileHover={{ scale: actionLoading['process-emails'] ? 1 : 1.02 }}
              whileTap={{ scale: actionLoading['process-emails'] ? 1 : 0.98 }}
              onClick={() => handleQuickAction('process-emails')}
              disabled={actionLoading['process-emails']}
              className="w-full flex items-center justify-between p-4 bg-primary-50 hover:bg-primary-100 dark:bg-primary-900/20 dark:hover:bg-primary-900/30 rounded-lg transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center space-x-3">
                <Mail className="h-5 w-5 text-primary-600" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">Process New Emails</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Check for and process unread emails</p>
                </div>
              </div>
              {actionLoading['process-emails'] && (
                <Loader2 className="h-4 w-4 text-primary-600 animate-spin" />
              )}
            </motion.button>

            <motion.button
              whileHover={{ scale: actionLoading['retrain-model'] ? 1 : 1.02 }}
              whileTap={{ scale: actionLoading['retrain-model'] ? 1 : 0.98 }}
              onClick={() => handleQuickAction('retrain-model')}
              disabled={actionLoading['retrain-model']}
              className="w-full flex items-center justify-between p-4 bg-green-50 hover:bg-green-100 dark:bg-green-900/20 dark:hover:bg-green-900/30 rounded-lg transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center space-x-3">
                <Brain className="h-5 w-5 text-green-600" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">Retrain AI Model</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Update classification model with recent feedback</p>
                </div>
              </div>
              {actionLoading['retrain-model'] && (
                <Loader2 className="h-4 w-4 text-green-600 animate-spin" />
              )}
            </motion.button>

            <motion.button
              whileHover={{ scale: actionLoading['generate-report'] ? 1 : 1.02 }}
              whileTap={{ scale: actionLoading['generate-report'] ? 1 : 0.98 }}
              onClick={() => handleQuickAction('generate-report')}
              disabled={actionLoading['generate-report']}
              className="w-full flex items-center justify-between p-4 bg-purple-50 hover:bg-purple-100 dark:bg-purple-900/20 dark:hover:bg-purple-900/30 rounded-lg transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center space-x-3">
                <BarChart3 className="h-5 w-5 text-purple-600" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">Generate Report</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Generate insights with pie and bar charts</p>
                </div>
              </div>
              {actionLoading['generate-report'] && (
                <Loader2 className="h-4 w-4 text-purple-600 animate-spin" />
              )}
            </motion.button>

            <motion.button
              whileHover={{ scale: actionLoading['security-scan'] ? 1 : 1.02 }}
              whileTap={{ scale: actionLoading['security-scan'] ? 1 : 0.98 }}
              onClick={() => handleQuickAction('security-scan')}
              disabled={actionLoading['security-scan']}
              className="w-full flex items-center justify-between p-4 bg-orange-50 hover:bg-orange-100 dark:bg-orange-900/20 dark:hover:bg-orange-900/30 rounded-lg transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center space-x-3">
                <Shield className="h-5 w-5 text-orange-600" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">Security Scan</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Scan recent emails for security threats</p>
                </div>
              </div>
              {actionLoading['security-scan'] && (
                <Loader2 className="h-4 w-4 text-orange-600 animate-spin" />
              )}
            </motion.button>
          </div>
        </motion.div>
      </div>

      {/* System Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="card"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            System Status
          </h2>
          <div className="flex items-center space-x-2">
            <div className={`h-2 w-2 rounded-full ${
              systemStatus?.autonomous_mode ? 'bg-green-500' : 'bg-gray-400'
            }`} />
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {systemStatus?.autonomous_mode ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <Zap className="h-5 w-5 text-blue-500" />
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Autonomous Mode
                </span>
                <p className={`text-sm font-medium ${
                  systemStatus?.autonomous_mode ? 'text-green-600' : 'text-gray-500'
                }`}>
                  {systemStatus?.autonomous_mode ? 'Enabled' : 'Disabled'}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <Clock className="h-5 w-5 text-purple-500" />
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Last Check
                </span>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {systemStatus?.last_email_check ? 
                    new Date(systemStatus.last_email_check).toLocaleTimeString() : 
                    'Never'
                  }
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <Brain className="h-5 w-5 text-green-500" />
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  AI Model
                </span>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {dashboardData?.ml_model_version || 'v1.0.0'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center space-x-3">
              <Shield className="h-5 w-5 text-cyan-500" />
              <div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Security
                </span>
                <p className="text-sm font-medium text-green-600">
                  All systems secure
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Additional System Info */}
        {systemStatus?.active_tasks && systemStatus.active_tasks.length > 0 && (
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center space-x-2 mb-2">
              <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Active Processing Tasks: {systemStatus.active_tasks.length}
              </span>
            </div>
            <p className="text-xs text-blue-600 dark:text-blue-300">
              {systemStatus.active_tasks.join(', ')}
            </p>
          </div>
        )}
      </motion.div>

      {/* Chat Interface - Floating */}
      <ChatInterface position="floating" defaultMinimized={true} />
    </div>
  );
};

export default DashboardHome;