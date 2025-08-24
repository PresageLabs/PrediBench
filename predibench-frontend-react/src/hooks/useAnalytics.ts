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

  return {
    trackEvent,
    trackPageView,
    trackUserAction,
    setUserProperty,
    setAnalyticsUserId,
  };
};