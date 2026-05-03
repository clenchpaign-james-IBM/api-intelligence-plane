import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { Server, CheckCircle, XCircle, Clock, RefreshCw, Plus, ArrowLeft, Loader, X, Trash2 } from 'lucide-react';
import Card from '../components/common/Card';
import Loading from '../components/common/Loading';
import Error from '../components/common/Error';
import AddGatewayForm from '../components/gateways/AddGatewayForm';
import GatewayCard from '../components/gateways/GatewayCard';
import { api } from '../services/api';
import type { Gateway } from '../types';
import { useNotification } from '../contexts/NotificationContext';

/**
 * Gateways Page
 * 
 * Page for managing API gateways:
 * - List of connected gateways
 * - Gateway status and capabilities
 * - Sync and management actions
 */
const Gateways = () => {
  const { showSuccess, showError, showConfirm } = useNotification();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { gatewayId } = useParams<{ gatewayId?: string }>();
  const [selectedGateway, setSelectedGateway] = useState<Gateway | null>(null);
  const [syncingGateway, setSyncingGateway] = useState<string | null>(null);
  const [connectingGateway, setConnectingGateway] = useState<string | null>(null);
  const [disconnectingGateway, setDisconnectingGateway] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedGateways, setSelectedGateways] = useState<Set<string>>(new Set());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [bulkSyncStatus, setBulkSyncStatus] = useState<{
    isRunning: boolean;
    results?: any;
  }>({ isRunning: false });

  // Fetch gateways
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['gateways'],
    queryFn: () => api.gateways.list(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Set selected gateway from URL parameter
  useEffect(() => {
    if (gatewayId && data?.items) {
      const gateway = data.items.find((g: Gateway) => g.id === gatewayId);
      if (gateway) {
        setSelectedGateway(gateway);
      }
    }
  }, [gatewayId, data]);

  // Sync gateway mutation
  const syncMutation = useMutation({
    mutationFn: (gatewayId: string) => api.gateways.sync(gatewayId),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['gateways'] });
      setSyncingGateway(null);
      showSuccess(
        'Sync Completed',
        `${data.apis_discovered} APIs discovered (${data.new_apis} new, ${data.updated_apis} updated)`
      );
    },
    onError: (error: any) => {
      console.error('Sync failed:', error);
      setSyncingGateway(null);
      const errorMessage = error.details?.detail || error.message || 'Failed to sync gateway. Please try again.';
      showError('Sync Failed', errorMessage);
    },
  });

  // Bulk sync mutation
  const bulkSyncMutation = useMutation({
    mutationFn: ({ gatewayIds, forceRefresh }: { gatewayIds: string[]; forceRefresh: boolean }) =>
      api.gateways.bulkSync(gatewayIds, forceRefresh),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['gateways'] });
      setBulkSyncStatus({ isRunning: false, results: data });
      setSelectedGateways(new Set());
      // Auto-hide results after 10 seconds
      setTimeout(() => {
        setBulkSyncStatus({ isRunning: false });
      }, 10000);
    },
    onError: (error: any) => {
      console.error('Bulk sync failed:', error);
      setBulkSyncStatus({ isRunning: false });
      const errorMessage = error.details?.detail || error.message || 'Failed to sync gateways. Please try again.';
      showError('Bulk Sync Failed', errorMessage);
    },
  });

  // Delete gateway mutation
  const deleteMutation = useMutation({
    mutationFn: (gatewayId: string) => api.gateways.delete(gatewayId),
    onSuccess: (_, gatewayId) => {
      queryClient.invalidateQueries({ queryKey: ['gateways'] });
      setSelectedGateways((prev) => {
        const next = new Set(prev);
        next.delete(gatewayId);
        return next;
      });
      if (selectedGateway?.id === gatewayId) {
        setSelectedGateway(null);
        navigate('/gateways');
      }
    },
    onError: (error: any) => {
      console.error('Delete failed:', error);
      const errorMessage = error.details?.detail || error.message || 'Failed to delete gateway. Please try again.';
      showError('Delete Failed', errorMessage);
    },
  });

  // Connect gateway mutation
  const connectMutation = useMutation({
    mutationFn: (gatewayId: string) => api.gateways.connect(gatewayId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gateways'] });
      setConnectingGateway(null);
      showSuccess('Gateway Connected', 'Gateway connected successfully');
    },
    onError: (error: any) => {
      console.error('Connect failed:', error);
      setConnectingGateway(null);
      const errorMessage = error.details?.detail || error.message || 'Failed to connect gateway. Please try again.';
      showError('Connect Failed', errorMessage);
    },
  });

  // Disconnect gateway mutation
  const disconnectMutation = useMutation({
    mutationFn: (gatewayId: string) => api.gateways.disconnect(gatewayId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gateways'] });
      setDisconnectingGateway(null);
      showSuccess('Gateway Disconnected', 'Gateway disconnected successfully');
    },
    onError: (error: any) => {
      console.error('Disconnect failed:', error);
      setDisconnectingGateway(null);
      const errorMessage = error.details?.detail || error.message || 'Failed to disconnect gateway. Please try again.';
      showError('Disconnect Failed', errorMessage);
    },
  });

  // Handle sync
  const handleSync = (gatewayId: string) => {
    setSyncingGateway(gatewayId);
    syncMutation.mutate(gatewayId);
  };

  // Handle connect
  const handleConnect = (gatewayId: string) => {
    setConnectingGateway(gatewayId);
    connectMutation.mutate(gatewayId);
  };

  // Handle disconnect
  const handleDisconnect = (gatewayId: string) => {
    const gateway = data?.items.find((g: Gateway) => g.id === gatewayId);
    showConfirm(
      'Disconnect Gateway',
      `Disconnect from gateway "${gateway?.name}"? The gateway will remain registered but inactive.`,
      () => {
        setDisconnectingGateway(gatewayId);
        disconnectMutation.mutate(gatewayId);
      }
    );
  };

  // Handle delete
  const handleDelete = (gateway: Gateway) => {
    showConfirm(
      'Delete Gateway',
      `Delete gateway "${gateway.name}"? This action cannot be undone.`,
      () => {
        deleteMutation.mutate(gateway.id);
      },
      'danger'
    );
  };

  // Handle bulk sync
  const handleBulkSync = (forceRefresh: boolean = false) => {
    if (selectedGateways.size === 0) {
      showError('No Selection', 'Please select at least one gateway to sync');
      return;
    }
    setBulkSyncStatus({ isRunning: true });
    bulkSyncMutation.mutate({
      gatewayIds: Array.from(selectedGateways),
      forceRefresh,
    });
  };

  // Handle select all
  const handleSelectAll = () => {
    if (selectedGateways.size === gateways.length) {
      setSelectedGateways(new Set());
    } else {
      setSelectedGateways(new Set(gateways.map((g: Gateway) => g.id)));
    }
  };

  // Handle select gateway
  const handleSelectGateway = (gatewayId: string) => {
    const newSelected = new Set(selectedGateways);
    if (newSelected.has(gatewayId)) {
      newSelected.delete(gatewayId);
    } else {
      newSelected.add(gatewayId);
    }
    setSelectedGateways(newSelected);
  };

  // Handle view details
  const handleViewDetails = (gateway: Gateway) => {
    navigate(`/gateways/${gateway.id}`);
  };

  // Handle back - uses browser history to return to previous page
  const handleBack = () => {
    setSelectedGateway(null);
    navigate(-1); // Go back to previous page (Dashboard or Gateways list)
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'disconnected': return <Clock className="w-5 h-5 text-gray-600" />;
      case 'error': return <XCircle className="w-5 h-5 text-red-600" />;
      default: return <Server className="w-5 h-5 text-gray-600" />;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'bg-green-100 text-green-800';
      case 'disconnected': return 'bg-gray-100 text-gray-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Get vendor badge color
  const getVendorColor = (vendor: string) => {
    switch (vendor) {
      case 'native': return 'bg-blue-100 text-blue-800';
      case 'webmethods': return 'bg-green-100 text-green-800';
      case 'kong': return 'bg-purple-100 text-purple-800';
      case 'apigee': return 'bg-orange-100 text-orange-800';
      case 'aws': return 'bg-yellow-100 text-yellow-800';
      case 'azure': return 'bg-cyan-100 text-cyan-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="p-6">
        <Loading message="Loading gateways..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6">
        <Error
          message="Failed to load gateways"
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  const gateways = data?.items || [];

  // If a gateway is selected, show detail view
  if (selectedGateway) {
    return (
      <div className="p-6 space-y-6">
        {/* Back Button */}
        <button
          onClick={handleBack}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium mb-4"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>

        {/* Gateway Details using GatewayCard component */}
        <GatewayCard
          gateway={selectedGateway}
          onSync={handleSync}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onDelete={handleDelete}
          isSyncing={syncingGateway === selectedGateway.id}
          isConnecting={connectingGateway === selectedGateway.id}
          isDisconnecting={disconnectingGateway === selectedGateway.id}
          isDeleting={deleteMutation.isPending && deleteMutation.variables === selectedGateway.id}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">API Gateways</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage and monitor connected API gateways
          </p>
        </div>
        <div className="flex gap-3">
          {selectedGateways.size > 0 && (
            <>
              <button
                onClick={() => handleBulkSync(false)}
                disabled={bulkSyncStatus.isRunning}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {bulkSyncStatus.isRunning ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Syncing {selectedGateways.size}...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    Sync Selected ({selectedGateways.size})
                  </>
                )}
              </button>
              <button
                onClick={() => setSelectedGateways(new Set())}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Clear Selection
              </button>
            </>
          )}
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Gateway
          </button>
          <button
            onClick={async () => {
              setIsRefreshing(true);
              try {
                await refetch();
              } finally {
                setIsRefreshing(false);
              }
            }}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <Server className="w-10 h-10 text-blue-600" />
            <div>
              <p className="text-sm text-gray-600">Total Gateways</p>
              <p className="text-2xl font-bold text-gray-900">{gateways.length}</p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-10 h-10 text-green-600" />
            <div>
              <p className="text-sm text-gray-600">Connected</p>
              <p className="text-2xl font-bold text-gray-900">
                {gateways.filter((g: Gateway) => g.status === 'connected').length}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <Clock className="w-10 h-10 text-gray-600" />
            <div>
              <p className="text-sm text-gray-600">Disconnected</p>
              <p className="text-2xl font-bold text-gray-900">
                {gateways.filter((g: Gateway) => g.status === 'disconnected').length}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <XCircle className="w-10 h-10 text-red-600" />
            <div>
              <p className="text-sm text-gray-600">Error</p>
              <p className="text-2xl font-bold text-gray-900">
                {gateways.filter((g: Gateway) => g.status === 'error').length}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Bulk Sync Results */}
      {bulkSyncStatus.results && (
        <Card padding="md">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Bulk Sync Results</h3>
              <button
                onClick={() => setBulkSyncStatus({ isRunning: false })}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="grid grid-cols-4 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Total</p>
                <p className="text-xl font-bold text-gray-900">{bulkSyncStatus.results.total}</p>
              </div>
              <div>
                <p className="text-gray-600">Successful</p>
                <p className="text-xl font-bold text-green-600">{bulkSyncStatus.results.successful}</p>
              </div>
              <div>
                <p className="text-gray-600">Failed</p>
                <p className="text-xl font-bold text-red-600">{bulkSyncStatus.results.failed}</p>
              </div>
              <div>
                <p className="text-gray-600">Duration</p>
                <p className="text-xl font-bold text-blue-600">{bulkSyncStatus.results.duration_seconds?.toFixed(2)}s</p>
              </div>
            </div>
            {bulkSyncStatus.results.results && bulkSyncStatus.results.results.length > 0 && (
              <div className="mt-4 space-y-2 max-h-60 overflow-y-auto">
                {bulkSyncStatus.results.results.map((result: any, index: number) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border ${
                      result.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {result.success ? (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-600" />
                        )}
                        <span className="font-medium text-gray-900">{result.gateway_name}</span>
                      </div>
                      {result.apis_discovered !== undefined && (
                        <span className="text-sm text-gray-600">
                          {result.apis_discovered} APIs discovered
                        </span>
                      )}
                    </div>
                    {result.error && (
                      <p className="text-sm text-red-700 mt-1">{result.error}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Gateway List */}
      <div className="space-y-4">
        {gateways.length > 0 && (
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-lg">
            <input
              type="checkbox"
              checked={selectedGateways.size === gateways.length && gateways.length > 0}
              onChange={handleSelectAll}
              className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">
              {selectedGateways.size === gateways.length ? 'Deselect All' : 'Select All'}
            </span>
          </div>
        )}
        {gateways.length === 0 ? (
          <div className="col-span-full">
            <Card padding="lg">
              <div className="text-center py-12">
                <Server className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Gateways Configured</h3>
                <p className="text-gray-600 mb-6">
                  Add your first API gateway to start discovering and monitoring APIs
                </p>
                <button
                  onClick={() => setShowAddForm(true)}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Add Gateway
                </button>
              </div>
            </Card>
          </div>
        ) : (
          gateways.map((gateway: Gateway) => (
            <Card key={gateway.id} padding="md">
              <div className="flex items-center gap-4">
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={selectedGateways.has(gateway.id)}
                  onChange={() => handleSelectGateway(gateway.id)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 flex-shrink-0"
                />
                
                {/* Status Icon & Basic Info */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {getStatusIcon(gateway.status)}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{gateway.name}</h3>
                    <p className="text-sm text-gray-600">{gateway.base_url}</p>
                  </div>
                </div>

                {/* Status & Vendor Badges */}
                <div className="flex gap-2 flex-shrink-0">
                  <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(gateway.status)}`}>
                    {gateway.status}
                  </span>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${getVendorColor(gateway.vendor)}`}>
                    {gateway.vendor}
                  </span>
                </div>

                {/* Capabilities */}
                {gateway.capabilities && gateway.capabilities.length > 0 && (
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-700 flex-shrink-0">Capabilities:</p>
                    <div className="flex flex-wrap gap-1">
                      {gateway.capabilities.map((capability) => (
                        <span
                          key={capability}
                          className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                        >
                          {capability}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="flex gap-4 text-sm flex-shrink-0">
                  <div>
                    <p className="text-gray-600">Created</p>
                    <p className="font-medium text-gray-900">
                      {new Date(gateway.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  {gateway.last_connected_at && (
                    <div>
                      <p className="text-gray-600">Last Connected</p>
                      <p className="font-medium text-gray-900">
                        {new Date(gateway.last_connected_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleSync(gateway.id)}
                    disabled={syncingGateway === gateway.id}
                    className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    {syncingGateway === gateway.id ? 'Syncing...' : 'Sync Now'}
                  </button>
                  <button
                    onClick={() => handleViewDetails(gateway)}
                    className="px-3 py-1 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition-colors text-xs flex items-center gap-1"
                  >
                    View Details
                  </button>
                  <button
                    onClick={() => handleDelete(gateway)}
                    disabled={deleteMutation.isPending && deleteMutation.variables === gateway.id}
                    className="px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    <Trash2 className="w-3 h-3" />
                    {deleteMutation.isPending && deleteMutation.variables === gateway.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Add Gateway Modal */}
      {showAddForm && (
        <AddGatewayForm
          onClose={() => setShowAddForm(false)}
          onSuccess={() => {
            setShowAddForm(false);
            refetch();
          }}
        />
      )}
    </div>
  );
};

export default Gateways;

// Made with Bob