import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mail, Search, Filter, Star, 
  MoreHorizontal, Calendar, User, Tag, MessageSquare, 
  AlertTriangle, Clock, CheckCircle,
  ExternalLink, RefreshCw
} from 'lucide-react';
import { useEmailStore, Email } from '../../store/emailStore';
import { useFeedbackStore } from '../../store/feedbackStore';
import LoadingSpinner from '../common/LoadingSpinner';
import { FeedbackModal } from '../common/FeedbackModal';
import { toast } from '../../store/toastStore';
import { apiService } from '../../services/api';

// Remove ExtendedEmail interface - use the properly typed Email interface from store

const EmailList: React.FC = () => {
  const { emails, setEmails, setLoading, setError, loading, error } = useEmailStore();
  const { markFeedbackSubmitted, isFeedbackSubmitted } = useFeedbackStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPriority, setSelectedPriority] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [feedbackModalEmail, setFeedbackModalEmail] = useState<Email | null>(null);

  // Load emails from API
  const loadEmails = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setError(null);
      
      const response = await apiService.getEmails({
        limit: 50,
        ...(selectedPriority !== 'all' && { priority: selectedPriority })
      });
      
      // Backend now guarantees proper Email objects, no transformation needed
      setEmails(response.emails as any);
    } catch (err: any) {
      console.error('Failed to load emails:', err);
      setError(err.message || 'Failed to load emails');
      toast.error('Failed to load emails', err.message || 'Please try again');
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [selectedPriority, setEmails, setLoading, setError]);

  // Load emails on component mount and when priority filter changes
  useEffect(() => {
    loadEmails();
  }, [selectedPriority, loadEmails]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadEmails(false);
    setRefreshing(false);
    toast.success('Emails refreshed', 'Email list has been updated');
  };

  const filteredEmails = useMemo(() => {
    return emails.filter(email => {
      const matchesSearch = searchTerm === '' || 
        email.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
        email.sender.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (email.purpose && email.purpose.toLowerCase().includes(searchTerm.toLowerCase()));
      
      const matchesPriority = selectedPriority === 'all' || email.priority === selectedPriority;
      const matchesStatus = selectedStatus === 'all' || 
        (selectedStatus === 'unread' && !email.isRead) ||
        (selectedStatus === 'starred' && email.isStarred) ||
        (selectedStatus === 'archived' && email.isArchived);
      
      return matchesSearch && matchesPriority && matchesStatus;
    });
  }, [emails, searchTerm, selectedPriority, selectedStatus]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-300';
      case 'HIGH':
        return 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-300';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300';
      case 'LOW':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-300';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
        return <AlertTriangle className="h-4 w-4" />;
      case 'HIGH':
        return <Clock className="h-4 w-4" />;
      default:
        return <CheckCircle className="h-4 w-4" />;
    }
  };

  const getPurposeColor = (purpose: string | undefined) => {
    if (!purpose) {
      return 'bg-gray-100 text-gray-700 border border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600';
    }
    
    const lowerPurpose = purpose.toLowerCase();
    
    // Alert/Security purposes
    if (lowerPurpose.includes('alert') || lowerPurpose.includes('security') || lowerPurpose.includes('warning')) {
      return 'bg-red-100 text-red-800 border border-red-200 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800';
    }
    
    // Promotional/Marketing purposes
    if (lowerPurpose.includes('promotion') || lowerPurpose.includes('marketing') || lowerPurpose.includes('advertisement')) {
      return 'bg-purple-100 text-purple-800 border border-purple-200 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-800';
    }
    
    // Transactional/Financial purposes
    if (lowerPurpose.includes('transactional') || lowerPurpose.includes('transaction') || lowerPurpose.includes('payment') || lowerPurpose.includes('invoice') || lowerPurpose.includes('receipt')) {
      return 'bg-green-100 text-green-800 border border-green-200 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800';
    }
    
    // Social/Personal purposes
    if (lowerPurpose.includes('social') || lowerPurpose.includes('personal') || lowerPurpose.includes('family') || lowerPurpose.includes('friend')) {
      return 'bg-blue-100 text-blue-800 border border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800';
    }
    
    // Newsletter/Informational purposes
    if (lowerPurpose.includes('newsletter') || lowerPurpose.includes('digest') || lowerPurpose.includes('news') || lowerPurpose.includes('update')) {
      return 'bg-indigo-100 text-indigo-800 border border-indigo-200 dark:bg-indigo-900/20 dark:text-indigo-300 dark:border-indigo-800';
    }
    
    // Work/Business purposes
    if (lowerPurpose.includes('work') || lowerPurpose.includes('business') || lowerPurpose.includes('meeting') || lowerPurpose.includes('project')) {
      return 'bg-amber-100 text-amber-800 border border-amber-200 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800';
    }
    
    // Support/Service purposes
    if (lowerPurpose.includes('support') || lowerPurpose.includes('service') || lowerPurpose.includes('help')) {
      return 'bg-teal-100 text-teal-800 border border-teal-200 dark:bg-teal-900/20 dark:text-teal-300 dark:border-teal-800';
    }
    
    // Default for any other purpose
    return 'bg-slate-100 text-slate-800 border border-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600';
  };

  const handleFeedback = async (correctedPriority: string, correctedIntent: string) => {
    if (!feedbackModalEmail) return;
    
    try {
      // Submit feedback to API
      await apiService.submitEmailFeedback(feedbackModalEmail.id, {
        corrected_priority: correctedPriority,
        corrected_intent: correctedIntent
      });

      // Mark feedback as submitted in the persistent feedback store
      markFeedbackSubmitted(feedbackModalEmail.id, correctedPriority, correctedIntent);
      
      toast.success(
        'Feedback submitted', 
        'Thank you! This helps improve our AI classification.'
      );
      
      setFeedbackModalEmail(null);
    } catch (err: any) {
      console.error('Failed to submit feedback:', err);
      toast.error('Failed to submit feedback', err.message || 'Please try again');
    }
  };

  const openFeedbackModal = (email: Email) => {
    setFeedbackModalEmail(email);
  };

  const EmailCard = ({ email, index }: { email: Email; index: number }) => (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ delay: index * 0.05 }}
      className={`card hover:shadow-md transition-all duration-200 cursor-pointer ${
        !email.isRead ? 'border-l-4 border-l-blue-500' : ''
      }`}
      onClick={() => setSelectedEmail(email)}
    >
      <div className="flex items-start space-x-4">
        {/* Priority Indicator */}
        <div className={`flex-shrink-0 p-2 rounded-lg ${getPriorityColor(email.priority)}`}>
          {getPriorityIcon(email.priority)}
        </div>

        {/* Email Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className={`text-sm font-medium truncate ${
                  !email.isRead ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-300'
                }`}>
                  {email.subject}
                </h3>
                {email.isStarred && <Star className="h-4 w-4 text-yellow-400 fill-current" />}
              </div>
              
              <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
                <User className="h-3 w-3" />
                <span>{email.sender}</span>
                <Calendar className="h-3 w-3 ml-2" />
                <span>{new Date(email.received_date).toLocaleDateString()}</span>
              </div>

              <div className="flex items-center space-x-2 mb-2">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPriorityColor(email.priority)}`}>
                  {email.priority}
                </span>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPurposeColor(email.purpose)}`}>
                  {email.purpose || 'Unknown'}
                </span>
                {email.confidence && email.confidence > 0 && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {(email.confidence * 100).toFixed(0)}% confidence
                  </span>
                )}
              </div>

              {email.summary && (
                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                  {email.summary}
                </p>
              )}

              {/* Labels */}
              {email.labels.length > 0 && (
                <div className="flex items-center space-x-1 mt-2">
                  <Tag className="h-3 w-3 text-gray-400" />
                  {email.labels.map(label => (
                    <span key={label} className="px-2 py-1 text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded">
                      {label}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex-shrink-0 flex items-center space-x-2">
              {!isFeedbackSubmitted(email.id) && (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    openFeedbackModal(email);
                  }}
                  className="px-2 py-1 text-xs text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors"
                  title="Provide feedback to improve classification"
                >
                  <MessageSquare className="h-3 w-3 inline mr-1" />
                  Feedback
                </motion.button>
              )}
              
              <button className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <LoadingSpinner size="lg" />
        <p className="text-gray-500 dark:text-gray-400">Loading emails...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertTriangle className="h-16 w-16 text-red-400" />
        <div className="text-center">
          <p className="text-red-600 dark:text-red-400 text-lg font-medium">
            Failed to load emails
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            {error}
          </p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => loadEmails()}
            className="mt-4 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Try Again
          </motion.button>
        </div>
      </div>
    );
  }

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
            Emails
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Manage and review your processed emails
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-300 text-white rounded-lg text-sm font-medium transition-colors flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
          </motion.button>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card"
      >
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search emails..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Priority Filter */}
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="unread">Unread</option>
            <option value="starred">Starred</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </motion.div>

      {/* Email List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="space-y-4"
      >
        <AnimatePresence mode="wait">
          {filteredEmails.length > 0 ? (
            <motion.div
              key="emails"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {filteredEmails.map((email, index) => (
                <EmailCard key={email.id} email={email} index={index} />
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="card text-center py-16"
            >
              <Mail className="h-16 w-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400 text-lg font-medium">
                {emails.length === 0 
                  ? "No emails processed yet"
                  : "No emails match your filters"
                }
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
                {emails.length === 0 
                  ? "Emails will appear here after processing"
                  : "Try adjusting your search or filters"
                }
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Email Detail Modal */}
      <AnimatePresence>
        {selectedEmail && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedEmail(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                      {selectedEmail.subject}
                    </h2>
                    <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600 dark:text-gray-400">
                      <span>From: {selectedEmail.sender}</span>
                      <span>{new Date(selectedEmail.received_date).toLocaleString()}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedEmail(null)}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <ExternalLink className="h-5 w-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <span className={`px-3 py-1 text-sm font-medium rounded-full ${getPriorityColor(selectedEmail.priority)}`}>
                      {selectedEmail.priority}
                    </span>
                    <span className={`px-3 py-1 text-sm font-medium rounded-full ${getPurposeColor(selectedEmail.purpose)}`}>
                      {selectedEmail.purpose || 'Unknown'}
                    </span>
                  </div>

                  {selectedEmail.summary && (
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <h3 className="font-medium text-gray-900 dark:text-white mb-2">AI Summary</h3>
                      <p className="text-gray-600 dark:text-gray-400">{selectedEmail.summary}</p>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Classification confidence: {selectedEmail.confidence && selectedEmail.confidence > 0 ? (selectedEmail.confidence * 100).toFixed(0) : 0}%
                    </div>
                    
                    {!isFeedbackSubmitted(selectedEmail.id) ? (
                      <div className="flex items-center space-x-3">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          Was this classification correct?
                        </span>
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => openFeedbackModal(selectedEmail)}
                          className="px-3 py-2 text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors"
                        >
                          <MessageSquare className="h-4 w-4 inline mr-1" />
                          Provide Feedback
                        </motion.button>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm text-green-600 dark:text-green-400">
                          Feedback submitted
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={feedbackModalEmail !== null}
        onClose={() => setFeedbackModalEmail(null)}
        onSubmit={handleFeedback}
        emailSubject={feedbackModalEmail?.subject || ''}
        currentPriority={feedbackModalEmail?.priority || ''}
        currentIntent={feedbackModalEmail?.purpose || ''}
      />
    </div>
  );
};

export default EmailList;