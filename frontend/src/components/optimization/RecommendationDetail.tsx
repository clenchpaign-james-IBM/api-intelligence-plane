import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckCircle, XCircle, PlayCircle, Trash2, Clock } from 'lucide-react';
import { OptimizationRecommendation, OptimizationAction } from '../../types/optimization';

interface Props {
  recommendation: OptimizationRecommendation;
  onApply?: (gatewayId: string, recommendationId: string) => void;
  onRemove?: (gatewayId: string, recommendationId: string) => void;
  onValidate?: (gatewayId: string, recommendationId: string) => void;
  onClose?: () => void;
  isApplying?: boolean;
}

export const RecommendationDetail: React.FC<Props> = ({
  recommendation,
  onApply,
  onRemove,
  onValidate,
  onClose,
  isApplying = false
}) => {
  const { ai_context, remediation_actions } = recommendation;
  const [showActions, setShowActions] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100';
      case 'implemented':
        return 'text-green-600 bg-green-100';
      case 'rejected':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'apply_policy':
        return <PlayCircle className="w-4 h-4" />;
      case 'remove_policy':
        return <Trash2 className="w-4 h-4" />;
      case 'validate':
        return <CheckCircle className="w-4 h-4" />;
      case 'manual_configuration':
        return <Clock className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getActionStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'in_progress':
        return <Clock className="w-4 h-4 text-blue-600" />;
      default:
        return <Clock className="w-4 h-4 text-gray-600" />;
    }
  };

  return (
    <div className="recommendation-detail">
      {/* Existing recommendation details */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">{recommendation.title}</h2>
        <p className="text-gray-600 mb-4">{recommendation.description}</p>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <span className="font-medium">Priority:</span> {recommendation.priority}
          </div>
          <div>
            <span className="font-medium">Effort:</span> {recommendation.implementation_effort}
          </div>
          <div>
            <span className="font-medium">Expected Improvement:</span>{' '}
            {recommendation.estimated_impact.improvement_percentage.toFixed(1)}%
          </div>
          <div>
            <span className="font-medium">Status:</span> {recommendation.status}
          </div>
        </div>

        <div className="mb-4">
          <h3 className="font-semibold mb-2">Implementation Steps:</h3>
          <ol className="list-decimal list-inside space-y-1">
            {recommendation.implementation_steps.map((step, index) => (
              <li key={index} className="text-sm text-gray-700">
                {step}
              </li>
            ))}
          </ol>
        </div>
      </div>
      
      {/* NEW: AI Insights Section */}
      {ai_context && (
        <div className="ai-insights-section mt-6 border-t pt-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            <span className="mr-2">🤖</span>
            AI-Generated Insights
          </h3>
          
          {ai_context.implementation_guidance && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2">
                Implementation Guidance
              </h4>
              <div className="bg-green-50 p-4 rounded-lg border border-green-100 prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {ai_context.implementation_guidance}
                </ReactMarkdown>
              </div>
            </div>
          )}
          
          {ai_context.prioritization && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2">
                Prioritization Guidance
              </h4>
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-100 prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {ai_context.prioritization}
                </ReactMarkdown>
              </div>
            </div>
          )}
          
          {ai_context.generated_at && (
            <p className="text-xs text-gray-500 mt-2">
              Generated: {new Date(ai_context.generated_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-6 pt-6 border-t">
        <h3 className="text-lg font-semibold mb-4">Actions</h3>
        <div className="flex gap-3 flex-wrap">
          {recommendation.gateway_id && recommendation.status === 'pending' && onApply && (
            <button
              onClick={() => onApply(recommendation.gateway_id!, recommendation.id)}
              disabled={isApplying}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <PlayCircle className="w-4 h-4" />
              {isApplying ? 'Remediating...' : 'Review & Apply'}
            </button>
          )}

          {onClose && (
            <button
              onClick={onClose}
              disabled={isApplying}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              Close
            </button>
          )}
            
          {recommendation.gateway_id && recommendation.status === 'implemented' && onRemove && (
            <button
              onClick={() => onRemove(recommendation.gateway_id!, recommendation.id)}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Remove Policy
            </button>
          )}
          
          {recommendation.gateway_id && recommendation.status === 'implemented' && onValidate && (
            <button
              onClick={() => onValidate(recommendation.gateway_id!, recommendation.id)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Validate Impact
            </button>
          )}
        </div>
      </div>

      {/* Remediation Actions History */}
      {remediation_actions && remediation_actions.length > 0 && (
        <div className="mt-6 pt-6 border-t">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Action History</h3>
            <button
              onClick={() => setShowActions(!showActions)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {showActions ? 'Hide' : 'Show'} ({remediation_actions.length})
            </button>
          </div>
          
          {showActions && (
            <div className="space-y-3">
              {remediation_actions.map((action: OptimizationAction, index: number) => (
                <div
                  key={index}
                  className="p-4 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getActionIcon(action.type)}
                      <span className="font-medium text-gray-900">
                        {action.action}
                      </span>
                    </div>
                    {getActionStatusIcon(action.status)}
                  </div>
                  
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>
                      <span className="font-medium">Type:</span> {action.type}
                    </div>
                    <div>
                      <span className="font-medium">Status:</span>{' '}
                      <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(action.status)}`}>
                        {action.status}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">Performed:</span>{' '}
                      {new Date(action.performed_at).toLocaleString()}
                    </div>
                    {action.performed_by && (
                      <div>
                        <span className="font-medium">By:</span> {action.performed_by}
                      </div>
                    )}
                    {action.gateway_policy_id && (
                      <div>
                        <span className="font-medium">Policy ID:</span> {action.gateway_policy_id}
                      </div>
                    )}
                    {action.error_message && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700">
                        <span className="font-medium">Error:</span> {action.error_message}
                      </div>
                    )}
                    {action.metadata?.override_metadata && (
                      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded">
                        <div className="font-medium text-blue-900 mb-2 flex items-center gap-2">
                          <span>✏️</span>
                          Manual Overrides Applied
                        </div>
                        <div className="text-sm space-y-1">
                          {action.metadata.override_metadata.overridden_fields &&
                           action.metadata.override_metadata.overridden_fields.length > 0 && (
                            <div>
                              <span className="font-medium text-blue-800">Modified Fields:</span>
                              <ul className="ml-4 mt-1 space-y-1">
                                {action.metadata.override_metadata.overridden_fields.map((field: string, idx: number) => {
                                  const oldValue = action.metadata?.override_metadata?.original_values?.[field];
                                  const newValue = action.metadata?.override_metadata?.new_values?.[field];
                                  return (
                                    <li key={idx} className="text-blue-700">
                                      <span className="font-mono text-xs">{field}</span>
                                      {oldValue !== undefined && newValue !== undefined && (
                                        <span className="ml-2 text-gray-600">
                                          ({JSON.stringify(oldValue)} → {JSON.stringify(newValue)})
                                        </span>
                                      )}
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          )}
                          {action.metadata.override_metadata.manual_analysis_notes && (
                            <div className="mt-2">
                              <span className="font-medium text-blue-800">Analysis Notes:</span>
                              <p className="text-blue-700 mt-1 italic">
                                "{action.metadata.override_metadata.manual_analysis_notes}"
                              </p>
                            </div>
                          )}
                          {action.metadata.override_metadata.reviewed_by && (
                            <div className="mt-1 text-xs text-blue-600">
                              Reviewed by: {action.metadata.override_metadata.reviewed_by}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    {action.metadata && Object.keys(action.metadata).length > 0 && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-blue-600 hover:text-blue-700">
                          View Full Metadata
                        </summary>
                        <pre className="mt-2 p-2 bg-white border rounded text-xs overflow-x-auto">
                          {JSON.stringify(action.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}


      {/* Validation Results */}
      {recommendation.validation_results && (
        <div className="mt-6 pt-6 border-t">
          <h3 className="text-lg font-semibold mb-4">Validation Results</h3>
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Expected Improvement:</span>{' '}
                {recommendation.validation_results.expected_improvement}%
              </div>
              <div>
                <span className="font-medium">Actual Improvement:</span>{' '}
                {recommendation.validation_results.actual_improvement}%
              </div>
              <div>
                <span className="font-medium">Achievement:</span>{' '}
                {recommendation.validation_results.improvement_percentage}%
              </div>
              <div>
                <span className="font-medium">Confidence:</span>{' '}
                {(recommendation.validation_results.confidence_score * 100).toFixed(1)}%
              </div>
            </div>
            <div className="mt-3 text-sm">
              <span className="font-medium">Status:</span>{' '}
              <span className={recommendation.validation_results.success ? 'text-green-700' : 'text-red-700'}>
                {recommendation.validation_results.message}
              </span>
            </div>
            <div className="mt-2 text-xs text-gray-600">
              Validated: {new Date(recommendation.validation_results.validation_timestamp).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Made with Bob
