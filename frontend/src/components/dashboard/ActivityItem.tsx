import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { 
  Activity, Clock, CheckCircle, AlertCircle, Calendar, 
  Mail, Brain, Zap, Archive, FileText, BarChart3, Shield
} from 'lucide-react';
import { ActivityItem as ActivityItemType } from '../../store/activityStore';
import PieChart from '../charts/PieChart';
import BarChart from '../charts/BarChart';

interface Props {
  activity: ActivityItemType;
  index: number;
}

// Memoized ActivityItem component to prevent unnecessary re-renders
const ActivityItem: React.FC<Props> = memo(({ activity, index }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'in_progress':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'email_processing':
        return <Mail className="h-4 w-4" />;
      case 'autonomous_task':
        return <Zap className="h-4 w-4" />;
      case 'autonomous_action':
        return <Archive className="h-4 w-4" />;
      case 'ml_training':
        return <Brain className="h-4 w-4" />;
      case 'report_generation':
        return <BarChart3 className="h-4 w-4" />;
      case 'security_scan':
        return <Shield className="h-4 w-4" />;
      case 'classification':
        return <FileText className="h-4 w-4" />;
      case 'archive':
        return <Archive className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'email_processing':
        return 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300';
      case 'autonomous_task':
        return 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300';
      case 'autonomous_action':
        return 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300';
      case 'ml_training':
        return 'bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300';
      case 'report_generation':
        return 'bg-violet-100 dark:bg-violet-900/20 text-violet-700 dark:text-violet-300';
      case 'security_scan':
        return 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300';
      case 'classification':
        return 'bg-indigo-100 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300';
      case 'archive':
        return 'bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300';
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ delay: index * 0.02 }} // Reduced delay for smoother rendering
      className="flex items-start space-x-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
    >
      <div className="flex-shrink-0 mt-1">
        {getStatusIcon(activity.status)}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2 mb-2">
          <span className={`inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium rounded-full ${getTypeColor(activity.type)}`}>
            {getTypeIcon(activity.type)}
            <span>{activity.type.replace('_', ' ')}</span>
          </span>
          {activity.stage && (
            <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
              {activity.stage}
            </span>
          )}
        </div>
        
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          {activity.title}
        </h3>
        
        {activity.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {activity.description}
          </p>
        )}
        
        {activity.progress !== undefined && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
              <span>Progress</span>
              <span>{activity.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${activity.progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }} // Reduced duration for smoother animation
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full"
              />
            </div>
          </div>
        )}
        
        {/* Chart visualization for report generation completion */}
        {activity.charts && activity.type === 'report_generation' && activity.status === 'completed' && (
          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {activity.charts.pie_chart && (
                <div className="flex justify-center">
                  <PieChart
                    data={activity.charts.pie_chart.data}
                    title={activity.charts.pie_chart.title}
                    size={140}
                  />
                </div>
              )}
              
              {activity.charts.bar_chart && (
                <div className="flex justify-center">
                  <BarChart
                    data={activity.charts.bar_chart.data}
                    title={activity.charts.bar_chart.title}
                    height={100}
                  />
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Security scan threat details */}
        {activity.type === 'security_scan' && activity.status === 'completed' && activity.scan_details && activity.scan_details.length > 0 && (
          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700">
            <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-3 flex items-center space-x-2">
              <Shield className="h-4 w-4" />
              <span>Threats Detected</span>
            </h4>
            <div className="space-y-3">
              {activity.scan_details.map((threat: any, idx: number) => (
                <div key={idx} className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-amber-200 dark:border-amber-700">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h5 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {threat.subject}
                      </h5>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        From: {threat.sender}
                      </p>
                    </div>
                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                      threat.risk_level === 'HIGH' ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300' :
                      threat.risk_level === 'MEDIUM' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300' :
                      'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'
                    }`}>
                      {threat.risk_level}
                    </span>
                  </div>
                  
                  {threat.flags && threat.flags.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Security Flags:</p>
                      <div className="flex flex-wrap gap-1">
                        {threat.flags.map((flag: string, flagIdx: number) => (
                          <span key={flagIdx} className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-2 py-1 rounded">
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {threat.llm_analysis && (
                    <div className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 p-2 rounded">
                      <span className="font-medium">AI Analysis: </span>
                      {threat.llm_analysis}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-1">
            <Calendar className="h-3 w-3" />
            <span>{new Date(activity.created_at).toLocaleString()}</span>
          </span>
          
          {activity.confidence && activity.confidence > 0 && (
            <span className="text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded">
              {(activity.confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
});

ActivityItem.displayName = 'ActivityItem';

export default ActivityItem;