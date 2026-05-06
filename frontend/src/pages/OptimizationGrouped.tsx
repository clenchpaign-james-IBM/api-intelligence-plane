import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Zap, TrendingUp, DollarSign } from 'lucide-react';
import Loading from '../components/common/Loading';
import Error from '../components/common/Error';
import { api } from '../services/api';
import type {
  Recommendation,
  RecommendationPriority,
  RecommendationStatus,
  RecommendationType
} from '../types';

/**
 * Optimization Page with Grouped Recommendations
 * 
 * Groups recommendations by API for better organization
 */
const OptimizationGrouped = () => {
  const [activeTab, setActiveTab] = useState<'recommendations' | 'rate-limiting'>('recommendations');
  const [selectedPriority] = useState<RecommendationPriority | 'all'>('all');
  const [selectedStatus] = useState<RecommendationStatus | 'all'>('all');
  const [selectedType] = useState<RecommendationType | 'all'>('all');
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null);

  // Fetch recommendations
  const { data, isLoading, error } = useQuery({
    queryKey: ['recommendations', selectedPriority, selectedStatus, selectedType],
    queryFn: () => {
      const params: any = {};
      if (selectedPriority !== 'all') params.priority = selectedPriority;
      if (selectedStatus !== 'all') params.status = selectedStatus;
      if (selectedType !== 'all') params.recommendation_type = selectedType;
      return api.recommendations.list(params);
    },
    refetchInterval: 60000,
  });

  // Group recommendations by API
  const groupedRecommendations = (data?.recommendations || []).reduce((acc: Record<string, Recommendation[]>, rec: Recommendation) => {
    const apiKey = rec.api_name || rec.api_id;
    if (!acc[apiKey]) acc[apiKey] = [];
    acc[apiKey].push(rec);
    return acc;
  }, {} as Record<string, Recommendation[]>);

  const recommendations = data?.recommendations || [];
  const pendingCount = recommendations.filter((r: Recommendation) => r.status === 'pending').length;
  const highPriorityCount = recommendations.filter((r: Recommendation) => r.priority === 'high' || r.priority === 'critical').length;
  const avgImprovement = recommendations.length > 0
    ? recommendations.reduce((sum: number, r: Recommendation) => sum + r.estimated_impact.improvement_percentage, 0) / recommendations.length
    : 0;
  const totalSavings = recommendations.reduce((sum: number, r: Recommendation) => sum + (r.cost_savings || 0), 0);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-800 border border-red-300';
      case 'high': return 'bg-orange-100 text-orange-800 border border-orange-300';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border border-yellow-300';
      case 'low': return 'bg-green-100 text-green-800 border border-green-300';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'implemented': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'expired': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeDisplayName = (type: string) => {
    return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <Loading message="Loading optimization recommendations..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Error message="Failed to load recommendations" />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">API Performance Optimization</h1>
            <p className="mt-2 text-sm text-gray-600">
              AI-powered performance recommendations grouped by API - caching, query optimization, resource allocation, and more
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('recommendations')}
              className={`${
                activeTab === 'recommendations'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2`}
            >
              <Zap className="w-5 h-5" />
              Recommendations (Grouped by API)
            </button>
          </nav>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
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
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Potential Savings</p>
              <p className="text-2xl font-bold text-blue-600">${totalSavings.toFixed(0)}/mo</p>
            </div>
            <DollarSign className="w-8 h-8 text-blue-500" />
          </div>
        </div>
      </div>

      {/* Grouped Recommendations */}
      {recommendations.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <Zap className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">
            No recommendations available.
            Recommendations are generated automatically every 30 minutes
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {(Object.entries(groupedRecommendations) as [string, Recommendation[]][]).map(([apiKey, apiRecs]) => (
            <div key={apiKey} className="bg-white rounded-lg shadow-lg p-6">
              {/* API Group Header - Highlighted */}
              <div className="flex items-center gap-3 mb-6 pb-4 border-b-2 border-blue-300">
                <div className="flex items-center gap-3 px-5 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-lg">
                  <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                  <h2 className="text-xl font-bold text-white">
                    {apiRecs[0].api_name || `API ${apiRecs[0].api_id.substring(0, 8)}...`}
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">
                    {apiRecs.length} recommendation{apiRecs.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              {/* Recommendations Grid for this API */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {apiRecs.map((recommendation: Recommendation) => (
                  <div
                    key={recommendation.id}
                    className="bg-gradient-to-br from-gray-50 to-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => setSelectedRecommendation(recommendation)}
                  >
                    {/* Title */}
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">
                      {recommendation.title}
                    </h3>
                    <p className="text-sm text-gray-600 line-clamp-2 mb-4">
                      {recommendation.description}
                    </p>

                    {/* Badges */}
                    <div className="flex items-center gap-2 mb-4 flex-wrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(recommendation.priority)}`}>
                        {recommendation.priority.toUpperCase()}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(recommendation.status)}`}>
                        {recommendation.status.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        {getTypeDisplayName(recommendation.recommendation_type)}
                      </span>
                    </div>

                    {/* Impact */}
                    <div className="bg-green-50 rounded-lg p-3 mb-3 border border-green-200">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">Expected Impact</span>
                        <span className="text-lg font-bold text-green-600">
                          +{recommendation.estimated_impact.improvement_percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {/* Effort & Savings */}
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-600">Effort:</span>
                        <span className="font-medium text-gray-900 capitalize">
                          {recommendation.implementation_effort}
                        </span>
                      </div>
                      {recommendation.cost_savings && (
                        <div className="flex items-center gap-1 text-blue-600 font-medium">
                          <DollarSign className="w-4 h-4" />
                          {recommendation.cost_savings.toFixed(0)}/mo
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail Modal */}
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
              {/* Prominent API Badge in Modal */}
              <div className="inline-flex items-center gap-3 px-5 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl shadow-lg mb-4">
                <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                <span className="text-xl font-bold text-white">
                  {selectedRecommendation.api_name || `API ${selectedRecommendation.api_id.substring(0, 8)}...`}
                </span>
              </div>
              
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                {selectedRecommendation.title}
              </h2>
              <p className="text-gray-600 mb-4">{selectedRecommendation.description}</p>

              {/* Rest of modal content... */}
              <button
                onClick={() => setSelectedRecommendation(null)}
                className="mt-6 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OptimizationGrouped;

// Made with Bob
