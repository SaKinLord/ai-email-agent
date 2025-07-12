import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, Search, Filter
} from 'lucide-react';
import { useActivityStore } from '../../store/activityStore';
import { useDebounce, useExpensiveMemo } from '../../hooks/usePerformance';
import ActivityItem from './ActivityItem';

const ActivityFeed: React.FC = () => {
  const { activities, isConnected } = useActivityStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('list');

  // Debounced search to prevent excessive filtering
  const debouncedSearchTerm = useDebounce(
    useCallback((term: string) => setSearchTerm(term), []),
    300
  );

  // Optimized filtered activities with expensive computation memoization
  const filteredActivities = useExpensiveMemo(() => {
    if (activities.length === 0) return [];
    
    return activities.filter(activity => {
      const matchesSearch = searchTerm === '' || 
        activity.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        activity.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        activity.type.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesStatus = selectedStatus === 'all' || activity.status === selectedStatus;
      const matchesType = selectedType === 'all' || activity.type === selectedType;
      
      return matchesSearch && matchesStatus && matchesType;
    });
  }, [activities, searchTerm, selectedStatus, selectedType], 
  // Custom equality check to prevent unnecessary re-computations
  (newDeps, oldDeps) => {
    return newDeps.length === oldDeps.length && 
           newDeps.every((dep, i) => dep === oldDeps[i]);
  });


  const activityCounts = useMemo(() => {
    const counts = { all: activities.length, completed: 0, error: 0, in_progress: 0 };
    activities.forEach(activity => {
      if (activity.status in counts) {
        counts[activity.status as keyof typeof counts]++;
      }
    });
    return counts;
  }, [activities]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center md:justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Activity Feed
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Real-time view of your email agent's activities
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
          
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {filteredActivities.length} of {activities.length} activities
          </div>
        </div>
      </motion.div>

      {/* Statistics Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {[
          { label: 'Total', value: activityCounts.all, color: 'text-blue-600' },
          { label: 'Completed', value: activityCounts.completed, color: 'text-green-600' },
          { label: 'In Progress', value: activityCounts.in_progress, color: 'text-yellow-600' },
          { label: 'Errors', value: activityCounts.error, color: 'text-red-600' },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 + index * 0.1 }}
            className="card text-center"
          >
            <p className={`text-2xl font-bold ${stat.color}`}>
              {stat.value}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {stat.label}
            </p>
          </motion.div>
        ))}
      </motion.div>

      {/* Filters and Search */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card"
      >
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search activities..."
              onChange={(e) => debouncedSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="in_progress">In Progress</option>
              <option value="error">Error</option>
            </select>
          </div>

          {/* Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="all">All Types</option>
            <option value="email_processing">Email Processing</option>
            <option value="autonomous_task">Autonomous Task</option>
            <option value="ml_training">ML Training</option>
            <option value="classification">Classification</option>
            <option value="archive">Archive</option>
          </select>

          {/* View Mode Toggle */}
          <div className="flex border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-2 text-sm ${
                viewMode === 'list'
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
              }`}
            >
              List
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-2 text-sm ${
                viewMode === 'timeline'
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
              }`}
            >
              Timeline
            </button>
          </div>
        </div>
      </motion.div>

      {/* Activity List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card"
      >
        <AnimatePresence mode="wait">
          {filteredActivities.length > 0 ? (
            <motion.div
              key="activities"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {filteredActivities.map((activity, index) => (
                <ActivityItem
                  key={activity.id}
                  activity={activity}
                  index={index}
                />
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="text-center py-16"
            >
              <Activity className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">
                {activities.length === 0 
                  ? "No activities yet"
                  : "No activities match your filters"
                }
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                {activities.length === 0 
                  ? "Activities will appear here as your agent processes emails"
                  : "Try adjusting your search or filters"
                }
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default ActivityFeed;