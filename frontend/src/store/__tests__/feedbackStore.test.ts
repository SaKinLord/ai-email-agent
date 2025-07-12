// Simple test to verify feedback store functionality
import { useFeedbackStore } from '../feedbackStore';

// Test the feedback store behavior
describe('FeedbackStore', () => {
  beforeEach(() => {
    // Clear feedback history before each test
    useFeedbackStore.getState().clearFeedbackHistory();
  });

  test('should mark feedback as submitted', () => {
    const store = useFeedbackStore.getState();
    
    // Initially, no feedback should be submitted
    expect(store.isFeedbackSubmitted('email1')).toBe(false);
    
    // Mark feedback as submitted
    store.markFeedbackSubmitted('email1', 'HIGH', 'action_request');
    
    // Now feedback should be marked as submitted
    expect(store.isFeedbackSubmitted('email1')).toBe(true);
    
    // Should be able to retrieve the feedback submission
    const submission = store.getFeedbackSubmission('email1');
    expect(submission).toMatchObject({
      emailId: 'email1',
      correctedPriority: 'HIGH',
      correctedIntent: 'action_request',
    });
    expect(submission?.submittedAt).toBeDefined();
  });

  test('should persist across store resets', () => {
    const store = useFeedbackStore.getState();
    
    // Mark feedback as submitted
    store.markFeedbackSubmitted('email2', 'MEDIUM', 'newsletter');
    expect(store.isFeedbackSubmitted('email2')).toBe(true);
    
    // Simulate store recreation (what happens on page refresh)
    const newStoreState = useFeedbackStore.getState();
    expect(newStoreState.isFeedbackSubmitted('email2')).toBe(true);
  });

  test('should provide feedback count and recent feedback', () => {
    const store = useFeedbackStore.getState();
    
    // Mark multiple feedback submissions
    store.markFeedbackSubmitted('email1', 'CRITICAL', 'action_request');
    store.markFeedbackSubmitted('email2', 'LOW', 'promotion');
    store.markFeedbackSubmitted('email3', 'HIGH', 'meeting_invite');
    
    // Check feedback count
    expect(store.getFeedbackCount()).toBe(3);
    
    // Check recent feedback
    const recentFeedback = store.getRecentFeedback(2);
    expect(recentFeedback).toHaveLength(2);
    expect(recentFeedback[0].emailId).toBe('email3'); // Most recent first
    expect(recentFeedback[0].correctedPriority).toBe('HIGH');
    expect(recentFeedback[0].correctedIntent).toBe('meeting_invite');
  });
});