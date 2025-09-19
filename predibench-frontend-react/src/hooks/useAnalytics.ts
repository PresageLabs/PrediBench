import { useCallback } from 'react';
import { logEvent, setUserProperties, setUserId } from 'firebase/analytics';
import { analytics } from '../firebase';

export interface AnalyticsEvent {
  name: string;
  parameters?: Record<string, any>;
}

export const useAnalytics = () => {
  const trackEvent = useCallback((eventName: string, parameters?: Record<string, any>) => {
    if (analytics) {
      logEvent(analytics, eventName, parameters);
    }
  }, []);

  const trackPageView = useCallback((pageName: string, pageTitle?: string) => {
    if (analytics) {
      logEvent(analytics, 'page_view', {
        page_title: pageTitle || pageName,
        page_location: window.location.href,
        page_path: window.location.pathname,
      });
    }
  }, []);

  const trackUserAction = useCallback((action: string, category?: string, label?: string) => {
    if (analytics) {
      logEvent(analytics, action, {
        event_category: category,
        event_label: label,
      });
    }
  }, []);

  const setUserProperty = useCallback((properties: Record<string, any>) => {
    if (analytics) {
      setUserProperties(analytics, properties);
    }
  }, []);

  const setAnalyticsUserId = useCallback((userId: string) => {
    if (analytics) {
      setUserId(analytics, userId);
    }
  }, []);

  const trackError = useCallback((error: Error, errorInfo?: Record<string, any>) => {
    if (analytics) {
      logEvent(analytics, 'exception', {
        description: error.message,
        fatal: false,
        ...errorInfo,
      });
    }
  }, []);

  const trackTiming = useCallback((name: string, value: number, category?: string) => {
    if (analytics) {
      logEvent(analytics, 'timing_complete', {
        name,
        value,
        event_category: category,
      });
    }
  }, []);

  const trackSearch = useCallback((searchTerm: string, category?: string) => {
    if (analytics) {
      logEvent(analytics, 'search', {
        search_term: searchTerm,
        search_category: category,
      });
    }
  }, []);

  return {
    trackEvent,
    trackPageView,
    trackUserAction,
    setUserProperty,
    setAnalyticsUserId,
    trackError,
    trackTiming,
    trackSearch,
  };
};