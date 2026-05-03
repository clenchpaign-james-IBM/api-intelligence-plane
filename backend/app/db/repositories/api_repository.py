"""
API Repository

Provides CRUD operations and specialized queries for API entities.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from app.db.repositories.base import BaseRepository
from app.models.base.api import API, APIStatus, AuthenticationType, DiscoveryMethod, PolicyAction, PolicyActionType

logger = logging.getLogger(__name__)


class APIRepository(BaseRepository[API]):
    """Repository for API entity operations."""
    
    def __init__(self):
        """Initialize the API repository."""
        super().__init__(index_name="api-inventory", model_class=API)
    
    def find_by_gateway(
        self,
        gateway_id: UUID,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find all APIs belonging to a specific gateway.
        
        Args:
            gateway_id: Gateway UUID
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        query = {
            "term": {
                "gateway_id": str(gateway_id)
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_by_status(
        self,
        status: APIStatus,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find all APIs with a specific status.
        
        Args:
            status: API status to filter by
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        query = {
            "term": {
                "status": status.value
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_shadow_apis(
        self,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find all shadow APIs.
        
        Args:
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of shadow APIs, total count)
        """
        query = {
            "term": {
                "intelligence_metadata.is_shadow": True
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_by_discovery_method(
        self,
        method: DiscoveryMethod,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find APIs by discovery method.
        
        Args:
            method: Discovery method to filter by
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        query = {
            "term": {
                "intelligence_metadata.discovery_method": method.value
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def search_by_name(
        self,
        name: str,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Search APIs by name (fuzzy match).
        
        Args:
            name: Name to search for
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        query = {
            "match": {
                "name": {
                    "query": name,
                    "fuzziness": "AUTO"
                }
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def search_by_tags(
        self,
        tags: List[str],
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Search APIs by tags.
        
        Args:
            tags: List of tags to search for
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        query = {
            "terms": {
                "tags": tags
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_unhealthy_apis(
        self,
        health_threshold: float = 50.0,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find APIs with health score below threshold.
        
        Args:
            health_threshold: Health score threshold (0-100)
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of unhealthy APIs, total count)
        """
        query = {
            "range": {
                "intelligence_metadata.health_score": {
                    "lt": health_threshold
                }
            }
        }
        sort = [{"intelligence_metadata.health_score": {"order": "asc"}}]
        return self.search(query, size=size, from_=from_, sort=sort)
    
    def find_by_gateway_and_api_id(
        self,
        gateway_id: UUID,
        api_id: UUID,
    ) -> Optional[API]:
        """
        Find API by gateway_id and api_id (unique key combination).
        
        Args:
            gateway_id: Gateway UUID
            api_id: API UUID
            
        Returns:
            API if found, None otherwise
        """
        query: Dict[str, Any] = {
            "bool": {
                "must": [
                    {"term": {"gateway_id": str(gateway_id)}},
                    {"term": {"id": str(api_id)}}
                ]
            }
        }
        
        results, _ = self.search(query, size=1)
        return results[0] if results else None
    
    def find_by_base_path(
        self,
        base_path: str,
        gateway_id: Optional[UUID] = None,
    ) -> Optional[API]:
        """
        Find API by base path (and optionally gateway).
        
        Args:
            base_path: Base path to search for
            gateway_id: Optional gateway ID to narrow search
            
        Returns:
            API if found, None otherwise
        """
        query: Dict[str, Any] = {
            "bool": {
                "must": [
                    {"term": {"base_path": base_path}}
                ]
            }
        }
        
        if gateway_id:
            query["bool"]["must"].append(
                {"term": {"gateway_id": str(gateway_id)}}
            )
        
        results, _ = self.search(query, size=1)
        return results[0] if results else None
    def find_by_request_path(
        self,
        request_path: str,
        gateway_id: UUID,
    ) -> Optional[API]:
        """
        Find API by matching request path against registered patterns.
        
        Uses path parsing and pattern matching to identify the API that handles
        a given request path, accounting for gateway routing and path parameters.
        
        Args:
            request_path: Full request path from transactional log
                         (e.g., /gateway/users-api/v1/users/123/profile)
            gateway_id: Gateway UUID
        
        Returns:
            Matching API if found, None otherwise
        
        Algorithm:
            1. Parse request_path to extract components (gateway_prefix, api_name, 
               api_version, resource_path)
            2. Query APIs by gateway_id, api_name, and api_version
            3. For each candidate API, check if resource_path matches any endpoint
            4. Return first matching API
        
        Example:
            >>> repo = APIRepository()
            >>> api = repo.find_by_request_path(
            ...     "/gateway/users-api/v1/users/123/profile",
            ...     gateway_id=UUID("...")
            ... )
        """
        from app.utils.path_matcher import parse_request_path, matches_api_endpoints
        
        # Parse the request path
        components = parse_request_path(request_path)
        if not components:
            logger.debug(f"Could not parse request path: {request_path}")
            return None
        
        # Query candidate APIs by gateway_id, api_name, and api_version
        query: Dict[str, Any] = {
            "bool": {
                "must": [
                    {"term": {"gateway_id": str(gateway_id)}},
                ]
            }
        }
        
        # Add api_name filter with multiple strategies
        # Try exact match first, then fuzzy match
        query["bool"]["should"] = [
            # Exact match on name.keyword (if available)
            {"term": {"name.keyword": components.api_name}},
            # Case-insensitive match
            {"match": {
                "name": {
                    "query": components.api_name,
                    "operator": "and",
                    "fuzziness": "AUTO"
                }
            }},
            # Phrase match for names with spaces
            {"match_phrase": {
                "name": components.api_name
            }}
        ]
        query["bool"]["minimum_should_match"] = 1
        
        # Add version filter as additional should clause
        query["bool"]["should"].extend([
            {"term": {"version_info.current_version": components.api_version}},
            {"match": {"version_info.current_version": components.api_version}}
        ])
        
        # Boost results that match both name and version
        candidates, _ = self.search(query, size=20)
        
        # Filter candidates by version if we got results
        if candidates and components.api_version:
            version_matched = [
                api for api in candidates
                if hasattr(api, 'version_info') and
                   hasattr(api.version_info, 'current_version') and
                   api.version_info.current_version == components.api_version
            ]
            if version_matched:
                candidates = version_matched
        
        if not candidates:
            logger.debug(
                f"No candidate APIs found for gateway={gateway_id}, "
                f"api_name={components.api_name}, version={components.api_version}"
            )
            return None
        
        # Match resource path against API endpoints
        for api in candidates:
            if matches_api_endpoints(components.resource_path, api):
                logger.debug(
                    f"Matched request path {request_path} to API {api.name} "
                    f"(id={api.id})"
                )
                return api
        
        logger.debug(
            f"No API matched resource path {components.resource_path} "
            f"from {len(candidates)} candidates"
        )
        return None
    
    
    def advanced_search(
        self,
        filters: Dict[str, Any],
        size: int = 100,
        from_: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> tuple[List[API], int]:
        """
        Advanced search with multiple filters.
        
        Args:
            filters: Dictionary of filter criteria
                - gateway_id: UUID
                - status: APIStatus
                - is_shadow: bool
                - min_health_score: float
                - max_health_score: float
                - tags: List[str]
                - name: str (fuzzy match)
            size: Number of results to return
            from_: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        must_clauses = []
        
        # Gateway filter
        if "gateway_id" in filters:
            must_clauses.append({
                "term": {"gateway_id": str(filters["gateway_id"])}
            })
        
        # Status filter
        if "status" in filters:
            status_value = filters["status"].value if isinstance(filters["status"], APIStatus) else filters["status"]
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # Shadow API filter
        if "is_shadow" in filters:
            must_clauses.append({
                "term": {"intelligence_metadata.is_shadow": filters["is_shadow"]}
            })
        
        # Health score range
        if "min_health_score" in filters or "max_health_score" in filters:
            range_query: Dict[str, Any] = {}
            if "min_health_score" in filters:
                range_query["gte"] = filters["min_health_score"]
            if "max_health_score" in filters:
                range_query["lte"] = filters["max_health_score"]
            must_clauses.append({
                "range": {"intelligence_metadata.health_score": range_query}
            })
        
        # Tags filter
        if "tags" in filters and filters["tags"]:
            must_clauses.append({
                "terms": {"tags": filters["tags"]}
            })
        
        # Name search (fuzzy)
        if "name" in filters:
            must_clauses.append({
                "match": {
                    "name": {
                        "query": filters["name"],
                        "fuzziness": "AUTO"
                    }
                }
            })
        
        # Build query
        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}]
            }
        }
        
        # Build sort
        sort = None
        if sort_by:
            sort = [{sort_by: {"order": sort_order}}]
        
        return self.search(query, size=size, from_=from_, sort=sort)
    
    def get_statistics(self, gateway_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get API statistics.
        
        Args:
            gateway_id: Optional gateway ID to filter by
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Build aggregation query
            aggs = {
                "total_apis": {"value_count": {"field": "id"}},
                "shadow_apis": {
                    "filter": {"term": {"intelligence_metadata.is_shadow": True}}
                },
                "by_status": {
                    "terms": {"field": "status"}
                },
                "by_discovery_method": {
                    "terms": {"field": "intelligence_metadata.discovery_method"}
                },
                "avg_health_score": {
                    "avg": {"field": "intelligence_metadata.health_score"}
                },
                "health_distribution": {
                    "histogram": {
                        "field": "intelligence_metadata.health_score",
                        "interval": 10
                    }
                }
            }
            
            # Add gateway filter if specified
            query = {"match_all": {}}
            if gateway_id:
                query = {"term": {"gateway_id": str(gateway_id)}}
            
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "query": query,
                    "aggs": aggs
                }
            )
            
            return {
                "total_apis": response["aggregations"]["total_apis"]["value"],
                "shadow_apis": response["aggregations"]["shadow_apis"]["doc_count"],
                "by_status": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in response["aggregations"]["by_status"]["buckets"]
                },
                "by_discovery_method": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in response["aggregations"]["by_discovery_method"]["buckets"]
                },
                "avg_health_score": response["aggregations"]["avg_health_score"]["value"],
                "health_distribution": [
                    {"range": f"{bucket['key']}-{bucket['key']+10}", "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["health_distribution"]["buckets"]
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get API statistics: {e}")
            raise


    def search_apis(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[APIStatus] = None,
        authentication_type: Optional[AuthenticationType] = None,
        is_shadow: Optional[bool] = None,
        health_score_min: Optional[float] = None,
        health_score_max: Optional[float] = None,
        gateway_id: Optional[UUID] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[API], int]:
        """
        Search APIs with multiple filter criteria.
        
        This method provides flexible multi-criteria filtering for agents,
        complementing existing list/get methods with text pattern matching,
        health score ranges, and date filtering.
        
        Args:
            name: API name pattern (case-insensitive wildcard match)
            description: Description pattern (case-insensitive text search)
            status: API status filter
            authentication_type: Authentication type filter
            is_shadow: Filter for shadow APIs (True/False/None for all)
            health_score_min: Minimum health score (0.0-1.0)
            health_score_max: Maximum health score (0.0-1.0)
            gateway_id: Filter by gateway ID
            created_after: Filter APIs created after this date
            created_before: Filter APIs created before this date
            page: Page number (1-based)
            page_size: Number of results per page (default: 20, max: 100)
            
        Returns:
            Tuple of (list of APIs, total count)
            
        Examples:
            # Find APIs with "payment" in name that have authentication enabled
            apis, total = repo.search_apis(
                name="payment",
                authentication_type=AuthenticationType.OAUTH2
            )
            
            # Find shadow APIs with low health scores
            apis, total = repo.search_apis(
                is_shadow=True,
                health_score_max=0.5
            )
        """
        # Validate and normalize pagination
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        from_ = (page - 1) * page_size
        
        # Validate health score ranges
        if health_score_min is not None:
            health_score_min = max(0.0, min(1.0, health_score_min))
        if health_score_max is not None:
            health_score_max = max(0.0, min(1.0, health_score_max))
        
        # Build bool query with must clauses
        must_clauses = []
        
        # Name filter (case-insensitive wildcard)
        if name:
            must_clauses.append({
                "wildcard": {
                    "name": {
                        "value": f"*{name.lower()}*",
                        "case_insensitive": True
                    }
                }
            })
        
        # Description filter (text search)
        if description:
            must_clauses.append({
                "match": {
                    "description": {
                        "query": description,
                        "operator": "and"
                    }
                }
            })
        
        # Status filter
        if status:
            status_value = status.value if isinstance(status, APIStatus) else status
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # Authentication type filter
        if authentication_type:
            auth_value = authentication_type.value if isinstance(authentication_type, AuthenticationType) else authentication_type
            must_clauses.append({
                "term": {"authentication.type": auth_value}
            })
        
        # Shadow API filter
        if is_shadow is not None:
            must_clauses.append({
                "term": {"intelligence_metadata.is_shadow": is_shadow}
            })
        
        # Health score range
        if health_score_min is not None or health_score_max is not None:
            range_query: Dict[str, Any] = {}
            if health_score_min is not None:
                range_query["gte"] = health_score_min
            if health_score_max is not None:
                range_query["lte"] = health_score_max
            must_clauses.append({
                "range": {"intelligence_metadata.health_score": range_query}
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
        
        # Execute search with sorting by created_at (newest first)
        sort = [{"created_at": {"order": "desc"}}]
        return self.search(query, size=page_size, from_=from_, sort=sort)


# Made with Bob
    
    def derive_security_policies(self, api: API) -> List[PolicyAction]:
        """
        Derive security-related policy actions from an API's policy_actions array.
        
        Filters policy_actions for security-related types:
        - AUTHENTICATION
        - AUTHORIZATION
        - TLS
        - CORS
        - VALIDATION
        - DATA_MASKING
        
        Args:
            api: API entity to analyze
            
        Returns:
            List of security-related PolicyAction objects
        """
        # Define security-related policy types
        security_types = {
            PolicyActionType.AUTHENTICATION,
            PolicyActionType.AUTHORIZATION,
            PolicyActionType.TLS,
            PolicyActionType.CORS,
            PolicyActionType.VALIDATION,
            PolicyActionType.DATA_MASKING,
        }
        
        # Handle case where policy_actions might be None
        if not api.policy_actions:
            logger.info(f"API {api.id} has no policy actions")
            return []
        
        # Filter policy actions for security types
        security_policies = [
            policy_action
            for policy_action in api.policy_actions
            if policy_action.action_type in security_types
        ]
        
        logger.info(
            f"Derived {len(security_policies)} security policies from API {api.id} "
            f"(total policies: {len(api.policy_actions)})"
        )
        
        return security_policies
    
    def find_apis_with_security_issues(
        self,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find APIs with potential security issues (low security score).
        
        Args:
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs with security issues, total count)
        """
        query = {
            "range": {
                "intelligence_metadata.security_score": {
                    "lt": 70.0
                }
            }
        }
        sort = [{"intelligence_metadata.security_score": {"order": "asc"}}]
        return self.search(query, size=size, from_=from_, sort=sort)
    
    def find_apis_by_policy_type(
        self,
        policy_type: str,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[API], int]:
        """
        Find APIs that have a specific policy action type applied.
        
        Args:
            policy_type: PolicyActionType value to search for
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of APIs, total count)
        """
        query = {
            "nested": {
                "path": "policy_actions",
                "query": {
                    "term": {
                        "policy_actions.action_type": policy_type
                    }
                }
            }
        }
        return self.search(query, size=size, from_=from_)