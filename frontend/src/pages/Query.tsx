/**
 * Query Page
 * 
 * Natural language query interface for API intelligence.
 * Provides a chat-like interface for asking questions about APIs.
 */

import React, { useEffect, useRef } from 'react';
import { QueryHistory } from '../components/query/QueryHistory';
import { QueryInput } from '../components/query/QueryInput';
import { useQuerySession } from '../hooks/useQuerySession';
import Loading from '../components/common/Loading';
import { useNotification } from '../contexts/NotificationContext';

export const Query: React.FC = () => {
  const { showConfirm } = useNotification();
  const {
    sessionId,
    queries,
    isLoading,
    error,
    executeQuery,
    loadSessionHistory,
    clearSession,
    createNewSession,
  } = useQuerySession();

  const historyEndRef = useRef<HTMLDivElement>(null);

  // Load history on mount - only if session has queries
  useEffect(() => {
    console.log('[Query Page] Mount effect - sessionId:', sessionId, 'queries.length:', queries.length);
    if (sessionId && queries.length === 0) {
      // Only load if we don't have queries yet
      loadSessionHistory().catch(() => {
        // Ignore errors on initial load (session might not exist yet)
        console.log('[Query Page] No existing session history');
      });
    }
  }, [sessionId]);

  // Auto-scroll to bottom when new queries arrive
  useEffect(() => {
    console.log('[Query Page] Queries updated, count:', queries.length);
    if (queries.length > 0) {
      console.log('[Query Page] Latest query:', queries[queries.length - 1]);
    }
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [queries]);

  const handleSubmit = async (query: string) => {
    console.log('[Query Page] handleSubmit called with:', query);
    if (!query.trim()) return;
    console.log('[Query Page] Executing query...');
    await executeQuery(query);
    console.log('[Query Page] Query execution complete');
  };

  const handleFollowUpClick = async (query: string) => {
    console.log('[Query Page] Follow-up clicked:', query);
    await handleSubmit(query);
  };

  const handleClearSession = () => {
    showConfirm(
      'Clear History',
      'Are you sure you want to clear the conversation history?',
      () => {
        clearSession();
      }
    );
  };

  const handleNewSession = async () => {
    if (queries.length > 0) {
      showConfirm(
        'New Conversation',
        'Start a new conversation? Current history will be saved but you will start fresh.',
        async () => {
          await createNewSession();
        }
      );
    } else {
      await createNewSession();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Natural Language Query
            </h1>
            <p className="text-sm text-gray-600 mt-2">
              Ask questions about your APIs in plain English
            </p>
          </div>
          <div className="flex items-center gap-3">
            {sessionId && (
              <div className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                Session: {sessionId.slice(0, 8)}...
              </div>
            )}
            <button
              onClick={handleNewSession}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              New Session
            </button>
            {queries.length > 0 && (
              <button
                onClick={handleClearSession}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Clear History
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto relative">
        {error && (
          <div className="flex justify-center items-center p-8">
            <div className="max-w-md w-full bg-red-50 border border-red-200 rounded-lg p-6 text-center">
              <div className="flex justify-center mb-4">
                <svg className="w-12 h-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-red-900 mb-2">Connection Error</h3>
              <p className="text-sm text-red-700 mb-4">
                Unable to connect to the backend server. Please make sure the server is running.
              </p>
              <div className="bg-white rounded p-3 mb-4">
                <p className="text-xs text-gray-600 font-mono">{error}</p>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
              >
                Retry Connection
              </button>
            </div>
          </div>
        )}

        <QueryHistory
          queries={queries}
          onFollowUpClick={handleFollowUpClick}
        />

        {isLoading && (
          <div className="flex justify-center p-4">
            <div className="flex items-center gap-2 text-gray-600">
              <Loading size="sm" />
              <span className="text-sm">Processing your query...</span>
            </div>
          </div>
        )}

        {/* Help Section - shown when no queries */}
        {queries.length === 0 && !isLoading && (
          <div className="flex justify-center p-4">
            <div className="w-full max-w-2xl">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-blue-900 mb-2">
                  💡 Tips for better results:
                </h3>
                <ul className="text-xs text-blue-800 space-y-1">
                  <li>• Be specific about what you want to know</li>
                  <li>• Use natural language - no need for technical syntax</li>
                  <li>• Ask follow-up questions to dive deeper</li>
                  <li>• Try asking about health, performance, security, or predictions</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        <div ref={historyEndRef} />
      </div>

      {/* Input Area */}
      <QueryInput
        onSubmit={handleSubmit}
        isLoading={isLoading}
        placeholder="Ask a question about your APIs..."
      />

    </div>
  );
};

// Made with Bob
