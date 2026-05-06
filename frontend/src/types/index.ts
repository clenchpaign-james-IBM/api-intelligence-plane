/**
 * TypeScript type definitions for API Intelligence Plane frontend.
 * 
 * These types match the backend data models and API responses.
 */

// API Entity (Vendor-Neutral)
export interface API {
  id: string;
  gateway_id: string;
  name: string;
  display_name?: string;
  description?: string;
  icon?: string;
  version?: string;
  version_info?: VersionInfo;
  type?: APIType;
  maturity_state?: MaturityState;
  groups?: string[];
  base_path: string;
  endpoints: Endpoint[];
  methods: string[];
  authentication_type: AuthenticationType;
  authentication_config?: Record<string, any>;
  ownership?: Ownership;
  publishing?: PublishingInfo;
  deployments?: DeploymentInfo[];
  tags?: string[];

  // Vendor-neutral policy actions
  policy_actions?: PolicyAction[];

  // Intelligence metadata (AI-derived fields)
  intelligence_metadata: IntelligenceMetadata;

  // OpenAPI definition
  api_definition?: APIDefinition;

  // Vendor-specific metadata
  vendor_metadata?: Record<string, any>;

  status: APIStatus;
  is_active?: boolean;

  // Timestamps
  created_at: string;
  updated_at: string;
}

// Intelligence Metadata (AI-derived fields)
export interface IntelligenceMetadata {
  is_shadow: boolean;
  discovery_method: DiscoveryMethod;
  discovered_at: string;
  last_seen_at: string;
  health_score: number;
  risk_score?: number;
  security_score?: number;
  compliance_status?: Record<string, boolean>;
  violation_count?: number;
  usage_trend?: string;
  has_active_predictions?: boolean;
}

// Policy Action (Vendor-Neutral)
export interface PolicyAction {
  action_type: PolicyActionType;
  enabled: boolean;
  stage?: string;
  config?: Record<string, any>;
  vendor_config?: Record<string, any>;
  name?: string;
  description?: string;
}

export type PolicyActionType =
  | 'authentication'
  | 'authorization'
  | 'rate_limiting'
  | 'caching'
  | 'logging'
  | 'validation'
  | 'transformation'
  | 'cors'
  | 'data_masking'
  | 'compression'
  | 'tls'
  | 'custom';

// OpenAPI Definition
export interface APIDefinition {
  type: string;
  version?: string;
  openapi_spec?: Record<string, any>;
  swagger_version?: string;
  base_path: string;
  paths?: Record<string, any>;
  schemas?: Record<string, any>;
  security_schemes?: Record<string, any>;
  vendor_extensions?: Record<string, any>;
}

export interface SecurityPolicies {
  authentication_required: boolean;
  authorization_enabled: boolean;
  rate_limiting_enabled: boolean;
  rate_limit_config?: {
    requests_per_minute: number;
    burst_size: number;
  };
  tls_enforced: boolean;
  tls_version?: string;
  cors_enabled: boolean;
  cors_config?: {
    allowed_origins: string[];
    allowed_methods: string[];
    allow_credentials: boolean;
  };
  input_validation_enabled: boolean;
  output_sanitization_enabled: boolean;
  logging_enabled: boolean;
  encryption_at_rest: boolean;
  waf_enabled: boolean;
  ip_whitelisting_enabled: boolean;
  allowed_ips?: string[];
  api_key_rotation_enabled: boolean;
  key_rotation_days?: number;
  compliance_standards?: string[];
  last_policy_update?: string;
}

export interface Endpoint {
  path: string;
  method: string;
  description?: string;
  parameters?: Parameter[];
  response_codes?: number[];
}

export interface Parameter {
  name: string;
  type: 'path' | 'query' | 'header' | 'body';
  data_type: string;
  required: boolean;
}

export interface Ownership {
  team?: string;
  contact?: string;
  repository?: string;
  organization?: string;
  department?: string;
}

export interface VersionInfo {
  current_version: string;
  previous_version?: string;
  next_version?: string;
  system_version: number;
  version_history?: string[];
}

export interface PublishingInfo {
  published_portals?: string[];
  published_to_registry?: boolean;
  catalog_name?: string;
  catalog_id?: string;
}

export interface DeploymentInfo {
  environment: string;
  gateway_endpoints: Record<string, string>;
  deployed_at?: string;
  deployment_status?: string;
}

