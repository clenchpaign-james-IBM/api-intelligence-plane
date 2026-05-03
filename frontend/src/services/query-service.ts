/**
 * Query Service - Natural Language Query API Client
 * 
 * Handles communication with the agentic query API endpoint,
 * including session management for multi-turn conversations.
 * 
 * Feature: 002-agentic-query
 * Task: T085
 */

import axios, { AxiosInstance } from 'axios';

// Session ID storage key
const SESSION_ID_KEY = 'agentic_query_session_id';

/**
 * Query request parameters
 */
export interface QueryRequest {
  query_text: string;
  session_id?: string;
  mode?: 'auto' | 'agentic' | 'fallback';
  options?: {
    max_iterations?: number;
    enable_synthesis?: boolean;
    enable_fallback?: boolean;
    timeout_ms?: number;
  };
}

/**
 * Query response structure
 */
export interface QueryResponse {
  query_id: string;
  session_id: string;
  query_text: string;
  execution_mode: 'agentic' | 'fallback' | 'hybrid';
  confidence: number;
  answer: string;
  results: {
    entity_type: string;
    entities: Record<string, any>;
    total_count: number;
    synthesis_summary: string;
  };
  agentic_metadata?: {
    coordinator_state: {
      iteration: number;
      max_iterations: number;
      is_complete: boolean;
      completion_reasoning: string;
      completed_steps: string[];
    };
    agent_decisions: Array<{
      agent_type: string;
      query: string;
      reasoning: string;
      confidence: number;
      selected_tools: string[];
      execution_time_ms: number;
      success: boolean;
    }>;
    tool_invocations: Array<{
      tool_name: string;
      parameters: Record<string, any>;
      result_count: number;
      execution_time_ms: number;
      success: boolean;
      cache_hit: boolean;
    }>;
    iterations: number;
    completed_steps: string[];
  };
  fallback_trigger?: {
    reason: string;
    reasoning: string;
    confidence_score?: number;
    tool_failure_rate?: number;
    execution_time_ms?: number;
    timestamp: string;
  };
  performance: {
    execution_time_ms: number;
    llm_calls: number;
    tool_calls: number;
    cache_hits: number;
  };
  metadata: {
    timestamp: string;
    version: string;
  };
}

/**
 * Query Service Class
 * 
 * Manages natural language queries with session persistence
 * for multi-turn conversations.
 */
export class QueryService {
  private client: AxiosInstance;
  private currentSessionId: string | null = null;

  constructor(baseURL: string = '/api/v1') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Load existing session ID from storage
    this.loadSessionId();
  }

  /**
   * Load session ID from localStorage
   */
  private loadSessionId(): void {
    try {
      const storedSessionId = localStorage.getItem(SESSION_ID_KEY);
      if (storedSessionId) {
        this.currentSessionId = storedSessionId;
        console.log('[QueryService] Loaded session ID:', storedSessionId);
      }
    } catch (error) {
      console.warn('[QueryService] Failed to load session ID:', error);
    }
  }

  /**
   * Save session ID to localStorage
   */
  private saveSessionId(sessionId: string): void {
    try {
      localStorage.setItem(SESSION_ID_KEY, sessionId);
      this.currentSessionId = sessionId;
      console.log('[QueryService] Saved session ID:', sessionId);
    } catch (error) {
      console.warn('[QueryService] Failed to save session ID:', error);
    }
  }

  /**
   * Get current session ID
   */
  public getSessionId(): string | null {
    return this.currentSessionId;
  }

  /**
   * Clear current session (start new conversation)
   */
  public clearSession(): void {
    try {
      localStorage.removeItem(SESSION_ID_KEY);
      this.currentSessionId = null;
      console.log('[QueryService] Cleared session');
    } catch (error) {
      console.warn('[QueryService] Failed to clear session:', error);
    }
  }

  /**
   * Execute a natural language query
   * 
   * Automatically maintains session ID for multi-turn conversations.
   * 
   * @param queryText - Natural language query
   * @param options - Optional query parameters
   * @returns Query response with results and metadata
   */
  public async executeQuery(
    queryText: string,
    options?: Partial<QueryRequest>
  ): Promise<QueryResponse> {
    const request: QueryRequest = {
      query_text: queryText,
      session_id: this.currentSessionId || undefined,
      ...options,
    };

    try {
      const response = await this.client.post<QueryResponse>('/query', request);
      
      // Save session ID from response for future queries
      if (response.data.session_id) {
        this.saveSessionId(response.data.session_id);
      }

      return response.data;
    } catch (error) {
      console.error('[QueryService] Query execution failed:', error);
      throw error;
    }
  }

  /**
   * Execute a query in a new session (ignore current session)
   * 
   * @param queryText - Natural language query
   * @param options - Optional query parameters
   * @returns Query response
   */
  public async executeNewQuery(
    queryText: string,
    options?: Partial<QueryRequest>
  ): Promise<QueryResponse> {
    // Temporarily clear session for this query
    const previousSessionId = this.currentSessionId;
    this.currentSessionId = null;

    try {
      const response = await this.executeQuery(queryText, options);
      return response;
    } finally {
      // Restore previous session if query failed
      if (previousSessionId && !this.currentSessionId) {
        this.currentSessionId = previousSessionId;
      }
    }
  }

  /**
   * Check if currently in a conversation session
   */
  public hasActiveSession(): boolean {
    return this.currentSessionId !== null;
  }
}

// Export singleton instance
export const queryService = new QueryService();

// Export default
export default queryService;

// Made with Bob
