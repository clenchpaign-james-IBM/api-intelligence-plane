"""
Gateway Repository

Provides CRUD operations and specialized queries for Gateway entities.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from app.db.repositories.base import BaseRepository
from app.models.gateway import Gateway, GatewayStatus, GatewayVendor

logger = logging.getLogger(__name__)


class GatewayRepository(BaseRepository[Gateway]):
    """Repository for Gateway entity operations."""
    
    def __init__(self):
        """Initialize the Gateway repository."""
        super().__init__(index_name="gateway-registry", model_class=Gateway)
    
    def find_by_status(
        self,
        status: GatewayStatus,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[Gateway], int]:
        """
        Find all gateways with a specific status.
        
        Args:
            status: Gateway status to filter by
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of gateways, total count)
        """
        query = {
            "term": {
                "status": status.value
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_by_vendor(
        self,
        vendor: GatewayVendor,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[Gateway], int]:
        """
        Find all gateways from a specific vendor.
        
        Args:
            vendor: Gateway vendor to filter by
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of gateways, total count)
        """
        query = {
            "term": {
                "vendor": vendor.value
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_connected_gateways(
        self,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[Gateway], int]:
        """
        Find all connected gateways.
        
        Args:
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of connected gateways, total count)
        """
        return self.find_by_status(GatewayStatus.CONNECTED, size=size, from_=from_)
    
    def find_by_name(
        self,
        name: str,
    ) -> Optional[Gateway]:
        """
        Find gateway by exact name.
        
        Args:
            name: Gateway name to search for
            
        Returns:
            Gateway if found, None otherwise
        """
        query = {
            "term": {
                "name.keyword": name
            }
        }
        results, _ = self.search(query, size=1)
        return results[0] if results else None
    
    def search_by_name(
        self,
        name: str,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[Gateway], int]:
        """
        Search gateways by name (fuzzy match).
        
        Args:
            name: Name to search for
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of gateways, total count)
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
    
    def find_with_capability(
        self,
        capability: str,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[Gateway], int]:
        """
        Find gateways that support a specific capability.
        
        Args:
            capability: Capability to search for
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of gateways, total count)
        """
        query = {
            "term": {
                "capabilities": capability
            }
        }
        return self.search(query, size=size, from_=from_)
    
    def find_with_errors(
        self,
        size: int = 100,
        from_: int = 0,
    ) -> tuple[List[Gateway], int]:
        """
        Find gateways with error status.
        
        Args:
            size: Number of results to return
            from_: Offset for pagination
            
        Returns:
            Tuple of (list of gateways with errors, total count)
        """
        return self.find_by_status(GatewayStatus.ERROR, size=size, from_=from_)
    
    def update_status(
        self,
        gateway_id: UUID,
        status: GatewayStatus,
        error_message: Optional[str] = None,
    ) -> Optional[Gateway]:
        """
        Update gateway status.
        
        Args:
            gateway_id: Gateway UUID
            status: New status
            error_message: Optional error message if status is ERROR
            
        Returns:
            Updated gateway if found, None otherwise
        """
        updates: Dict[str, Any] = {"status": status.value}
        
        if status == GatewayStatus.CONNECTED:
            from datetime import datetime
            updates["last_connected_at"] = datetime.utcnow().isoformat()
            updates["last_error"] = None
        elif status == GatewayStatus.ERROR and error_message:
            updates["last_error"] = error_message
        
        return self.update(str(gateway_id), updates)
    
    def update_api_count(
        self,
        gateway_id: UUID,
        api_count: int,
    ) -> Optional[Gateway]:
        """
        Update the API count for a gateway.
        
        Args:
            gateway_id: Gateway UUID
            api_count: New API count
            
        Returns:
            Updated gateway if found, None otherwise
        """
        return self.update(str(gateway_id), {"api_count": api_count})
    
    def increment_api_count(
        self,
        gateway_id: UUID,
        increment: int = 1,
    ) -> Optional[Gateway]:
        """
        Increment the API count for a gateway.
        
        Args:
            gateway_id: Gateway UUID
            increment: Amount to increment by (default: 1)
            
        Returns:
            Updated gateway if found, None otherwise
        """
        gateway = self.get(str(gateway_id))
        if gateway:
            new_count = gateway.api_count + increment
            return self.update_api_count(gateway_id, new_count)
        return None
    
    def advanced_search(
        self,
        filters: Dict[str, Any],
        size: int = 100,
        from_: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> tuple[List[Gateway], int]:
        """
        Advanced search with multiple filters.
        
        Args:
            filters: Dictionary of filter criteria
                - status: GatewayStatus
                - vendor: GatewayVendor
                - capabilities: List[str]
                - metrics_enabled: bool
                - security_scanning_enabled: bool
                - rate_limiting_enabled: bool
                - name: str (fuzzy match)
            size: Number of results to return
            from_: Offset for pagination
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (list of gateways, total count)
        """
        must_clauses = []
        
        # Status filter
        if "status" in filters:
            status_value = filters["status"].value if isinstance(filters["status"], GatewayStatus) else filters["status"]
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # Vendor filter
        if "vendor" in filters:
            vendor_value = filters["vendor"].value if isinstance(filters["vendor"], GatewayVendor) else filters["vendor"]
            must_clauses.append({
                "term": {"vendor": vendor_value}
            })
        
        # Capabilities filter
        if "capabilities" in filters and filters["capabilities"]:
            must_clauses.append({
                "terms": {"capabilities": filters["capabilities"]}
            })
        
        # Boolean filters
        for bool_field in ["metrics_enabled", "security_scanning_enabled", "rate_limiting_enabled"]:
            if bool_field in filters:
                must_clauses.append({
                    "term": {bool_field: filters[bool_field]}
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get gateway statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Build aggregation query
            aggs = {
                "total_gateways": {"value_count": {"field": "id"}},
                "by_status": {
                    "terms": {"field": "status"}
                },
                "by_vendor": {
                    "terms": {"field": "vendor"}
                },
                "total_apis": {
                    "sum": {"field": "api_count"}
                },
                "avg_apis_per_gateway": {
                    "avg": {"field": "api_count"}
                },
                "metrics_enabled_count": {
                    "filter": {"term": {"metrics_enabled": True}}
                },
                "security_enabled_count": {
                    "filter": {"term": {"security_scanning_enabled": True}}
                },
                "rate_limiting_enabled_count": {
                    "filter": {"term": {"rate_limiting_enabled": True}}
                }
            }
            
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "query": {"match_all": {}},
                    "aggs": aggs
                }
            )
            
            return {
                "total_gateways": response["aggregations"]["total_gateways"]["value"],
                "by_status": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in response["aggregations"]["by_status"]["buckets"]
                },
                "by_vendor": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in response["aggregations"]["by_vendor"]["buckets"]
                },
                "total_apis": response["aggregations"]["total_apis"]["value"],
                "avg_apis_per_gateway": response["aggregations"]["avg_apis_per_gateway"]["value"],
                "metrics_enabled_count": response["aggregations"]["metrics_enabled_count"]["doc_count"],
                "security_enabled_count": response["aggregations"]["security_enabled_count"]["doc_count"],
                "rate_limiting_enabled_count": response["aggregations"]["rate_limiting_enabled_count"]["doc_count"],
            }
            
        except Exception as e:
            logger.error(f"Failed to get gateway statistics: {e}")
            raise
    
    def search_gateways(
        self,
        name: Optional[str] = None,
        vendor: Optional[GatewayVendor] = None,
        status: Optional[GatewayStatus] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Gateway], int]:
        """
        Search gateways with multiple filter criteria.
        
        This method provides flexible multi-criteria filtering for agents,
        complementing the existing list/get methods with text pattern matching
        and date range filtering.
        
        Args:
            name: Gateway name pattern (case-insensitive wildcard match)
            vendor: Gateway vendor filter
            status: Gateway status filter
            created_after: Filter gateways created after this date
            created_before: Filter gateways created before this date
            page: Page number (1-based)
            page_size: Number of results per page (default: 20, max: 100)
            
        Returns:
            Tuple of (list of gateways, total count)
            
        Examples:
            # Find gateways with "prod" in name that are connected
            gateways, total = repo.search(name="prod", status=GatewayStatus.CONNECTED)
            
            # Find webMethods gateways created in last 7 days
            from datetime import datetime, timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            gateways, total = repo.search(
                vendor=GatewayVendor.WEBMETHODS,
                created_after=week_ago
            )
        """
        # Validate and normalize pagination
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        from_ = (page - 1) * page_size
        
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
        
        # Vendor filter
        if vendor:
            vendor_value = vendor.value if isinstance(vendor, GatewayVendor) else vendor
            must_clauses.append({
                "term": {"vendor": vendor_value}
            })
        
        # Status filter
        if status:
            status_value = status.value if isinstance(status, GatewayStatus) else status
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # Date range filters
        if created_after or created_before:
            range_query: Dict[str, Any] = {}
            if created_after:
                range_query["gte"] = created_after.isoformat()
            if created_before:
                range_query["lte"] = created_before.isoformat()
            must_clauses.append({
                "range": {"created_at": range_query}
            })
        
        # Build final query
        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}]
            }
        }
        
        # Execute search with sorting by created_at (newest first)
        sort = [{"created_at": {"order": "desc"}}]
        return super().search(query, size=page_size, from_=from_, sort=sort)


# Made with Bob