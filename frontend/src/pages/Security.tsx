/**
 * Security Page - API-Centric View
 * 
 * Main page for API security monitoring. APIs are the primary focus,
 * with vulnerabilities organized under each API.
 */

import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import type { API, Vulnerability, SecurityPosture, VulnerabilitySeverity, VulnerabilityStatus } from '../types';
import { securityService, getSecurityPosture } from '../services/security';
import { api } from '../services/api';
import { APISecurityCard } from '../components/security/APISecurityCard';
import { SecurityDashboard } from '../components/security/SecurityDashboard';
import GatewaySelector from '../components/common/GatewaySelector';
import { useNotification } from '../contexts/NotificationContext';
import { useScan } from '../contexts/ScanContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const Security: React.FC = () => {
  const { showSuccess, showError } = useNotification();
  const { startScan, updateProgress, completeScan, getScanStateForPage } = useScan();
  const { gatewayId } = useParams<{ gatewayId?: string }>();
  const [selectedGatewayId, setSelectedGatewayId] = useState<string | null>(gatewayId || null);
  const [selectedTab, setSelectedTab] = useState<'by-api' | 'overview'>('overview');
  const [severityFilter, setSeverityFilter] = useState<VulnerabilitySeverity | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<VulnerabilityStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<string | 'all'>('all');
  const [sortBy, setSortBy] = useState<'risk' | 'name' | 'vulnerabilities'>('risk');
  const queryClient = useQueryClient();

  // Get scan state from context
  const { isScanning, scanProgress } = getScanStateForPage('security', selectedGatewayId);

  // Handle gateway selection
  const handleGatewayChange = (newGatewayId: string | null) => {
    setSelectedGatewayId(newGatewayId);
  };

  // Fetch APIs (filtered by gateway if selected)
  const {
    data: apisData,
    isLoading: apisLoading,
    error: apisError,
  } = useQuery({
    queryKey: ['apis', selectedGatewayId],
    queryFn: () => {
      const params: any = { page_size: 1000 };
      if (selectedGatewayId) params.gateway_id = selectedGatewayId;
      return api.apis.list(params);
    },
    staleTime: 0, // Always fetch fresh data
    refetchInterval: 30000,
  });

  // Fetch all vulnerabilities (filtered by gateway if selected)
  const {
    data: vulnerabilities,
    isLoading: vulnerabilitiesLoading,
    error: vulnerabilitiesError,
    refetch: refetchVulnerabilities,
  } = useQuery<Vulnerability[]>({
    queryKey: ['vulnerabilities', severityFilter, statusFilter, typeFilter, selectedGatewayId],
    queryFn: () => {
      const params = {
        gateway_id: selectedGatewayId || undefined,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        limit: 1000,
      };
      console.log('[Security.tsx] Fetching vulnerabilities with params:', params);
      console.log('[Security.tsx] statusFilter value:', statusFilter);
      return securityService.getVulnerabilities(params);
    },
    staleTime: 0, // Always fetch fresh data
    refetchInterval: 30000,
  });

  // Fetch security posture
  const {
    data: posture,
    isLoading: postureLoading,
    refetch: refetchPosture,
  } = useQuery<SecurityPosture>({
    queryKey: ['security-posture', selectedGatewayId],
    queryFn: () => getSecurityPosture({ gateway_id: selectedGatewayId || undefined }),
    staleTime: 0, // Always fetch fresh data
    refetchInterval: 30000,
  });

  // Extract APIs array from response
  const apis = apisData?.items || [];

  // Handle manual scan - scan all APIs in the selected gateway
  const handleManualScan = async () => {
    if (!selectedGatewayId) {
      showError('No Gateway Selected', 'Please select a gateway to scan');
      return;
    }

    startScan('security', selectedGatewayId, apis.length);

    try {
      let successCount = 0;
      let failCount = 0;

      // Scan each API in the selected gateway
      for (let i = 0; i < apis.length; i++) {
        const apiItem = apis[i];
        updateProgress('security', selectedGatewayId, i + 1);

        try {
          await fetch(`${API_BASE_URL}/api/v1/gateways/${selectedGatewayId}/security/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              gateway_id: selectedGatewayId,
              api_id: apiItem.id,
            }),
          });
          successCount++;
        } catch (error) {
          console.error(`Failed to scan API ${apiItem.name}:`, error);
          failCount++;
        }
      }

      // Refresh data
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['vulnerabilities'] }),
        queryClient.invalidateQueries({ queryKey: ['security-posture'] }),
      ]);

      showSuccess(
        'Security Scan Complete',
        `Total APIs: ${apis.length}\nSuccessful: ${successCount}\nFailed: ${failCount}`,
        8000
      );
    } catch (error) {
      console.error('Security scan failed:', error);
      showError('Scan Failed', 'Failed to complete security scan. Please try again.');
    } finally {
      completeScan('security', selectedGatewayId);
    }
  };

  // Group vulnerabilities by API
  const apiSecurityData = React.useMemo(() => {
    if (!apis || apis.length === 0 || !vulnerabilities) return [];

    const vulnsByApi = new Map<string, Vulnerability[]>();
    vulnerabilities.forEach(vuln => {
      if (!vulnsByApi.has(vuln.api_id)) {
        vulnsByApi.set(vuln.api_id, []);
      }
      vulnsByApi.get(vuln.api_id)!.push(vuln);
    });

    return apis.map((api: API) => {
      const apiVulns = vulnsByApi.get(api.id) || [];
      const criticalCount = apiVulns.filter(v => v.severity === 'critical').length;
      const highCount = apiVulns.filter(v => v.severity === 'high').length;
      const mediumCount = apiVulns.filter(v => v.severity === 'medium').length;
      const lowCount = apiVulns.filter(v => v.severity === 'low').length;
      const riskScore = Math.min(
        criticalCount * 40 + highCount * 25 + mediumCount * 15 + lowCount * 5,
        100
      );

      return {
        api,
        vulnerabilities: apiVulns,
        riskScore,
        totalCount: apiVulns.length,
      };
    });
  }, [apis, vulnerabilities]);

  // Sort API security data
  const sortedApiSecurityData = React.useMemo(() => {
    const data = [...apiSecurityData];
    
    switch (sortBy) {
      case 'risk':
        return data.sort((a, b) => b.riskScore - a.riskScore);
      case 'vulnerabilities':
        return data.sort((a, b) => b.totalCount - a.totalCount);
      case 'name':
        return data.sort((a, b) => a.api.name.localeCompare(b.api.name));
      default:
        return data;
    }
  }, [apiSecurityData, sortBy]);

  // Filter to show only APIs with vulnerabilities or all
  const [showOnlyWithVulns, setShowOnlyWithVulns] = useState(false);
  const filteredApiSecurityData = showOnlyWithVulns
    ? sortedApiSecurityData.filter(item => item.totalCount > 0)
    : sortedApiSecurityData;

  const handleRemediationComplete = () => {
    refetchVulnerabilities();
    refetchPosture();
  };

  // Handle filter callbacks from SecurityDashboard
  const handleFilterBySeverity = (severity: VulnerabilitySeverity) => {
    setSeverityFilter(severity);
    setSelectedTab('by-api');
  };

  const handleFilterByStatus = (status: VulnerabilityStatus) => {
    setStatusFilter(status);
    setSelectedTab('by-api');
  };

  const handleFilterByType = (type: string) => {
    setTypeFilter(type);
    setSelectedTab('by-api');
  };

  const handleViewAllVulnerabilities = () => {
    setSeverityFilter('all');
    setStatusFilter('all');
    setTypeFilter('all');
    setSelectedTab('by-api');
  };

  const isLoading = apisLoading || vulnerabilitiesLoading;
  const hasError = apisError || vulnerabilitiesError;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">API Security Center</h1>
            <p className="mt-2 text-sm text-gray-600">
              Monitor security vulnerabilities across all APIs and track automated remediation
            </p>
          </div>
          <button
            onClick={handleManualScan}
            disabled={isScanning || !selectedGatewayId}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
            title={!selectedGatewayId ? 'Select a gateway to scan' : 'Scan all APIs in selected gateway for security vulnerabilities'}
          >
            <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? `Scanning ${scanProgress?.current}/${scanProgress?.total}...` : 'Manual Scan'}
          </button>
        </div>
      </div>
      {/* Gateway Selector */}
      <div className="mb-6">
        <GatewaySelector
          selectedGatewayId={selectedGatewayId}
          onGatewayChange={handleGatewayChange}
          showAllOption={true}
        />
      </div>


      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setSelectedTab('overview')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Security Overview
          </button>
          <button
            onClick={() => setSelectedTab('by-api')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'by-api'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            APIs
            {apis && (
              <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                {apis.length}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* APIs Tab */}
      {selectedTab === 'by-api' && (
        <div>
          {/* Active Filters Display */}
          {(severityFilter !== 'all' || statusFilter !== 'all' || typeFilter !== 'all') && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-blue-900">Active Filters:</span>
                  {severityFilter !== 'all' && (
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                      Severity: {severityFilter}
                    </span>
                  )}
                  {statusFilter !== 'all' && (
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                      Status: {statusFilter.replace('_', ' ')}
                    </span>
                  )}
                  {typeFilter !== 'all' && (
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                      Type: {typeFilter.replace('_', ' ')}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => {
                    setSeverityFilter('all');
                    setStatusFilter('all');
                    setTypeFilter('all');
                  }}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  Clear All
                </button>
              </div>
            </div>
          )}

          {/* Filters and Controls */}
          <div className="mb-6 flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity Filter
              </label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as VulnerabilitySeverity | 'all')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status Filter
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as VulnerabilityStatus | 'all')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="remediated">Remediated</option>
                <option value="verified">Verified</option>
                <option value="false_positive">False Positive</option>
                <option value="accepted_risk">Accepted Risk</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'risk' | 'name' | 'vulnerabilities')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="risk">Risk Score (High to Low)</option>
                <option value="vulnerabilities">Vulnerability Count</option>
                <option value="name">API Name (A-Z)</option>
              </select>
            </div>

            <div className="flex items-end">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showOnlyWithVulns}
                  onChange={(e) => setShowOnlyWithVulns(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Show only APIs with vulnerabilities</span>
              </label>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading API security data...</p>
            </div>
          )}

          {/* Error State */}
          {hasError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">Failed to load API security data</p>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !hasError && filteredApiSecurityData.length === 0 && (
            <div className="text-center py-12 bg-white rounded-lg shadow-md">
              <div className="text-gray-400 mb-2">
                <svg
                  className="mx-auto h-12 w-12"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <p className="text-gray-500">
                {showOnlyWithVulns
                  ? 'No APIs with vulnerabilities found'
                  : 'No APIs found'}
              </p>
            </div>
          )}

          {/* API Security Cards */}
          {!isLoading && !hasError && filteredApiSecurityData.length > 0 && (
            <div className="space-y-3">
              {filteredApiSecurityData.map(({ api, vulnerabilities: apiVulns }) => (
                <APISecurityCard
                  key={api.id}
                  api={api}
                  vulnerabilities={apiVulns}
                  onRemediate={handleRemediationComplete}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Overview Tab */}
      {selectedTab === 'overview' && (
        <div>
          {postureLoading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading security posture...</p>
            </div>
          )}

          {posture && (
            <SecurityDashboard
              posture={posture}
              onFilterBySeverity={handleFilterBySeverity}
              onFilterByStatus={handleFilterByStatus}
              onFilterByType={handleFilterByType}
              onViewAllVulnerabilities={handleViewAllVulnerabilities}
            />
          )}
        </div>
      )}
    </div>
  );
};

// Made with Bob
