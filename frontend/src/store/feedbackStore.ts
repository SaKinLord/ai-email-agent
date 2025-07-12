import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FeedbackSubmission {
  emailId: string;
  submittedAt: string;
  correctedPriority: string;
  correctedIntent: string;
}

interface FeedbackState {
  submittedFeedback: Record<string, FeedbackSubmission>;
  
  // Actions
  markFeedbackSubmitted: (emailId: string, correctedPriority: string, correctedIntent: string) => void;
  isFeedbackSubmitted: (emailId: string) => boolean;
  getFeedbackSubmission: (emailId: string) => FeedbackSubmission | null;
  clearFeedbackHistory: () => void;
  getFeedbackCount: () => number;
  getRecentFeedback: (limit?: number) => FeedbackSubmission[];
}

export const useFeedbackStore = create<FeedbackState>()(
  persist(
    (set, get) => ({
      submittedFeedback: {},
      
      markFeedbackSubmitted: (emailId: string, correctedPriority: string, correctedIntent: string) => {
        set((state) => ({
          submittedFeedback: {
            ...state.submittedFeedback,
            [emailId]: {
              emailId,
              submittedAt: new Date().toISOString(),
              correctedPriority,
              correctedIntent,
            },
          },
        }));
      },
      
      isFeedbackSubmitted: (emailId: string) => {
        return emailId in get().submittedFeedback;
      },
      
      getFeedbackSubmission: (emailId: string) => {
        return get().submittedFeedback[emailId] || null;
      },
      
      clearFeedbackHistory: () => {
        set({ submittedFeedback: {} });
      },
      
      getFeedbackCount: () => {
        return Object.keys(get().submittedFeedback).length;
      },
      
      getRecentFeedback: (limit = 10) => {
        const feedback = Object.values(get().submittedFeedback);
        return feedback
          .sort((a, b) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime())
          .slice(0, limit);
      },
    }),
    {
      name: 'maia-feedback-store', // unique name for localStorage
      // Only persist the submitted feedback, not the functions
      partialize: (state) => ({ submittedFeedback: state.submittedFeedback }),
    }
  )
);