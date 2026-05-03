/**
 * API Security Card Component
 * 
 * Displays an API with its security vulnerabilities and metrics.
 * This is the primary component for the API-centric security view.
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import type { API, Vulnerability } from '../../types';
import { VulnerabilityCard } from './VulnerabilityCard';

interface APISecurityCardProps {
  api: API;
  vulnerabilities: Vulnerability[];
  onRemediate?: () => void;
}

export const APISecurityCard: React.FC<APISecurityCardProps> = ({
  api,
  vulnerabilities,
  onRemediate,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Calculate security metrics - ONLY for OPEN vulnerabilities
  const openVulnerabilities = vulnerabilities.filter(v => v.status === 'open');
  const criticalCount = openVulnerabilities.filter(v => v.severity === 'critical').length;
  const highCount = openVulnerabilities.filter(v => v.severity === 'high').length;
  const mediumCount = openVulnerabilities.filter(v => v.severity === 'medium').length;
  const lowCount = openVulnerabilities.filter(v => v.severity === 'low').length;
  const totalCount = vulnerabilities.length;

  const openCount = openVulnerabilities.length;
  const remediatedCount = vulnerabilities.filter(v =>
    v.status === 'remediated' || v.verification_status === 'verified'
  ).length;
  
  // Debug logging
  console.log(`[APISecurityCard] API: ${api.name}`);
  console.log(`[APISecurityCard] Total vulnerabilities: ${vulnerabilities.length}`);
  console.log(`[APISecurityCard] Open vulnerabilities: ${openCount}`);
  console.log(`[APISecurityCard] Vulnerabilities:`, vulnerabilities.map(v => ({
    id: v.id,
    title: v.title,
    status: v.status,
    verification_status: v.verification_status
  })));
  console.log(`[APISecurityCard] Open count: ${openCount}, Remediated count: ${remediatedCount}`);

  // Calculate risk score (0-100, higher is worse) - ONLY from OPEN vulnerabilities
  const riskScore = Math.min(
    criticalCount * 40 + highCount * 25 + mediumCount * 15 + lowCount * 5,
    100
  );

  const getRiskLevel = (score: number): string => {
    if (score >= 75) return 'Critical';
    if (score >= 50) return 'High';
    if (score >= 25) return 'Medium';
    return 'Low';
  };

  const getRiskColor = (score: number): string => {
    if (score >= 75) return 'text-red-600 bg-red-50 border-red-200';
    if (score >= 50) return 'text-orange-600 bg-orange-50 border-orange-200';
    if (score >= 25) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-green-600 bg-green-50 border-green-200';
  };

  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden border border-gray-200">
      {/* Main Card Content */}
      <div className="px-4 py-2.5">
        <div className="flex items-start justify-between gap-4">
          {/* Left: API Info */}
          <div className="flex items-start gap-2 flex-1 min-w-0">
            <svg className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <div className="flex-1 min-w-0">
              <Link to={`/apis/${api.id}`} className="text-base font-bold text-gray-900 hover:text-blue-600 transition-colors block">
                {api.name}
              </Link>
              <p className="text-xs text-gray-600 mt-0.5">
                {api.base_path} • {api.methods.join(', ')} • {api.endpoints.length} endpoints
              </p>
              
              {/* Policy Actions - Inline */}
              {api.policy_actions && api.policy_actions.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {api.policy_actions.some((action) => action.enabled && action.action_type === 'authentication') && (
                    <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded">Auth</span>
                  )}
                  {api.policy_actions.some((action) =>
                    action.enabled &&
                    action.action_type === 'tls' &&
                    (action.config?.enforce_tls === true || action.vendor_config?.enforce_tls === true)
                  ) && (
                    <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded">TLS</span>
                  )}
                  {api.policy_actions.some((action) => action.enabled && action.action_type === 'rate_limiting') && (
                    <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded">Rate Limit</span>
                  )}
                  {api.policy_actions.some((action) => action.enabled && action.action_type === 'authorization') && (
                    <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded">Authorization</span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Center: Vulnerability Summary */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Severity Badges */}
            <div className="flex items-center gap-1">
              {criticalCount > 0 && (
                <span className="px-2 py-1 text-xs font-semibold bg-red-100 text-red-800 rounded">
                  {criticalCount} Critical
                </span>
              )}
              {highCount > 0 && (
                <span className="px-2 py-1 text-xs font-semibold bg-orange-100 text-orange-800 rounded">
                  {highCount} High
                </span>
              )}
              {mediumCount > 0 && (
                <span className="px-2 py-1 text-xs font-semibold bg-yellow-100 text-yellow-800 rounded">
                  {mediumCount} Medium
                </span>
              )}
              {lowCount > 0 && (
                <span className="px-2 py-1 text-xs font-semibold bg-blue-100 text-blue-800 rounded">
                  {lowCount} Low
                </span>
              )}
              {totalCount === 0 && (
                <span className="px-2 py-1 text-xs font-semibold bg-green-100 text-green-800 rounded">
                  ✓ No Issues
                </span>
              )}
            </div>

            {/* Status Summary */}
            <div className="text-center px-3 py-1 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs text-gray-600">
                <span className="font-bold text-red-600">{openCount}</span> Open •
                <span className="font-bold text-green-600 ml-1">{remediatedCount}</span> Fixed
              </div>
            </div>
          </div>

          {/* Right: Risk Score & Expand */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className={`px-3 py-1.5 rounded border ${getRiskColor(riskScore)}`}>
              <div className="text-center">
                <div className="text-lg font-bold leading-none">{riskScore}</div>
                <div className="text-xs leading-none mt-0.5">{getRiskLevel(riskScore)}</div>
              </div>
            </div>

            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 hover:bg-gray-100 rounded transition-colors"
              title={isExpanded ? 'Hide vulnerabilities' : 'Show vulnerabilities'}
            >
              <svg
                className={`w-5 h-5 text-gray-600 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Vulnerabilities */}
      {isExpanded && (
        <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
          {vulnerabilities.length === 0 ? (
            <div className="text-center py-6 text-gray-500">
              <svg className="mx-auto h-10 w-10 text-green-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm">No vulnerabilities found for this API</p>
            </div>
          ) : (
            <div className="space-y-2">
              {vulnerabilities.map((vulnerability) => (
                <VulnerabilityCard
                  key={vulnerability.id}
                  vulnerability={vulnerability}
                  onRemediate={onRemediate}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};


// Made with Bob