// Removed CurrentMetrics - metrics are now fetched separately with time buckets

export type AuthenticationType =
  | 'none'
  | 'basic'
  | 'bearer'
  | 'oauth2'
  | 'api_key'
  | 'mtls'
  | 'custom';
export type DiscoveryMethod =
  | 'registered'
  | 'traffic_analysis'
  | 'log_analysis'
  | 'gateway_sync';
export type APIStatus = 'active' | 'inactive' | 'deprecated' | 'failed';
export type APIType = 'REST' | 'SOAP' | 'GRAPHQL' | 'WEBSOCKET' | 'GRPC' | 'ODATA';
export type MaturityState = 'Beta' | 'Test' | 'Productive' | 'Deprecated' | 'Retired';

// Gateway Entity
export interface Gateway {
  id: string;
  name: string;
  vendor: GatewayVendor;
  version?: string;
  base_url: string;
  transactional_logs_url?: string;
  connection_type: ConnectionType;
  base_url_credentials?: GatewayCredentials;
  transactional_logs_credentials?: GatewayCredentials;
  capabilities: string[];
  status: GatewayStatus;
  last_connected_at?: string;
  last_error?: string;
  api_count: number;
  metrics_enabled: boolean;
  security_scanning_enabled: boolean;
  rate_limiting_enabled: boolean;
  configuration?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface GatewayCredentials {
  type: string;
  api_key?: string;
  username?: string;
  password?: string;
  token?: string;
  [key: string]: any;
}

export type GatewayVendor = 'native' | 'webmethods' | 'kong' | 'apigee' | 'aws' | 'azure' | 'custom';

// Query Entity
export interface Query {
  id: string;
  session_id: string;
  user_id?: string;
  query_text: string;
  query_type: NLQueryType;
  interpreted_intent: InterpretedIntent;
  opensearch_query?: Record<string, any>;
  results: QueryResults;
  response_text: string;
  confidence_score: number;
  execution_time_ms: number;
  feedback?: UserFeedback;
  feedback_comment?: string;
  follow_up_queries?: string[];
  metadata?: Record<string, any>;
  created_at: string;
}

export interface InterpretedIntent {
  action: string;
  entities: string[];
  filters: Record<string, any>;
  time_range?: TimeRange;
}

export interface TimeRange {
  start: string;
  end: string;
}

export interface QueryResults {
  data: any[];
  count: number;
  execution_time: number;
  aggregations?: Record<string, any>;
}

export type NLQueryType = 'status' | 'trend' | 'prediction' | 'security' | 'performance' | 'comparison' | 'general';
export type UserFeedback = 'helpful' | 'not_helpful' | 'partially_helpful';

// Query Request/Response
export interface QueryRequest {
  query_text: string;
  session_id?: string;
}

export interface QueryResponse {
  query_id: string;
  query_text: string;
  response_text: string;
  confidence_score: number;
  results: Record<string, any>;
  follow_up_queries?: string[];
  execution_time_ms: number;
}

export interface FeedbackRequest {
  feedback: UserFeedback;
  comment?: string;
}
export type ConnectionType = 'rest_api' | 'grpc' | 'graphql';
export type GatewayStatus = 'connected' | 'disconnected' | 'error' | 'maintenance';

// Metric Entity (Time-Bucketed)
export interface Metric {
  id: string;
  api_id: string;
  gateway_id: string;
  application_id?: string;
  timestamp: string;
  time_bucket: TimeBucket;
  
  // Request counts
  request_count: number;
  success_count: number;
  failure_count: number;
  
  // Response times
  response_time_avg: number;
  response_time_p50: number;
  response_time_p95: number;
  response_time_p99: number;
  response_time_min: number;
  response_time_max: number;
  
  // Timing breakdown
  gateway_time_avg: number;
  backend_time_avg: number;
  
  // Cache metrics
  cache_hit_rate: number;
  cache_hit_count: number;
  cache_miss_count: number;
  cache_bypass_count: number;
  
  // Data transfer
  total_data_size: number;
  avg_request_size: number;
  avg_response_size: number;
  
  // HTTP status codes
  status_2xx_count: number;
  status_3xx_count: number;
  status_4xx_count: number;
  status_5xx_count: number;
  
  // Per-endpoint breakdown
  endpoint_metrics?: EndpointMetric[];
  
  timeout_count: number;
  throughput: number;
  status_codes: Record<string, number>;

