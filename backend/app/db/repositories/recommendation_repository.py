"""
Recommendation Repository

Handles CRUD operations and queries for optimization recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.db.repositories.base import BaseRepository
from app.models.recommendation import (
    OptimizationRecommendation,
    RecommendationType,
    RecommendationPriority,
    RecommendationStatus,
)


class RecommendationRepository(BaseRepository[OptimizationRecommendation]):
    """Repository for managing optimization recommendations"""

    def __init__(self):
        super().__init__(
            index_name="optimization-recommendations",
            model_class=OptimizationRecommendation,
        )

    def create_recommendation(
        self, recommendation: OptimizationRecommendation
    ) -> OptimizationRecommendation:
        """
        Create a new recommendation

        Args:
            recommendation: OptimizationRecommendation model instance

        Returns:
            Created recommendation with ID
        """
        return self.create(recommendation)

    def check_duplicate_recommendation(
        self,
        gateway_id: str,
        api_id: str,
        recommendation_type: RecommendationType,
        status: RecommendationStatus = RecommendationStatus.PENDING,
    ) -> Optional[OptimizationRecommendation]:
        """
        Check if a similar recommendation already exists for the API in the gateway

        Args:
            gateway_id: Gateway UUID
            api_id: API UUID
            recommendation_type: Type of recommendation
            status: Status to check (default: PENDING)

        Returns:
            Existing recommendation if found, None otherwise
        """
        query = {
            "bool": {
                "must": [
                    {"term": {"gateway_id": gateway_id}},
                    {"term": {"api_id": api_id}},
                    {"term": {"recommendation_type": recommendation_type.value}},
                    {"term": {"status": status.value}},
                ]
            }
        }

        recommendations, _ = self.search(query=query, size=1)
        return recommendations[0] if recommendations else None

    async def mark_outdated_as_expired(
        self,
        gateway_id: UUID,
        api_id: UUID,
        current_recommendation_ids: list[UUID],
    ) -> int:
        """Mark recommendations not in current list as expired.
        
        This method finds all PENDING recommendations for an API that are NOT
        in the current recommendation list and marks them as EXPIRED.
        
        Args:
            gateway_id: Gateway identifier
            api_id: API identifier
            current_recommendation_ids: List of recommendation IDs from current analysis
            
        Returns:
            Number of recommendations marked as expired
        """
        from datetime import datetime
        
        # Build query for PENDING recommendations not in current list
        query = {
            "bool": {
                "must": [
                    {"term": {"gateway_id": str(gateway_id)}},
                    {"term": {"api_id": str(api_id)}},
                    {"term": {"status": RecommendationStatus.PENDING.value}},
                ],
                "must_not": [
                    {"terms": {"id.keyword": [str(rid) for rid in current_recommendation_ids]}}
                ] if current_recommendation_ids else []
            }
        }
        
        # Update script to mark as expired
        script = {
            "source": """
                ctx._source.status = params.status;
                ctx._source.updated_at = params.updated_at;
            """,
            "params": {
                "status": RecommendationStatus.EXPIRED.value,
                "updated_at": datetime.utcnow().isoformat(),
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
                f"Marked {updated_count} recommendations as expired for API {api_id} in gateway {gateway_id}"
            )
            return updated_count
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to mark recommendations as expired: {e}")
            return 0

    def get_recommendation(
        self, recommendation_id: str
    ) -> Optional[OptimizationRecommendation]:
        """
        Get recommendation by ID

        Args:
            recommendation_id: Recommendation UUID

        Returns:
            Recommendation if found, None otherwise
        """
        return self.get(recommendation_id)

    def list_recommendations(
        self,
        gateway_id: Optional[str] = None,
        api_id: Optional[str] = None,
        priority: Optional[RecommendationPriority] = None,
        status: Optional[RecommendationStatus] = None,
        recommendation_type: Optional[RecommendationType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List recommendations with filters

        Args:
            gateway_id: Filter by Gateway ID (primary dimension)
            api_id: Filter by API ID (secondary dimension)
            priority: Filter by priority level
            status: Filter by recommendation status
            recommendation_type: Filter by recommendation type
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Dict with recommendations list and pagination info
        """
        must_clauses = []

        if gateway_id:
            must_clauses.append({"term": {"gateway_id": gateway_id}})
        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})
        if priority:
            must_clauses.append({"term": {"priority": priority.value}})
        if status:
            must_clauses.append({"term": {"status": status.value}})
        if recommendation_type:
            must_clauses.append(
                {"term": {"recommendation_type": recommendation_type.value}}
            )

        # Default to pending recommendations if no status filter
        if not status:
            must_clauses.append({"term": {"status": RecommendationStatus.PENDING.value}})

        query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

        # Sort by priority (critical first) and estimated impact (highest first)
        sort = [
            {
                "priority": {
                    "order": "asc",
                    "unmapped_type": "keyword",
                }
            },
            {
                "estimated_impact.improvement_percentage": {
                    "order": "desc",
                    "unmapped_type": "float",
                }
            },
        ]

        # Calculate offset from page number
        from_ = (page - 1) * page_size

        recommendations, total = self.search(
            query=query,
            sort=sort,
            size=page_size,
            from_=from_,
        )

        return {
            "recommendations": recommendations,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_pending_recommendations_for_api(
        self, api_id: str
    ) -> List[OptimizationRecommendation]:
        """
        Get all pending recommendations for a specific API

        Args:
            api_id: API UUID

        Returns:
            List of pending recommendations
        """
        query = {
            "bool": {
                "must": [
                    {"term": {"api_id": api_id}},
                    {"term": {"status": RecommendationStatus.PENDING.value}},
                ]
            }
        }

        recommendations, _ = self.search(query=query, size=100)
        return recommendations

    def get_recommendations_by_type(
        self,
        recommendation_type: RecommendationType,
        api_id: Optional[str] = None,
    ) -> List[OptimizationRecommendation]:
        """
        Get recommendations by type

        Args:
            recommendation_type: Type of recommendation
            api_id: Optional API ID filter

        Returns:
            List of recommendations
        """
        must_clauses = [
            {"term": {"recommendation_type": recommendation_type.value}},
        ]

        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})

        query = {"bool": {"must": must_clauses}}

        recommendations, _ = self.search(query=query, size=100)
        return recommendations

    def update_recommendation_status(
        self,
        recommendation_id: str,
        status: RecommendationStatus,
        implemented_at: Optional[datetime] = None,
    ) -> Optional[OptimizationRecommendation]:
        """
        Update recommendation status

        Args:
            recommendation_id: Recommendation UUID
            status: New status
            implemented_at: When the recommendation was implemented

        Returns:
            Updated recommendation if found
        """
        update_doc = {
            "status": status.value,
        }

        if implemented_at:
            update_doc["implemented_at"] = implemented_at.isoformat()

        return self.update(recommendation_id, update_doc)

    def add_validation_results(
        self,
        recommendation_id: str,
        validation_results: Dict[str, Any],
    ) -> Optional[OptimizationRecommendation]:
        """
        Add validation results after implementation

        Args:
            recommendation_id: Recommendation UUID
            validation_results: Validation results data

        Returns:
            Updated recommendation with validation results
        """
        update_doc = {
            "validation_results": validation_results,
        }

        return self.update(recommendation_id, update_doc)

    def get_high_impact_recommendations(
        self,
        min_improvement: float = 20.0,
        api_id: Optional[str] = None,
    ) -> List[OptimizationRecommendation]:
        """
        Get high-impact recommendations

        Args:
            min_improvement: Minimum improvement percentage
            api_id: Optional API ID filter

        Returns:
            List of high-impact recommendations
        """
        must_clauses = [
            {
                "range": {
                    "estimated_impact.improvement_percentage": {"gte": min_improvement}
                }
            },
            {"term": {"status": RecommendationStatus.PENDING.value}},
        ]

        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})

        query = {"bool": {"must": must_clauses}}

        recommendations, _ = self.search(query=query, size=100)
        return recommendations

    def get_expired_recommendations(self) -> List[OptimizationRecommendation]:
        """
        Get recommendations that have expired

        Returns:
            List of expired pending recommendations
        """
        now = datetime.utcnow()
        query = {
            "bool": {
                "must": [
                    {"term": {"status": RecommendationStatus.PENDING.value}},
                    {"range": {"expires_at": {"lt": now.isoformat()}}},
                ]
            }
        }

        recommendations, _ = self.search(query=query, size=1000)
        return recommendations

    def get_implementation_stats(
        self, api_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get recommendation implementation statistics

        Args:
            api_id: Optional API ID filter
            days: Number of days to look back

        Returns:
            Dict with implementation statistics
        """
        start_time = datetime.utcnow() - timedelta(days=days)

        must_clauses = [
            {"range": {"created_at": {"gte": start_time.isoformat()}}},
        ]

        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})

        query = {"bool": {"must": must_clauses}}

        # Aggregation for statistics
        aggs = {
            "by_status": {
                "terms": {"field": "status"},
            },
            "by_priority": {
                "terms": {"field": "priority"},
            },
            "by_type": {
                "terms": {"field": "recommendation_type"},
            },
            "avg_improvement": {
                "avg": {"field": "estimated_impact.improvement_percentage"}
            },
            "total_cost_savings": {"sum": {"field": "cost_savings"}},
        }

        result = self.client.search(
            index=self.index_name, body={"query": query, "aggs": aggs, "size": 0}
        )

        aggregations = result.get("aggregations", {})

        return {
            "total_recommendations": result["hits"]["total"]["value"],
            "by_status": [
                {"status": bucket["key"], "count": bucket["doc_count"]}
                for bucket in aggregations.get("by_status", {}).get("buckets", [])
            ],
            "by_priority": [
                {"priority": bucket["key"], "count": bucket["doc_count"]}
                for bucket in aggregations.get("by_priority", {}).get("buckets", [])
            ],
            "by_type": [
                {"type": bucket["key"], "count": bucket["doc_count"]}
                for bucket in aggregations.get("by_type", {}).get("buckets", [])
            ],
            "avg_improvement": aggregations.get("avg_improvement", {}).get("value", 0),
            "total_cost_savings": aggregations.get("total_cost_savings", {}).get(
                "value", 0
            ),
        }

    def get_validation_success_rate(
        self, api_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get validation success rate for implemented recommendations

        Args:
            api_id: Optional API ID filter
            days: Number of days to look back

        Returns:
            Dict with validation statistics
        """
        start_time = datetime.utcnow() - timedelta(days=days)

        must_clauses = [
            {"term": {"status": RecommendationStatus.IMPLEMENTED.value}},
            {"exists": {"field": "validation_results"}},
            {"range": {"implemented_at": {"gte": start_time.isoformat()}}},
        ]

        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})

        query = {"bool": {"must": must_clauses}}

        # Aggregation for success rate
        aggs = {
            "by_success": {
                "terms": {"field": "validation_results.success"},
            },
            "avg_actual_improvement": {
                "avg": {"field": "validation_results.actual_impact.actual_improvement"}
            },
        }

        result = self.client.search(
            index=self.index_name, body={"query": query, "aggs": aggs, "size": 0}
        )

        aggregations = result.get("aggregations", {})
        total = result["hits"]["total"]["value"]

        success_buckets = aggregations.get("by_success", {}).get("buckets", [])
        success_count = next(
            (b["doc_count"] for b in success_buckets if b["key"] == True), 0
        )

        return {
            "total_validated": total,
            "successful": success_count,
            "failed": total - success_count,
            "success_rate": (success_count / total * 100) if total > 0 else 0,
            "avg_actual_improvement": aggregations.get("avg_actual_improvement", {}).get(
                "value", 0
            ),
        }

    def delete_old_recommendations(self, days: int = 90) -> int:
        """
        Delete recommendations older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of deleted recommendations
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = {"range": {"created_at": {"lt": cutoff_date.isoformat()}}}

        result = self.client.delete_by_query(
            index=self.index_name, body={"query": query}
        )

        return result.get("deleted", 0)

    def search_recommendations(
        self,
        type: Optional[RecommendationType] = None,
        priority: Optional[RecommendationPriority] = None,
        status: Optional[RecommendationStatus] = None,
        impact_min: Optional[float] = None,
        impact_max: Optional[float] = None,
        api_name: Optional[str] = None,
        gateway_id: Optional[UUID] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[OptimizationRecommendation], int]:
        """
        Search optimization recommendations with multiple filter criteria.
        
        This method provides flexible multi-criteria filtering for agents,
        complementing existing list/get methods with type, priority, status,
        impact range, and date filtering.
        
        Args:
            type: Recommendation type filter (caching, rate_limiting, etc.)
            priority: Recommendation priority filter (critical, high, medium, low)
            status: Recommendation status filter (pending, implemented, rejected)
            impact_min: Minimum expected impact percentage (0-100)
            impact_max: Maximum expected impact percentage (0-100)
            api_name: API name pattern (case-insensitive wildcard match)
            gateway_id: Filter by gateway ID
            created_after: Filter recommendations created after this date
            created_before: Filter recommendations created before this date
            page: Page number (1-based)
            page_size: Number of results per page (default: 20, max: 100)
            
        Returns:
            Tuple of (list of recommendations, total count)
            
        Examples:
            # Find caching recommendations with high priority that are pending
            recs, total = repo.search_recommendations(
                type=RecommendationType.CACHING,
                priority=RecommendationPriority.HIGH,
                status=RecommendationStatus.PENDING
            )
            
            # Find high-impact recommendations (>20%)
            recs, total = repo.search_recommendations(
                impact_min=20.0,
                status=RecommendationStatus.PENDING
            )
        """
        # Validate and normalize pagination
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        from_ = (page - 1) * page_size
        
        # Validate impact ranges
        if impact_min is not None:
            impact_min = max(0.0, min(100.0, impact_min))
        if impact_max is not None:
            impact_max = max(0.0, min(100.0, impact_max))
        
        # Build bool query with must clauses
        must_clauses = []
        
        # Type filter
        if type:
            type_value = type.value if isinstance(type, RecommendationType) else type
            must_clauses.append({
                "term": {"recommendation_type": type_value}
            })
        
        # Priority filter
        if priority:
            priority_value = priority.value if isinstance(priority, RecommendationPriority) else priority
            must_clauses.append({
                "term": {"priority": priority_value}
            })
        
        # Status filter
        if status:
            status_value = status.value if isinstance(status, RecommendationStatus) else status
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # Impact range
        if impact_min is not None or impact_max is not None:
            range_query: Dict[str, Any] = {}
            if impact_min is not None:
                range_query["gte"] = impact_min
            if impact_max is not None:
                range_query["lte"] = impact_max
            must_clauses.append({
                "range": {"expected_impact": range_query}
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
        if created_after or created_before:
            date_range_query: Dict[str, Any] = {}
            if created_after:
                date_range_query["gte"] = created_after.isoformat()
            if created_before:
                date_range_query["lte"] = created_before.isoformat()
            must_clauses.append({
                "range": {"created_at": date_range_query}
            })
        
        # Build final query
        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}]
            }
        }
        
        # Execute search with sorting by priority (critical first) and created_at (newest first)
        sort = [
            {"priority": {"order": "asc"}},  # critical < high < medium < low
            {"created_at": {"order": "desc"}}
        ]
        
        try:
            recommendations, total = self.search(query, size=page_size, from_=from_, sort=sort)
            return recommendations, total
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to search recommendations: {e}")
            return [], 0


# Made with Bob