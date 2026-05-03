/**
 * Security Dashboard Component
 *
 * Displays overall security posture metrics and risk score with interactive filtering.
 */

import React from 'react';
import type { SecurityPosture, VulnerabilitySeverity, VulnerabilityStatus } from '../../types';
import { getRiskLevelColor } from '../../services/security';

interface SecurityDashboardProps {
  posture: SecurityPosture;
  onFilterBySeverity?: (severity: VulnerabilitySeverity) => void;
  onFilterByStatus?: (status: VulnerabilityStatus) => void;
  onFilterByType?: (type: string) => void;
  onViewAllVulnerabilities?: () => void;
}

export const SecurityDashboard: React.FC<SecurityDashboardProps> = ({
  posture,
  onFilterBySeverity,
  onFilterByStatus,
  onFilterByType,
  onViewAllVulnerabilities,
}) => {
  const severityOrder: VulnerabilitySeverity[] = ['critical', 'high', 'medium', 'low', 'info'];

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Security Posture</h2>

      {/* Risk Score */}
      <div className="mb-8 p-6 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Overall Risk Score</h3>
            <p className="text-sm text-gray-600">
              Based on vulnerability severity and remediation status
            </p>
          </div>
          <div className="text-center">
            <div className={`text-6xl font-bold ${getRiskLevelColor(posture.risk_level)}`}>
              {posture.risk_score}
            </div>
            <div className="text-sm font-medium text-gray-600 mt-2">
              Risk Level: <span className={getRiskLevelColor(posture.risk_level)}>
                {posture.risk_level.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <button
          onClick={onViewAllVulnerabilities}
          className="p-4 bg-blue-50 rounded-lg border border-blue-200 hover:bg-blue-100 hover:shadow-md transition-all text-left cursor-pointer"
        >
          <div className="text-sm font-medium text-blue-700 mb-1">Open Vulnerabilities</div>
          <div className="text-3xl font-bold text-blue-900">{posture.total_vulnerabilities}</div>
          {onViewAllVulnerabilities && (
            <div className="text-xs text-blue-600 mt-2">Click to view all →</div>
          )}
        </button>

        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="text-sm font-medium text-green-700 mb-1">Remediation Rate</div>
          <div className="text-3xl font-bold text-green-900">
            {posture.remediation_rate.toFixed(1)}%
          </div>
        </div>

        <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
          <div className="text-sm font-medium text-purple-700 mb-1">Avg Remediation Time</div>
          <div className="text-3xl font-bold text-purple-900">
            {posture.avg_remediation_time_ms
              ? formatTime(posture.avg_remediation_time_ms)
              : 'N/A'}
          </div>
        </div>
      </div>

      {/* Vulnerabilities by Severity */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Vulnerabilities by Severity
          {onFilterBySeverity && (
            <span className="text-sm font-normal text-gray-500 ml-2">(Click to filter)</span>
          )}
        </h3>
        <div className="space-y-3">
          {severityOrder.map((severity) => {
            const count = posture.by_severity[severity] || 0;
            const percentage =
              posture.total_vulnerabilities > 0
                ? (count / posture.total_vulnerabilities) * 100
                : 0;

            return (
              <button
                key={severity}
                onClick={() => onFilterBySeverity?.(severity)}
                disabled={!onFilterBySeverity || count === 0}
                className={`flex items-center w-full ${
                  onFilterBySeverity && count > 0
                    ? 'hover:bg-gray-50 cursor-pointer rounded-lg p-2 -mx-2 transition-colors'
                    : ''
                } ${count === 0 ? 'opacity-50' : ''}`}
              >
                <div className="w-32 text-sm font-medium text-gray-700 capitalize text-left">
                  {severity}
                </div>
                <div className="flex-1 mx-4">
                  <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                    <div
                      className={`h-full ${getSeverityBarColor(severity)} transition-all duration-300`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
                <div className="w-20 text-right">
                  <span className="text-sm font-semibold text-gray-900">{count}</span>
                  <span className="text-xs text-gray-500 ml-1">
                    ({percentage.toFixed(0)}%)
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Vulnerabilities by Status */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Vulnerabilities by Status
          {onFilterByStatus && (
            <span className="text-sm font-normal text-gray-500 ml-2">(Click to filter)</span>
          )}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Object.entries(posture.by_status).map(([status, count]) => (
            <button
              key={status}
              onClick={() => onFilterByStatus?.(status as VulnerabilityStatus)}
              disabled={!onFilterByStatus || count === 0}
              className={`p-4 bg-gray-50 rounded-lg border border-gray-200 transition-all text-left ${
                onFilterByStatus && count > 0
                  ? 'hover:shadow-md hover:bg-gray-100 cursor-pointer'
                  : ''
              } ${count === 0 ? 'opacity-50' : ''}`}
            >
              <div className="text-sm font-medium text-gray-600 mb-1 capitalize">
                {status.replace('_', ' ')}
              </div>
              <div className="text-2xl font-bold text-gray-900">{count}</div>
              {onFilterByStatus && count > 0 && (
                <div className="text-xs text-blue-600 mt-2">Click to filter →</div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Vulnerabilities by Type */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Vulnerabilities by Type
          {onFilterByType && (
            <span className="text-sm font-normal text-gray-500 ml-2">(Click to filter)</span>
          )}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(posture.by_type).map(([type, count]) => (
            <button
              key={type}
              onClick={() => onFilterByType?.(type)}
              disabled={!onFilterByType || count === 0}
              className={`p-4 bg-gray-50 rounded-lg border border-gray-200 transition-all text-left ${
                onFilterByType && count > 0
                  ? 'hover:shadow-md hover:bg-gray-100 cursor-pointer'
                  : ''
              } ${count === 0 ? 'opacity-50' : ''}`}
            >
              <div className="text-sm font-medium text-gray-600 mb-1 capitalize">
                {type.replace('_', ' ')}
              </div>
              <div className="text-2xl font-bold text-gray-900">{count}</div>
              {onFilterByType && count > 0 && (
                <div className="text-xs text-blue-600 mt-2">Click to filter →</div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Compliance Issues */}
      {posture.compliance_issues && posture.compliance_issues.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Compliance Issues
          </h3>
          <div className="space-y-3">
            {posture.compliance_issues.map((issue, index) => (
              <div
                key={index}
                className="p-4 bg-amber-50 rounded-lg border border-amber-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                        {issue.standard}
                      </span>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getComplianceSeverityColor(issue.severity)}`}>
                        {issue.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{issue.description}</p>
                    <div className="text-xs text-gray-600">
                      Affects <span className="font-semibold">{issue.affected_apis}</span> API{issue.affected_apis !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper functions
function getSeverityBarColor(severity: VulnerabilitySeverity): string {
  const colors: Record<VulnerabilitySeverity, string> = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-blue-500',
    info: 'bg-gray-400',
  };
  return colors[severity] || colors.info;
}

function getComplianceSeverityColor(severity: VulnerabilitySeverity): string {
  const colors: Record<VulnerabilitySeverity, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
    info: 'bg-gray-100 text-gray-800',
  };
  return colors[severity] || colors.info;
}

function formatTime(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

// Made with Bob
