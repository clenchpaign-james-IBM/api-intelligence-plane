/**
 * Compliance Service Client
 * 
 * Handles all compliance-related API calls to the backend.
 */

import apiClient from './api';
import type {
  ComplianceViolation,
  ComplianceViolationListResponse,
  ComplianceScanRequest,
  ComplianceScanResponse,
  CompliancePosture,
  AuditReportRequest,
  AuditReportResponse,
  ComplianceStandard,
  ComplianceSeverity,
  ComplianceStatus,
} from '../types';

/**
 * Scan an API for compliance violations
 */
export const scanAPICompliance = async (
  request: ComplianceScanRequest
): Promise<ComplianceScanResponse> => {
  const response = await apiClient.post('/api/v1/compliance/scan', request);
  return response.data;
};

/**
 * Get all compliance violations with optional filters (gateway-scoped)
 */
export const getComplianceViolations = async (params: {
  api_id?: string;
  gateway_id: string;
  standard?: ComplianceStandard;
  severity?: ComplianceSeverity;
  status?: ComplianceStatus;
  skip?: number;
  limit?: number;
}): Promise<ComplianceViolationListResponse> => {

  // Build query params (excluding gateway_id as it's in the path)
  const queryParams: any = {};
  if (params.api_id) queryParams.api_id = params.api_id;
  if (params.standard) queryParams.standard = params.standard;
  if (params.severity) queryParams.severity = params.severity;
  if (params.status) queryParams.status = params.status;
  if (params.limit) queryParams.limit = params.limit;

  const response = await apiClient.get(
    `/api/v1/gateways/${params.gateway_id}/compliance/violations`,
    { params: queryParams }
  );
  
  console.log('[compliance.ts] Raw axios response:', {
    hasData: !!response.data,
    dataType: typeof response.data,
    isArray: Array.isArray(response.data),
    length: Array.isArray(response.data) ? response.data.length : 'N/A',
    firstItem: Array.isArray(response.data) && response.data.length > 0 ? response.data[0] : null,
    fullResponse: response
  });
  
  // Backend returns array directly in response.data
  // React Query may have already unwrapped this, so check both
  const rawData = response.data || response;
  const violations = Array.isArray(rawData) ? rawData : [];
  
  console.log('[compliance.ts] Wrapped violations:', {
    count: violations.length,
    firstViolation: violations[0],
    rawDataType: typeof rawData,
    rawDataIsArray: Array.isArray(rawData)
  });
  
  return {
    violations,
    total: violations.length,
    page: 1,
    page_size: violations.length,
    filters_applied: {
      standard: params?.standard,
      severity: params?.severity,
      status: params?.status,
      api_id: params?.api_id,
    },
  };
};

/**
 * Get a specific compliance violation by ID
 */
export const getComplianceViolation = async (
  violationId: string
): Promise<ComplianceViolation> => {
  const response = await apiClient.get(`/compliance/violations/${violationId}`);
  return response.data;
};

/**
 * Get compliance posture (overall compliance metrics) (gateway-scoped)
 */