  // Metadata
  vendor_metadata?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export type TimeBucket = '1m' | '5m' | '1h' | '1d';

export interface ExternalCall {
  call_type: 'http' | 'database' | 'cache' | 'messaging' | 'other';
  target_service: string;
  target_endpoint?: string;
  duration_ms: number;
  status_code?: number;
  success: boolean;
  error_message?: string;
}

export interface TransactionalLog {
  id: string;
  gateway_id: string;
  api_id: string;
  application_id?: string;
  transaction_id?: string;
  correlation_id?: string;
  request_id?: string;
  timestamp: string;
  event_type: string;
  event_status: string;
  method?: string;
  path?: string;
  resource_path?: string;
  operation_name?: string;
  consumer_id?: string;
  consumer_name?: string;
  status_code?: number;
  backend_status_code?: number;
  latency_ms?: number;
  backend_latency_ms?: number;
  total_time_ms?: number;
  request_size_bytes?: number;
  response_size_bytes?: number;
  cache_status?: string;
  error_origin?: string;
  error_message?: string;
  client_ip?: string;
  protocol?: string;
  host?: string;
  user_agent?: string;
  region?: string;
  environment?: string;
  tags?: string[];
  external_calls?: ExternalCall[];
  metadata?: Record<string, any>;
}

export interface EndpointMetric {
  endpoint: string;
  method: string;
  response_time_p50: number;
  response_time_p95: number;
  response_time_p99: number;
  error_rate: number;
  request_count: number;
}

// Prediction Entity
export interface Prediction {
  id: string;
  api_id: string;
  api_name?: string;
  prediction_type: PredictionType;
  predicted_at: string;
  predicted_time: string;
  confidence_score: number;
  severity: PredictionSeverity;
  status: PredictionStatus;
  description?: string;
  contributing_factors: ContributingFactor[];
  recommended_actions: string[];
  actual_outcome?: ActualOutcome;
  actual_time?: string;
  accuracy_score?: number;
  model_version: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ContributingFactor {
  factor: string;
  current_value: number;
  threshold: number;
  trend: string;
  weight: number;
}

export type PredictionType = 'failure' | 'degradation' | 'capacity' | 'security';
export type PredictionSeverity = 'critical' | 'high' | 'medium' | 'low';
export type PredictionStatus = 'active' | 'resolved' | 'false_positive' | 'expired';
export type ActualOutcome = 'occurred' | 'prevented' | 'false_alarm';

// Prediction List Response
export interface PredictionListResponse {
  items: Prediction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Prediction Statistics Response
export interface PredictionStatsResponse {
  total_predictions: number;
  active_predictions: number;
  accuracy_rate: number;
  by_severity: Record<PredictionSeverity, number>;
  by_type: Record<PredictionType, number>;
  by_outcome: Record<ActualOutcome, number>;
}

// Vulnerability Entity
export interface Vulnerability {
  id: string;
  gateway_id: string;
  api_id: string;
  vulnerability_type: VulnerabilityType;
  severity: VulnerabilitySeverity;
  category: VulnerabilityCategory;
  title: string;
  description: string;
  cve_id?: string;
  cvss_score?: number;
  affected_endpoints: string[];
  remediation: string;
  remediation_type?: RemediationType;
  remediation_actions?: RemediationAction[];
  status: VulnerabilityStatus;
  detected_at: string;
  resolved_at?: string;
  remediated_at?: string;
  verification_status?: VerificationStatus;
  metadata?: Record<string, any>;
  
  // Per-vulnerability remediation plan fields (Option B implementation)
  recommended_remediation?: RecommendedRemediation;
  recommended_priority?: string;
  recommended_verification_steps?: string[];
  recommended_estimated_time_hours?: number;
  plan_generated_at?: string;
  plan_source?: 'llm' | 'rule_based' | 'hybrid' | 'manual_override';
  plan_version?: string;
  plan_status?: 'generated' | 'reviewed' | 'approved' | 'superseded' | 'rejected';
  
