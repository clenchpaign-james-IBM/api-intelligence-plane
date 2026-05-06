import type { Vulnerability } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const securityService = {
  /**
   * Get security summary for dashboard (gateway-scoped)
   */
  async getSummary(params?: {
    gateway_id?: string;
  }): Promise<{
    total_vulnerabilities: number;
    critical_vulnerabilities: number;
    high_vulnerabilities: number;
    medium_vulnerabilities: number;
    low_vulnerabilities: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.gateway_id) queryParams.append('gateway_id', params.gateway_id);
    
    const url = `${API_BASE_URL}/api/v1/security/summary${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch security summary: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Get vulnerabilities with optional filters (gateway-scoped)
   */
  async getVulnerabilities(params?: {
    api_id?: string;
    gateway_id?: string;
    status?: string;
    severity?: string;
    limit?: number;
  }): Promise<Vulnerability[]> {
    const queryParams = new URLSearchParams();
    if (params?.api_id) queryParams.append('api_id', params.api_id);
    if (params?.gateway_id) queryParams.append('gateway_id', params.gateway_id);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.severity) queryParams.append('severity', params.severity);
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const url = `${API_BASE_URL}/api/v1/security/vulnerabilities${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch vulnerabilities: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Get security posture (gateway-scoped)
   */
  async getSecurityPosture(params?: {
    gateway_id?: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.gateway_id) queryParams.append('gateway_id', params.gateway_id);
    
    const url = `${API_BASE_URL}/api/v1/security/posture${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch security posture: ${response.statusText}`);
    }

    return response.json();
  },
};

// Export for backward compatibility
export const getVulnerabilities = securityService.getVulnerabilities;
export const getSecurityPosture = securityService.getSecurityPosture;

/**
 * Get color class for vulnerability severity
 */
export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'text-red-600 bg-red-100';
    case 'high':
      return 'text-orange-600 bg-orange-100';
    case 'medium':
      return 'text-yellow-600 bg-yellow-100';
    case 'low':
      return 'text-blue-600 bg-blue-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

/**
 * Get color class for risk level
 */
export function getRiskLevelColor(riskLevel: string): string {
  const colors: Record<string, string> = {
    low: 'text-green-600',
    medium: 'text-yellow-600',
    high: 'text-orange-600',
    critical: 'text-red-600',
  };
  return colors[riskLevel] || 'text-gray-600';
}

/**
 * Get color class for vulnerability status
 */
export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'open':
      return 'text-red-600 bg-red-100';
    case 'in_progress':
      return 'text-yellow-600 bg-yellow-100';
    case 'resolved':
      return 'text-green-600 bg-green-100';
    case 'false_positive':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

/**
 * Preview remediation policy for a vulnerability
 */
export async function previewRemediation(
  gatewayId: string,
  vulnerabilityId: string
): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/gateways/${gatewayId}/security/vulnerabilities/${vulnerabilityId}/preview-remediation`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to preview remediation: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Remediate a vulnerability with optional overrides
 */
export async function remediateVulnerability(
  gatewayId: string,
  vulnerabilityId: string,
  options?: {
    strategy?: string;
    override_config?: Record<string, any>;
    manual_analysis?: {
      reason?: string;
      risk_acknowledgement?: string;
      reviewed_by?: string;
    };
  }
): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/gateways/${gatewayId}/security/vulnerabilities/${vulnerabilityId}/remediate`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      remediation_strategy: options?.strategy,
      override_config: options?.override_config,
      manual_analysis: options?.manual_analysis,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to remediate vulnerability: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Verify remediation of a vulnerability
 */
export async function verifyRemediation(gatewayId: string, vulnerabilityId: string): Promise<any> {
  const url = `${API_BASE_URL}/api/v1/gateways/${gatewayId}/security/vulnerabilities/${vulnerabilityId}/verify`;
  const response = await fetch(url, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error(`Failed to verify remediation: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Made with Bob