export const getCompliancePosture = async (params: {
  api_id?: string;
  gateway_id: string;
  standard?: ComplianceStandard;
}): Promise<CompliancePosture> => {
  try {
    // Build query params (excluding gateway_id as it's in the path)
    const queryParams: any = {};
    if (params.api_id) queryParams.api_id = params.api_id;
    if (params.standard) queryParams.standard = params.standard;

    const response = await apiClient.get(
      `/api/v1/gateways/${params.gateway_id}/compliance/posture`,
      { params: queryParams }
    );
    
    // Handle both wrapped (response.data) and unwrapped (response) formats
    // React Query may unwrap the AxiosResponse before passing to our function
    const data = response.data || response;
    
    // Check if data exists and has expected structure
    if (!data || typeof data !== 'object') {
      console.error('Invalid data in compliance posture response:', data);
      throw new Error('No valid data received from compliance posture endpoint');
    }
    
    // Map backend response to frontend CompliancePosture interface
    const openViolations = data.by_status?.open || 0;
    const resolvedViolations = data.by_status?.resolved || 0;
    const inProgressViolations = data.by_status?.in_progress || 0;
    const acceptedRiskViolations = data.by_status?.accepted_risk || 0;
    const falsePositiveViolations = data.by_status?.false_positive || 0;
    
    // Calculate risk level based on compliance score
    let riskLevel: 'low' | 'medium' | 'high' | 'critical' = 'low';
    if (data.compliance_score < 50) riskLevel = 'critical';
    else if (data.compliance_score < 70) riskLevel = 'high';
    else if (data.compliance_score < 85) riskLevel = 'medium';
    
    // Helper function to calculate score from violations (inverse relationship)
    const calculateScoreFromViolations = (violations: number): number => {
      if (violations === 0) return 100;
      // Score decreases as violations increase
      // Using logarithmic scale: score = 100 - (log(violations + 1) * 20)
      const score = Math.max(0, 100 - (Math.log10(violations + 1) * 20));
      return Math.round(score);
    };
    
    // Map by_standard to ComplianceStandardScore format
    const byStandard: Record<ComplianceStandard, any> = {
      GDPR: {
        standard: 'GDPR',
        score: calculateScoreFromViolations(data.by_standard?.gdpr || 0),
        violations: data.by_standard?.gdpr || 0,
        compliant_controls: 0,
        total_controls: 0,
        last_assessed: new Date().toISOString()
      },
      HIPAA: {
        standard: 'HIPAA',
        score: calculateScoreFromViolations(data.by_standard?.hipaa || 0),
        violations: data.by_standard?.hipaa || 0,
        compliant_controls: 0,
        total_controls: 0,
        last_assessed: new Date().toISOString()
      },
      PCI_DSS: {
        standard: 'PCI_DSS',
        score: calculateScoreFromViolations(data.by_standard?.pci_dss || 0),
        violations: data.by_standard?.pci_dss || 0,
        compliant_controls: 0,
        total_controls: 0,
        last_assessed: new Date().toISOString()
      },
      SOC2: {
        standard: 'SOC2',
        score: calculateScoreFromViolations(data.by_standard?.soc2 || 0),
        violations: data.by_standard?.soc2 || 0,
        compliant_controls: 0,
        total_controls: 0,
        last_assessed: new Date().toISOString()
      },
      ISO_27001: {
        standard: 'ISO_27001',
        score: calculateScoreFromViolations(data.by_standard?.iso_27001 || 0),
        violations: data.by_standard?.iso_27001 || 0,
        compliant_controls: 0,
        total_controls: 0,
        last_assessed: new Date().toISOString()
      },
    };
    
    // Use backend's compliance_score if > 0, otherwise calculate from total violations
    const overallScore = data.compliance_score > 0
      ? data.compliance_score
      : calculateScoreFromViolations(data.total_violations || 0);
    
    return {
      total_violations: data.total_violations || 0,
      open_violations: openViolations,
      resolved_violations: resolvedViolations,
      by_severity: data.by_severity || { critical: 0, high: 0, medium: 0, low: 0 },
      by_standard: byStandard,
      by_status: {
        open: openViolations,
        in_progress: inProgressViolations,
        resolved: resolvedViolations,
        accepted_risk: acceptedRiskViolations,
        false_positive: falsePositiveViolations,
      },
      overall_score: overallScore,
      risk_level: riskLevel,
      last_scan_date: data.last_scan || new Date().toISOString(),
      compliance_trends: [],
    };
  } catch (error) {
    console.error('Failed to fetch compliance posture:', error);
    // Return default empty posture on error
    return getDefaultCompliancePosture();
  }
};

/**
 * Get default empty compliance posture
 */
function getDefaultCompliancePosture(): CompliancePosture {
  const timestamp = new Date().toISOString();
  return {
    total_violations: 0,
    open_violations: 0,
    resolved_violations: 0,
    by_severity: { critical: 0, high: 0, medium: 0, low: 0 },
    by_standard: {
      GDPR: { standard: 'GDPR', score: 100, violations: 0, compliant_controls: 0, total_controls: 0, last_assessed: timestamp },
      HIPAA: { standard: 'HIPAA', score: 100, violations: 0, compliant_controls: 0, total_controls: 0, last_assessed: timestamp },
      PCI_DSS: { standard: 'PCI_DSS', score: 100, violations: 0, compliant_controls: 0, total_controls: 0, last_assessed: timestamp },
      SOC2: { standard: 'SOC2', score: 100, violations: 0, compliant_controls: 0, total_controls: 0, last_assessed: timestamp },
      ISO_27001: { standard: 'ISO_27001', score: 100, violations: 0, compliant_controls: 0, total_controls: 0, last_assessed: timestamp },
    },
    by_status: {
      open: 0,
      in_progress: 0,
      resolved: 0,
      accepted_risk: 0,
      false_positive: 0
    },
    overall_score: 100.0,
    risk_level: 'low',
    last_scan_date: timestamp,
    compliance_trends: [],
  };
}

/**
 * Generate an audit report (gateway-scoped)
 */
export const generateAuditReport = async (
  request: AuditReportRequest
): Promise<AuditReportResponse> => {
  try {
    // Extract gateway_id from request and use it in the path
    if (!request.gateway_id) {
      throw new Error('gateway_id is required for audit report generation');
    }
    
    // Remove gateway_id from request body since it's only needed in the path
    const { gateway_id, ...requestBody } = request;
    
    // Convert standards to lowercase to match backend enum values
    const normalizedBody = {
      ...requestBody,
      standards: requestBody.standards?.map(s => s.toLowerCase()),
    };
    
    const response = await apiClient.post(
      `/api/v1/gateways/${gateway_id}/compliance/reports/audit`,
      normalizedBody
    );
    // Handle both wrapped (response.data) and unwrapped (response) formats
    const data = response.data || response;
    return data;
  } catch (error: any) {
    console.error('Failed to generate audit report:', error);
    throw new Error(error.response?.data?.detail || error.message || 'Failed to generate audit report');
  }
};

