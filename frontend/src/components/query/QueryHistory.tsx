/**
 * Query History Component
 * 
 * Displays the conversation history for the current session,
 * allowing users to see previous queries and navigate through them.
 * 
 * Feature: 002-agentic-query
 * Task: T086
 */

import React, { useState, useEffect } from 'react';
import { queryService, QueryResponse } from '../../services/query-service';

interface QueryHistoryItem {
  query_text: string;
  timestamp: string;
  execution_mode: string;
  confidence: number;
  answer: string;
}

interface QueryHistoryProps {
  /**
   * Callback when a historical query is selected
   */
  onQuerySelect?: (query: string) => void;
  
  /**
   * Maximum number of queries to display
   */
  maxItems?: number;
  
  /**
   * Whether to show detailed information
   */
  showDetails?: boolean;
}

/**
 * QueryHistory Component
 * 
 * Displays a list of previous queries in the current session
 * with their results and metadata.
 */
export const QueryHistory: React.FC<QueryHistoryProps> = ({
  onQuerySelect,
  maxItems = 10,
  showDetails = false,
}) => {
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Load history from localStorage on mount
  useEffect(() => {
    loadHistory();
    
    // Update session ID
    const currentSessionId = queryService.getSessionId();
    setSessionId(currentSessionId);
  }, []);

  /**
   * Load query history from localStorage
   */
  const loadHistory = () => {
    try {
      const storedHistory = localStorage.getItem('query_history');
      if (storedHistory) {
        const parsed = JSON.parse(storedHistory);
        setHistory(parsed.slice(0, maxItems));
      }
    } catch (error) {
      console.error('[QueryHistory] Failed to load history:', error);
    }
  };

  /**
   * Add a query to history
   */
  const addToHistory = (response: QueryResponse) => {
    const item: QueryHistoryItem = {
      query_text: response.query_text,
      timestamp: response.metadata.timestamp,
      execution_mode: response.execution_mode,
      confidence: response.confidence,
      answer: response.answer,
    };

    const newHistory = [item, ...history].slice(0, maxItems);
    setHistory(newHistory);

    // Save to localStorage
    try {
      localStorage.setItem('query_history', JSON.stringify(newHistory));
    } catch (error) {
      console.error('[QueryHistory] Failed to save history:', error);
    }
  };

  /**
   * Clear all history
   */
  const clearHistory = () => {
    setHistory([]);
    try {
      localStorage.removeItem('query_history');
    } catch (error) {
      console.error('[QueryHistory] Failed to clear history:', error);
    }
  };

  /**
   * Handle query selection
   */
  const handleQueryClick = (query: string) => {
    if (onQuerySelect) {
      onQuerySelect(query);
    }
  };

  /**
   * Format timestamp for display
   */
  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      
      return date.toLocaleDateString();
    } catch {
      return timestamp;
    }
  };

  /**
   * Get confidence color
   */
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  /**
   * Get execution mode badge color
   */
  const getModeColor = (mode: string): string => {
    switch (mode) {
      case 'agentic':
        return 'bg-blue-100 text-blue-800';
      case 'fallback':
        return 'bg-gray-100 text-gray-800';
      case 'hybrid':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Note: addToHistory can be called via ref if needed
  // Example usage: const historyRef = useRef<{ addToHistory: (response: QueryResponse) => void }>(null);

  if (history.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>No query history yet</p>
        <p className="text-sm mt-2">Your conversation history will appear here</p>
      </div>
    );
  }

  return (
    <div className="query-history bg-white rounded-lg shadow">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-semibold">Query History</h3>
          {sessionId && (
            <span className="text-xs text-gray-500">
              Session: {sessionId.slice(0, 8)}...
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </button>
          <button
            onClick={clearHistory}
            className="text-sm text-red-600 hover:text-red-800"
          >
            Clear
          </button>
        </div>
      </div>

      {/* History List */}
      <div className="divide-y max-h-96 overflow-y-auto">
        {history.map((item, index) => (
          <div
            key={index}
            className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
            onClick={() => handleQueryClick(item.query_text)}
          >
            {/* Query Text */}
            <div className="flex items-start justify-between">
              <p className="font-medium text-gray-900 flex-1">
                {item.query_text}
              </p>
              <span className="text-xs text-gray-500 ml-2">
                {formatTimestamp(item.timestamp)}
              </span>
            </div>

            {/* Metadata */}
            {showDetails && (
              <div className="mt-2 flex items-center space-x-3 text-sm">
                {/* Execution Mode */}
                <span
                  className={`px-2 py-1 rounded text-xs font-medium ${getModeColor(
                    item.execution_mode
                  )}`}
                >
                  {item.execution_mode}
                </span>

                {/* Confidence */}
                <span className={`text-xs ${getConfidenceColor(item.confidence)}`}>
                  {(item.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
            )}

            {/* Answer Preview */}
            {isExpanded && (
              <div className="mt-2 text-sm text-gray-600">
                <p className="line-clamp-2">{item.answer}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      {history.length >= maxItems && (
        <div className="p-2 text-center text-xs text-gray-500 border-t">
          Showing last {maxItems} queries
        </div>
      )}
    </div>
  );
};

export default QueryHistory;

// Made with Bob
