#!/usr/bin/env python3
"""
Enhanced Pattern Simulator for webmethods API Gateway

This script generates realistic traffic patterns by orchestrating actual API invocations
that reach the gateway and generate real transaction logs and events.

Key Principles:
1. All requests must reach the gateway to generate transaction logs
2. Patterns are simulated through request timing, volume, and endpoint variations
3. No reliance on query parameters that the gateway doesn't understand
4. Uses actual HTTP status codes and response times from the gateway

Patterns Supported:
- steady: Consistent traffic at specified RPS
- increasing-error-trend: Gradually increasing error rate over time
- bucketed-error-trend: Step-wise increasing error rate in discrete buckets
- decreasing-response-time: Natural response time variations (gateway-dependent)
- decreasing-availability: Simulated downtime windows with actual errors
- burst: Periodic traffic spikes with increased error probability
- traffic-ramp-up: Gradually increasing request rate
- error-burst: Concentrated error windows
- increasing-response-time: Natural response time variations (gateway-dependent)
- rate-limit-hit: Aggressive traffic to trigger rate limiting
- auth-failures: Alternating valid/invalid credentials
- shadow-api-probe: Probing undocumented/internal endpoints
"""

import argparse
import json
import random
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

import requests
from requests.auth import HTTPBasicAuth


@dataclass
class PatternConfig:
    """Configuration for a traffic pattern."""
    name: str
    base_rps: float
    duration_seconds: int
    error_injection_enabled: bool
    auth_variation_enabled: bool
    endpoint_variation_enabled: bool


@dataclass
class RequestResult:
    """Result of a single request."""
    request_number: int
    timestamp: float
    url: str
    method: str
    status_code: Optional[int]
    latency_ms: float
    error: Optional[str]
    pattern_phase: str