/**
 * Update compliance violation status
 */
export const updateViolationStatus = async (
  violationId: string,
  status: ComplianceStatus,
  notes?: string
): Promise<ComplianceViolation> => {
  const response = await apiClient.patch(`/compliance/violations/${violationId}`, {
    status,
    notes,
  });
  return response.data;
};

/**
 * Mark violation as false positive
 */
export const markAsFalsePositive = async (
  violationId: string,
  reason: string
): Promise<ComplianceViolation> => {
  return updateViolationStatus(violationId, 'false_positive', reason);
};

/**
 * Accept risk for a violation
 */
export const acceptRisk = async (
  violationId: string,
  justification: string
): Promise<ComplianceViolation> => {
  return updateViolationStatus(violationId, 'accepted_risk', justification);
};

/**
 * Resolve a violation
 */
export const resolveViolation = async (
  violationId: string,
  resolution_notes: string
): Promise<ComplianceViolation> => {
  return updateViolationStatus(violationId, 'resolved', resolution_notes);
};

/**
 * Export audit report in specified format
 */
export const exportAuditReport = async (
  gatewayId: string,
  reportId: string,
  format: 'pdf' | 'json' | 'html' = 'json'
): Promise<Blob> => {
  try {
    console.log('[exportAuditReport] Requesting:', { gatewayId, reportId, format });
    
    // Use raw axios to bypass any interceptor issues
    const axios = (await import('axios')).default;
    const baseURL = import.meta.env.VITE_API_BASE_URL || '';
    
    const response = await axios.get(
      `${baseURL}/api/v1/gateways/${gatewayId}/compliance/reports/audit/${reportId}/export`,
      {
        params: { format },
        responseType: format === 'html' ? 'text' : 'json',
        headers: {
          'Accept': format === 'html' ? 'text/html' : 'application/json',
        },
      }
    );
    
    console.log('[exportAuditReport] Raw axios response:', {
      status: response.status,
      statusText: response.statusText,
      dataType: typeof response.data,
      isObject: typeof response.data === 'object',
      isString: typeof response.data === 'string',
      isBlob: response.data instanceof Blob,
      hasHeaders: !!response.headers,
      contentType: response.headers ? response.headers['content-type'] : 'no headers',
      dataKeys: response.data && typeof response.data === 'object' ? Object.keys(response.data) : 'N/A',
      dataLength: response.data ? (typeof response.data === 'string' ? response.data.length : JSON.stringify(response.data).length) : 0,
      dataPreview: response.data ? (typeof response.data === 'string' ? response.data.substring(0, 200) : JSON.stringify(response.data).substring(0, 200)) : 'no data',
    });
    
    // Validate response data
    if (!response.data) {
      console.error('[exportAuditReport] Response data is null or undefined');
      throw new Error('Received empty response from server');
    }
    
    // For JSON format, return as-is
    if (format === 'json') {
      const jsonStr = JSON.stringify(response.data, null, 2);
      return new Blob([jsonStr], { type: 'application/json' });
    }
    
    // For HTML/PDF, backend returns it as a JSON response
    // The actual HTML/PDF content should be in response.data directly as a string
    // OR it might be wrapped in an object
    let content: string;
    
    if (typeof response.data === 'string') {
      // Direct string response
      content = response.data;
    } else if (typeof response.data === 'object') {
      // Backend might wrap it in an object - try common keys
      if ('content' in response.data) {
        content = response.data.content;
      } else if ('html' in response.data) {
        content = response.data.html;
      } else if ('data' in response.data) {
        content = response.data.data;
      } else {
        // Last resort: stringify the whole object
        console.warn('[exportAuditReport] Unexpected object structure, stringifying:', response.data);
        content = JSON.stringify(response.data, null, 2);
      }
    } else {
      console.error('[exportAuditReport] Unexpected response type:', typeof response.data);
      throw new Error(`Invalid response type: ${typeof response.data}`);
    }
    
    if (!content || content.length === 0) {
      console.error('[exportAuditReport] Empty content after extraction');
      throw new Error('Received empty report content from server');
    }
    
    // Convert HTML/PDF content to Blob
    const contentType = format === 'html' ? 'text/html; charset=utf-8' : 'application/pdf';
    console.log('[exportAuditReport] Creating blob:', {
      contentLength: content.length,
      contentType,
      contentPreview: content.substring(0, 100),
    });
    
    return new Blob([content], { type: contentType });
  } catch (error: any) {
    console.error('[exportAuditReport] Failed to export audit report:', error);
    console.error('[exportAuditReport] Error details:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    });
    throw new Error(error.response?.data?.detail || error.message || 'Failed to export audit report');
  }
};

// Made with Bob
