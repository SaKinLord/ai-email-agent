import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { MessageCircle, Sparkles, Mail, Brain, Calendar, Filter } from 'lucide-react';
import ChatInterface from './ChatInterface';
import { useAgentStore } from '../../store/agentStore';
import { useEmailStore } from '../../store/emailStore';

const Chat: React.FC = () => {
  const { setShowChat } = useAgentStore();
  const { dashboardData } = useEmailStore();

  // Ensure chat is shown when this component mounts
  useEffect(() => {
    setShowChat(true);
    
    // Clean up: hide chat when component unmounts (if user navigates away)
    return () => {
      // Don't hide chat on unmount to maintain state
    };
  }, [setShowChat]);

  const quickStartActions = [
    {
      icon: Mail,
      title: "Email Summary",
      description: "Get a quick overview of your important emails",
      prompt: "Summarize my important emails from today",
      color: "bg-blue-500"
    },
    {
      icon: Filter,
      title: "Priority Check",
      description: "Find urgent messages that need attention",
      prompt: "Show me any urgent messages that need my attention",
      color: "bg-red-500"
    },
    {
      icon: Brain,
      title: "Email Insights",
      description: "Discover patterns and trends in your inbox",
      prompt: "What patterns do you see in my recent emails?",
      color: "bg-purple-500"
    },
    {
      icon: Calendar,
      title: "Schedule Helper",
      description: "Find meeting requests and scheduling emails",
      prompt: "Help me find any meeting requests or scheduling emails",
      color: "bg-green-500"
    }
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-3 mb-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <MessageCircle className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Chat with Maia
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Your intelligent email assistant for natural conversation
            </p>
          </div>
        </div>

        {/* Email context summary */}
        {dashboardData && (
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center space-x-2 mb-2">
              <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-800 dark:text-blue-300">
                Current Email Context
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="text-center">
                <div className="font-semibold text-blue-900 dark:text-blue-100">
                  {dashboardData.total_emails || 0}
                </div>
                <div className="text-blue-600 dark:text-blue-400">Total Emails</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-blue-900 dark:text-blue-100">
                  {dashboardData.unread_count || 0}
                </div>
                <div className="text-blue-600 dark:text-blue-400">Unread</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-blue-900 dark:text-blue-100">
                  {(dashboardData.priority_counts?.HIGH || 0) + (dashboardData.priority_counts?.CRITICAL || 0)}
                </div>
                <div className="text-blue-600 dark:text-blue-400">High Priority</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-blue-900 dark:text-blue-100">
                  {dashboardData.autonomous_actions_today || 0}
                </div>
                <div className="text-blue-600 dark:text-blue-400">Recent Actions</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex gap-6">
        {/* Quick Actions Sidebar */}
        <div className="w-80 flex-shrink-0">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Sparkles className="h-4 w-4 mr-2 text-blue-500" />
              Quick Actions
            </h3>
            
            <div className="space-y-3">
              {quickStartActions.map((action, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => {
                    // This will trigger the chat interface to send the prompt
                    const event = new CustomEvent('sendChatMessage', { 
                      detail: action.prompt 
                    });
                    window.dispatchEvent(event);
                  }}
                  className="w-full p-3 text-left rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-md transition-all group"
                >
                  <div className="flex items-start space-x-3">
                    <div className={`p-2 rounded-lg ${action.color} text-white group-hover:scale-110 transition-transform`}>
                      <action.icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                        {action.title}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {action.description}
                      </p>
                    </div>
                  </div>
                </motion.button>
              ))}
            </div>

            {/* Chat Tips */}
            <div className="mt-6 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <h4 className="font-medium text-gray-900 dark:text-white mb-2 text-sm">
                💡 Chat Tips
              </h4>
              <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                <li>• Ask questions in natural language</li>
                <li>• Request email summaries by date or sender</li>
                <li>• Get help organizing your inbox</li>
                <li>• Find specific emails by description</li>
                <li>• Ask for email management suggestions</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 min-w-0">
          <ChatInterface 
            position="inline"
            className="h-full bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700"
          />
        </div>
      </div>
    </div>
  );
};

export default Chat;