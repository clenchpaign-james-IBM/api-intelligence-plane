"""
Configuration Management

Centralized configuration using Pydantic Settings for type-safe,
environment-based configuration management.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables with the
    prefix specified in model_config.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application Settings
    APP_NAME: str = "API Intelligence Plane"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    
    # Server Settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    RELOAD: bool = Field(default=True, description="Enable auto-reload")
    
    # CORS Settings
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # OpenSearch Settings
    OPENSEARCH_HOST: str = Field(default="localhost", description="OpenSearch host")
    OPENSEARCH_PORT: int = Field(default=9200, description="OpenSearch port")
    OPENSEARCH_USER: str = Field(default="admin", description="OpenSearch username")
    OPENSEARCH_PASSWORD: str = Field(default="admin", description="OpenSearch password")
    OPENSEARCH_USE_SSL: bool = Field(default=False, description="Use SSL for OpenSearch")
    OPENSEARCH_VERIFY_CERTS: bool = Field(
        default=False, description="Verify SSL certificates"
    )
    OPENSEARCH_POOL_SIZE: int = Field(
        default=10, description="Connection pool size"
    )
    OPENSEARCH_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
    OPENSEARCH_MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    
    # LLM Provider Settings
    LLM_PROVIDER: str = Field(
        default="openai", description="LLM provider (openai, anthropic, google, azure, ollama, watsonx, etc.)"
    )
    LLM_MODEL: str = Field(
        default="gpt-4", description="Default LLM model to use"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7, description="LLM temperature for generation"
    )
    LLM_MAX_TOKENS: int = Field(
        default=2000, description="Maximum tokens for LLM responses"
    )
    
    # Agent Execution Settings (to prevent infinite loops)
    AGENT_MAX_ITERATIONS: int = Field(
        default=15, description="Maximum tool calling iterations per agent execution"
    )
    AGENT_MAX_EXECUTION_TIME: int = Field(
        default=30, description="Maximum execution time in seconds per agent"
    )
    
    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = Field(
        default=None, description="OpenAI API key"
    )
    OPENAI_ORG_ID: Optional[str] = Field(
        default=None, description="OpenAI organization ID"
    )
    
    # Anthropic Settings
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )
    
    # Google Settings
    GOOGLE_API_KEY: Optional[str] = Field(
        default=None, description="Google API key"
    )
    
    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY: Optional[str] = Field(
        default=None, description="Azure OpenAI API key"
    )
    
    # Agent Settings
    AGENT_TIMEOUT: int = Field(
        default=30, description="Timeout for AI agent operations in seconds"
    )
    AGENT_CACHE_TTL: int = Field(
        default=300, description="Cache TTL for agent results in seconds (5 minutes)"
    )
    AGENT_MAX_RESULTS: int = Field(
        default=3, description="Maximum number of results to enhance with agents"
    )
    # Agentic Query Fallback Settings (T073)
    FALLBACK_CONFIDENCE_THRESHOLD: float = Field(
        default=0.1, description="Minimum confidence score before triggering fallback"
    )
    FALLBACK_FAILURE_RATE_THRESHOLD: float = Field(
        default=0.1, description="Maximum tool failure rate before triggering fallback"
    )
    FALLBACK_TIMEOUT_SECONDS: float = Field(
        default=10.0, description="Maximum workflow execution time before triggering fallback"
    )
    FALLBACK_ALERT_RATE_THRESHOLD: float = Field(
        default=0.1, description="Fallback rate threshold for triggering monitoring alerts (20%)"
    )
    FALLBACK_ALERT_ENABLED: bool = Field(
        default=True, description="Enable fallback rate monitoring alerts"
    )
    
    
    # Optimization AI Settings
    OPTIMIZATION_AI_ENABLED: bool = Field(
        default=True, description="Enable AI-enhanced optimization recommendations"
    )
    OPTIMIZATION_AI_THRESHOLD: float = Field(
        default=0.8, description="Confidence threshold for triggering AI enhancement in optimizations"
    )
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(
        default=None, description="Azure OpenAI endpoint"
    )
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = Field(
        default=None, description="Azure OpenAI deployment name"
    )

    # IBM watsonx Settings
    WATSONX_API_KEY: Optional[str] = Field(
        default=None, description="IBM watsonx API key"
    )
    WATSONX_URL: Optional[str] = Field(
        default=None, description="IBM watsonx base URL"
    )
    WATSONX_PROJECT_ID: Optional[str] = Field(
        default=None, description="IBM watsonx project ID"
    )

    # Ollama Settings
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434", description="Ollama base URL"
    )
    
    # Scheduler Settings
    SCHEDULER_ENABLED: bool = Field(
        default=True, description="Enable background scheduler"
    )
    API_DISCOVERY_INTERVAL_MINUTES: int = Field(
        default=5, description="API discovery interval in minutes per gateway"
    )
    METRICS_INTERVAL_MINUTES: int = Field(
        default=5, description="Metrics collection interval in minutes"
    )
    SECURITY_SCAN_INTERVAL_MINUTES: int = Field(
        default=1, description="Security scan interval in minutes"
    )
    COMPLIANCE_SCAN_INTERVAL_MINUTES: int = Field(
        default=1, description="Compliance scan interval in minutes"
    )
    PREDICTION_INTERVAL_MINUTES: int = Field(
        default=1, description="Prediction generation interval in minutes"
    )
    OPTIMIZATION_INTERVAL_MINUTES: int = Field(
        default=1, description="Optimization analysis interval in minutes"
    )
    TRANSACTIONAL_LOGS_INTERVAL_MINUTES: int = Field(
        default=5, description="Transactional logs collection interval in minutes per gateway"
    )
    METRICS_AGGREGATION_BUCKET: str = Field(
        default="5m", description="Default time bucket for metrics aggregation (1m, 5m, 1h, 1d)"
    )
    
    # TLS/SSL Settings
    TLS_ENABLED: bool = Field(
        default=False, description="Enable TLS 1.3 for server"
    )
    TLS_CERT_FILE: Optional[str] = Field(
        default=None, description="Path to TLS certificate file"
    )
    TLS_KEY_FILE: Optional[str] = Field(
        default=None, description="Path to TLS private key file"
    )
    TLS_CA_FILE: Optional[str] = Field(
        default=None, description="Path to TLS CA certificate file"
    )
    
    # OpenSearch TLS Settings
    OPENSEARCH_CLIENT_CERT: Optional[str] = Field(
        default=None, description="Path to OpenSearch client certificate"
    )
    OPENSEARCH_CLIENT_KEY: Optional[str] = Field(
        default=None, description="Path to OpenSearch client key"
    )
    OPENSEARCH_CA_CERT: Optional[str] = Field(
        default=None, description="Path to OpenSearch CA certificate"
    )
    
    # Client TLS Settings (for external API calls)
    CLIENT_CERT_FILE: Optional[str] = Field(
        default=None, description="Path to client certificate file"
    )
    CLIENT_KEY_FILE: Optional[str] = Field(
        default=None, description="Path to client private key file"
    )
    CLIENT_CA_FILE: Optional[str] = Field(
        default=None, description="Path to client CA certificate file"
    )
    
    # Security Settings
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key for encryption",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration"
    )
    
    # Data Retention Settings
    METRICS_RETENTION_DAYS: int = Field(
        default=90, description="Metrics data retention in days"
    )
    QUERY_HISTORY_RETENTION_DAYS: int = Field(
        default=30, description="Query history retention in days"
    )
    
    # Performance Settings
    MAX_RESULT_WINDOW: int = Field(
        default=10000, description="Maximum OpenSearch result window"
    )
    DEFAULT_PAGE_SIZE: int = Field(
        default=20, description="Default pagination size"
    )
    MAX_PAGE_SIZE: int = Field(
        default=100, description="Maximum pagination size"
    )
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="json", description="Log format (json or text)"
    )
    LOG_FILE: Optional[str] = Field(
        default=None, description="Log file path (None for stdout only)"
    )
    
    # MCP Server Settings
    MCP_DISCOVERY_PORT: int = Field(default=8001, description="Discovery MCP server port")
    MCP_METRICS_PORT: int = Field(default=8002, description="Metrics MCP server port")
    MCP_SECURITY_PORT: int = Field(default=8003, description="Security MCP server port")
    MCP_OPTIMIZATION_PORT: int = Field(
        default=8004, description="Optimization MCP server port"
    )
    
    @property
    def opensearch_url(self) -> str:
        """Get the full OpenSearch URL."""
        protocol = "https" if self.OPENSEARCH_USE_SSL else "http"
        return f"{protocol}://{self.OPENSEARCH_HOST}:{self.OPENSEARCH_PORT}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"


# Global settings instance
settings = Settings()

# Made with Bob