class PatternSimulator:
    """Orchestrates pattern-based traffic generation."""
    
    def __init__(
        self,
        base_url: str,
        method: str = "GET",
        payload: Optional[dict] = None,
        auth: Optional[HTTPBasicAuth] = None,
        timeout: float = 10.0,
        max_workers: int = 50,
    ):
        self.base_url = base_url.rstrip('/')
        self.method = method.upper()
        self.payload = payload
        self.auth = auth
        self.timeout = timeout
        self.max_workers = max_workers
        self.running = True
        self.print_lock = threading.Lock()
        self.results: list[RequestResult] = []
        self.results_lock = threading.Lock()
        
        # Parse base URL for endpoint variations
        parsed = urlparse(base_url)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc
        self.base_path = parsed.path or '/'
    
    def stop(self):
        """Stop the simulator."""
        self.running = False
    
    def _generate_error_endpoint(self, request_number: int, pattern_phase: str) -> str:
        """Generate an endpoint that will likely return an error."""
        # Use invalid resource IDs or non-existent paths
        error_variations = [
            f"{self.base_path}/nonexistent_{request_number}",
            f"{self.base_path}/invalid_id_999999",
            f"{self.base_path}/missing_resource",
            f"{self.base_path}/error_{pattern_phase}",
            f"{self.base_path.rstrip('/')}_invalid",
        ]
        path = random.choice(error_variations)
        return urlunparse((self.base_scheme, self.base_netloc, path, '', '', ''))
    
    def _generate_shadow_endpoint(self, request_number: int) -> str:
        """Generate a shadow/undocumented endpoint."""
        shadow_paths = [
            "/api/internal/debug",
            "/api/internal/metrics",
            "/api/internal/health",
            "/api/v1/admin/users",
            "/api/v1/admin/config",
            "/api/v1/admin/settings",
            "/api/legacy/v0/data",
            "/api/legacy/deprecated",
            "/.well-known/security.txt",
            "/actuator/health",
            "/swagger.json",
            "/api-docs",
        ]
        path = random.choice(shadow_paths)
        return urlunparse((self.base_scheme, self.base_netloc, path, '', '', ''))
    
    def _execute_request(
        self,
        request_number: int,
        url: str,
        method: str,
        payload: Optional[dict],
        auth: Optional[HTTPBasicAuth],
        pattern_phase: str,
    ) -> RequestResult:
        """Execute a single HTTP request and return the result."""
        start = time.perf_counter()
        timestamp = time.time()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=payload if method in {"POST", "PUT", "PATCH"} else None,
                auth=auth,
                timeout=self.timeout,
                allow_redirects=False,  # Don't follow redirects to see actual gateway response
            )
            latency_ms = (time.perf_counter() - start) * 1000
            
            result = RequestResult(
                request_number=request_number,
                timestamp=timestamp,
                url=url,
                method=method,
                status_code=response.status_code,
                latency_ms=latency_ms,
                error=None,
                pattern_phase=pattern_phase,
            )
            
            with self.print_lock:
                print(
                    f"[{request_number:04d}] {method} {url} -> "
                    f"{response.status_code} | {latency_ms:.0f}ms | {pattern_phase}"
                )
            
            return result
            
        except requests.RequestException as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            
            result = RequestResult(
                request_number=request_number,
                timestamp=timestamp,
                url=url,
                method=method,
                status_code=None,
                latency_ms=latency_ms,
                error=str(exc),
                pattern_phase=pattern_phase,
            )
            
            with self.print_lock:
                print(
                    f"[{request_number:04d}] {method} {url} -> "
                    f"ERROR: {exc} | {latency_ms:.0f}ms | {pattern_phase}"
                )
            
            return result
    
    def _steady_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate steady traffic at constant RPS."""
        interval = 1.0 / config.base_rps
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < config.duration_seconds * config.base_rps:
                request_number += 1
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    self.base_url,
                    self.method,
                    self.payload,
                    self.auth,
                    "steady",
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _increasing_error_trend_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic with gradually increasing error rate."""
        interval = 1.0 / config.base_rps
        total_requests = int(config.duration_seconds * config.base_rps)
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < total_requests:
                request_number += 1
                
                # Calculate error probability based on progress
                progress = (request_number - 1) / max(1, total_requests - 1)
                error_probability = min(0.85, 0.05 + (progress * 0.75))
                
                # Decide whether to inject error
                should_inject_error = random.random() < error_probability
                
                if should_inject_error:
                    url = self._generate_error_endpoint(request_number, "increasing-error")
                    phase = f"increasing-error-{int(progress * 100)}%"
                else:
                    url = self.base_url
                    phase = f"normal-{int(progress * 100)}%"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _bucketed_error_trend_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic with step-wise increasing error rate in buckets."""
        interval = 1.0 / config.base_rps
        total_requests = int(config.duration_seconds * config.base_rps)
        bucket_count = min(6, max(2, total_requests // 10))
        bucket_size = max(1, total_requests // bucket_count)
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < total_requests:
                request_number += 1
                
                # Determine bucket and error probability
                bucket_index = min(bucket_count - 1, (request_number - 1) // bucket_size)
                error_probability = min(0.95, 0.05 + (bucket_index * 0.15))
                
                # Decide whether to inject error
                should_inject_error = random.random() < error_probability
                
                if should_inject_error:
                    url = self._generate_error_endpoint(request_number, f"bucket-{bucket_index + 1}")
                    phase = f"bucket-{bucket_index + 1}-error"
                else:
                    url = self.base_url
                    phase = f"bucket-{bucket_index + 1}-normal"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _burst_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic with periodic bursts."""
        base_interval = 1.0 / config.base_rps
        burst_interval = base_interval / 5  # 5x faster during burst
        burst_duration = 3  # seconds
        quiet_duration = 9  # seconds
        cycle_duration = burst_duration + quiet_duration
        
        request_number = 0
        next_run = time.perf_counter()
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and (time.perf_counter() - start_time) < config.duration_seconds:
                request_number += 1
                
                # Determine if we're in burst phase
                cycle_position = (time.perf_counter() - start_time) % cycle_duration
                in_burst = cycle_position < burst_duration
                
                if in_burst:
                    interval = burst_interval
                    # 30% error rate during burst
                    should_inject_error = random.random() < 0.3
                    phase = "burst"
                else:
                    interval = base_interval
                    should_inject_error = False
                    phase = "quiet"
                
                if should_inject_error:
                    url = self._generate_error_endpoint(request_number, "burst-overload")
                else:
                    url = self.base_url
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _traffic_ramp_up_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic with gradually increasing RPS."""
        start_rps = config.base_rps * 0.1  # Start at 10% of target
        end_rps = config.base_rps * 2.0    # End at 200% of target
        
        request_number = 0
        next_run = time.perf_counter()
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and (time.perf_counter() - start_time) < config.duration_seconds:
                request_number += 1
                
                # Calculate current RPS based on progress
                elapsed = time.perf_counter() - start_time
                progress = min(1.0, elapsed / config.duration_seconds)
                current_rps = start_rps + (end_rps - start_rps) * progress
                interval = 1.0 / current_rps
                
                phase = f"ramp-{int(current_rps)}rps"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    self.base_url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _error_burst_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic with concentrated error windows."""
        interval = 1.0 / config.base_rps
        error_window_size = 5  # 5 requests
        cycle_size = 20  # Every 20 requests
        
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < config.duration_seconds * config.base_rps:
                request_number += 1
                
                # Determine if we're in error burst window
                cycle_position = (request_number - 1) % cycle_size
                in_error_burst = 8 <= cycle_position <= (8 + error_window_size - 1)
                
                if in_error_burst:
                    url = self._generate_error_endpoint(request_number, "error-burst")
                    phase = "error-burst"
                else:
                    url = self.base_url
                    phase = "normal"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _rate_limit_hit_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate aggressive traffic to trigger rate limiting."""
        # Start at base RPS and progressively increase
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < config.duration_seconds * config.base_rps * 10:
                request_number += 1
                
                # Progressively increase speed
                speed_multiplier = min(20, 3 + request_number // 10)
                interval = (1.0 / config.base_rps) / speed_multiplier
                
                phase = f"rate-limit-{speed_multiplier}x"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    self.base_url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _auth_failures_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic with alternating valid/invalid credentials."""
        interval = 1.0 / config.base_rps
        request_number = 0
        next_run = time.perf_counter()
        
        # Invalid credentials for testing
        invalid_auth = HTTPBasicAuth("invalid_user", "invalid_password")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < config.duration_seconds * config.base_rps:
                request_number += 1
                
                # Alternate between valid and invalid credentials
                if request_number % 2 == 0:
                    auth = invalid_auth
                    phase = "auth-invalid"
                else:
                    auth = self.auth
                    phase = "auth-valid"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    self.base_url,
                    self.method,
                    self.payload,
                    auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _shadow_api_probe_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """Generate traffic probing shadow/undocumented endpoints."""
        interval = 1.0 / config.base_rps
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < config.duration_seconds * config.base_rps:
                request_number += 1
                
                # Mix of legitimate and shadow endpoint requests
                if request_number % 3 == 0:
                    url = self._generate_shadow_endpoint(request_number)
                    phase = "shadow-probe"
                else:
                    url = self.base_url
                    phase = "normal"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def _prediction_trigger_pattern(self, config: PatternConfig) -> list[RequestResult]:
        """
        Generate traffic designed to trigger API health predictions.
        
        This pattern creates three distinct phases to trigger different prediction types:
        
        Phase 1 (0-33%): Degradation Risk
        - Gradual response time increase (simulated via increasing load)
        - Declining throughput (reduced RPS)
        - Moderate error rate increase (5-10%)
        
        Phase 2 (33-66%): Capacity Risk
        - Rapid request growth (2x-3x normal RPS)
        - High P99 response times (aggressive concurrent requests)
        
        Phase 3 (66-100%): Failure Risk
        - High error rate (>10% and increasing)
        - Degrading response times (>2000ms P95)
        - Declining availability (<95%)
        """
        total_requests = int(config.duration_seconds * config.base_rps)
        phase1_end = total_requests // 3
        phase2_end = (total_requests * 2) // 3
        
        request_number = 0
        next_run = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while self.running and request_number < total_requests:
                request_number += 1
                
                # Determine current phase
                if request_number <= phase1_end:
                    # Phase 1: Degradation Risk
                    # Gradual slowdown with moderate errors
                    phase = "degradation"
                    progress = request_number / phase1_end
                    
                    # Gradually reduce RPS (declining throughput)
                    current_rps = config.base_rps * (1.0 - 0.3 * progress)
                    interval = 1.0 / current_rps
                    
                    # Moderate error injection (5-10%)
                    error_probability = 0.05 + (0.05 * progress)
                    should_inject_error = random.random() < error_probability
                    
                    if should_inject_error:
                        url = self._generate_error_endpoint(request_number, "degradation")
                        phase_label = f"degradation-error-{int(error_probability * 100)}%"
                    else:
                        url = self.base_url
                        phase_label = f"degradation-normal-{int(progress * 100)}%"
                
                elif request_number <= phase2_end:
                    # Phase 2: Capacity Risk
                    # Rapid traffic growth with high concurrency
                    phase = "capacity"
                    progress = (request_number - phase1_end) / (phase2_end - phase1_end)
                    
                    # Rapidly increase RPS (2x-3x normal)
                    rps_multiplier = 2.0 + (1.0 * progress)
                    current_rps = config.base_rps * rps_multiplier
                    interval = 1.0 / current_rps
                    
                    # Low error rate during capacity stress
                    should_inject_error = random.random() < 0.05
                    
                    if should_inject_error:
                        url = self._generate_error_endpoint(request_number, "capacity-overload")
                        phase_label = f"capacity-overload-{int(rps_multiplier)}x"
                    else:
                        url = self.base_url
                        phase_label = f"capacity-growth-{int(rps_multiplier)}x"
                
                else:
                    # Phase 3: Failure Risk
                    # High error rate with degrading performance
                    phase = "failure"
                    progress = (request_number - phase2_end) / (total_requests - phase2_end)
                    
                    # Return to normal RPS but with high errors
                    current_rps = config.base_rps
                    interval = 1.0 / current_rps
                    
                    # High and increasing error rate (10-30%)
                    error_probability = 0.10 + (0.20 * progress)
                    should_inject_error = random.random() < error_probability
                    
                    if should_inject_error:
                        url = self._generate_error_endpoint(request_number, "failure-imminent")
                        phase_label = f"failure-error-{int(error_probability * 100)}%"
                    else:
                        url = self.base_url
                        phase_label = f"failure-normal-{int(progress * 100)}%"
                
                futures.append(executor.submit(
                    self._execute_request,
                    request_number,
                    url,
                    self.method,
                    self.payload,
                    self.auth,
                    phase_label,
                ))
                
                next_run += interval
                sleep_for = next_run - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    next_run = time.perf_counter()
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    with self.print_lock:
                        print(f"ERROR collecting result: {e}")
            
            return results
    
    def run_pattern(self, pattern_name: str, config: PatternConfig) -> list[RequestResult]:
        """Run the specified pattern."""
        print(f"\n{'='*80}")
        print(f"Starting pattern: {pattern_name}")
        print(f"Base RPS: {config.base_rps}, Duration: {config.duration_seconds}s")
        print(f"{'='*80}\n")
        
        pattern_methods = {
            "steady": self._steady_pattern,
            "increasing-error-trend": self._increasing_error_trend_pattern,
            "bucketed-error-trend": self._bucketed_error_trend_pattern,
            "burst": self._burst_pattern,
            "traffic-ramp-up": self._traffic_ramp_up_pattern,
            "error-burst": self._error_burst_pattern,
            "rate-limit-hit": self._rate_limit_hit_pattern,
            "auth-failures": self._auth_failures_pattern,
            "shadow-api-probe": self._shadow_api_probe_pattern,
            "prediction-trigger": self._prediction_trigger_pattern,
            # Response time patterns rely on gateway behavior
            "decreasing-response-time": self._steady_pattern,
            "increasing-response-time": self._steady_pattern,
            "decreasing-availability": self._increasing_error_trend_pattern,
        }
        
        method = pattern_methods.get(pattern_name, self._steady_pattern)
        results = method(config)
        
        with self.results_lock:
            self.results.extend(results)
        
        print(f"\n{'='*80}")
        print(f"Pattern completed: {pattern_name}")
        print(f"Total requests: {len(results)}")
        print(f"{'='*80}\n")
        
        return results
    
    def print_summary(self):
        """Print summary statistics."""
        if not self.results:
            print("No results to summarize")
            return
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.status_code and 200 <= r.status_code < 300)
        errors = sum(1 for r in self.results if r.error or (r.status_code and r.status_code >= 400))
        avg_latency = sum(r.latency_ms for r in self.results) / total
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total Requests: {total}")
        print(f"Successful (2xx): {successful} ({successful/total*100:.1f}%)")
        print(f"Errors (4xx/5xx): {errors} ({errors/total*100:.1f}%)")
        print(f"Average Latency: {avg_latency:.0f}ms")
        print(f"{'='*80}\n")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Enhanced Pattern Simulator for webmethods API Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("--url", required=True, help="Target API URL")
    parser.add_argument("--method", default="GET", help="HTTP method (default: GET)")
    parser.add_argument("--payload", help="JSON request payload for POST/PUT/PATCH")
    parser.add_argument("--username", help="Basic auth username")
    parser.add_argument("--password", help="Basic auth password")
    parser.add_argument(
        "--pattern",
        required=True,
        choices=[
            "steady",
            "increasing-error-trend",
            "bucketed-error-trend",
            "decreasing-response-time",
            "decreasing-availability",
            "burst",
            "traffic-ramp-up",
            "error-burst",
            "increasing-response-time",
            "rate-limit-hit",
            "auth-failures",
            "shadow-api-probe",
            "prediction-trigger",
        ],
        help="Traffic pattern to simulate",
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=5.0,
        help="Base requests per second (default: 5.0)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Pattern duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=50,
        help="Maximum concurrent workers (default: 50)",
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Parse payload if provided
    payload = None
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON payload: {e}")
            return 1
    
    # Setup authentication
    auth = None
    if args.username or args.password:
        auth = HTTPBasicAuth(args.username or "", args.password or "")
    
    # Create pattern configuration
    config = PatternConfig(
        name=args.pattern,
        base_rps=args.rps,
        duration_seconds=args.duration,
        error_injection_enabled=True,
        auth_variation_enabled=args.pattern == "auth-failures",
        endpoint_variation_enabled=args.pattern in ["shadow-api-probe", "increasing-error-trend", "prediction-trigger"],
    )
    
    # Create simulator
    simulator = PatternSimulator(
        base_url=args.url,
        method=args.method,
        payload=payload,
        auth=auth,
        timeout=args.timeout,
        max_workers=args.max_workers,
    )
    
    # Setup signal handler
    def handle_interrupt(signum, frame):
        print("\n\nInterrupted! Stopping...")
        simulator.stop()
    
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # Run pattern
    try:
        simulator.run_pattern(args.pattern, config)
        simulator.print_summary()
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
