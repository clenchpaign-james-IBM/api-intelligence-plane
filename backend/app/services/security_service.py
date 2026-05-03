"""Security Service for API Intelligence Plane.

Orchestrates security scanning, vulnerability management, and automated remediation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.agents.security_agent import SecurityAgent
from app.config import Settings
from app.db.repositories.api_repository import APIRepository
from app.db.repositories.gateway_repository import GatewayRepository
from app.db.repositories.vulnerability_repository import VulnerabilityRepository
from app.models.base.api import API, PolicyAction, PolicyActionType
from app.models.base.policy_configs import (
    AuthenticationConfig,
    AuthorizationConfig,
    CorsConfig,
    RateLimitConfig,
    TlsConfig,
    ValidationConfig,
)
from app.models.vulnerability import (
    ConfigurationType,
    Vulnerability,
    VulnerabilityStatus,
    VulnerabilityType,
    VulnerabilitySeverity,
    RemediationType,
    RemediationAction,
    VerificationStatus,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for security scanning and vulnerability management.
    
    This service provides:
    1. Hybrid security policy coverage analysis (rule-based + AI)
    2. Vulnerability detection and tracking
    3. Automated remediation workflows via Gateway adapters
    4. Real remediation verification
    5. Security posture reporting with compliance
    """

    def __init__(
        self,
        settings: Settings,
        api_repository: Optional[APIRepository] = None,
        vulnerability_repository: Optional[VulnerabilityRepository] = None,
        llm_service: Optional[LLMService] = None,
        security_agent: Optional[SecurityAgent] = None,
        metrics_repository: Optional[Any] = None,
        gateway_repository: Optional[GatewayRepository] = None,
        gateway_adapter: Optional[Any] = None,
    ):
        """Initialize security service.

        Args:
            settings: Application settings
            api_repository: API repository instance
            vulnerability_repository: Vulnerability repository instance
            llm_service: LLM service instance
            security_agent: Security agent instance
            metrics_repository: Metrics repository instance
            gateway_repository: Gateway repository instance
            gateway_adapter: Gateway adapter instance for policy application
        """
        self.settings = settings
        self.api_repository = api_repository or APIRepository()
        self.vulnerability_repository = vulnerability_repository or VulnerabilityRepository()
        self.llm_service = llm_service or LLMService(settings)
        
        # Import here to avoid circular dependency
        from app.db.repositories.metrics_repository import MetricsRepository
        
        self.metrics_repository = metrics_repository or MetricsRepository()
        self.gateway_repository = gateway_repository or GatewayRepository()
        
        self.security_agent = security_agent or SecurityAgent(
            self.llm_service,
            self.metrics_repository
        )
        
        # Gateway adapter for applying policies
        self.gateway_adapter = gateway_adapter

    async def scan_api_security(
        self,
        gateway_id: UUID,
        api_id: UUID,
    ) -> Dict[str, Any]:
        """Scan API for security policy coverage issues using hybrid approach.

        Args:
            gateway_id: Gateway UUID (primary scope dimension)
            api_id: API to scan (secondary scope dimension)

        Returns:
            Scan results with vulnerabilities, compliance issues, and remediation plan
        """
        try:
            logger.info(f"Starting hybrid security scan for API {api_id} in gateway {gateway_id}")

            # Get API details
            api = self.api_repository.get(str(api_id))
            if not api:
                raise ValueError(f"API not found: {api_id}")
            
            # Verify API belongs to gateway
            if api.gateway_id != gateway_id:
                raise ValueError(f"API {api_id} does not belong to gateway {gateway_id}")

            # Perform hybrid security analysis (always uses both rule-based and AI)
            analysis_result = await self.security_agent.analyze_api_security(api)

            # Store vulnerabilities with deduplication
            stored_vulnerabilities = []
            for vuln_data in analysis_result.get("vulnerabilities", []):
                # Convert dict to Vulnerability if needed
                if isinstance(vuln_data, dict):
                    vulnerability = Vulnerability(**vuln_data)
                else:
                    vulnerability = vuln_data

                # Check if vulnerability already exists
                existing = await self.vulnerability_repository.find_existing_vulnerability(
                    api_id=vulnerability.api_id,
                    vulnerability_type=vulnerability.vulnerability_type.value,
                    title=vulnerability.title,
                )
                
                logger.info(
                    f"Checking vulnerability: {vulnerability.title[:50]}... "
                    f"Existing: {'YES ('+str(existing.id)+')' if existing else 'NO'}"
                )

                if existing:
                    # Update existing vulnerability if there are changes
                    should_update = False
                    update_data = {}

                    # Check if severity changed
                    if existing.severity != vulnerability.severity:
                        update_data["severity"] = vulnerability.severity.value
                        should_update = True

                    # Check if description changed
                    if existing.description != vulnerability.description:
                        update_data["description"] = vulnerability.description
                        should_update = True

                    # Check if affected endpoints changed
                    if existing.affected_endpoints != vulnerability.affected_endpoints:
                        update_data["affected_endpoints"] = vulnerability.affected_endpoints
                        should_update = True

                    # Check if remediation plan changed
                    if existing.recommended_remediation != vulnerability.recommended_remediation:
                        update_data["recommended_remediation"] = vulnerability.recommended_remediation
                        update_data["plan_generated_at"] = datetime.utcnow()
                        should_update = True

                    # Update if changes detected
                    if should_update:
                        update_data["updated_at"] = datetime.utcnow()
                        self.vulnerability_repository.update(str(existing.id), update_data)
                        logger.info(
                            f"Updated existing vulnerability {existing.id} for API {api_id}"
                        )
                        # Use updated vulnerability
                        existing_dict = existing.dict()
                        existing_dict.update(update_data)
                        stored_vulnerabilities.append(Vulnerability(**existing_dict))
                    else:
                        logger.info(
                            f"Vulnerability {existing.id} unchanged, skipping update"
                        )
                        stored_vulnerabilities.append(existing)
                else:
                    # Create new vulnerability only if it doesn't exist
                    logger.info(
                        f"Creating NEW vulnerability {vulnerability.id} for API {api_id}"
                    )
                    self.vulnerability_repository.create(vulnerability)
                    logger.info(
                        f"Created new vulnerability {vulnerability.id} for API {api_id}"
                    )
                    stored_vulnerabilities.append(vulnerability)

            logger.info(
                f"Security scan complete. Found {len(stored_vulnerabilities)} vulnerabilities"
            )

            return {
                "scan_id": str(UUID(int=0)),  # Generate proper scan ID
                "gateway_id": str(gateway_id),
                "api_id": str(api_id),
                "api_name": api.name,
                "scan_completed_at": datetime.utcnow().isoformat(),
                "vulnerabilities_found": len(stored_vulnerabilities),
                "severity_breakdown": self._calculate_severity_breakdown(
                    stored_vulnerabilities
                ),
                "vulnerabilities": [v.dict() for v in stored_vulnerabilities],
                "compliance_issues": analysis_result.get("compliance_issues", []),
                "remediation_plan": analysis_result.get("remediation_plan", {}),
                "metrics_analyzed": analysis_result.get("metrics_analyzed", 0),
            }

        except Exception as e:
            logger.error(f"Security scan failed for API {api_id}: {str(e)}")
            raise

    async def scan_gateway_apis(self, gateway_id: UUID) -> Dict[str, Any]:
        """Scan all APIs within a specific gateway for security issues.

        Args:
            gateway_id: Gateway UUID (primary scope dimension)

        Returns:
            Aggregated scan results for the gateway
        """
        try:
            logger.info(f"Starting security scan for all APIs in gateway {gateway_id}")

            # Get all APIs for this gateway
            apis, _ = self.api_repository.find_by_gateway(gateway_id, size=1000)
            
            scan_results = []
            total_vulnerabilities = 0

            for api in apis:
                try:
                    result = await self.scan_api_security(gateway_id, api.id)
                    scan_results.append(result)
                    total_vulnerabilities += result["vulnerabilities_found"]
                except Exception as e:
                    logger.error(f"Failed to scan API {api.name}: {str(e)}")
                    continue

            logger.info(
                f"Completed security scan. Scanned {len(scan_results)} APIs, "
                f"found {total_vulnerabilities} vulnerabilities"
            )

            return {
                "gateway_id": str(gateway_id),
                "scan_completed_at": datetime.utcnow().isoformat(),
                "apis_scanned": len(scan_results),
                "total_vulnerabilities": total_vulnerabilities,
                "scan_results": scan_results,
            }

        except Exception as e:
            logger.error(f"Bulk security scan failed: {str(e)}")
            raise

    async def remediate_vulnerability(
        self,
        vulnerability_id: UUID,
        remediation_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger automated remediation for a vulnerability.
        
        Uses the stored recommended_remediation plan from Option B implementation
        to guide the remediation process.

        Args:
            vulnerability_id: Vulnerability to remediate
            remediation_strategy: Optional specific strategy to use

        Returns:
            Remediation result
        """
        try:
            logger.info(f"Starting remediation for vulnerability: {vulnerability_id}")

            # Get vulnerability
            vulnerability = self.vulnerability_repository.get(str(vulnerability_id))
            if not vulnerability:
                raise ValueError(f"Vulnerability not found: {vulnerability_id}")

            # Check if already remediated
            if vulnerability.status == VulnerabilityStatus.REMEDIATED:
                return {
                    "vulnerability_id": str(vulnerability_id),
                    "status": "already_remediated",
                    "message": "Vulnerability already remediated",
                }

            # Check if automated remediation is possible
            if vulnerability.remediation_type != RemediationType.AUTOMATED:
                remediation_type_str = vulnerability.remediation_type.value if vulnerability.remediation_type else "manual"
                return {
                    "vulnerability_id": str(vulnerability_id),
                    "status": "manual_required",
                    "message": f"Vulnerability requires {remediation_type_str} remediation",
                    "recommendation": "Manual intervention required",
                    "recommended_plan": vulnerability.recommended_remediation,  # Include stored plan
                }

            # Get API details
            api = self.api_repository.get(str(vulnerability.api_id))
            if not api:
                raise ValueError(f"API not found: {vulnerability.api_id}")

            # Use recommended_remediation plan if available
            if vulnerability.recommended_remediation:
                logger.info(f"Using stored remediation plan (source: {vulnerability.plan_source}, version: {vulnerability.plan_version})")
                
                # Initialize remediation_actions from recommended plan
                if not vulnerability.remediation_actions:
                    from app.models.vulnerability import RemediationAction
                    recommended_actions = vulnerability.recommended_remediation.get("actions", [])
                    vulnerability.remediation_actions = [
                        RemediationAction(
                            action=action.get("action", ""),
                            type=action.get("type", "configuration"),
                            status="pending",
                        )
                        for action in recommended_actions
                    ]

            # Perform automated remediation
            remediation_result = await self._apply_automated_remediation(
                api=api,
                vulnerability=vulnerability,
                strategy=remediation_strategy,
            )

            # Check if remediation was successful
            result_actions = remediation_result.get("actions", [])
            all_successful = all(
                action.status == "completed"
                for action in result_actions
            )
            
            # Update vulnerability status based on remediation success
            if all_successful:
                vulnerability.status = VulnerabilityStatus.REMEDIATED
                vulnerability.remediated_at = datetime.utcnow()
                vulnerability.verification_status = VerificationStatus.PENDING
            else:
                vulnerability.status = VulnerabilityStatus.IN_PROGRESS
            
            # Merge remediation actions from result with existing actions
            if result_actions:
                vulnerability.remediation_actions = result_actions
            
            vulnerability.updated_at = datetime.utcnow()
            
            # Update plan status if plan was used
            if vulnerability.recommended_remediation and vulnerability.plan_status == "generated":
                vulnerability.plan_status = "approved"  # Mark as approved when remediation starts

            self.vulnerability_repository.update(
                str(vulnerability.id),
                vulnerability.dict(exclude={"id"})
            )
            
            # Force OpenSearch index refresh to make changes immediately visible
            self.vulnerability_repository.client.indices.refresh(
                index=self.vulnerability_repository.index_name
            )

            logger.info(f"Remediation completed for vulnerability: {vulnerability_id} (status: {vulnerability.status})")

            return {
                "vulnerability_id": str(vulnerability_id),
                "status": "remediation_applied",
                "remediation_result": remediation_result,
                "message": "Remediation applied successfully. Next security scan will validate the fix.",
            }

        except Exception as e:
            logger.error(f"Remediation failed for vulnerability {vulnerability_id}: {str(e)}")
            raise

    async def verify_remediation(
        self,
        vulnerability_id: UUID,
    ) -> Dict[str, Any]:
        """Verify that remediation was successful.

        Args:
            vulnerability_id: Vulnerability to verify

        Returns:
            Verification result
        """
        try:
            logger.info(f"Verifying remediation for vulnerability: {vulnerability_id}")

            # Get vulnerability
            vulnerability = self.vulnerability_repository.get(str(vulnerability_id))
            if not vulnerability:
                raise ValueError(f"Vulnerability not found: {vulnerability_id}")

            # Get API
            api = self.api_repository.get(str(vulnerability.api_id))
            if not api:
                raise ValueError(f"API not found: {vulnerability.api_id}")

            # Re-scan the specific vulnerability area
            verification_result = await self._verify_vulnerability_fixed(
                api=api,
                vulnerability=vulnerability,
            )

            # Update vulnerability based on verification
            if verification_result["is_fixed"]:
                vulnerability.status = VulnerabilityStatus.REMEDIATED
                vulnerability.remediated_at = datetime.utcnow()
                vulnerability.verification_status = VerificationStatus.VERIFIED
            else:
                vulnerability.verification_status = VerificationStatus.FAILED

            vulnerability.updated_at = datetime.utcnow()
            self.vulnerability_repository.update(
                str(vulnerability.id),
                vulnerability.dict(exclude={"id"})
            )
            
            # Force OpenSearch index refresh to make status change immediately visible
            self.vulnerability_repository.client.indices.refresh(
                index=self.vulnerability_repository.index_name
            )

            logger.info(
                f"Verification complete for vulnerability {vulnerability_id}: "
                f"{'FIXED' if verification_result['is_fixed'] else 'NOT FIXED'}"
            )

            return verification_result

        except Exception as e:
            logger.error(f"Verification failed for vulnerability {vulnerability_id}: {str(e)}")
            raise

    async def get_security_posture(
        self,
        api_id: Optional[UUID] = None,
        gateway_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get security posture metrics.

        Args:
            api_id: Optional API filter
            gateway_id: Optional gateway filter

        Returns:
            Security posture metrics
        """
        try:
            posture = await self.vulnerability_repository.get_security_posture(
                api_id=api_id,
                gateway_id=gateway_id
            )

            # Calculate additional metrics
            total = posture["total_vulnerabilities"]
            by_status = posture["by_status"]
            
            remediation_rate = 0
            if total > 0:
                remediated = by_status.get("remediated", 0)
                remediation_rate = (remediated / total) * 100

            # Calculate risk score (0-100, higher is worse)
            risk_score = self._calculate_risk_score(posture)

            return {
                **posture,
                "remediation_rate": round(remediation_rate, 2),
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score),
            }

        except Exception as e:
            logger.error(f"Failed to get security posture: {str(e)}")
            raise

    async def get_vulnerabilities(
        self,
        api_id: Optional[UUID] = None,
        status: Optional[VulnerabilityStatus] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Vulnerability]:
        """Get vulnerabilities with optional filters.

        Args:
            api_id: Optional API filter
            status: Optional status filter
            severity: Optional severity filter
            limit: Maximum results

        Returns:
            List of vulnerabilities
        """
        try:
            if api_id:
                return await self.vulnerability_repository.find_by_api_id(
                    api_id, None, status, limit
                )
            elif severity:
                return await self.vulnerability_repository.find_by_severity(
                    severity, status, limit
                )
            else:
                return await self.vulnerability_repository.find_open_vulnerabilities(
                    api_id, limit
                )

        except Exception as e:
            logger.error(f"Failed to get vulnerabilities: {str(e)}")
            raise

    async def get_security_summary(
        self,
        gateway_id: Optional[UUID] = None,
    ) -> Dict[str, int]:
        """Get security summary with vulnerability counts by severity.

        Uses efficient OpenSearch aggregations and filters by gateway_id if provided.

        Args:
            gateway_id: Optional gateway filter

        Returns:
            Dictionary with vulnerability counts by severity
        """
        try:
            return await self.vulnerability_repository.get_summary_by_severity(gateway_id)
        except Exception as e:
            logger.error(f"Failed to get security summary: {str(e)}")
            raise

    # Private helper methods

    async def _apply_automated_remediation(
        self,
        api: API,
        vulnerability: Vulnerability,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply automated remediation for a vulnerability via Gateway adapter."""
        actions = []
        
        # Get gateway adapter for this API
        if not self.gateway_adapter:
            # Get gateway for this API
            gateway = self.gateway_repository.get(str(api.gateway_id))
            if not gateway:
                raise ValueError(f"Gateway not found for API: {api.id}")
            
            # Get adapter from factory
            from app.adapters.factory import GatewayAdapterFactory
            self.gateway_adapter = GatewayAdapterFactory.create_adapter(gateway)
            await self.gateway_adapter.connect()
        
        try:
            # Apply remediation based on vulnerability type
            if vulnerability.vulnerability_type == VulnerabilityType.AUTHENTICATION:
                policy = PolicyAction(
                    action_type=PolicyActionType.AUTHENTICATION,
                    enabled=True,
                    stage="request",
                    config=AuthenticationConfig(
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
                    ),
                    vendor_config={},
                    name=f"Authentication Policy for {api.name}",
                    description=f"Security remediation for vulnerability {vulnerability.id}",
                )
                success = await self.gateway_adapter.apply_authentication_policy(
                    str(api.id), policy
                )
                actions.append(
                    RemediationAction(
                        action="Applied OAuth2 authentication policy at gateway",
                        type="gateway_policy",
                        status="completed" if success else "failed",
                        performed_at=datetime.utcnow(),
                        performed_by="security_agent",
                        gateway_policy_id=f"auth-{api.id}" if success else None,
                        error_message=None if success else "Failed to apply policy",
                    )
                )
                
            elif vulnerability.vulnerability_type == VulnerabilityType.AUTHORIZATION:
                policy = PolicyAction(
                    action_type=PolicyActionType.AUTHORIZATION,
                    enabled=True,
                    stage="request",
                    config=AuthorizationConfig(
                        allowed_users=None,
                        denied_users=None,
                        allowed_groups=None,
                        denied_groups=None,
                        allowed_roles=["user", "admin"],
                        denied_roles=None,
                        allowed_access_profiles=None,
                        required_permissions=None,
                        any_permissions=["read", "write", "delete"],
                        required_scopes=None,
                        any_scopes=None,
                        required_claims=None,
                        allowed_ip_ranges=None,
                        denied_ip_ranges=None,
                        allowed_time_windows=None,
                        timezone=None,
                        authorization_mode="any",
                        custom_authorization_expression=None,
                        unauthorized_status_code=403,
                        unauthorized_message=None,
                    ),
                    vendor_config={},
                    name=f"Authorization Policy for {api.name}",
                    description=f"Security remediation for vulnerability {vulnerability.id}",
                )
                success = await self.gateway_adapter.apply_authorization_policy(
                    str(api.id), policy
                )
                actions.append(
                    RemediationAction(
                        action="Applied RBAC authorization policy at gateway",
                        type="gateway_policy",
                        status="completed" if success else "failed",
                        performed_at=datetime.utcnow(),
                        performed_by="security_agent",
                        gateway_policy_id=f"authz-{api.id}" if success else None,
                        error_message=None if success else "Failed to apply policy",
                    )
                )
                
            elif vulnerability.vulnerability_type == VulnerabilityType.CONFIGURATION:
                if vulnerability.configuration_type == ConfigurationType.RATE_LIMITING:
                    policy = PolicyAction(
                        action_type=PolicyActionType.RATE_LIMITING,
                        enabled=True,
                        stage="request",
                        config=RateLimitConfig(
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
                        ),
                        vendor_config={},
                        name=f"Rate Limit Policy for {api.name}",
                        description=f"Security remediation for vulnerability {vulnerability.id}",
                    )
                    success = await self.gateway_adapter.apply_rate_limit_policy(
                        str(api.id), policy
                    )
                    actions.append(
                        RemediationAction(
                            action="Applied rate limiting policy (100 req/min)",
                            type="gateway_policy",
                            status="completed" if success else "failed",
                            performed_at=datetime.utcnow(),
                            performed_by="security_agent",
                            gateway_policy_id=f"ratelimit-{api.id}" if success else None,
                            error_message=None if success else "Failed to apply policy",
                        )
                    )
                    
                elif vulnerability.configuration_type == ConfigurationType.TLS:
                    policy = PolicyAction(
                        action_type=PolicyActionType.TLS,
                        enabled=True,
                        stage="request",
                        config=TlsConfig(
                            enforce_tls=True,
                            min_tls_version="1.2",
                            allowed_cipher_suites=[
                                "TLS_AES_128_GCM_SHA256",
                                "TLS_AES_256_GCM_SHA384",
                            ],
                            require_client_certificate=False,
                            trusted_ca_certificates=None,
                            verify_backend_certificate=True,
                        ),
                        vendor_config={"hsts_enabled": True},
                        name=f"TLS Policy for {api.name}",
                        description=f"Security remediation for vulnerability {vulnerability.id}",
                    )
                    success = await self.gateway_adapter.apply_tls_policy(
                        str(api.id), policy
                    )
                    actions.append(
                        RemediationAction(
                            action="Enforced HTTPS-only with TLS 1.2+ at gateway",
                            type="gateway_policy",
                            status="completed" if success else "failed",
                            performed_at=datetime.utcnow(),
                            performed_by="security_agent",
                            gateway_policy_id=f"tls-{api.id}" if success else None,
                            error_message=None if success else "Failed to apply policy",
                        )
                    )
                    
                elif vulnerability.configuration_type == ConfigurationType.CORS:
                    # Get base_path from API (now a top-level field)
                    base_path = api.base_path if hasattr(api, 'base_path') else "/"
                    policy = PolicyAction(
                        action_type=PolicyActionType.CORS,
                        enabled=True,
                        stage="request",
                        config=CorsConfig(
                            allowed_origins=[base_path],
                            allowed_methods=["GET", "POST", "PUT", "DELETE"],
                            allowed_headers=["Content-Type", "Authorization"],
                            exposed_headers=[],
                            allow_credentials=True,
                            max_age_seconds=3600,
                        ),
                        vendor_config={},
                        name=f"CORS Policy for {api.name}",
                        description=f"Security remediation for vulnerability {vulnerability.id}",
                    )
                    success = await self.gateway_adapter.apply_cors_policy(
                        str(api.id), policy
                    )
                    actions.append(
                        RemediationAction(
                            action="Applied secure CORS policy at gateway",
                            type="gateway_policy",
                            status="completed" if success else "failed",
                            performed_at=datetime.utcnow(),
                            performed_by="security_agent",
                            gateway_policy_id=f"cors-{api.id}" if success else None,
                            error_message=None if success else "Failed to apply policy",
                        )
                    )
                    
                elif vulnerability.configuration_type == ConfigurationType.INPUT_VALIDATION:
                    policy = PolicyAction(
                        action_type=PolicyActionType.VALIDATION,
                        enabled=True,
                        stage="request",
                        config=ValidationConfig(
                            validate_request_schema=True,
                            validate_response_schema=False,
                            validate_query_params=True,
                            validate_path_params=True,
                            validate_headers=True,
                            validate_content_type=True,
                            allowed_content_types=None,
                            strict_mode=False,
                            return_validation_errors=True,
                        ),
                        vendor_config={
                            "size_limits": {"request": 10485760, "response": 10485760},
                            "sanitization_rules": ["strip_html", "escape_sql"],
                        },
                        name=f"Validation Policy for {api.name}",
                        description=f"Security remediation for vulnerability {vulnerability.id}",
                    )
                    success = await self.gateway_adapter.apply_validation_policy(
                        str(api.id), policy
                    )
                    actions.append(
                        RemediationAction(
                            action="Applied input validation policy at gateway",
                            type="gateway_policy",
                            status="completed" if success else "failed",
                            performed_at=datetime.utcnow(),
                            performed_by="security_agent",
                            gateway_policy_id=f"validation-{api.id}" if success else None,
                            error_message=None if success else "Failed to apply policy",
                        )
                    )
                    
                elif vulnerability.configuration_type == ConfigurationType.SECURITY_HEADERS:
                    from app.models.base.policy_configs import TransformationConfig
                    policy = PolicyAction(
                        action_type=PolicyActionType.TRANSFORMATION,
                        enabled=True,
                        stage="response",
                        config=TransformationConfig(
                            transform_response=True,
                            add_headers={
                                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                                "X-Frame-Options": "DENY",
                                "X-Content-Type-Options": "nosniff",
                                "Content-Security-Policy": "default-src 'self'",
                                "X-XSS-Protection": "1; mode=block",
                            }
                        ),
                        vendor_config={},
                        name=f"Security Headers Policy for {api.name}",
                        description=f"Security remediation for vulnerability {vulnerability.id}",
                    )
                    success = await self.gateway_adapter.apply_security_headers_policy(
                        str(api.id), policy
                    )
                    actions.append(
                        RemediationAction(
                            action="Applied security headers policy at gateway",
                            type="gateway_policy",
                            status="completed" if success else "failed",
                            performed_at=datetime.utcnow(),
                            performed_by="security_agent",
                            gateway_policy_id=f"headers-{api.id}" if success else None,
                            error_message=None if success else "Failed to apply policy",
                        )
                    )

            return {
                "actions": actions,
                "applied_at": datetime.utcnow().isoformat(),
                "strategy_used": strategy or "default",
            }
            
        except Exception as e:
            logger.error(f"Remediation failed: {e}")
            actions.append(
                RemediationAction(
                    action=f"Failed to apply remediation: {str(e)}",
                    type="gateway_policy",
                    status="failed",
                    performed_at=datetime.utcnow(),
                    performed_by="security_agent",
                    gateway_policy_id=None,
                    error_message=str(e),
                )
            )
            return {
                "actions": actions,
                "applied_at": datetime.utcnow().isoformat(),
                "strategy_used": strategy or "default",
                "error": str(e),
            }

    async def _verify_vulnerability_fixed(
        self,
        api: API,
        vulnerability: Vulnerability,
    ) -> Dict[str, Any]:
        """Verify that a vulnerability has been fixed by re-scanning."""
        try:
            # Re-run security analysis for this specific API
            analysis_result = await self.security_agent.analyze_api_security(api)
            
            # Check if the same vulnerability still exists
            is_fixed = True
            for vuln_data in analysis_result.get("vulnerabilities", []):
                if isinstance(vuln_data, dict):
                    vuln = Vulnerability(**vuln_data)
                else:
                    vuln = vuln_data
                    
                # Check if same type and title (indicating same issue)
                if (vuln.vulnerability_type == vulnerability.vulnerability_type and
                    vuln.title == vulnerability.title):
                    is_fixed = False
                    break
            
            return {
                "vulnerability_id": str(vulnerability.id),
                "is_fixed": is_fixed,
                "verified_at": datetime.utcnow().isoformat(),
                "verification_method": "automated_rescan",
                "details": "Policy verified through re-scanning" if is_fixed else "Vulnerability still detected",
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                "vulnerability_id": str(vulnerability.id),
                "is_fixed": False,
                "verified_at": datetime.utcnow().isoformat(),
                "verification_method": "automated_rescan",
                "details": f"Verification failed: {str(e)}",
                "error": str(e),
            }

    def _calculate_severity_breakdown(
        self,
        vulnerabilities: List[Vulnerability],
    ) -> Dict[str, int]:
        """Calculate severity breakdown from vulnerabilities."""
        breakdown = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for vuln in vulnerabilities:
            severity = vuln.severity.value
            if severity in breakdown:
                breakdown[severity] += 1

        return breakdown

    def _calculate_risk_score(self, posture: Dict[str, Any]) -> int:
        """Calculate overall risk score (0-100, higher is worse)."""
        by_severity = posture.get("by_severity", {})
        
        # Weight by severity
        score = (
            by_severity.get("critical", 0) * 40 +
            by_severity.get("high", 0) * 25 +
            by_severity.get("medium", 0) * 15 +
            by_severity.get("low", 0) * 5
        )

        # Cap at 100
        return min(score, 100)

    def _get_risk_level(self, risk_score: int) -> str:
        """Get risk level from risk score."""
        if risk_score >= 75:
            return "critical"
        elif risk_score >= 50:
            return "high"
        elif risk_score >= 25:
            return "medium"
        else:
            return "low"

    def check_missing_security_policies(self, api: API) -> List[str]:
        """
        Check for missing security policies in API's policy_actions array.
        
        This method analyzes the vendor-neutral policy_actions to identify
        missing security policies that should be present.
        
        Args:
            api: API to check
            
        Returns:
            List of missing policy types
        """
        missing_policies = []
        
        # Get existing policy action types
        existing_types = set()
        if api.policy_actions:
            for policy_action in api.policy_actions:
                if policy_action.enabled:
                    existing_types.add(policy_action.action_type)
        
        # Check for required security policies
        required_policies = {
            PolicyActionType.AUTHENTICATION: "Authentication policy missing",
            PolicyActionType.AUTHORIZATION: "Authorization policy missing",
            PolicyActionType.TLS: "TLS/HTTPS enforcement missing",
            PolicyActionType.CORS: "CORS policy missing",
            PolicyActionType.VALIDATION: "Input validation policy missing",
        }
        
        for policy_type, message in required_policies.items():
            if policy_type not in existing_types:
                missing_policies.append(message)
        
        # Check for security headers (custom policy type)
        has_security_headers = False
        if api.policy_actions:
            for policy_action in api.policy_actions:
                if (policy_action.action_type == PolicyActionType.CUSTOM and
                    policy_action.enabled and
                    policy_action.config and
                    any(header in str(policy_action.config).lower()
                        for header in ['hsts', 'x-frame-options', 'x-content-type-options'])):
                    has_security_headers = True
                    break
        
        if not has_security_headers:
            missing_policies.append("Security headers policy missing")
        
    async def create_ticket(
        self,
        vulnerability_id: UUID,
        ticket_system: str = "jira",
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a manual ticket for non-remediable vulnerabilities.
        
        This method creates a ticket in an external ticketing system (e.g., Jira, ServiceNow)
        for vulnerabilities that require manual intervention.
        
        Args:
            vulnerability_id: Vulnerability to create ticket for
            ticket_system: Target ticketing system (default: "jira")
            assignee: Optional assignee for the ticket
            
        Returns:
            Ticket creation result with ticket ID and URL
        """
        try:
            logger.info(f"Creating manual ticket for vulnerability: {vulnerability_id}")
            
            # Get vulnerability details
            vulnerability = self.vulnerability_repository.get(str(vulnerability_id))
            if not vulnerability:
                raise ValueError(f"Vulnerability not found: {vulnerability_id}")
            
            # Get API details
            api = self.api_repository.get(str(vulnerability.api_id))
            if not api:
                raise ValueError(f"API not found: {vulnerability.api_id}")
            
            # Prepare ticket data
            ticket_data = {
                "title": f"[Security] {vulnerability.title} - {api.name}",
                "description": self._format_ticket_description(vulnerability, api),
                "priority": self._map_severity_to_priority(vulnerability.severity),
                "labels": [
                    "security",
                    "vulnerability",
                    vulnerability.vulnerability_type.value,
                    vulnerability.severity.value,
                ],
                "vulnerability_id": str(vulnerability_id),
                "api_id": str(api.id),
                "api_name": api.name,
            }
            
            if assignee:
                ticket_data["assignee"] = assignee
            
            # Create ticket in external system
            # Note: This is a placeholder for actual integration
            # In production, this would call the actual ticketing system API
            ticket_result = await self._create_external_ticket(
                ticket_system=ticket_system,
                ticket_data=ticket_data,
            )
            
            # Update vulnerability with ticket reference
            vulnerability.metadata = vulnerability.metadata or {}
            vulnerability.metadata["ticket_id"] = ticket_result["ticket_id"]
            vulnerability.metadata["ticket_url"] = ticket_result["ticket_url"]
            vulnerability.metadata["ticket_system"] = ticket_system
            vulnerability.updated_at = datetime.utcnow()
            
            self.vulnerability_repository.update(
                str(vulnerability.id),
                vulnerability.dict(exclude={"id"})
            )
            
            logger.info(
                f"Created ticket {ticket_result['ticket_id']} for vulnerability {vulnerability_id}"
            )
            
            return {
                "vulnerability_id": str(vulnerability_id),
                "ticket_id": ticket_result["ticket_id"],
                "ticket_url": ticket_result["ticket_url"],
                "ticket_system": ticket_system,
                "status": "created",
                "message": f"Ticket created successfully in {ticket_system}",
            }
            
        except Exception as e:
            logger.error(f"Failed to create ticket for vulnerability {vulnerability_id}: {str(e)}")
            raise
    
    def _format_ticket_description(
        self,
        vulnerability: Vulnerability,
        api: API,
    ) -> str:
        """Format vulnerability details for ticket description."""
        description = f"""
# Security Vulnerability Report

## Vulnerability Details
- **Type**: {vulnerability.vulnerability_type.value}
- **Severity**: {vulnerability.severity.value}
- **Status**: {vulnerability.status.value}
- **Detected**: {vulnerability.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Description
{vulnerability.description}

## Affected API
- **Name**: {api.name}
- **Base Path**: {api.base_path}
- **Gateway ID**: {api.gateway_id}

## Remediation Information
"""
        
        if vulnerability.recommended_remediation:
            description += "\n### Recommended Actions\n"
            for action in vulnerability.recommended_remediation.get("actions", []):
                description += f"- {action.get('action', 'N/A')}\n"
            
            if "estimated_time" in vulnerability.recommended_remediation:
                description += f"\n**Estimated Time**: {vulnerability.recommended_remediation['estimated_time']}\n"
        
        if vulnerability.remediation_type:
            description += f"\n**Remediation Type**: {vulnerability.remediation_type.value}\n"
        
        if vulnerability.affected_endpoints:
            description += "\n### Affected Endpoints\n"
            for endpoint in vulnerability.affected_endpoints:
                description += f"- {endpoint}\n"
        
        if vulnerability.references:
            description += "\n### References\n"
            for ref in vulnerability.references:
                description += f"- {ref}\n"
        
        return description.strip()
    
    def _map_severity_to_priority(self, severity: VulnerabilitySeverity) -> str:
        """Map vulnerability severity to ticket priority."""
        severity_to_priority = {
            VulnerabilitySeverity.CRITICAL: "highest",
            VulnerabilitySeverity.HIGH: "high",
            VulnerabilitySeverity.MEDIUM: "medium",
            VulnerabilitySeverity.LOW: "low",
        }
        return severity_to_priority.get(severity, "medium")
    
    async def _create_external_ticket(
        self,
        ticket_system: str,
        ticket_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create ticket in external ticketing system.
        
        This is a placeholder implementation. In production, this would integrate
        with actual ticketing systems like Jira, ServiceNow, GitHub Issues, etc.
        
        Args:
            ticket_system: Target ticketing system
            ticket_data: Ticket data to create
            
        Returns:
            Created ticket information
        """
        # Placeholder implementation
        # In production, this would call the actual API:
        # - Jira: Use jira-python library or REST API
        # - ServiceNow: Use ServiceNow REST API
        # - GitHub: Use PyGithub or GitHub REST API
        
        ticket_id = f"{ticket_system.upper()}-{uuid4().hex[:8]}"
        ticket_url = f"https://{ticket_system}.example.com/browse/{ticket_id}"
        
        logger.info(
            f"[PLACEHOLDER] Would create ticket in {ticket_system}: {ticket_id}"
        )
        
        return {
            "ticket_id": ticket_id,
            "ticket_url": ticket_url,
            "created_at": datetime.utcnow().isoformat(),
        }

        return missing_policies


# Made with Bob