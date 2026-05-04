/**
 * Compliance Page - API-Centric View
 *
 * Main page for API compliance monitoring. APIs are the primary focus,
 * with compliance violations organized under each API.
 */

import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import type {
  API,
  ComplianceViolation,
  CompliancePosture,
  ComplianceStandard,
  ComplianceSeverity,
  ComplianceStatus,
  Gateway
} from '../types';
import {
  getComplianceViolations,
  getCompliancePosture
} from '../services/compliance';
import { api } from '../services/api';
import { gatewayService } from '../services/gateway';
import { ComplianceViolationCard } from '../components/compliance/ComplianceViolationCard';
import { ComplianceDashboard } from '../components/compliance/ComplianceDashboard';
import { AuditReportGenerator } from '../components/compliance/AuditReportGenerator';
import GatewaySelector from '../components/common/GatewaySelector';
import { useNotification } from '../contexts/NotificationContext';
import { useScan } from '../contexts/ScanContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const Compliance: React.FC = () => {
  const { showSuccess, showError } = useNotification();
  const { startScan, updateProgress, completeScan, getScanStateForPage } = useScan();
  const { gatewayId } = useParams<{ gatewayId?: string }>();
  const [selectedGatewayId, setSelectedGatewayId] = useState<string | null>(gatewayId || null);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'by-api' | 'audit'>('overview');
  const [standardFilter, setStandardFilter] = useState<ComplianceStandard | 'all'>('all');
  const [severityFilter, setSeverityFilter] = useState<ComplianceSeverity | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<ComplianceStatus | 'all'>('all');
  const [sortBy, setSortBy] = useState<'risk' | 'name' | 'violations'>('risk');
  const queryClient = useQueryClient();

  // Get scan state from context
  const { isScanning, scanProgress } = getScanStateForPage('compliance', selectedGatewayId);

  // Fetch all gateways for "All Gateways" option
  const { data: gatewaysData } = useQuery({
    queryKey: ['gateways'],
    queryFn: () => gatewayService.list({ limit: 100 }),
    refetchInterval: 60000,
  });

  const allGateways = gatewaysData?.items || [];

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
      const params: any = {};
      if (selectedGatewayId) params.gateway_id = selectedGatewayId;
      return api.apis.list(params);
    },
    refetchInterval: 30000,
  });

  // Fetch all compliance violations (from all gateways if "All" is selected)
  const {
    data: violationsResponse,
    isLoading: violationsLoading,
    error: violationsError,
    refetch: refetchViolations,
  } = useQuery({
    queryKey: ['compliance-violations', standardFilter, severityFilter, statusFilter, selectedGatewayId],
    queryFn: async () => {
      console.log('[Compliance] Fetching violations with filters:', {
        selectedGatewayId,
        standardFilter,
        severityFilter,
        statusFilter
      });

      // If "All Gateways" is selected, fetch from all gateways and aggregate
      if (!selectedGatewayId) {
        const allViolations: ComplianceViolation[] = [];
        
        for (const gateway of allGateways) {
          try {
            const response = await getComplianceViolations({
              gateway_id: gateway.id,
              standard: standardFilter !== 'all' ? standardFilter : undefined,
              severity: severityFilter !== 'all' ? severityFilter : undefined,
              status: statusFilter !== 'all' ? statusFilter : undefined,
              limit: 1000,
            });
            allViolations.push(...response.violations);
          } catch (error) {
            console.error(`Failed to fetch violations for gateway ${gateway.id}:`, error);
          }
        }
        
        console.log('[Compliance] Aggregated violations from all gateways:', allViolations.length);
        return {
          violations: allViolations,
          total: allViolations.length,
          page: 1,
          page_size: allViolations.length,
          filters_applied: {},
        };
      }
      
      // Single gateway selected
      const response = await getComplianceViolations({
        gateway_id: selectedGatewayId,
        standard: standardFilter !== 'all' ? standardFilter : undefined,
        severity: severityFilter !== 'all' ? severityFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        limit: 1000,
      });
      console.log('[Compliance] Fetched violations for gateway:', {
        gatewayId: selectedGatewayId,
        violationsCount: response.violations?.length || 0,
        response
      });
      return response;
    },
    refetchInterval: 30000,
    enabled: allGateways.length > 0, // Only run when gateways are loaded
  });

  // Fetch compliance posture (aggregate from all gateways if "All" is selected)
  const {
    data: posture,
    isLoading: postureLoading,
    refetch: refetchPosture,
  } = useQuery<CompliancePosture | null>({
    queryKey: ['compliance-posture', selectedGatewayId],
    queryFn: async () => {
      // If "All Gateways" is selected, fetch from all gateways and aggregate
      if (!selectedGatewayId) {
        const allPostures: CompliancePosture[] = [];
        
        for (const gateway of allGateways) {
          try {
            const postureData = await getCompliancePosture({ gateway_id: gateway.id });
            allPostures.push(postureData);
          } catch (error) {
            console.error(`Failed to fetch posture for gateway ${gateway.id}:`, error);
          }
        }
        
        // Aggregate postures
        if (allPostures.length === 0) {
          return null;
        }
        
        const aggregated: CompliancePosture = {
          total_violations: allPostures.reduce((sum, p) => sum + p.total_violations, 0),
          open_violations: allPostures.reduce((sum, p) => sum + p.open_violations, 0),
          resolved_violations: allPostures.reduce((sum, p) => sum + p.resolved_violations, 0),
          by_severity: {
            critical: allPostures.reduce((sum, p) => sum + p.by_severity.critical, 0),
            high: allPostures.reduce((sum, p) => sum + p.by_severity.high, 0),
            medium: allPostures.reduce((sum, p) => sum + p.by_severity.medium, 0),
            low: allPostures.reduce((sum, p) => sum + p.by_severity.low, 0),
          },
          by_standard: {
            GDPR: {
              standard: 'GDPR',
              score: Math.round(allPostures.reduce((sum, p) => sum + p.by_standard.GDPR.score, 0) / allPostures.length),
              violations: allPostures.reduce((sum, p) => sum + p.by_standard.GDPR.violations, 0),
              compliant_controls: allPostures.reduce((sum, p) => sum + p.by_standard.GDPR.compliant_controls, 0),
              total_controls: allPostures.reduce((sum, p) => sum + p.by_standard.GDPR.total_controls, 0),
              last_assessed: new Date().toISOString(),
            },
            HIPAA: {
              standard: 'HIPAA',
              score: Math.round(allPostures.reduce((sum, p) => sum + p.by_standard.HIPAA.score, 0) / allPostures.length),
              violations: allPostures.reduce((sum, p) => sum + p.by_standard.HIPAA.violations, 0),
              compliant_controls: allPostures.reduce((sum, p) => sum + p.by_standard.HIPAA.compliant_controls, 0),
              total_controls: allPostures.reduce((sum, p) => sum + p.by_standard.HIPAA.total_controls, 0),
              last_assessed: new Date().toISOString(),
            },
            PCI_DSS: {
              standard: 'PCI_DSS',
              score: Math.round(allPostures.reduce((sum, p) => sum + p.by_standard.PCI_DSS.score, 0) / allPostures.length),
              violations: allPostures.reduce((sum, p) => sum + p.by_standard.PCI_DSS.violations, 0),
              compliant_controls: allPostures.reduce((sum, p) => sum + p.by_standard.PCI_DSS.compliant_controls, 0),
              total_controls: allPostures.reduce((sum, p) => sum + p.by_standard.PCI_DSS.total_controls, 0),
              last_assessed: new Date().toISOString(),
            },
            SOC2: {
              standard: 'SOC2',
              score: Math.round(allPostures.reduce((sum, p) => sum + p.by_standard.SOC2.score, 0) / allPostures.length),
              violations: allPostures.reduce((sum, p) => sum + p.by_standard.SOC2.violations, 0),
              compliant_controls: allPostures.reduce((sum, p) => sum + p.by_standard.SOC2.compliant_controls, 0),
              total_controls: allPostures.reduce((sum, p) => sum + p.by_standard.SOC2.total_controls, 0),
              last_assessed: new Date().toISOString(),
            },
            ISO_27001: {
              standard: 'ISO_27001',
              score: Math.round(allPostures.reduce((sum, p) => sum + p.by_standard.ISO_27001.score, 0) / allPostures.length),
              violations: allPostures.reduce((sum, p) => sum + p.by_standard.ISO_27001.violations, 0),
              compliant_controls: allPostures.reduce((sum, p) => sum + p.by_standard.ISO_27001.compliant_controls, 0),
              total_controls: allPostures.reduce((sum, p) => sum + p.by_standard.ISO_27001.total_controls, 0),
              last_assessed: new Date().toISOString(),
            },
          },
          by_status: {
            open: allPostures.reduce((sum, p) => sum + p.by_status.open, 0),
            in_progress: allPostures.reduce((sum, p) => sum + p.by_status.in_progress, 0),
            resolved: allPostures.reduce((sum, p) => sum + p.by_status.resolved, 0),
            accepted_risk: allPostures.reduce((sum, p) => sum + p.by_status.accepted_risk, 0),
            false_positive: allPostures.reduce((sum, p) => sum + p.by_status.false_positive, 0),
          },
          overall_score: Math.round(allPostures.reduce((sum, p) => sum + p.overall_score, 0) / allPostures.length),
          risk_level: allPostures.some(p => p.risk_level === 'critical') ? 'critical' :
                      allPostures.some(p => p.risk_level === 'high') ? 'high' :
                      allPostures.some(p => p.risk_level === 'medium') ? 'medium' : 'low',
          last_scan_date: new Date().toISOString(),
          compliance_trends: [],
        };
        
        return aggregated;
      }
      
      // Single gateway selected
      return getCompliancePosture({ gateway_id: selectedGatewayId });
    },
    refetchInterval: 30000,
    enabled: allGateways.length > 0, // Only run when gateways are loaded
  });

  // Extract APIs array and violations from response
  const apis = apisData?.items || [];
  const violations = violationsResponse?.violations || [];

  // Handle manual scan - scan all APIs in the selected gateway
  const handleManualScan = async () => {
    if (!selectedGatewayId) {
      showError('No Gateway Selected', 'Please select a gateway to scan');
      return;
    }

    startScan('compliance', selectedGatewayId, apis.length);

    try {
      let successCount = 0;
      let failCount = 0;

      // Scan each API in the selected gateway
      for (let i = 0; i < apis.length; i++) {
        const apiItem = apis[i];
        updateProgress('compliance', selectedGatewayId, i + 1);

        try {
          await fetch(`${API_BASE_URL}/api/v1/gateways/${selectedGatewayId}/compliance/scan`, {
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
        queryClient.invalidateQueries({ queryKey: ['compliance-violations'] }),
        queryClient.invalidateQueries({ queryKey: ['compliance-posture'] }),
      ]);

      showSuccess(
        'Compliance Scan Complete',
        `Total APIs: ${apis.length}\nSuccessful: ${successCount}\nFailed: ${failCount}`,
        8000
      );
    } catch (error) {
      console.error('Compliance scan failed:', error);
      showError('Scan Failed', 'Failed to complete compliance scan. Please try again.');
    } finally {
      completeScan('compliance', selectedGatewayId);
    }
  };

  // Group violations by API
  const apiComplianceData = React.useMemo(() => {
    if (!apis || apis.length === 0 || !violations) {
      console.log('[Compliance] No APIs or violations:', { apisCount: apis?.length, violationsCount: violations?.length });
      return [];
    }

    console.log('[Compliance] Grouping violations by API:', {
      apisCount: apis.length,
      violationsCount: violations.length,
      sampleViolation: violations[0],
      sampleAPI: apis[0]
    });

    const violationsByApi = new Map<string, ComplianceViolation[]>();
    violations.forEach(violation => {
      if (!violationsByApi.has(violation.api_id)) {
        violationsByApi.set(violation.api_id, []);
      }
      violationsByApi.get(violation.api_id)!.push(violation);
    });

    console.log('[Compliance] Violations grouped:', {
      uniqueAPIIds: Array.from(violationsByApi.keys()),
      violationCounts: Array.from(violationsByApi.entries()).map(([id, viols]) => ({ id, count: viols.length }))
    });

    return apis.map((api: API) => {
      const apiViolations = violationsByApi.get(api.id) || [];
      console.log(`[Compliance] API ${api.name} (${api.id}): ${apiViolations.length} violations`);
      const criticalCount = apiViolations.filter(v => v.severity === 'critical').length;
      const highCount = apiViolations.filter(v => v.severity === 'high').length;
      const mediumCount = apiViolations.filter(v => v.severity === 'medium').length;
      const lowCount = apiViolations.filter(v => v.severity === 'low').length;
      const riskScore = Math.min(
        criticalCount * 40 + highCount * 25 + mediumCount * 15 + lowCount * 5,
        100
      );

      return {
        api,
        violations: apiViolations,
        riskScore,
        totalCount: apiViolations.length,
      };
    });
  }, [apis, violations]);

  // Sort API compliance data
  const sortedApiComplianceData = React.useMemo(() => {
    const data = [...apiComplianceData];
    
    switch (sortBy) {
      case 'risk':
        return data.sort((a, b) => b.riskScore - a.riskScore);
      case 'violations':
        return data.sort((a, b) => b.totalCount - a.totalCount);
      case 'name':
        return data.sort((a, b) => a.api.name.localeCompare(b.api.name));
      default:
        return data;
    }
  }, [apiComplianceData, sortBy]);

  // Filter to show only APIs with violations or all
  const [showOnlyWithViolations, setShowOnlyWithViolations] = useState(false);
  const filteredApiComplianceData = showOnlyWithViolations
    ? sortedApiComplianceData.filter(item => item.totalCount > 0)
    : sortedApiComplianceData;

  const handleViolationUpdate = () => {
    refetchViolations();
    refetchPosture();
  };

  // Handle filter callbacks from ComplianceDashboard
  const handleFilterByStandard = (standard: ComplianceStandard) => {
    setStandardFilter(standard);
    setSelectedTab('by-api');
  };

  const handleFilterBySeverity = (severity: ComplianceSeverity) => {
    setSeverityFilter(severity);
    setSelectedTab('by-api');
  };

  const handleFilterByStatus = (status: ComplianceStatus) => {
    setStatusFilter(status);
    setSelectedTab('by-api');
  };

  const handleViewAllViolations = () => {
    setStandardFilter('all');
    setSeverityFilter('all');
    setStatusFilter('all');
    setSelectedTab('by-api');
  };

  const isLoading = apisLoading || violationsLoading;
  const hasError = apisError || violationsError;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Compliance Monitoring Center</h1>
            <p className="mt-2 text-sm text-gray-600">
              Monitor regulatory compliance across all APIs and track audit readiness
            </p>
          </div>
          <button
            onClick={handleManualScan}
            disabled={isScanning || !selectedGatewayId}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors"
            title={!selectedGatewayId ? 'Select a gateway to scan' : 'Scan all APIs in selected gateway for compliance violations'}
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
      {(selectedGatewayId || allGateways.length > 0) && (
        <>
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
                Compliance Overview
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
              <button
                onClick={() => setSelectedTab('audit')}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  selectedTab === 'audit'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Audit Reports
              </button>
            </nav>
          </div>

          {/* APIs Tab */}
          {selectedTab === 'by-api' && (
            <div>
              {/* Active Filters Display */}
              {(standardFilter !== 'all' || severityFilter !== 'all' || statusFilter !== 'all') && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-blue-900">Active Filters:</span>
                  {standardFilter !== 'all' && (
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                      Standard: {standardFilter}
                    </span>
                  )}
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
                </div>
                <button
                  onClick={() => {
                    setStandardFilter('all');
                    setSeverityFilter('all');
                    setStatusFilter('all');
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
                Standard Filter
              </label>
              <select
                value={standardFilter}
                onChange={(e) => setStandardFilter(e.target.value as ComplianceStandard | 'all')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Standards</option>
                <option value="GDPR">GDPR</option>
                <option value="HIPAA">HIPAA</option>
                <option value="SOC2">SOC2</option>
                <option value="PCI_DSS">PCI-DSS</option>
                <option value="ISO_27001">ISO 27001</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity Filter
              </label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as ComplianceSeverity | 'all')}
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
                onChange={(e) => setStatusFilter(e.target.value as ComplianceStatus | 'all')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="accepted_risk">Accepted Risk</option>
                <option value="false_positive">False Positive</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'risk' | 'name' | 'violations')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="risk">Risk Score (High to Low)</option>
                <option value="violations">Violation Count</option>
                <option value="name">API Name (A-Z)</option>
              </select>
            </div>

            <div className="flex items-end">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showOnlyWithViolations}
                  onChange={(e) => setShowOnlyWithViolations(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Show only APIs with violations</span>
              </label>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading compliance data...</p>
            </div>
          )}

          {/* Error State */}
          {hasError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">Failed to load compliance data</p>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !hasError && filteredApiComplianceData.length === 0 && (
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
                {showOnlyWithViolations
                  ? 'No APIs with compliance violations found'
                  : 'No APIs found'}
              </p>
            </div>
          )}

          {/* API Compliance Violation Cards */}
          {!isLoading && !hasError && filteredApiComplianceData.length > 0 && (
            <div className="space-y-3">
              {filteredApiComplianceData.map(({ api, violations: apiViolations }) => (
                <div key={api.id} className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{api.name}</h3>
                      <p className="text-sm text-gray-500">{api.base_path}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        apiViolations.length === 0
                          ? 'bg-green-100 text-green-800'
                          : apiViolations.some((v: { severity: string }) => v.severity === 'critical')
                          ? 'bg-red-100 text-red-800'
                          : apiViolations.some((v: { severity: string }) => v.severity === 'high')
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {apiViolations.length} {apiViolations.length === 1 ? 'Violation' : 'Violations'}
                      </span>
                    </div>
                  </div>

                  {apiViolations.length > 0 && (
                    <div className="space-y-3">
                      {apiViolations.map((violation: ComplianceViolation) => (
                        <ComplianceViolationCard
                          key={violation.id}
                          violation={violation}
                          onUpdate={handleViolationUpdate}
                        />
                      ))}
                    </div>
                  )}

                  {apiViolations.length === 0 && (
                    <div className="text-center py-4 text-gray-500">
                      <svg
                        className="mx-auto h-8 w-8 text-green-500 mb-2"
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
                      <p className="text-sm">No compliance violations detected</p>
                    </div>
                  )}
                </div>
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
                  <p className="mt-2 text-gray-600">Loading compliance posture...</p>
                </div>
              )}

              {posture && (
                <ComplianceDashboard
                  posture={posture}
                  onFilterByStandard={handleFilterByStandard}
                  onFilterBySeverity={handleFilterBySeverity}
                  onFilterByStatus={handleFilterByStatus}
                  onViewAllViolations={handleViewAllViolations}
                />
              )}
            </div>
          )}

          {/* Audit Reports Tab */}
          {selectedTab === 'audit' && (
            <div>
              <AuditReportGenerator
                apis={apis}
                gatewayId={selectedGatewayId}
                onReportGenerated={() => {
                  // Optionally refresh data after report generation
                  refetchViolations();
                  refetchPosture();
                }}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Made with Bob