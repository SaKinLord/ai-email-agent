import React, { memo } from 'react';
import DashboardHome from './DashboardHome';
import ActivityFeed from './ActivityFeed';
import EmailList from './EmailList';
import Settings from './Settings';
import Autonomous from './Autonomous';
import Chat from './Chat';

// Memoized components to prevent unnecessary re-renders
export const MemoizedDashboardHome = memo(DashboardHome);
export const MemoizedActivityFeed = memo(ActivityFeed);
export const MemoizedEmailList = memo(EmailList);
export const MemoizedSettings = memo(Settings);
export const MemoizedAutonomous = memo(Autonomous);
export const MemoizedChat = memo(Chat);