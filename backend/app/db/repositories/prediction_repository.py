"""
Prediction Repository

Handles CRUD operations and queries for API failure predictions.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.db.repositories.base import BaseRepository
from app.models.prediction import Prediction, PredictionType, PredictionStatus, PredictionSeverity

logger = logging.getLogger(__name__)


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for managing API failure predictions"""

    def __init__(self):
        super().__init__(index_name="api-predictions", model_class=Prediction)

    def create_prediction(self, prediction: Prediction) -> Prediction:
        """
        Create a new prediction

        Args:
            prediction: Prediction model instance

        Returns:
            Created prediction with ID
        """
        return self.create(prediction)

    def upsert_prediction(self, prediction: Prediction) -> Prediction:
        """
        Create or update a prediction based on api_id, prediction_type, and predicted_time.
        
        This prevents duplicate predictions by checking if a similar prediction already exists
        for the same API, type, and time window (within 1 hour).
        
        Args:
            prediction: Prediction model instance
            
        Returns:
            Created or updated prediction
        """
        # Search for existing prediction with same api_id, type, and similar predicted_time
        try:
            # Look for predictions within 1 hour of the predicted time
            time_window_start = prediction.predicted_time - timedelta(hours=1)
            time_window_end = prediction.predicted_time + timedelta(hours=1)
            
            result = self.client.search(
                index=self.index_name,
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"api_id": str(prediction.api_id)}},
                                {"term": {"prediction_type": prediction.prediction_type.value}},
                                {"term": {"status": PredictionStatus.ACTIVE.value}},
                                {
                                    "range": {
                                        "predicted_time": {
                                            "gte": time_window_start.isoformat(),
                                            "lte": time_window_end.isoformat(),
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    "size": 1,
                    "sort": [{"created_at": {"order": "desc"}}]
                }
            )
            
            if result['hits']['total']['value'] > 0:
                # Update existing prediction
                existing_hit = result['hits']['hits'][0]
                existing_id = existing_hit['_source']['id']
                
                update_doc = {
                    "confidence_score": prediction.confidence_score,
                    "severity": prediction.severity.value,
                    "contributing_factors": [f.dict() for f in prediction.contributing_factors],
                    "recommended_actions": prediction.recommended_actions,
                    "metadata": prediction.metadata,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                
                updated = self.update(existing_id, update_doc)
                if updated:
                    return updated
            
            # No existing prediction found, create new one
            return self.create(prediction)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to upsert prediction: {e}")
            # Fallback to create
            return self.create(prediction)

    def get_prediction(self, prediction_id: str) -> Optional[Prediction]:
        """
        Get prediction by ID

        Args:
            prediction_id: Prediction UUID

        Returns:
            Prediction if found, None otherwise
        """
        # Search by the id field, not the OpenSearch _id
        try:
            result = self.client.search(
                index=self.index_name,
                body={
                    "query": {
                        "term": {
                            "id.keyword": prediction_id  # Use .keyword for exact match on UUID string
                        }
                    },
                    "size": 1
                }
            )
            
            if result['hits']['total']['value'] > 0:
                hit = result['hits']['hits'][0]
                return self.model_class(**hit['_source'])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get prediction {prediction_id}: {e}")
            return None

    def list_predictions(
        self,
        gateway_id: Optional[str] = None,
        api_id: Optional[str] = None,
        severity: Optional[PredictionSeverity] = None,
        status: Optional[PredictionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List predictions with filters

        Args:
            gateway_id: Filter by Gateway ID (primary dimension)
            api_id: Filter by API ID (secondary dimension)
            severity: Filter by severity level
            status: Filter by prediction status
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Dict with predictions list and pagination info
        """
        must_clauses = []

        if gateway_id:
            must_clauses.append({"term": {"gateway_id": gateway_id}})
        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})
        if severity:
            must_clauses.append({"term": {"severity": severity.value}})
        if status:
            must_clauses.append({"term": {"status": status.value}})

        # Default to active predictions if no status filter
        if not status:
            must_clauses.append({"term": {"status": PredictionStatus.ACTIVE.value}})

        query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

        # Sort by predicted_time (earliest first) and confidence (highest first)
        sort = [
            {"predicted_time": {"order": "asc"}},
            {"confidence_score": {"order": "desc"}},
        ]

        # Calculate offset from page number
        from_ = (page - 1) * page_size

        predictions, total = self.search(
            query=query,
            sort=sort,
            size=page_size,
            from_=from_,
        )

        # Enrich predictions with API names
        predictions = self._enrich_with_api_names(predictions)

        return {
            "predictions": predictions,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    
    def _enrich_with_api_names(self, predictions: List[Prediction]) -> List[Prediction]:
        """
        Enrich predictions with API names by fetching from API inventory
        
        Args:
            predictions: List of predictions
            
        Returns:
            Predictions with api_name populated
        """
        if not predictions:
            return predictions
        
        # Get unique API IDs
        api_ids = list(set(str(p.api_id) for p in predictions))
        
        # Fetch API names in bulk
        api_names = {}
        try:
            # Fetch each API document individually
            for api_id in api_ids:
                try:
                    result = self.client.get(
                        index="api-inventory",
                        id=api_id,
                        params={"_source": "name"}
                    )
                    if result.get("found"):
                        source = result.get("_source", {})
                        api_names[api_id] = source.get("name", "Unknown API")
                except Exception:
                    # API not found, skip
                    pass
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to fetch API names: {e}")
        
        # Populate api_name in predictions
        for prediction in predictions:
            prediction.api_name = api_names.get(str(prediction.api_id), f"API {str(prediction.api_id)[:8]}")
        
        return predictions

    def get_active_predictions_for_api(self, api_id: str) -> List[Prediction]:
        """
        Get all active predictions for a specific API

        Args:
            api_id: API UUID

        Returns:
            List of active predictions
        """
        query = {
            "bool": {
                "must": [
                    {"term": {"api_id": api_id}},
                    {"term": {"status": PredictionStatus.ACTIVE.value}},
                ]
            }
        }

        predictions, _ = self.search(query=query, size=100)
        return predictions

    def get_predictions_by_time_window(
        self,
        start_time: datetime,
        end_time: datetime,
        api_id: Optional[str] = None,
    ) -> List[Prediction]:
        """
        Get predictions within a time window

        Args:
            start_time: Start of time window
            end_time: End of time window
            api_id: Optional API ID filter

        Returns:
            List of predictions
        """
        range_clause: Dict[str, Any] = {
            "range": {
                "predicted_time": {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat(),
                }
            }
        }
        
        must_clauses: List[Dict[str, Any]] = [range_clause]

        if api_id:
            term_clause: Dict[str, Any] = {"term": {"api_id": api_id}}
            must_clauses.append(term_clause)

        query = {"bool": {"must": must_clauses}}

        predictions, _ = self.search(query=query, size=1000)
        return predictions

    def update_prediction_status(
        self,
        prediction_id: str,
        status: PredictionStatus,
        actual_outcome: Optional[str] = None,
        actual_time: Optional[datetime] = None,
    ) -> Optional[Prediction]:
        """
        Update prediction status and outcome

        Args:
            prediction_id: Prediction UUID
            status: New status
            actual_outcome: What actually happened
            actual_time: When the event occurred

        Returns:
            Updated prediction if found
        """
        update_doc = {
            "status": status.value,
        }

        if actual_outcome:
            update_doc["actual_outcome"] = actual_outcome
        if actual_time:
            update_doc["actual_time"] = actual_time.isoformat()

        return self.update(prediction_id, update_doc)

    def calculate_and_update_accuracy(
        self, prediction_id: str
    ) -> Optional[Prediction]:
        """
        Calculate and update prediction accuracy score

        Args:
            prediction_id: Prediction UUID

        Returns:
            Updated prediction with accuracy score
        """
        prediction = self.get_prediction(prediction_id)
        if not prediction or not prediction.actual_time:
            return None

        # Calculate accuracy: 1 - |predicted_time - actual_time| / 48h
        time_diff = abs(
            (prediction.predicted_time - prediction.actual_time).total_seconds()
        )
        max_window = 48 * 3600  # 48 hours in seconds
        accuracy = max(0.0, 1.0 - (time_diff / max_window))

        update_doc = {
            "accuracy_score": accuracy,
        }

        return self.update(prediction_id, update_doc)

    def get_expired_predictions(self) -> List[Prediction]:
        """
        Get predictions that have expired (predicted_time has passed)

        Returns:
            List of expired active predictions
        """
        now = datetime.utcnow()
        query = {
            "bool": {
                "must": [
                    {"term": {"status": PredictionStatus.ACTIVE.value}},
                    {"range": {"predicted_time": {"lt": now.isoformat()}}},
                ]
            }
        }

        predictions, _ = self.search(query=query, size=1000)
        return predictions

    def get_prediction_accuracy_stats(
        self, api_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get prediction accuracy statistics

        Args:
            api_id: Optional API ID filter
            days: Number of days to look back

        Returns:
            Dict with accuracy statistics
        """
        start_time = datetime.utcnow() - timedelta(days=days)

        must_clauses = [
            {"exists": {"field": "accuracy_score"}},
            {"range": {"predicted_at": {"gte": start_time.isoformat()}}},
        ]

        if api_id:
            must_clauses.append({"term": {"api_id": api_id}})

        query = {"bool": {"must": must_clauses}}

        # Aggregation for statistics
        aggs = {
            "avg_accuracy": {"avg": {"field": "accuracy_score"}},
            "min_accuracy": {"min": {"field": "accuracy_score"}},
            "max_accuracy": {"max": {"field": "accuracy_score"}},
            "by_outcome": {
                "terms": {"field": "actual_outcome"},
                "aggs": {"avg_accuracy": {"avg": {"field": "accuracy_score"}}},
            },
        }

        result = self.client.search(
            index=self.index_name, body={"query": query, "aggs": aggs, "size": 0}
        )

        aggregations = result.get("aggregations", {})

        return {
            "total_predictions": result["hits"]["total"]["value"],
            "avg_accuracy": aggregations.get("avg_accuracy", {}).get("value", 0),
            "min_accuracy": aggregations.get("min_accuracy", {}).get("value", 0),
            "max_accuracy": aggregations.get("max_accuracy", {}).get("value", 0),
            "by_outcome": [
                {
                    "outcome": bucket["key"],
                    "count": bucket["doc_count"],
                    "avg_accuracy": bucket["avg_accuracy"]["value"],
                }
                for bucket in aggregations.get("by_outcome", {}).get("buckets", [])
            ],
        }

    def delete_old_predictions(self, days: int = 90) -> int:
        """
        Delete predictions older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of deleted predictions
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = {"range": {"created_at": {"lt": cutoff_date.isoformat()}}}

        result = self.client.delete_by_query(
            index=self.index_name, body={"query": query}
        )

        return result.get("deleted", 0)

    def search_predictions(
        self,
        prediction_type: Optional[PredictionType] = None,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        severity: Optional[PredictionSeverity] = None,
        status: Optional[PredictionStatus] = None,
        predicted_after: Optional[datetime] = None,
        predicted_before: Optional[datetime] = None,
        api_name: Optional[str] = None,
        gateway_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Prediction], int]:
        """
        Search predictions with multiple filter criteria.
        
        This method provides flexible multi-criteria filtering for agents,
        complementing existing list/get methods with prediction type, confidence
        range, severity, and time range filtering.
        
        Args:
            prediction_type: Prediction type filter (failure, degradation, capacity, security)
            confidence_min: Minimum confidence score (0.0-1.0)
            confidence_max: Maximum confidence score (0.0-1.0)
            severity: Prediction severity filter (critical, high, medium, low)
            status: Prediction status filter (active, resolved, false_positive, expired)
            predicted_after: Filter predictions with predicted_time after this date
            predicted_before: Filter predictions with predicted_time before this date
            api_name: API name pattern (case-insensitive wildcard match)
            gateway_id: Filter by gateway ID
            page: Page number (1-based)
            page_size: Number of results per page (default: 20, max: 100)
            
        Returns:
            Tuple of (list of predictions, total count)
            
        Examples:
            # Show predictions with confidence >80% for production gateway
            preds, total = repo.search_predictions(
                confidence_min=0.8,
                gateway_id=UUID("...")
            )
            
            # Find failure predictions in next hour
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            hour_later = now + timedelta(hours=1)
            preds, total = repo.search_predictions(
                prediction_type=PredictionType.FAILURE,
                predicted_after=now,
                predicted_before=hour_later
            )
        """
        # Validate and normalize pagination
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        from_ = (page - 1) * page_size
        
        # Validate confidence ranges
        if confidence_min is not None:
            confidence_min = max(0.0, min(1.0, confidence_min))
        if confidence_max is not None:
            confidence_max = max(0.0, min(1.0, confidence_max))
        
        # Build bool query with must clauses
        must_clauses = []
        
        # Prediction type filter
        if prediction_type:
            type_value = prediction_type.value if isinstance(prediction_type, PredictionType) else prediction_type
            must_clauses.append({
                "term": {"prediction_type": type_value}
            })
        
        # Confidence range
        if confidence_min is not None or confidence_max is not None:
            range_query: Dict[str, Any] = {}
            if confidence_min is not None:
                range_query["gte"] = confidence_min
            if confidence_max is not None:
                range_query["lte"] = confidence_max
            must_clauses.append({
                "range": {"confidence_score": range_query}
            })
        
        # Severity filter
        if severity:
            severity_value = severity.value if isinstance(severity, PredictionSeverity) else severity
            must_clauses.append({
                "term": {"severity": severity_value}
            })
        
        # Status filter
        if status:
            status_value = status.value if isinstance(status, PredictionStatus) else status
            must_clauses.append({
                "term": {"status": status_value}
            })
        
        # Predicted time range filters
        if predicted_after or predicted_before:
            time_range_query: Dict[str, Any] = {}
            if predicted_after:
                time_range_query["gte"] = predicted_after.isoformat()
            if predicted_before:
                time_range_query["lte"] = predicted_before.isoformat()
            must_clauses.append({
                "range": {"predicted_time": time_range_query}
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
        
        # Build final query
        query = {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}]
            }
        }
        
        # Execute search with sorting by severity (critical first) and predicted_time (soonest first)
        sort = [
            {"severity": {"order": "asc"}},  # critical < high < medium < low
            {"predicted_time": {"order": "asc"}}  # soonest first
        ]
        
        try:
            predictions, total = self.search(query, size=page_size, from_=from_, sort=sort)
            return predictions, total
        except Exception as e:
            logger.error(f"Failed to search predictions: {e}")
            return [], 0


# Made with Bob
