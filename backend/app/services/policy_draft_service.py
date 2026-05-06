"""
Policy Draft Service

Generates default policy configurations for remediation and optimization,
supports user overrides, and produces final PolicyAction objects.

This service separates default generation from policy application,
enabling preview-before-apply workflows and manual override capabilities.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base.api import PolicyAction, PolicyActionType
from app.models.base.policy_configs import (
    RateLimitConfig,
    AuthenticationConfig,
    CachingConfig,
    TlsConfig,
)
from app.models.recommendation import RecommendationType, OptimizationRecommendation
from app.models.vulnerability import Vulnerability, VulnerabilityType, ConfigurationType
from app.models.api import API

logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class ManualAnalysis(BaseModel):
    """Manual analysis metadata for policy overrides."""
    
    reason: Optional[str] = Field(None, description="Reason for override")
    risk_acknowledgement: Optional[str] = Field(None, description="Risk acknowledgement")
    reviewed_by: Optional[str] = Field(None, description="User who reviewed")
    change_summary: Optional[List[str]] = Field(None, description="List of changes made")


class FieldMetadata(BaseModel):
    """Metadata for an editable field."""
    
    field_name: str
    field_type: str
    description: str
    default_value: Any
    required: bool = False
    constraints: Optional[Dict[str, Any]] = None


class PolicyDraft(BaseModel):
    """Policy draft with defaults and editable fields."""
    
    policy_type: str
    action_type: PolicyActionType
    default_config: Dict[str, Any]
    editable_fields: List[FieldMetadata]
    manual_analysis_required: bool = False
    warnings: List[str] = []
    vendor_constraints: Optional[Dict[str, Any]] = None


class PolicyOverrideRequest(BaseModel):
    """Request to override policy configuration."""
    
    override_config: Optional[Dict[str, Any]] = Field(None, description="Fields to override")
    manual_analysis: Optional[ManualAnalysis] = Field(None, description="Manual analysis metadata")


# ============================================================================
# Policy Draft Service
# ============================================================================

class PolicyDraftService:
    """Service for generating policy drafts and handling overrides."""
    
    def __init__(self):
        """Initialize the policy draft service."""
    
    # Vendor capability mappings
    VENDOR_CAPABILITIES = {
        "webmethods": {
            # WebMethods API Gateway - primary integrated gateway with comprehensive support
            "rate_limiting": [
                "requests_per_second", "requests_per_minute", "requests_per_hour",
                "concurrent_requests", "burst_allowance", "rate_limit_key",
                "custom_key_header", "enforcement_action", "include_rate_limit_headers"
            ],
            "caching": [
                "ttl_seconds", "cache_key_strategy", "vary_headers", "vary_query_params",
                "respect_cache_control_headers", "cache_methods", "cache_status_codes",
                "max_payload_size_bytes", "invalidate_on_methods"
            ],
            "tls": [
                "min_tls_version", "allowed_cipher_suites", "require_client_certificate",
                "verify_backend_certificate"
            ],
            "authentication": [
                "auth_type", "jwt_issuer", "jwt_audience", "oauth_scopes",
                "api_key_header", "basic_auth_realm", "mtls_ca_cert",
                "session_timeout", "token_expiry", "rate_limit_per_user", "allowed_origins"
            ],
        },
        "kong": {
            "rate_limiting": ["requests_per_second", "requests_per_minute", "requests_per_hour", "burst_allowance", "rate_limit_key", "enforcement_action"],
            "caching": ["ttl_seconds", "cache_key_strategy", "vary_headers", "cache_methods", "cache_status_codes"],
            "tls": ["min_tls_version", "allowed_cipher_suites", "require_client_certificate"],
            "authentication": ["auth_type", "oauth_provider", "oauth_scopes", "jwt_issuer", "jwt_audience", "api_key_header"],
        },
        "apigee": {
            "rate_limiting": ["requests_per_minute", "requests_per_hour", "concurrent_requests", "rate_limit_key"],
            "caching": ["ttl_seconds", "cache_key_strategy", "cache_methods"],
            "tls": ["min_tls_version", "allowed_cipher_suites"],
            "authentication": ["auth_type", "oauth_provider", "oauth_scopes", "jwt_issuer"],
        },
        "aws_api_gateway": {
            "rate_limiting": ["requests_per_second", "burst_allowance"],
            "caching": ["ttl_seconds"],
            "tls": ["min_tls_version"],
            "authentication": ["auth_type", "jwt_issuer", "jwt_audience"],
        },
        "mulesoft": {
            "rate_limiting": ["requests_per_second", "requests_per_minute", "rate_limit_key", "enforcement_action"],
            "caching": ["ttl_seconds", "cache_key_strategy"],
            "tls": ["min_tls_version", "allowed_cipher_suites"],
            "authentication": ["auth_type", "oauth_provider", "oauth_scopes"],
        },
    }
    
    def get_vendor_capabilities(self, vendor: str, policy_type: str) -> List[str]:
        """Get supported fields for a vendor and policy type.
        
        Args:
            vendor: Gateway vendor name (e.g., "kong", "apigee")
            policy_type: Policy type (e.g., "rate_limiting", "caching")
        
        Returns:
            List of supported field names for this vendor/policy combination
        """
        vendor_lower = vendor.lower()
        
        # Return all fields if vendor not in capability map (assume full support)
        if vendor_lower not in self.VENDOR_CAPABILITIES:
            return []  # Empty list means no restrictions
        
        vendor_caps = self.VENDOR_CAPABILITIES[vendor_lower]
        return vendor_caps.get(policy_type, [])
    
    def apply_vendor_restrictions(
        self,
        editable_fields: List[FieldMetadata],
        vendor: str,
        policy_type: str,
    ) -> List[FieldMetadata]:
        """Apply vendor-specific restrictions to editable fields.
        
        Marks fields as read-only if not supported by the vendor.
        
        Args:
            editable_fields: List of field metadata
            vendor: Gateway vendor name
            policy_type: Policy type
        
        Returns:
            Updated list of field metadata with vendor restrictions applied
        """
        supported_fields = self.get_vendor_capabilities(vendor, policy_type)
        
        # If no restrictions (empty list), return fields as-is
        if not supported_fields:
            return editable_fields
        
        # Mark unsupported fields as read-only
        restricted_fields = []
        for field in editable_fields:
            field_copy = field.copy()
            if field.field_name not in supported_fields:
                # Add vendor restriction to constraints
                if not field_copy.constraints:
                    field_copy.constraints = {}
                field_copy.constraints["vendor_restricted"] = True
                field_copy.constraints["vendor_restriction_reason"] = f"Not supported by {vendor}"
            restricted_fields.append(field_copy)
        
        return restricted_fields
        pass
    
    # ========================================================================
    # Optimization Policy Drafts
    # ========================================================================
    
    def build_optimization_caching_draft(
        self,
        recommendation: OptimizationRecommendation,
        api: API,
    ) -> PolicyDraft:
        """Build caching policy draft for optimization recommendation."""
        
        default_config = CachingConfig(
            ttl_seconds=300,
            max_ttl_seconds=None,
            cache_key_strategy="url_headers",
            vary_headers=["Accept", "Accept-Encoding"],
            vary_query_params=None,
            respect_cache_control_headers=True,
            cache_methods=["GET", "HEAD"],
            cache_status_codes=[200, 203, 204, 206, 300, 301],
            max_payload_size_bytes=None,
            invalidate_on_methods=["POST", "PUT", "PATCH", "DELETE"],
        )
        
        editable_fields = [
            FieldMetadata(
                field_name="ttl_seconds",
                field_type="integer",
                description="Cache time-to-live in seconds",
                default_value=300,
                required=True,
                constraints={"min": 1, "max": 86400}
            ),
            FieldMetadata(
                field_name="cache_key_strategy",
                field_type="string",
                description="Strategy for generating cache keys",
                default_value="url_headers",
                required=True,
                constraints={"enum": ["url", "url_headers", "url_query", "custom"]}
            ),
            FieldMetadata(
                field_name="vary_headers",
                field_type="array",
                description="Headers to include in cache key",
                default_value=["Accept", "Accept-Encoding"],
                required=False
            ),
            FieldMetadata(
                field_name="cache_methods",
                field_type="array",
                description="HTTP methods to cache",
                default_value=["GET", "HEAD"],
                required=False
            ),
            FieldMetadata(
                field_name="cache_status_codes",
                field_type="array",
                description="HTTP status codes to cache",
                default_value=[200, 203, 204, 206, 300, 301],
                required=False
            ),
            FieldMetadata(
                field_name="max_payload_size_bytes",
                field_type="integer",
                description="Maximum payload size to cache (bytes)",
                default_value=None,
                required=False,
                constraints={"min": 1}
            ),
        ]
        
        warnings = []
        # Note: API model doesn't have a direct method field
        # Caching warnings would need to check endpoints if needed
        
        return PolicyDraft(
            policy_type="caching",
            action_type=PolicyActionType.CACHING,
            default_config=default_config.dict(),
            editable_fields=editable_fields,
            manual_analysis_required=False,
            warnings=warnings
        )
    
    def build_optimization_rate_limiting_draft(
        self,
        recommendation: OptimizationRecommendation,
        api: API,
    ) -> PolicyDraft:
        """Build rate limiting policy draft for optimization recommendation."""
        
        default_config = RateLimitConfig(
            requests_per_second=100,
            requests_per_minute=5000,
            requests_per_hour=250000,
            requests_per_day=None,
            concurrent_requests=50,
            burst_allowance=None,
            rate_limit_key="ip",
            custom_key_header=None,
            enforcement_action="throttle",
            include_rate_limit_headers=True,
            consumer_tiers=None,
        )
        
        editable_fields = [
            FieldMetadata(
                field_name="requests_per_second",
                field_type="integer",
                description="Maximum requests per second",
                default_value=100,
                required=False,
                constraints={"min": 1}
            ),
            FieldMetadata(
                field_name="requests_per_minute",
                field_type="integer",
                description="Maximum requests per minute",
                default_value=5000,
                required=False,
                constraints={"min": 1}
            ),
            FieldMetadata(
                field_name="requests_per_hour",
                field_type="integer",
                description="Maximum requests per hour",
                default_value=250000,
                required=False,
                constraints={"min": 1}
            ),
            FieldMetadata(
                field_name="concurrent_requests",
                field_type="integer",
                description="Maximum concurrent requests",
                default_value=50,
                required=False,
                constraints={"min": 1}
            ),
            FieldMetadata(
                field_name="burst_allowance",
                field_type="integer",
                description="Additional requests allowed in burst",
                default_value=None,
                required=False,
                constraints={"min": 0}
            ),
            FieldMetadata(
                field_name="rate_limit_key",
                field_type="string",
                description="Key to use for rate limiting",
                default_value="ip",
                required=True,
                constraints={"enum": ["ip", "user", "api_key", "custom"]}
            ),
            FieldMetadata(
                field_name="enforcement_action",
                field_type="string",
                description="Action when limit exceeded",
                default_value="throttle",
                required=True,
                constraints={"enum": ["reject", "throttle", "queue"]}
            ),
        ]
        
        return PolicyDraft(
            policy_type="rate_limiting",
            action_type=PolicyActionType.RATE_LIMITING,
            default_config=default_config.dict(),
            editable_fields=editable_fields,
            manual_analysis_required=False,
            warnings=[]
        )
    
    # ========================================================================
    # Security Policy Drafts
    # ========================================================================
    
    def build_security_rate_limiting_draft(
        self,
        vulnerability: Vulnerability,
        api: API,
    ) -> PolicyDraft:
        """Build rate limiting policy draft for security vulnerability."""
        
        default_config = RateLimitConfig(
            requests_per_second=None,
            requests_per_minute=100,
            requests_per_hour=None,
            requests_per_day=None,
            concurrent_requests=None,
            burst_allowance=20,
            rate_limit_key="ip",
            custom_key_header=None,
            enforcement_action="reject",
            include_rate_limit_headers=True,
            consumer_tiers=None,
        )
        
        editable_fields = [
            FieldMetadata(
                field_name="requests_per_minute",
                field_type="integer",
                description="Maximum requests per minute",
                default_value=100,
                required=True,
                constraints={"min": 1}
            ),
            FieldMetadata(
                field_name="burst_allowance",
                field_type="integer",
                description="Additional requests allowed in burst",
                default_value=20,
                required=False,
                constraints={"min": 0}
            ),
            FieldMetadata(
                field_name="rate_limit_key",
                field_type="string",
                description="Key to use for rate limiting",
                default_value="ip",
                required=True,
                constraints={"enum": ["ip", "user", "api_key", "custom"]}
            ),
            FieldMetadata(
                field_name="enforcement_action",
                field_type="string",
                description="Action when limit exceeded",
                default_value="reject",
                required=True,
                constraints={"enum": ["reject", "throttle"]}
            ),
        ]
        
        warnings = []
        if vulnerability.severity == "critical":
            warnings.append("Critical vulnerability - consider stricter rate limits")
        
        return PolicyDraft(
            policy_type="rate_limiting",
            action_type=PolicyActionType.RATE_LIMITING,
            default_config=default_config.dict(),
            editable_fields=editable_fields,
            manual_analysis_required=False,
            warnings=warnings
        )
    
    def build_security_tls_draft(
        self,
        vulnerability: Vulnerability,
        api: API,
    ) -> PolicyDraft:
        """Build TLS policy draft for security vulnerability."""
        
        default_config = TlsConfig(
            enforce_tls=True,
            min_tls_version="1.2",
            allowed_cipher_suites=[
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
            ],
            require_client_certificate=False,
            trusted_ca_certificates=None,
            verify_backend_certificate=True,
        )
        
        editable_fields = [
            FieldMetadata(
                field_name="min_tls_version",
                field_type="string",
                description="Minimum TLS version required",
                default_value="1.2",
                required=True,
                constraints={"enum": ["1.0", "1.1", "1.2", "1.3"]}
            ),
            FieldMetadata(
                field_name="allowed_cipher_suites",
                field_type="array",
                description="Allowed TLS cipher suites",
                default_value=["TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384"],
                required=False
            ),
            FieldMetadata(
                field_name="require_client_certificate",
                field_type="boolean",
                description="Require client certificate for mTLS",
                default_value=False,
                required=False
            ),
            FieldMetadata(
                field_name="verify_backend_certificate",
                field_type="boolean",
                description="Verify backend server certificate",
                default_value=True,
                required=False
            ),
        ]
        
        warnings = []
        if vulnerability.severity in ["critical", "high"]:
            warnings.append("Consider upgrading to TLS 1.3 for enhanced security")
        
        return PolicyDraft(
            policy_type="tls",
            action_type=PolicyActionType.TLS,
            default_config=default_config.dict(),
            editable_fields=editable_fields,
            manual_analysis_required=False,
            warnings=warnings
        )
    def build_security_authentication_draft(
        self,
        vulnerability: Vulnerability,
        api: API,
    ) -> PolicyDraft:
        """Build authentication policy draft for security vulnerability."""
        
        default_config = AuthenticationConfig(
            auth_type="oauth2",
            oauth_provider="default",
            oauth_scopes=["read", "write"],
            oauth_token_endpoint=None,
            jwt_issuer=None,
            jwt_audience=None,
            jwt_public_key_url=None,
            api_key_header=None,
            api_key_query_param=None,
            allow_anonymous=False,
            cache_credentials=True,
            cache_ttl_seconds=300,
        )
        
        editable_fields = [
            FieldMetadata(
                field_name="auth_type",
                field_type="string",
                description="Authentication type",
                default_value="oauth2",
                required=True,
                constraints={"enum": ["oauth2", "jwt", "api_key", "basic", "custom"]}
            ),
            FieldMetadata(
                field_name="oauth_provider",
                field_type="string",
                description="OAuth2 provider name",
                default_value="default",
                required=False
            ),
            FieldMetadata(
                field_name="oauth_scopes",
                field_type="array",
                description="Required OAuth2 scopes",
                default_value=["read", "write"],
                required=False
            ),
            FieldMetadata(
                field_name="oauth_token_endpoint",
                field_type="string",
                description="OAuth2 token endpoint URL",
                default_value=None,
                required=False
            ),
            FieldMetadata(
                field_name="jwt_issuer",
                field_type="string",
                description="JWT issuer claim",
                default_value=None,
                required=False
            ),
            FieldMetadata(
                field_name="jwt_audience",
                field_type="string",
                description="JWT audience claim",
                default_value=None,
                required=False
            ),
            FieldMetadata(
                field_name="jwt_public_key_url",
                field_type="string",
                description="JWT public key URL (JWKS)",
                default_value=None,
                required=False
            ),
            FieldMetadata(
                field_name="api_key_header",
                field_type="string",
                description="API key header name",
                default_value=None,
                required=False
            ),
            FieldMetadata(
                field_name="allow_anonymous",
                field_type="boolean",
                description="Allow anonymous access",
                default_value=False,
                required=False
            ),
            FieldMetadata(
                field_name="cache_credentials",
                field_type="boolean",
                description="Cache validated credentials",
                default_value=True,
                required=False
            ),
            FieldMetadata(
                field_name="cache_ttl_seconds",
                field_type="integer",
                description="Credential cache TTL in seconds",
                default_value=300,
                required=False,
                constraints={"min": 60, "max": 3600}
            ),
        ]
        
        warnings = []
        if vulnerability.severity in ["critical", "high"]:
            warnings.append("Critical authentication vulnerability - immediate remediation recommended")
        warnings.append("Ensure OAuth2/JWT endpoints are properly configured before applying")
        
        return PolicyDraft(
            policy_type="authentication",
            action_type=PolicyActionType.AUTHENTICATION,
            default_config=default_config.dict(),
            editable_fields=editable_fields,
            manual_analysis_required=True,  # Authentication requires careful configuration
            warnings=warnings
        )
    
    
    # ========================================================================
    # Draft Generation Orchestration
    # ========================================================================
    
    def generate_optimization_draft(
        self,
        recommendation: OptimizationRecommendation,
        api: API,
    ) -> PolicyDraft:
        """Generate policy draft for optimization recommendation."""
        
        rec_type = recommendation.recommendation_type
        
        if rec_type == RecommendationType.CACHING:
            return self.build_optimization_caching_draft(recommendation, api)
        elif rec_type == RecommendationType.RATE_LIMITING:
            return self.build_optimization_rate_limiting_draft(recommendation, api)
        else:
            raise ValueError(f"Unsupported optimization type: {rec_type}")
    
    def generate_security_draft(
        self,
        vulnerability: Vulnerability,
        api: API,
    ) -> PolicyDraft:
        """Generate policy draft for security vulnerability."""
        
        vuln_type = vulnerability.vulnerability_type
        config_type = vulnerability.configuration_type
        
        if vuln_type == VulnerabilityType.AUTHENTICATION:
            return self.build_security_authentication_draft(vulnerability, api)
        elif vuln_type == VulnerabilityType.CONFIGURATION:
            if config_type == ConfigurationType.RATE_LIMITING:
                return self.build_security_rate_limiting_draft(vulnerability, api)
            elif config_type == ConfigurationType.TLS:
                return self.build_security_tls_draft(vulnerability, api)
        
        raise ValueError(
            f"Unsupported vulnerability type for preview: {vuln_type} / {config_type}"
        )
    
    # ========================================================================
    # Override Handling
    # ========================================================================
    
    def merge_config_with_overrides(
        self,
        default_config: Union[RateLimitConfig, CachingConfig, TlsConfig, AuthenticationConfig],
        override_config: Optional[Dict[str, Any]],
        editable_fields: List[FieldMetadata],
    ) -> Union[RateLimitConfig, CachingConfig, TlsConfig, AuthenticationConfig]:
        """Merge default config with user overrides.
        
        Only fields listed in editable_fields can be overridden.
        """
        if not override_config:
            return default_config
        
        # Get editable field names
        editable_field_names = {field.field_name for field in editable_fields}
        
        # Filter overrides to only editable fields
        filtered_overrides = {
            key: value
            for key, value in override_config.items()
            if key in editable_field_names
        }
        
        if not filtered_overrides:
            return default_config
        
        # Merge overrides into default config
        config_dict = default_config.dict()
        config_dict.update(filtered_overrides)
        
        # Reconstruct typed config
        config_class = type(default_config)
        return config_class(**config_dict)
    
    def build_final_policy_action(
        self,
        draft: PolicyDraft,
        override_request: Optional[PolicyOverrideRequest],
        api: API,
        entity_id: UUID,
        entity_type: str,  # "recommendation" or "vulnerability"
    ) -> tuple[PolicyAction, Dict[str, Any]]:
        """Build final PolicyAction with overrides applied.
        
        Returns:
            Tuple of (PolicyAction, audit_metadata)
        """
        # Parse default config into typed model
        config_class_map = {
            PolicyActionType.CACHING: CachingConfig,
            PolicyActionType.RATE_LIMITING: RateLimitConfig,
            PolicyActionType.TLS: TlsConfig,
            PolicyActionType.AUTHENTICATION: AuthenticationConfig,
        }
        
        config_class = config_class_map.get(draft.action_type)
        if not config_class:
            raise ValueError(f"Unsupported action type: {draft.action_type}")
        
        default_config = config_class(**draft.default_config)
        
        # Apply overrides if provided
        final_config = default_config
        override_fields = []
        
        if override_request and override_request.override_config:
            final_config = self.merge_config_with_overrides(
                default_config,
                override_request.override_config,
                draft.editable_fields
            )
            
            # Track which fields were overridden
            for key, value in override_request.override_config.items():
                default_value = getattr(default_config, key, None)
                if value != default_value:
                    override_fields.append(f"{key}: {default_value} -> {value}")
        
        # Build PolicyAction
        policy_action = PolicyAction(
            action_type=draft.action_type,
            enabled=True,
            stage="request" if draft.action_type == PolicyActionType.RATE_LIMITING else "response",
            config=final_config,
            vendor_config={},
            name=f"{draft.policy_type.title()} Policy for {api.name}",
            description=f"Policy applied from {entity_type} {entity_id}",
        )
        
        # Build audit metadata
        audit_metadata = {
            "generated_default_config": default_config.dict(),
            "applied_config": final_config.dict(),
            "override_fields": override_fields,
            "policy_type": draft.policy_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "applied_at": datetime.utcnow().isoformat(),
        }
        
        # Add manual analysis if provided
        if override_request and override_request.manual_analysis:
            audit_metadata["manual_analysis"] = {
                "reason": override_request.manual_analysis.reason,
                "risk_acknowledgement": override_request.manual_analysis.risk_acknowledgement,
                "reviewed_by": override_request.manual_analysis.reviewed_by,
                "change_summary": override_request.manual_analysis.change_summary or override_fields,
                "reviewed_at": datetime.utcnow().isoformat(),
            }
        
        return policy_action, audit_metadata

# Made with Bob
