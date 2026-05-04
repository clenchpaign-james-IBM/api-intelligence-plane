import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Zap, TrendingUp, Filter, RefreshCw } from 'lucide-react';
import Loading from '../components/common/Loading';
import Error from '../components/common/Error';
import GatewaySelector from '../components/common/GatewaySelector';
import { RecommendationCard } from '../components/optimization/RecommendationCard';
import { RecommendationDetail } from '../components/optimization/RecommendationDetail';
import { api } from '../services/api';
import type { OptimizationRecommendation } from '../types/optimization';
import type {
  RecommendationPriority,
  RecommendationStatus,
  RecommendationType
} from '../types';
import { useNotification } from '../contexts/NotificationContext';
import { useScan } from '../contexts/ScanContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Optimization Page
 *
 * Displays unified performance optimization recommendations including:
 * - Caching recommendations
 * - Compression recommendations
 * - Rate limiting recommendations
 * - Filtering by priority, status, and type
 * - Statistics and impact metrics
 * - Policy application to Gateway
 */
const Optimization = () => {
  const { showSuccess, showError, showWarning, showConfirm } = useNotification();
  const { startScan, updateProgress, completeScan, getScanStateForPage } = useScan();
  const { gatewayId } = useParams<{ gatewayId?: string }>();
  const [selectedGatewayId, setSelectedGatewayId] = useState<string | null>(gatewayId || null);
  const [selectedPriority, setSelectedPriority] = useState<RecommendationPriority | 'all'>('all');
  const [selectedStatus, setSelectedStatus] = useState<RecommendationStatus | 'all'>('all');
  const [selectedType, setSelectedType] = useState<RecommendationType | 'all'>('all');
  const [selectedRecommendation, setSelectedRecommendation] = useState<OptimizationRecommendation | null>(null);
  
  const queryClient = useQueryClient();

  // Get scan state from context
  const { isScanning, scanProgress } = getScanStateForPage('optimization', selectedGatewayId);

  // Handle gateway selection
  const handleGatewayChange = (newGatewayId: string | null) => {
    setSelectedGatewayId(newGatewayId);
  };

  // Fetch recommendations (filtered by gateway if selected)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['recommendations', selectedPriority, selectedStatus, selectedType, selectedGatewayId],
    queryFn: () => {
      const params: any = {};
      if (selectedPriority !== 'all') params.priority = selectedPriority;
      if (selectedStatus !== 'all') params.status = selectedStatus;
      if (selectedType !== 'all') params.recommendation_type = selectedType;
      if (selectedGatewayId) params.gateway_id = selectedGatewayId;
      return api.recommendations.list(params);
    },
    staleTime: 0, // Always fetch fresh data
    refetchInterval: 60000, // Refetch every minute
  });

  // Fetch statistics
  const { data: stats } = useQuery({
    queryKey: ['recommendation-stats'],
    queryFn: () => api.recommendations.stats(),
    staleTime: 0, // Always fetch fresh data
    refetchInterval: 60000,
  });

  // Fetch APIs for the selected gateway
  const { data: apisData } = useQuery({
    queryKey: ['apis', selectedGatewayId],
    queryFn: () => {
      if (!selectedGatewayId) return { items: [] };
      return api.apis.list({ gateway_id: selectedGatewayId, page_size: 1000 });
    },
    enabled: !!selectedGatewayId,
  });

  const apis = apisData?.items || [];

  // Handle manual scan - generate recommendations for all APIs in selected gateway
  const handleManualScan = async () => {
    if (!selectedGatewayId) {
      showError('No Gateway Selected', 'Please select a gateway to scan');
      return;
    }

    startScan('optimization', selectedGatewayId, apis.length);

    try {
      let successCount = 0;
      let failCount = 0;
      let totalRecommendations = 0;

      // Generate recommendations for each API in the selected gateway
      for (let i = 0; i < apis.length; i++) {
        const apiItem = apis[i];
        updateProgress('optimization', selectedGatewayId, i + 1);

        try {
          const response = await fetch(
            `${API_BASE_URL}/api/v1/gateways/${selectedGatewayId}/optimization/recommendations/generate?api_id=${apiItem.id}`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
            }
          );
          
          if (response.ok) {
            const data = await response.json();
            totalRecommendations += data.recommendations_generated || 0;
            successCount++;
          } else {
            failCount++;
          }
        } catch (error) {
          console.error(`Failed to generate recommendations for API ${apiItem.name}:`, error);
          failCount++;
        }
      }

      // Refresh data
      await queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      await queryClient.invalidateQueries({ queryKey: ['recommendation-stats'] });

      showSuccess(
        'Recommendation Generation Complete',
        `Total APIs: ${apis.length}\nSuccessful: ${successCount}\nFailed: ${failCount}\nRecommendations Generated: ${totalRecommendations}`,
        8000
      );
    } catch (error) {
      console.error('Recommendation generation failed:', error);
      showError('Generation Failed', 'Failed to complete recommendation generation. Please try again.');
    } finally {
      completeScan('optimization', selectedGatewayId);
    }
  };

  // Apply policy mutation (creates or updates policy in Gateway)
  const applyMutation = useMutation({
    mutationFn: ({ gatewayId, recommendationId }: { gatewayId: string; recommendationId: string }) =>
      api.recommendations.applyToGateway(gatewayId, recommendationId),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      if (data.requires_manual_configuration) {
        showWarning(
          'Manual Configuration Required',
          `${data.message}\n\nInstructions:\n${data.instructions?.join('\n') || 'See recommendation details'}`,
          10000
        );
      } else {
        showSuccess('Policy Applied', 'The policy has been created or updated in the Gateway.');
      }
    },
    onError: (error: any) => {
      showError('Apply Failed', error.message || 'Unknown error');
    },
  });

  // Remove policy mutation
  const removeMutation = useMutation({
    mutationFn: ({ gatewayId, recommendationId }: { gatewayId: string; recommendationId: string }) =>
      api.recommendations.removeFromGateway(gatewayId, recommendationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      showSuccess('Policy Removed', 'Policy removed from Gateway successfully');
    },
    onError: (error: any) => {
      showError('Remove Failed', error.message || 'Unknown error');
    },
  });

  // Validate recommendation mutation
  const validateMutation = useMutation({
    mutationFn: ({ gatewayId, recommendationId, validationWindowHours }: { gatewayId: string; recommendationId: string; validationWindowHours?: number }) =>
      api.recommendations.validate(gatewayId, recommendationId, validationWindowHours || 24),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      if (data.success) {
        showSuccess(
          'Validation Successful',
          `Expected: ${data.expected_improvement}%\nActual: ${data.actual_improvement}%\nImprovement: ${data.improvement_percentage}%\nConfidence: ${(data.confidence_score * 100).toFixed(1)}%`,
          8000
        );
      } else {
        showError('Validation Failed', data.message);
      }
    },
    onError: (error: any) => {
      showError('Validation Failed', error.message || 'Unknown error');
    },
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6">
        <Loading message="Loading optimization recommendations..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <Error message="Failed to load recommendations" />
      </div>
    );
  }

  const recommendations = data?.recommendations || [];
  const pendingCount = recommendations.filter((r: OptimizationRecommendation) => r.status === 'pending').length;
  const highPriorityCount = recommendations.filter((r: OptimizationRecommendation) =>
    r.priority === 'critical' || r.priority === 'high'
  ).length;
  const avgImprovement = stats?.avg_improvement || 0;

  // Group recommendations by API
  const groupedRecommendations: Record<string, OptimizationRecommendation[]> = recommendations.reduce((acc: Record<string, OptimizationRecommendation[]>, rec: OptimizationRecommendation) => {
    const apiKey = rec.api_name || rec.api_id;
    if (!acc[apiKey]) acc[apiKey] = [];
    acc[apiKey].push(rec);
    return acc;
  }, {} as Record<string, OptimizationRecommendation[]>);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Performance Optimization</h1>
            <p className="mt-2 text-sm text-gray-600">
              API-centric performance recommendations for caching, compression, and rate limiting
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleManualScan}
              disabled={isScanning || !selectedGatewayId}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
              title={!selectedGatewayId ? 'Select a gateway to scan' : 'Generate recommendations for all APIs in selected gateway'}
            >
              <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
              {isScanning ? `Scanning ${scanProgress?.current}/${scanProgress?.total}...` : 'Manual Scan'}
            </button>
          </div>
        </div>
      </div>
      {/* Gateway Selector */}
      <GatewaySelector
        selectedGatewayId={selectedGatewayId}
        onGatewayChange={handleGatewayChange}
        showAllOption={true}
      />


      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Pending Actions</p>
              <p className="text-2xl font-bold text-gray-900">{pendingCount}</p>
            </div>
            <Zap className="w-8 h-8 text-yellow-500" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">High Priority</p>
              <p className="text-2xl font-bold text-orange-600">{highPriorityCount}</p>
            </div>
            <TrendingUp className="w-8 h-8 text-orange-500" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Improvement</p>
              <p className="text-2xl font-bold text-green-600">{avgImprovement.toFixed(1)}%</p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-500" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <Filter className="w-5 h-5 text-gray-500" />
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Priority:</label>
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value as RecommendationPriority | 'all')}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Status:</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as RecommendationStatus | 'all')}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="implemented">Implemented</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Type:</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as RecommendationType | 'all')}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="caching">Caching</option>
              <option value="rate_limiting">Rate Limiting</option>
              <option value="compression">Compression</option>
            </select>
          </div>
        </div>
      </div>

      {/* Recommendations List - Grouped by API */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-4">Recommendations (Grouped by API)</h2>
        {recommendations.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <Zap className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No recommendations found</p>
            <p className="text-sm text-gray-500 mt-2">
              Recommendations are generated automatically every 30 minutes
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {Object.entries(groupedRecommendations).map(([apiKey, apiRecs]) => (
              <div key={apiKey} className="bg-white rounded-lg shadow-lg p-6">
                {/* API Group Header */}
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {apiRecs[0].api_name || `API ${apiRecs[0].api_id.substring(0, 8)}...`}
                  </h3>
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                    {apiRecs.length} recommendation{apiRecs.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Recommendations Grid for this API */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {apiRecs.map((recommendation: OptimizationRecommendation) => (
                    <RecommendationCard
                      key={recommendation.id}
                      recommendation={recommendation}
                      onClick={() => setSelectedRecommendation(recommendation)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Detailed View Modal */}
      {selectedRecommendation && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedRecommendation(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <RecommendationDetail
                recommendation={selectedRecommendation}
                onApply={(gatewayId, recommendationId) => {
                  applyMutation.mutate(
                    { gatewayId, recommendationId },
                    {
                      onSuccess: () => {
                        setSelectedRecommendation(null);
                      },
                    }
                  );
                }}
                onRemove={(gatewayId, recommendationId) => {
                  showConfirm(
                    'Remove Policy',
                    'Are you sure you want to remove this policy from the gateway?',
                    () => {
                      removeMutation.mutate({ gatewayId, recommendationId });
                      setSelectedRecommendation(null);
                    }
                  );
                }}
                onValidate={(gatewayId, recommendationId) => {
                  validateMutation.mutate({ gatewayId, recommendationId });
                }}
                onClose={() => setSelectedRecommendation(null)}
                isApplying={applyMutation.isPending}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Optimization;

// Made with Bob