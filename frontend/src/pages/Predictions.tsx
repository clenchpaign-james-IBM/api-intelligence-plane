import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { AlertTriangle, Bot, TrendingUp, RefreshCw } from 'lucide-react';
import PredictionCard from '../components/predictions/PredictionCard';
import PredictionTimeline from '../components/predictions/PredictionTimeline';
import Loading from '../components/common/Loading';
import Error from '../components/common/Error';
import GatewaySelector from '../components/common/GatewaySelector';
import { api } from '../services/api';
import type { Prediction, PredictionSeverity, PredictionStatus } from '../types';
import { useNotification } from '../contexts/NotificationContext';
import { useScan } from '../contexts/ScanContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Predictions Page
 * 
 * Displays API failure predictions with:
 * - List of active predictions
 * - Filtering by severity and status
 * - Timeline visualization
 * - Detailed prediction cards
 */
const Predictions = () => {
  const { showSuccess, showError } = useNotification();
  const { startScan, updateProgress, completeScan, getScanStateForPage } = useScan();
  const { gatewayId } = useParams<{ gatewayId?: string }>();
  const [selectedGatewayId, setSelectedGatewayId] = useState<string | null>(gatewayId || null);
  const [selectedSeverity] = useState<PredictionSeverity | 'all'>('all');
  const [selectedStatus] = useState<PredictionStatus | 'all'>('all');
  const [selectedPrediction, setSelectedPrediction] = useState<Prediction | null>(null);
  const queryClient = useQueryClient();

  // Get scan state from context
  const { isScanning, scanProgress } = getScanStateForPage('predictions', selectedGatewayId);
  
  // Handle gateway selection
  const handleGatewayChange = (newGatewayId: string | null) => {
    setSelectedGatewayId(newGatewayId);
  };

  // Fetch predictions (filtered by gateway if selected)
  const { data, isLoading, error } = useQuery({
    queryKey: ['predictions', selectedSeverity, selectedStatus, selectedGatewayId],
    queryFn: () => {
      const params: any = {};
      if (selectedSeverity !== 'all') params.severity = selectedSeverity;
      if (selectedStatus !== 'all') params.status = selectedStatus;
      if (selectedGatewayId) params.gateway_id = selectedGatewayId;
      return api.predictions.list(params);
    },
    staleTime: 0, // Always fetch fresh data
    refetchInterval: 60000, // Refetch every minute
  });

  // Calculate derived values BEFORE early returns to avoid hooks order issues
  const predictions = data?.predictions || [];
  const activePredictions = predictions.filter((p: Prediction) => p.status === 'active');
  const criticalCount = predictions.filter((p: Prediction) => p.severity === 'critical').length;
  const aiEnhancedCount = useMemo(
    () =>
      predictions.filter(
        (p: Prediction) =>
          Boolean((p as Prediction & { metadata?: Record<string, unknown> }).metadata?.ai_enhanced)
      ).length,
    [predictions]
  );

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

  // Handle manual scan - generate predictions for all APIs in selected gateway
  const handleManualScan = async () => {
    if (!selectedGatewayId) {
      showError('No Gateway Selected', 'Please select a gateway to scan');
      return;
    }

    startScan('predictions', selectedGatewayId, apis.length);

    try {
      let successCount = 0;
      let failCount = 0;
      let totalPredictions = 0;

      // Generate predictions for each API in the selected gateway
      for (let i = 0; i < apis.length; i++) {
        const apiItem = apis[i];
        updateProgress('predictions', selectedGatewayId, i + 1);

        try {
          const response = await fetch(
            `${API_BASE_URL}/api/v1/gateways/${selectedGatewayId}/predictions/generate?api_id=${apiItem.id}`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
            }
          );
          
          if (response.ok) {
            const data = await response.json();
            totalPredictions += data.predictions_generated || 0;
            successCount++;
          } else {
            failCount++;
          }
        } catch (error) {
          console.error(`Failed to generate predictions for API ${apiItem.name}:`, error);
          failCount++;
        }
      }

      // Refresh data
      await queryClient.invalidateQueries({ queryKey: ['predictions'] });

      showSuccess(
        'Prediction Generation Complete',
        `Total APIs: ${apis.length}\nSuccessful: ${successCount}\nFailed: ${failCount}\nPredictions Generated: ${totalPredictions}`,
        8000
      );
    } catch (error) {
      console.error('Prediction generation failed:', error);
      showError('Generation Failed', 'Failed to complete prediction generation. Please try again.');
    } finally {
      completeScan('predictions', selectedGatewayId);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6">
        <Loading message="Loading predictions..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <Error message="Failed to load predictions" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">API Failure Predictions</h1>
            <p className="mt-2 text-sm text-gray-600">
              Scheduler-generated predictions of potential API failures 24-48 hours in advance
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleManualScan}
              disabled={isScanning || !selectedGatewayId}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
              title={!selectedGatewayId ? 'Select a gateway to scan' : 'Generate predictions for all APIs in selected gateway'}
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Predictions</p>
                <p className="text-2xl font-bold text-gray-900">{activePredictions.length}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-yellow-500" />
            </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Critical Severity</p>
                <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Predictions</p>
                <p className="text-2xl font-bold text-gray-900">{predictions.length}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-blue-500" />
            </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">AI-Enhanced Predictions</p>
                <p className="text-2xl font-bold text-indigo-600">{aiEnhancedCount}</p>
              </div>
              <Bot className="w-8 h-8 text-indigo-500" />
            </div>
        </div>
      </div>

      {/* Timeline View */}
      {activePredictions.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Prediction Timeline</h2>
          <PredictionTimeline
            predictions={activePredictions}
            onPredictionClick={setSelectedPrediction}
          />
        </div>
      )}

      {/* Predictions List */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-4">All Predictions</h2>
        {predictions.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No predictions found</p>
            <p className="text-sm text-gray-500 mt-2">
              Click "Generate Predictions" to analyze your APIs
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {predictions.map((prediction: Prediction) => (
              <PredictionCard
                key={prediction.id}
                prediction={prediction}
                onClick={() => setSelectedPrediction(prediction)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detailed View Modal */}
      {selectedPrediction && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedPrediction(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <PredictionCard
                prediction={selectedPrediction}
                detailed
                onClick={() => {}}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Predictions;

// Made with Bob