  created_at: string;
  updated_at: string;
}

// Recommended remediation structure
export interface RecommendedRemediation {
  vulnerability_id: string;
  summary: string;
  actions: RemediationPlanAction[];
  dependencies?: string[];
  rollback_plan?: string;
  priority: string;
  estimated_time_hours: number;
  verification_steps: string[];
}

export interface RemediationPlanAction {
  step: number;
  action: string;
  type: 'configuration' | 'policy' | 'upgrade';
  estimated_minutes: number;
}

export type VulnerabilityType = 'authentication' | 'authorization' | 'injection' | 'data_exposure' | 'configuration' | 'dependency' | 'compliance' | 'data_protection' | 'other';
export type VulnerabilitySeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type VulnerabilityCategory = 'authentication' | 'authorization' | 'injection' | 'data_exposure' | 'configuration' | 'dependency' | 'other';
export type VulnerabilityStatus = 'open' | 'in_progress' | 'remediated' | 'false_positive' | 'accepted_risk';
export type VerificationStatus = 'verified' | 'failed' | 'pending';
export type RemediationType = 'automated' | 'manual' | 'assisted';
export type ComplianceStandard = 'GDPR' | 'HIPAA' | 'PCI_DSS' | 'SOC2' | 'ISO_27001';

export interface RemediationAction {
  action: string;
  type: string;
  status: 'pending' | 'completed' | 'failed';
  performed_at?: string;
  performed_by?: string;
  gateway_policy_id?: string;
  error_message?: string;
  metadata?: {
    override_metadata?: {
      overridden_fields?: string[];
      original_values?: Record<string, any>;
      new_values?: Record<string, any>;
      manual_analysis_notes?: string;
      reviewed_by?: string;
    };
    [key: string]: any;
  };
}

// Security Posture
export interface SecurityPosture {
  total_vulnerabilities: number;
  by_severity: Record<VulnerabilitySeverity, number>;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  remediation_rate: number;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  avg_remediation_time_ms?: number;
  compliance_issues?: ComplianceIssue[];
}

export interface ComplianceIssue {
  standard: ComplianceStandard;
  affected_apis: number;
  severity: VulnerabilitySeverity;
  description: string;
}

// Scan Response
export interface ScanResponse {
  scan_id: string;
  api_id: string;
  api_name: string;
  scan_completed_at: string;
  vulnerabilities_found: number;
  severity_breakdown: Record<VulnerabilitySeverity, number>;
  vulnerabilities: Vulnerability[];
  remediation_plan: Record<string, any>;
  ai_enhanced: boolean;
  compliance_issues?: ComplianceStandard[];
}

// Remediation Response
export interface RemediationResponse {
  vulnerability_id: string;
  status: string;
  remediation_result?: Record<string, any>;
  verification_result?: Record<string, any>;
  message?: string;
}

// Optimization Action Types
export type OptimizationActionType = 'apply_policy' | 'remove_policy' | 'validate' | 'manual_configuration';
export type OptimizationActionStatus = 'completed' | 'pending' | 'failed' | 'in_progress';

// Optimization Action Entity
export interface OptimizationAction {
  action: string;
  type: OptimizationActionType;
  status: OptimizationActionStatus;
  performed_at: string;
  performed_by: string;
  gateway_policy_id?: string;
  error_message?: string;
  metadata?: Record<string, any>;
}

// Validation Results
export interface ActualImpact {
  metric: string;
  before_value: number;
  after_value: number;
  actual_improvement: number;
}

export interface ValidationResults {
  actual_impact: ActualImpact;
  success: boolean;
  measured_at: string;
}

// Recommendation Entity
export interface Recommendation {
  id: string;
  gateway_id: string;
  api_id: string;
  api_name?: string;
  recommendation_type: RecommendationType;
  title: string;
  description: string;
  priority: RecommendationPriority;
  estimated_impact: EstimatedImpact;
  implementation_effort: ImplementationEffort;
  implementation_steps: string[];
  status: RecommendationStatus;
  implemented_at?: string;
  validation_results?: ValidationResults;
  remediation_actions?: OptimizationAction[];
  cost_savings?: number;
  metadata?: Record<string, any>;
  vendor_metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  expires_at?: string;
}

export interface EstimatedImpact {
  metric: string;
  current_value: number;
  expected_value: number;
  improvement_percentage: number;
  confidence: number;
}

export type RecommendationType = 'caching' | 'rate_limiting' | 'compression';
export type RecommendationPriority = 'critical' | 'high' | 'medium' | 'low';
export type RecommendationStatus = 'pending' | 'in_progress' | 'implemented' | 'rejected' | 'expired';
export type ImplementationEffort = 'low' | 'medium' | 'high';

// Recommendation List Response
export interface RecommendationListResponse {
  recommendations: Recommendation[];
  total: number;
  page: number;
  page_size: number;
}

// Recommendation Statistics Response
export interface RecommendationStatsResponse {
  total_recommendations: number;
  by_status: Array<{ status: string; count: number }>;
  by_priority: Array<{ priority: string; count: number }>;
  by_type: Array<{ type: string; count: number }>;
  avg_improvement: number;
  total_cost_savings: number;
}

// Rate Limit Policy Entity
export interface RateLimitPolicy {
  id: string;
  api_id: string;
  api_name?: string;
  policy_name: string;
  policy_type: PolicyType;
  status: PolicyStatus;
  limit_thresholds: LimitThresholds;
  priority_rules?: PriorityRule[];
  burst_allowance?: number;
  adaptation_parameters?: AdaptationParameters;
  consumer_tiers?: ConsumerTier[];
  enforcement_action: EnforcementAction;
  applied_at?: string;
  last_adjusted_at?: string;
  effectiveness_score?: number;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface LimitThresholds {
  requests_per_second?: number;
  requests_per_minute?: number;
  requests_per_hour?: number;
  concurrent_requests?: number;
}

export interface PriorityRule {
  tier: string;
  multiplier: number;
  guaranteed_throughput: number;
  burst_multiplier: number;
}

export interface AdaptationParameters {
  learning_rate: number;
  adjustment_frequency: number;
  min_threshold?: number;
  max_threshold?: number;
}

export interface ConsumerTier {
  tier_name: string;
  tier_level: number;
  rate_multiplier: number;
  priority_score: number;
}

export type PolicyType = 'fixed' | 'adaptive' | 'priority_based' | 'burst_allowance';
export type PolicyStatus = 'active' | 'inactive' | 'testing';
export type EnforcementAction = 'throttle' | 'reject' | 'queue';

// Rate Limit Policy List Response
export interface RateLimitPolicyListResponse {
  policies: RateLimitPolicy[];
  total: number;
  page: number;
  page_size: number;
}

// Rate Limit Effectiveness Response
export interface RateLimitEffectivenessResponse {
  policy_id: string;
  api_id: string;
  effectiveness_score: number;
  metrics: {
    error_rate: number;
    avg_response_time: number;
    throttled_requests: number;
    total_requests: number;
  };
  recommendations: string[];
  analysis_period: {
    start: string;
    end: string;
  };
}

// Rate Limit Suggestion Response
export interface RateLimitSuggestionResponse {
  api_id: string;
  suggested_policy: {
    policy_type: PolicyType;
    limit_thresholds: LimitThresholds;
    enforcement_action: EnforcementAction;
  };
  reasoning: string;
  traffic_analysis: {
    avg_throughput: number;
    peak_throughput: number;
    p95_throughput: number;
    coefficient_of_variation: number;
  };
}

// Query History Entity
export interface QueryHistory {
  id: string;
  query_text: string;
  query_type: QueryType;
  results_count: number;
  execution_time_ms: number;
  status: QueryStatus;
  error_message?: string;
  created_at: string;
}

export type QueryType = 'discovery' | 'metrics' | 'security' | 'recommendations' | 'general';
export type QueryStatus = 'success' | 'error' | 'timeout';

// Dashboard Statistics
export interface DashboardStats {
  total_apis: number;
  active_apis: number;
  shadow_apis: number;
  total_gateways: number;
  active_gateways: number;
  avg_health_score: number;
  avg_response_time: number;
  total_requests_24h: number;
  error_rate_24h: number;
  critical_vulnerabilities: number;
  high_priority_recommendations: number;
}

// Generic Paginated Response
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip?: number;
  limit?: number;
}

// API List Response
export interface APIListResponse {
  items: API[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Gateway List Response
export interface GatewayListResponse {
  items: Gateway[];
  total: number;
}

// Metrics Response (Time-Bucketed)
export interface MetricsResponse {
  api_id: string;
  time_bucket: TimeBucket;
  time_series: TimeSeriesDataPoint[];
  aggregated: AggregatedMetrics;
  cache_metrics: CacheMetrics;
  timing_breakdown: TimingBreakdown;
  status_breakdown: StatusBreakdown;
  total_data_points: number;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  time_bucket?: TimeBucket;
  request_count: number;
  success_count: number;
  failure_count: number;
  response_time_avg: number;
  response_time_p50: number;
  response_time_p95: number;
  response_time_p99: number;
  cache_hit_rate?: number;
  gateway_time_avg?: number;
  backend_time_avg?: number;
  throughput?: number;
  status_4xx_count?: number;
  status_5xx_count?: number;
}

export interface AggregatedMetrics {
  total_requests: number;
  success_rate: number;
  failure_rate: number;
  avg_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
}

export interface CacheMetrics {
  avg_hit_rate: number;
  total_hits: number;
  total_misses: number;
  total_bypasses: number;
}

export interface TimingBreakdown {
  avg_gateway_time: number;
  avg_backend_time: number;
  gateway_overhead_pct: number;
}

export interface StatusBreakdown {
  '2xx': number;
  '3xx': number;
  '4xx': number;
  '5xx': number;
}

// Legacy - kept for backward compatibility during migration
export interface MetricsTimeSeriesResponse {
  api_id: string;
  start: string;
  end: string;
  interval_minutes: number;
  data_points: number;
  metrics: TimeSeriesDataPoint[];
}

// Compliance Violation Entity
export interface ComplianceViolation {
  id: string;
  api_id: string;
  api_name?: string;
  gateway_id: string;
  compliance_standard: ComplianceStandard;
  violation_type: ComplianceViolationType;
  severity: ComplianceSeverity;
  status: ComplianceStatus;
  title: string;
  description: string;
  regulation_reference?: string;
  regulatory_reference?: string;
  affected_endpoints?: string[];
  evidence: ComplianceEvidence[];
  remediation_steps?: string[];
  remediation_documentation?: RemediationDocumentation;
  detected_at: string;
  detection_method: DetectionMethod;
  resolved_at?: string;
  remediated_at?: string;
  last_audit_date?: string;
  next_audit_date?: string;
  audit_trail: AuditTrailEntry[];
  risk_score?: number;
  risk_level?: string;
  business_impact?: string;
  data?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ComplianceEvidence {
  type: string;
  description: string;
  source: string;
  collected_at: string;
  data: Record<string, any>;
}

export interface RemediationDocumentation {
  steps_taken: string[];
  verification_method: string;
  verification_result: string;
  documented_by: string;
  documented_at: string;
}

export interface AuditTrailEntry {
  timestamp: string;
  action: string;
  performed_by: string;
  details: Record<string, any>;
}

export type ComplianceViolationType =
  // GDPR
  | 'gdpr_data_protection'
  | 'gdpr_consent_management'
  | 'gdpr_data_breach_notification'
  | 'gdpr_right_to_erasure'
  | 'gdpr_data_portability'
  // HIPAA
  | 'hipaa_access_control'
  | 'hipaa_audit_controls'
  | 'hipaa_transmission_security'
  | 'hipaa_authentication'
  | 'hipaa_encryption'
  // SOC2
  | 'soc2_access_control'
  | 'soc2_change_management'
  | 'soc2_system_monitoring'
  | 'soc2_logical_access'
  | 'soc2_encryption'
  // PCI-DSS
  | 'pci_dss_network_security'
  | 'pci_dss_access_control'
  | 'pci_dss_encryption'
  | 'pci_dss_monitoring'
  | 'pci_dss_vulnerability_management'
  // ISO 27001
  | 'iso27001_access_control'
  | 'iso27001_cryptography'
  | 'iso27001_operations_security'
  | 'iso27001_communications_security'
  | 'iso27001_system_acquisition';

export type ComplianceSeverity = 'critical' | 'high' | 'medium' | 'low';
export type ComplianceStatus = 'open' | 'in_progress' | 'resolved' | 'accepted_risk' | 'false_positive';
export type DetectionMethod = 'automated' | 'manual' | 'ai_enhanced';

// Compliance Posture
export interface CompliancePosture {
  total_violations: number;
  open_violations: number;
  resolved_violations: number;
  by_standard: Record<ComplianceStandard, ComplianceStandardScore>;
  by_severity: Record<ComplianceSeverity, number>;
  by_status: Record<ComplianceStatus, number>;
  overall_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  last_scan_date: string;
  next_audit_date?: string;
  compliance_trends: ComplianceTrend[];
}

export interface ComplianceStandardScore {
  standard: ComplianceStandard;
  score: number;
  violations: number;
  compliant_controls: number;
  total_controls: number;
  last_assessed: string;
}

export interface ComplianceTrend {
  date: string;
  score: number;
  violations: number;
}

// Audit Report (matches backend AuditReportSchema)
export interface AuditReport {
  report_id: string;
  generated_at: string;
  report_period: {
    start: string;
    end: string;
  };
  executive_summary: string;
  compliance_posture: {
    total_violations: number;
    open_violations: number;
    remediated_violations: number;
    remediation_rate: number;
  };
  violations_by_standard: Record<string, number>;
  violations_by_severity: Record<string, number>;
  remediation_status: Record<string, number>;
  violations_needing_audit: ComplianceViolation[];
  audit_evidence: AuditEvidence[];
  recommendations: string[];
  detailed_violations?: ComplianceViolation[];
}

// Audit Evidence
export interface AuditEvidence {
  type: string;
  description: string;
  source: string;
  timestamp: string;
  data?: Record<string, any>;
}

// Type guard for AuditReport validation
export function isAuditReport(data: unknown): data is AuditReport {
  if (!data || typeof data !== 'object') {
    return false;
  }
  
  const report = data as Partial<AuditReport>;
  
  return (
    typeof report.report_id === 'string' &&
    typeof report.generated_at === 'string' &&
    typeof report.executive_summary === 'string' &&
    report.report_period !== undefined &&
    typeof report.report_period === 'object' &&
    typeof report.report_period.start === 'string' &&
    typeof report.report_period.end === 'string' &&
    report.compliance_posture !== undefined &&
    typeof report.compliance_posture === 'object' &&
    typeof report.compliance_posture.total_violations === 'number' &&
    typeof report.compliance_posture.open_violations === 'number' &&
    typeof report.compliance_posture.remediated_violations === 'number' &&
    typeof report.compliance_posture.remediation_rate === 'number' &&
    report.violations_by_severity !== undefined &&
    typeof report.violations_by_severity === 'object' &&
    report.violations_by_standard !== undefined &&
    typeof report.violations_by_standard === 'object' &&
    Array.isArray(report.recommendations)
  );
}

// Validate and normalize audit report data
export function validateAuditReport(data: unknown): AuditReport {
  if (!isAuditReport(data)) {
    throw new Error('Invalid audit report data structure');
  }
  
  return data;
}

export interface AuditFinding {
  standard: ComplianceStandard;
  violation_type: ComplianceViolationType;
  severity: ComplianceSeverity;
  affected_apis: string[];
  description: string;
  regulation_reference: string;
  evidence: string[];
  risk_assessment: string;
}

export interface AuditRecommendation {
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  affected_standards: ComplianceStandard[];
  implementation_effort: 'low' | 'medium' | 'high';
  expected_impact: string;
}

export interface ViolationsSummary {
  total: number;
  by_severity: Record<ComplianceSeverity, number>;
  by_standard: Record<ComplianceStandard, number>;
  by_status: Record<ComplianceStatus, number>;
  critical_violations: ComplianceViolation[];
}

export interface RemediationStatus {
  total_violations: number;
  remediated: number;
  in_progress: number;
  pending: number;
  avg_remediation_time_days: number;
  remediation_rate: number;
}

// Compliance Scan Request/Response
export interface ComplianceScanRequest {
  api_id: string;
  standards?: ComplianceStandard[];
  force_rescan?: boolean;
}

export interface ComplianceScanResponse {
  scan_id: string;
  api_id: string;
  api_name: string;
  scan_completed_at: string;
  violations_found: number;
  severity_breakdown: Record<ComplianceSeverity, number>;
  violations: ComplianceViolation[];
  compliance_score: number;
  standards_checked: ComplianceStandard[];
}

// Audit Report Request/Response
export interface AuditReportRequest {
  gateway_id: string;
  api_ids?: string[];
  standards?: ComplianceStandard[];
  start_date?: string;
  end_date?: string;
}

export interface AuditReportResponse {
  report: AuditReport;
  generated_at: string;
  format: 'json' | 'pdf' | 'html';
}

// Compliance Violation List Response
export interface ComplianceViolationListResponse {
  violations: ComplianceViolation[];
  total: number;
  page: number;
  page_size: number;
  filters_applied: {
    standard?: ComplianceStandard;
    severity?: ComplianceSeverity;
    status?: ComplianceStatus;
    api_id?: string;
  };
}

// Made with Bob