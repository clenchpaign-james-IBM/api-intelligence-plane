/**
 * Audit Report Generator Component
 *
 * Allows users to generate comprehensive audit reports for compliance monitoring.
 * Supports filtering by standards, APIs, and date ranges.
 */

import React, { useState } from 'react';
import type { API, ComplianceStandard, AuditReport } from '../../types';
import { generateAuditReport, exportAuditReport } from '../../services/compliance';

interface AuditReportGeneratorProps {
  apis: API[];
  gatewayId: string | null;
  onReportGenerated?: () => void;
}

export const AuditReportGenerator: React.FC<AuditReportGeneratorProps> = ({
  apis,
  gatewayId,
  onReportGenerated,
}) => {
  const [reportType, setReportType] = useState<'comprehensive' | 'standard_specific' | 'api_specific'>('comprehensive');
  const [selectedStandards, setSelectedStandards] = useState<ComplianceStandard[]>([]);
  const [selectedApis, setSelectedApis] = useState<string[]>([]);
  const [periodStart, setPeriodStart] = useState<string>('');
  const [periodEnd, setPeriodEnd] = useState<string>('');
  const [includeResolved, setIncludeResolved] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedReport, setGeneratedReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const allStandards: ComplianceStandard[] = ['GDPR', 'HIPAA', 'SOC2', 'PCI_DSS', 'ISO_27001'];

  const handleStandardToggle = (standard: ComplianceStandard) => {
    setSelectedStandards(prev =>
      prev.includes(standard)
        ? prev.filter(s => s !== standard)
        : [...prev, standard]
    );
  };

  const handleApiToggle = (apiId: string) => {
    setSelectedApis(prev =>
      prev.includes(apiId)
        ? prev.filter(id => id !== apiId)
        : [...prev, apiId]
    );
  };

  const handleGenerateReport = async () => {
    if (!gatewayId) {
      setError('Please select a gateway first');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGeneratedReport(null);

    try {
      // Backend now supports multiple API IDs and standards
      const response = await generateAuditReport({
        gateway_id: gatewayId,
        api_ids: selectedApis.length > 0 ? selectedApis : undefined,
        standards: selectedStandards.length > 0 ? selectedStandards : undefined,
        start_date: periodStart || undefined,
        end_date: periodEnd || undefined,
      });

      // Backend returns the report directly, not wrapped in a 'report' field
      setGeneratedReport(response as any);
      
      if (onReportGenerated) {
        onReportGenerated();
      }
    } catch (err) {
      setError(`Failed to generate report: ${err}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportReport = async (format: 'json' | 'pdf' | 'html') => {
    if (!generatedReport || !gatewayId) return;

    try {
      const blob = await exportAuditReport(gatewayId, generatedReport.report_id, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-report-${generatedReport.report_id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      // Check if it's a PDF not implemented error
      if (err.response?.status === 501) {
        setError('PDF export is not yet implemented. Please use HTML or JSON export instead.');
      } else {
        setError(`Failed to export report: ${err.message || err}`);
      }
    }
  };

  // Set default date range (last 30 days)
  React.useEffect(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    
    setPeriodEnd(end.toISOString().split('T')[0]);
    setPeriodStart(start.toISOString().split('T')[0]);
  }, []);

  return (
    <div className="space-y-6">
      {/* Report Configuration */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Generate Audit Report</h2>

        {/* Report Type */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Report Type
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => setReportType('comprehensive')}
              className={`p-4 rounded-lg border-2 transition-all ${
                reportType === 'comprehensive'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-semibold text-gray-900 mb-1">Comprehensive</div>
              <div className="text-sm text-gray-600">All standards and APIs</div>
            </button>
            <button
              onClick={() => setReportType('standard_specific')}
              className={`p-4 rounded-lg border-2 transition-all ${
                reportType === 'standard_specific'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-semibold text-gray-900 mb-1">Standard Specific</div>
              <div className="text-sm text-gray-600">Select specific standards</div>
            </button>
            <button
              onClick={() => setReportType('api_specific')}
              className={`p-4 rounded-lg border-2 transition-all ${
                reportType === 'api_specific'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-semibold text-gray-900 mb-1">API Specific</div>
              <div className="text-sm text-gray-600">Select specific APIs</div>
            </button>
          </div>
        </div>

        {/* Standards Selection */}
        {(reportType === 'standard_specific' || reportType === 'comprehensive') && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Compliance Standards {reportType === 'standard_specific' && '(Required)'}
            </label>
            <div className="flex flex-wrap gap-2">
              {allStandards.map(standard => (
                <button
                  key={standard}
                  onClick={() => handleStandardToggle(standard)}
                  className={`px-4 py-2 rounded-lg border-2 transition-all ${
                    selectedStandards.includes(standard)
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {standard.replace('_', '-')}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* API Selection */}
        {(reportType === 'api_specific' || reportType === 'comprehensive') && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              APIs {reportType === 'api_specific' && '(Required)'}
            </label>
            <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg p-3">
              <div className="space-y-2">
                {apis.map(api => (
                  <label key={api.id} className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                    <input
                      type="checkbox"
                      checked={selectedApis.includes(api.id)}
                      onChange={() => handleApiToggle(api.id)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{api.name}</span>
                    <span className="text-xs text-gray-500">({api.base_path})</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Date Range */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Report Period
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Start Date</label>
              <input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">End Date</label>
              <input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Options */}
        <div className="mb-6">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeResolved}
              onChange={(e) => setIncludeResolved(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Include resolved violations</span>
          </label>
        </div>

        {/* Generate Button */}
        <div className="flex gap-4">
          <button
            onClick={handleGenerateReport}
            disabled={isGenerating || 
              (reportType === 'standard_specific' && selectedStandards.length === 0) ||
              (reportType === 'api_specific' && selectedApis.length === 0)}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isGenerating ? 'Generating Report...' : 'Generate Report'}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}
      </div>

      {/* Generated Report Display */}
      {generatedReport && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Audit Report</h2>
              <p className="text-sm text-gray-600">
                Generated on {new Date(generatedReport.generated_at).toLocaleString()}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExportReport('pdf')}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
              >
                Export PDF
              </button>
              <button
                onClick={() => handleExportReport('html')}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
              >
                Export HTML
              </button>
              <button
                onClick={() => handleExportReport('json')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
              >
                Export JSON
              </button>
            </div>
          </div>

          {/* Report Metadata */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600 mb-1">Report ID</div>
                <div className="font-medium text-gray-900">
                  {generatedReport.report_id}
                </div>
              </div>
              <div>
                <div className="text-gray-600 mb-1">Period</div>
                <div className="font-medium text-gray-900">
                  {new Date(generatedReport.report_period.start).toLocaleDateString()} -{' '}
                  {new Date(generatedReport.report_period.end).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>

          {/* Compliance Posture */}
          <div className="mb-6 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Compliance Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-gray-600 mb-1">Total Violations</div>
                <div className="text-2xl font-bold text-gray-900">
                  {generatedReport.compliance_posture?.total_violations || 0}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Open</div>
                <div className="text-2xl font-bold text-orange-600">
                  {generatedReport.compliance_posture?.open_violations || 0}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Remediated</div>
                <div className="text-2xl font-bold text-green-600">
                  {generatedReport.remediation_status?.remediated_violations || 0}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Remediation Rate</div>
                <div className="text-2xl font-bold text-blue-600">
                  {generatedReport.remediation_status?.remediation_rate?.toFixed(1) || 0}%
                </div>
              </div>
            </div>
          </div>

          {/* Executive Summary */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Executive Summary</h3>
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {generatedReport.executive_summary}
              </p>
            </div>
          </div>

          {/* Violations Summary */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Violations by Severity</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                <div className="text-sm text-red-700 mb-1">Critical</div>
                <div className="text-2xl font-bold text-red-900">
                  {generatedReport.violations_by_severity?.critical || 0}
                </div>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                <div className="text-sm text-orange-700 mb-1">High</div>
                <div className="text-2xl font-bold text-orange-900">
                  {generatedReport.violations_by_severity?.high || 0}
                </div>
              </div>
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="text-sm text-yellow-700 mb-1">Medium</div>
                <div className="text-2xl font-bold text-yellow-900">
                  {generatedReport.violations_by_severity?.medium || 0}
                </div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm text-blue-700 mb-1">Low</div>
                <div className="text-2xl font-bold text-blue-900">
                  {generatedReport.violations_by_severity?.low || 0}
                </div>
              </div>
            </div>
          </div>

          {/* Violations by Standard */}
          {generatedReport.violations_by_standard && Object.keys(generatedReport.violations_by_standard).length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Violations by Standard</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(generatedReport.violations_by_standard).map(([standard, count]) => (
                  <div key={standard} className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="text-sm text-blue-700 mb-1">{standard.replace('_', '-')}</div>
                    <div className="text-2xl font-bold text-blue-900">{count}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {generatedReport.recommendations && generatedReport.recommendations.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Recommendations</h3>
              <div className="space-y-2">
                {generatedReport.recommendations.map((recommendation, index) => (
                  <div key={index} className="p-4 bg-green-50 rounded-lg border border-green-200">
                    <div className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-green-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                        {index + 1}
                      </span>
                      <p className="text-sm text-gray-700 flex-1">{recommendation}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detailed Violations */}
          {(generatedReport as any).detailed_violations && (generatedReport as any).detailed_violations.length > 0 && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Detailed Violations (Showing {(generatedReport as any).detailed_violations.length})
              </h3>
              <div className="space-y-3">
                {(generatedReport as any).detailed_violations.map((violation: any, index: number) => (
                  <div key={violation.id || index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                          violation.severity === 'critical' ? 'bg-red-100 text-red-800' :
                          violation.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                          violation.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {violation.severity?.toUpperCase()}
                        </span>
                        <span className="ml-2 inline-block px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800">
                          {violation.compliance_standard?.toUpperCase()}
                        </span>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        violation.status === 'open' ? 'bg-red-100 text-red-800' :
                        violation.status === 'resolved' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {violation.status?.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                    <h4 className="font-medium text-gray-900 mb-1">{violation.violation_type?.replace(/_/g, ' ')}</h4>
                    <p className="text-sm text-gray-600 mb-2">{violation.description}</p>
                    <div className="text-xs text-gray-500">
                      API ID: {violation.api_id} | Detected: {new Date(violation.detected_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Made with Bob