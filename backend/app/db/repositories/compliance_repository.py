"""Compliance Violation repository for API Intelligence Plane.

Provides CRUD operations and queries for compliance violations.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from opensearchpy import OpenSearch

from app.db.repositories.base import BaseRepository
from app.models.compliance import ComplianceViolation, ComplianceStatus, ComplianceStandard


class ComplianceRepository(BaseRepository[ComplianceViolation]):
    """Repository for ComplianceViolation entities."""

    def __init__(self):
        """Initialize repository."""
        super().__init__(
            index_name="compliance-violations",
            model_class=ComplianceViolation,
        )

    async def find_existing_violation(
        self,
        gateway_id: UUID,
        api_id: UUID,
        violation_type: str,
        compliance_standard: str,
    ) -> Optional[ComplianceViolation]:
        """Find existing violation by unique key attributes.

        Args:
            gateway_id: Gateway identifier
            api_id: API identifier
            violation_type: Type of violation
            compliance_standard: Compliance standard

        Returns:
            Existing violation if found, None otherwise
        """
        query = {
            "bool": {
                "must": [
                    {"term": {"gateway_id": str(gateway_id)}},
                    {"term": {"api_id": str(api_id)}},
                    {"term": {"violation_type": violation_type}},
                    {"term": {"compliance_standard": compliance_standard}},
                ]
            }
        }

        body = {
            "query": query,
            "size": 1,
            "sort": [{"detected_at": {"order": "desc"}}],
        }

        response = self.client.search(index=self.index_name, body=body)
        hits = response["hits"]["hits"]
        
        if hits:
            return self.model_class(**hits[0]["_source"])
        return None

    async def find_by_api_id(
        self,
        api_id: UUID,
        gateway_id: Optional[UUID] = None,
        status: Optional[ComplianceStatus] = None,
        limit: int = 100,
    ) -> list[ComplianceViolation]:
        """Find compliance violations for a specific API.

        Args:
            api_id: API identifier
            gateway_id: Optional Gateway ID filter (primary dimension)
            status: Optional status filter
            limit: Maximum results to return

        Returns:
            List of compliance violations
        """
        must_clauses = [{"term": {"api_id": str(api_id)}}]
        
        if gateway_id:
            must_clauses.append({"term": {"gateway_id": str(gateway_id)}})
        
        query: dict[str, Any] = {
            "bool": {
                "must": must_clauses
            }
        }

        if status:
            query["bool"]["must"].append({"term": {"status": status.value}})

        body = {
            "query": query,
            "sort": [{"detected_at": {"order": "desc"}}],
            "size": limit,
        }

        response = self.client.search(index=self.index_name, body=body)
        return [
            self.model_class(**hit["_source"]) for hit in response["hits"]["hits"]
        ]

    async def find_by_standard(
        self,
        standard: ComplianceStandard,
        status: Optional[ComplianceStatus] = None,
        limit: int = 100,
    ) -> list[ComplianceViolation]:
        """Find violations by compliance standard.

        Args:
            standard: Compliance standard (GDPR, HIPAA, SOC2, PCI-DSS, ISO 27001)
            status: Optional status filter
            limit: Maximum results to return

        Returns:
            List of compliance violations
        """
        query: dict[str, Any] = {
            "bool": {
                "must": [
                    {"term": {"compliance_standard": standard.value}},
                ]
            }
        }

        if status:
            query["bool"]["must"].append({"term": {"status": status.value}})

        body = {
            "query": query,
            "sort": [{"detected_at": {"order": "desc"}}],
            "size": limit,
        }

        response = self.client.search(index=self.index_name, body=body)
        return [
            self.model_class(**hit["_source"]) for hit in response["hits"]["hits"]
        ]

    async def mark_undetected_as_resolved(
        self,
        gateway_id: UUID,
        api_id: UUID,
        detected_violation_ids: list[UUID],
        scan_time: datetime,
    ) -> int:
        """Mark violations not in detected list as resolved.
        
        This method finds all OPEN violations for an API that were NOT
        detected in the current scan and marks them as RESOLVED.
        
        Args:
            gateway_id: Gateway identifier
            api_id: API identifier
            detected_violation_ids: List of violation IDs found in current scan
            scan_time: Timestamp of the scan
            
        Returns:
            Number of violations marked as resolved
        """
        # Build query for OPEN violations not in detected list
        query = {
            "bool": {
                "must": [
                    {"term": {"gateway_id": str(gateway_id)}},
                    {"term": {"api_id": str(api_id)}},
                    {"term": {"status": ComplianceStatus.OPEN.value}},
                ],
                "must_not": [
                    {"terms": {"id.keyword": [str(vid) for vid in detected_violation_ids]}}
                ] if detected_violation_ids else []
            }
        }
        
        # Update script to mark as resolved
        script = {
            "source": """
                ctx._source.status = params.status;
                ctx._source.resolved_at = params.resolved_at;
                ctx._source.updated_at = params.updated_at;
            """,
            "params": {
                "status": ComplianceStatus.REMEDIATED.value,
                "resolved_at": scan_time.isoformat(),
                "updated_at": scan_time.isoformat(),
            }
        }
        
        body = {
            "query": query,
            "script": script,
        }
        
        try:
            response = self.client.update_by_query(
                index=self.index_name,
                body=body,
            )
            # Refresh index after update
            self.client.indices.refresh(index=self.index_name)
            updated_count = response.get("updated", 0)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                f"Marked {updated_count} violations as resolved for API {api_id} in gateway {gateway_id}"
            )
            return updated_count
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to mark violations as resolved: {e}")
            return 0

    async def find_by_severity(
        self,
        severity: str,
        status: Optional[ComplianceStatus] = None,
        limit: int = 100,
    ) -> list[ComplianceViolation]:
        """Find violations by severity level.

        Args:
            severity: Severity level (critical, high, medium, low)
            status: Optional status filter
            limit: Maximum results to return

        Returns:
            List of compliance violations
        """
        query: dict[str, Any] = {
            "bool": {
                "must": [
                    {"term": {"severity": severity}},
                ]
            }
        }

        if status:
            query["bool"]["must"].append({"term": {"status": status.value}})

        body = {
            "query": query,
            "sort": [{"detected_at": {"order": "desc"}}],
            "size": limit,
        }

        response = self.client.search(index=self.index_name, body=body)
        return [
            self.model_class(**hit["_source"]) for hit in response["hits"]["hits"]
        ]

    async def find_open_violations(
        self,
        api_id: Optional[UUID] = None,
        standard: Optional[ComplianceStandard] = None,
        limit: int = 100,
    ) -> list[ComplianceViolation]:
        """Find all open compliance violations.

        Args:
            api_id: Optional API filter
            standard: Optional compliance standard filter
            limit: Maximum results to return

        Returns:
            List of open compliance violations
        """
        query: dict[str, Any] = {
            "bool": {
                "must": [
                    {"term": {"status": ComplianceStatus.OPEN.value}},
                ]
            }
        }

        if api_id:
            query["bool"]["must"].append({"term": {"api_id": str(api_id)}})
        
        if standard:
            query["bool"]["must"].append({"term": {"compliance_standard": standard.value}})

        body = {
            "query": query,
            "sort": [
                {"severity": {"order": "asc"}},  # Critical first
                {"detected_at": {"order": "desc"}},
            ],
            "size": limit,
        }

        response = self.client.search(index=self.index_name, body=body)
        return [
            self.model_class(**hit["_source"]) for hit in response["hits"]["hits"]
        ]

    async def get_compliance_posture(
        self,
        api_id: Optional[UUID] = None,
        standard: Optional[ComplianceStandard] = None,
    ) -> dict[str, Any]:
        """Get compliance posture statistics.

        Args:
            api_id: Optional API filter
            standard: Optional compliance standard filter

        Returns:
            Compliance posture metrics
        """
        query: dict[str, Any] = {"bool": {"must": []}}

        if api_id:
            query["bool"]["must"].append({"term": {"api_id": str(api_id)}})
        
        if standard:
            query["bool"]["must"].append({"term": {"compliance_standard": standard.value}})

        if not query["bool"]["must"]:
            query = {"match_all": {}}

        body = {
            "query": query,
            "size": 0,
            "aggs": {
                "by_severity": {
                    "terms": {"field": "severity", "size": 10}
                },
                "by_status": {
                    "terms": {"field": "status", "size": 10}
                },
                "by_standard": {
                    "terms": {"field": "compliance_standard", "size": 10}
                },
                "by_violation_type": {
                    "terms": {"field": "violation_type", "size": 20}
                },
                "avg_remediation_time": {
                    "avg": {
                        "script": {
                            "source": """
                                if (doc['remediated_at'].size() > 0 && doc['detected_at'].size() > 0) {
                                    return doc['remediated_at'].value.toInstant().toEpochMilli() - 
                                           doc['detected_at'].value.toInstant().toEpochMilli();
                                }
                                return null;
                            """
                        }
                    }
                },
                "violations_by_month": {
                    "date_histogram": {
                        "field": "detected_at",
                        "calendar_interval": "month"
                    }
                },
            },
        }

        response = self.client.search(index=self.index_name, body=body)
        aggs = response["aggregations"]

        return {
            "total_violations": response["hits"]["total"]["value"],
            "by_severity": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_severity"]["buckets"]
            },
            "by_status": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_status"]["buckets"]
            },
            "by_standard": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_standard"]["buckets"]
            },
            "by_violation_type": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_violation_type"]["buckets"]
            },
            "avg_remediation_time_ms": aggs["avg_remediation_time"].get("value"),
            "violations_by_month": [
                {
                    "month": bucket["key_as_string"],
                    "count": bucket["doc_count"]
                }
                for bucket in aggs["violations_by_month"]["buckets"]
            ],
        }

    async def find_violations_needing_audit(
        self,
        days_until_audit: int = 30,
        limit: int = 100,
    ) -> list[ComplianceViolation]:
        """Find violations that need attention before upcoming audit.

        Args:
            days_until_audit: Days until next audit
            limit: Maximum results to return

        Returns:
            List of violations needing attention
        """
        from datetime import timedelta
        
        audit_date = datetime.utcnow() + timedelta(days=days_until_audit)
        
        query = {
            "bool": {
                "should": [
                    # Open violations
                    {"term": {"status": ComplianceStatus.OPEN.value}},
                    # In progress violations
                    {"term": {"status": ComplianceStatus.IN_PROGRESS.value}},
                ],
                "minimum_should_match": 1,
                "must": [
                    # Next audit date is approaching
                    {
                        "range": {
                            "next_audit_date": {
                                "lte": audit_date.isoformat()
                            }
                        }
                    }
                ]
            }
        }

        body = {
            "query": query,
            "sort": [
                {"severity": {"order": "asc"}},  # Critical first
                {"next_audit_date": {"order": "asc"}},  # Soonest audit first
            ],
            "size": limit,
        }

        response = self.client.search(index=self.index_name, body=body)
        return [
            self.model_class(**hit["_source"]) for hit in response["hits"]["hits"]
        ]

    async def generate_audit_report_data(
        self,
        standard: Optional[ComplianceStandard] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Generate data for audit report.

        Args:
            standard: Optional compliance standard filter
            start_date: Optional start date for report period
            end_date: Optional end date for report period

        Returns:
            Audit report data
        """
        query: dict[str, Any] = {"bool": {"must": []}}

        if standard:
            query["bool"]["must"].append({"term": {"compliance_standard": standard.value}})
        
        if start_date or end_date:
            date_range: dict[str, Any] = {}
            if start_date:
                date_range["gte"] = start_date.isoformat()
            if end_date:
                date_range["lte"] = end_date.isoformat()
            query["bool"]["must"].append({"range": {"detected_at": date_range}})

        if not query["bool"]["must"]:
            query = {"match_all": {}}

        body = {
            "query": query,
            "size": 0,
            "aggs": {
                "total_violations": {
                    "value_count": {"field": "id"}
                },
                "by_severity": {
                    "terms": {"field": "severity", "size": 10}
                },
                "by_status": {
                    "terms": {"field": "status", "size": 10}
                },
                "by_standard": {
                    "terms": {"field": "compliance_standard", "size": 10}
                },
                "by_violation_type": {
                    "terms": {"field": "violation_type", "size": 30}
                },
                "remediated_count": {
                    "filter": {"term": {"status": ComplianceStatus.REMEDIATED.value}}
                },
                "open_count": {
                    "filter": {"term": {"status": ComplianceStatus.OPEN.value}}
                },
                "critical_count": {
                    "filter": {"term": {"severity": "critical"}}
                },
                "high_count": {
                    "filter": {"term": {"severity": "high"}}
                },
            },
        }

        response = self.client.search(index=self.index_name, body=body)
        aggs = response["aggregations"]

        total = response["hits"]["total"]["value"]
        remediated = aggs["remediated_count"]["doc_count"]
        
        return {
            "report_period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "summary": {
                "total_violations": total,
                "remediated_violations": remediated,
                "open_violations": aggs["open_count"]["doc_count"],
                "critical_violations": aggs["critical_count"]["doc_count"],
                "high_violations": aggs["high_count"]["doc_count"],
                "remediation_rate": (remediated / total * 100) if total > 0 else 0,
            },
            "by_severity": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_severity"]["buckets"]
            },
            "by_status": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_status"]["buckets"]
            },
            "by_standard": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_standard"]["buckets"]
            },
            "by_violation_type": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs["by_violation_type"]["buckets"]
            },
        }

    def search_compliance_violations(
        self,
        standard: Optional[ComplianceStandard] = None,
        violation_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[ComplianceStatus] = None,
        api_name: Optional[str] = None,
        gateway_id: Optional[UUID] = None,
        discovered_after: Optional[datetime] = None,
        discovered_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ComplianceViolation], int]:
        """
        Search compliance violations with multiple filter criteria.
        
        This method provides flexible multi-criteria filtering for agents,
        complementing existing list/get methods with standard, violation type,
        severity, and date range filtering.
        
        Args:
            standard: Compliance standard filter (GDPR, HIPAA, SOC2, PCI_DSS, ISO_27001)
            violation_type: Violation type filter
            severity: Violation severity (critical, high, medium, low)
            status: Violation status filter
            api_name: API name pattern (case-insensitive wildcard match)
            gateway_id: Filter by gateway ID
            discovered_after: Filter violations discovered after this date
            discovered_before: Filter violations discovered before this date
            page: Page number (1-based)
            page_size: Number of results per page (default: 20, max: 100)
            
        Returns:
            Tuple of (list of compliance violations, total count)
            
        Examples:
            # Show GDPR violations with high severity from last quarter
            from datetime import datetime, timedelta
            quarter_ago = datetime.utcnow() - timedelta(days=90)
            violations, total = repo.search_compliance_violations(
                standard=ComplianceStandard.GDPR,
                severity="high",
                discovered_after=quarter_ago
            )
        """
        # Validate and normalize pagination
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        from_ = (page - 1) * page_size
        
        # Build bool query with must clauses
        must_clauses = []
        
        # Standard filter
        if standard:
            standard_value = standard.value if isinstance(standard, ComplianceStandard) else standard
            must_clauses.append({
                "term": {"compliance_standard": standard_value}
            })
        
        # Violation type filter
        if violation_type:
            must_clauses.append({
                "term": {"violation_type": violation_type.lower()}
            })
        
        # Severity filter
        if severity:
            must_clauses.append({
                "term": {"severity": severity.lower()}
            })
        
        # Status filter
        if status:
            status_value = status.value if isinstance(status, ComplianceStatus) else status
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # API name filter (case-insensitive wildcard)
        if api_name:
            must_clauses.append({
                "wildcard": {
                    "api_name": {
                        "value": f"*{api_name.lower()}*",
                        "case_insensitive": True
                    }
                }
            })
        
        # Gateway filter
        if gateway_id:
            must_clauses.append({
                "term": {"gateway_id": str(gateway_id)}
            })
        
        # Date range filters
        if discovered_after or discovered_before:
            range_query: dict[str, Any] = {}
            if discovered_after:
                range_query["gte"] = discovered_after.isoformat()
            if discovered_before:
                range_query["lte"] = discovered_before.isoformat()
            must_clauses.append({
                "range": {"detected_at": range_query}
            })
        
        # Build final query
        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}]
            }
        }
        
        # Execute search with sorting by severity (critical first) and detected_at (newest first)
        body = {
            "query": query,
            "sort": [
                {"severity": {"order": "asc"}},  # critical < high < medium < low
                {"detected_at": {"order": "desc"}}
            ],
            "size": page_size,
            "from": from_,
        }
        
        try:
            response = self.client.search(index=self.index_name, body=body)
            violations = [
                self.model_class(**hit["_source"]) for hit in response["hits"]["hits"]
            ]
            total = response["hits"]["total"]["value"]
            return violations, total
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to search compliance violations: {e}")
            return [], 0


# Made with Bob