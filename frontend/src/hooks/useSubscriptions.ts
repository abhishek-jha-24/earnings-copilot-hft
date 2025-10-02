import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Subscription } from '../types';

export const useSubscriptions = () => {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSubscriptions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getSubscriptions();
      setSubscriptions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch subscriptions');
    } finally {
      setLoading(false);
    }
  };

  const addSubscription = async (ticker: string) => {
    try {
      setError(null);
      await apiService.createSubscription({ 
        ticker, 
        channels: ['ws'] // Default to websocket notifications
      });
      await fetchSubscriptions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add subscription');
    }
  };

  const removeSubscription = async (ticker: string) => {
    try {
      setError(null);
      await apiService.deleteSubscription(ticker);
      await fetchSubscriptions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove subscription');
    }
  };

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  return {
    subscriptions,
    loading,
    error,
    addSubscription,
    removeSubscription,
    refreshSubscriptions: fetchSubscriptions,
  };
};
