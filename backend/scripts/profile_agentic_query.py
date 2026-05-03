"""
Performance Profiling Script for Agentic Query Service

Profiles agent workflows to identify performance bottlenecks and
validate performance targets (<5s single-agent, <10s multi-agent).

Feature: 002-agentic-query
Task: T100

Usage:
    python backend/scripts/profile_agentic_query.py
"""

import asyncio
import time
import statistics
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import httpx

# API endpoint
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class AgenticQueryProfiler:
    """
    Profiles agentic query performance across different query types.
    """
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def profile_query(
        self,
        query: str,
        query_type: str,
        iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Profile a single query multiple times and collect statistics.
        
        Args:
            query: Natural language query
            query_type: Type of query (single-agent, multi-agent, etc.)
            iterations: Number of times to run the query
            
        Returns:
            Performance statistics
        """
        execution_times = []
        llm_calls = []
        tool_calls = []
        cache_hits = []
        iterations_counts = []
        
        print(f"Profiling query: {query} ({iterations} iterations)")
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Call query API endpoint
                response = await self.client.post(
                    f"{self.base_url}/api/v1/query",
                    json={"query_text": query}
                )
                response.raise_for_status()
                result = response.json()
                
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                execution_times.append(execution_time)
                
                # Collect metrics
                if result.get("performance"):
                    perf = result["performance"]
                    llm_calls.append(perf.get("llm_calls", 0))
                    tool_calls.append(perf.get("tool_calls", 0))
                    cache_hits.append(perf.get("cache_hits", 0))
                
                if result.get("agentic_metadata"):
                    metadata = result["agentic_metadata"]
                    iterations_counts.append(metadata.get("iterations", 0))
                
                print(f"  Iteration {i+1}/{iterations}: {execution_time:.2f}ms")
                
            except Exception as e:
                print(f"  Iteration {i+1}/{iterations} failed: {e}")
                continue
        
        # Calculate statistics
        stats = {
            "query": query,
            "query_type": query_type,
            "iterations": iterations,
            "successful_runs": len(execution_times),
            "execution_time": {
                "min": min(execution_times) if execution_times else 0,
                "max": max(execution_times) if execution_times else 0,
                "mean": statistics.mean(execution_times) if execution_times else 0,
                "median": statistics.median(execution_times) if execution_times else 0,
                "stdev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            },
            "llm_calls": {
                "min": min(llm_calls) if llm_calls else 0,
                "max": max(llm_calls) if llm_calls else 0,
                "mean": statistics.mean(llm_calls) if llm_calls else 0,
            },
            "tool_calls": {
                "min": min(tool_calls) if tool_calls else 0,
                "max": max(tool_calls) if tool_calls else 0,
                "mean": statistics.mean(tool_calls) if tool_calls else 0,
            },
            "cache_hits": {
                "total": sum(cache_hits),
                "mean": statistics.mean(cache_hits) if cache_hits else 0,
            },
            "coordinator_iterations": {
                "min": min(iterations_counts) if iterations_counts else 0,
                "max": max(iterations_counts) if iterations_counts else 0,
                "mean": statistics.mean(iterations_counts) if iterations_counts else 0,
            },
        }
        
        self.results.append(stats)
        return stats
    
    async def run_performance_suite(self) -> Dict[str, Any]:
        """
        Run comprehensive performance profiling suite.
        
        Returns:
            Complete performance report
        """
        print("=" * 80)
        print("Starting Agentic Query Performance Profiling")
        print("=" * 80)
        
        # Single-agent queries (target: <5s)
        print("\n[1/4] Profiling Single-Agent Queries...")
        await self.profile_query(
            "Show me all critical vulnerabilities",
            "single-agent-security",
            iterations=10
        )
        
        await self.profile_query(
            "List all APIs in gateway local",
            "single-agent-discovery",
            iterations=10
        )
        
        await self.profile_query(
            "Show me APIs with high latency",
            "single-agent-metrics",
            iterations=10
        )
        
        # Multi-agent queries (target: <10s)
        print("\n[2/4] Profiling Multi-Agent Queries...")
        await self.profile_query(
            "Which APIs have both high latency and security vulnerabilities?",
            "multi-agent-metrics-security",
            iterations=5
        )
        
        await self.profile_query(
            "Show me APIs in production gateway with compliance violations",
            "multi-agent-discovery-compliance",
            iterations=5
        )
        
        # Iterative queries (target: 2-3 iterations)
        print("\n[3/4] Profiling Iterative Queries...")
        await self.profile_query(
            "Show APIs managed by gateway local",
            "iterative-gateway-resolution",
            iterations=5
        )
        
        await self.profile_query(
            "Show insecure APIs managed by gateway local",
            "iterative-multi-step",
            iterations=5
        )
        
        # Complex queries
        print("\n[4/4] Profiling Complex Queries...")
        await self.profile_query(
            "What is the compliance status of my slowest APIs?",
            "complex-multi-domain",
            iterations=3
        )
        
        # Generate report
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Returns:
            Performance report with validation results
        """
        print("\n" + "=" * 80)
        print("Performance Profiling Report")
        print("=" * 80)
        
        # Categorize results
        single_agent_results = [r for r in self.results if "single-agent" in r["query_type"]]
        multi_agent_results = [r for r in self.results if "multi-agent" in r["query_type"]]
        iterative_results = [r for r in self.results if "iterative" in r["query_type"]]
        
        # Calculate category averages
        single_agent_avg = statistics.mean([
            r["execution_time"]["mean"] for r in single_agent_results
        ]) if single_agent_results else 0
        
        multi_agent_avg = statistics.mean([
            r["execution_time"]["mean"] for r in multi_agent_results
        ]) if multi_agent_results else 0
        
        iterative_avg_iterations = statistics.mean([
            r["coordinator_iterations"]["mean"] for r in iterative_results
        ]) if iterative_results else 0
        
        # Validate performance targets
        single_agent_pass = single_agent_avg < 5000  # <5s
        multi_agent_pass = multi_agent_avg < 10000  # <10s
        iterations_pass = iterative_avg_iterations <= 3  # 2-3 iterations
        
        # Print summary
        print("\n📊 Performance Summary:")
        print(f"  Single-Agent Queries: {single_agent_avg:.2f}ms (target: <5000ms) {'✅ PASS' if single_agent_pass else '❌ FAIL'}")
        print(f"  Multi-Agent Queries: {multi_agent_avg:.2f}ms (target: <10000ms) {'✅ PASS' if multi_agent_pass else '❌ FAIL'}")
        print(f"  Coordinator Iterations: {iterative_avg_iterations:.1f} (target: ≤3) {'✅ PASS' if iterations_pass else '❌ FAIL'}")
        
        # Print detailed results
        print("\n📋 Detailed Results:")
        for result in self.results:
            print(f"\n  Query: {result['query']}")
            print(f"  Type: {result['query_type']}")
            print(f"  Execution Time: {result['execution_time']['mean']:.2f}ms (±{result['execution_time']['stdev']:.2f}ms)")
            print(f"  LLM Calls: {result['llm_calls']['mean']:.1f}")
            print(f"  Tool Calls: {result['tool_calls']['mean']:.1f}")
            print(f"  Cache Hits: {result['cache_hits']['mean']:.1f}")
            print(f"  Iterations: {result['coordinator_iterations']['mean']:.1f}")
        
        # Generate report dict
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "single_agent_avg_ms": single_agent_avg,
                "multi_agent_avg_ms": multi_agent_avg,
                "iterative_avg_iterations": iterative_avg_iterations,
                "single_agent_pass": single_agent_pass,
                "multi_agent_pass": multi_agent_pass,
                "iterations_pass": iterations_pass,
                "overall_pass": single_agent_pass and multi_agent_pass and iterations_pass,
            },
            "detailed_results": self.results,
        }
        
        print("\n" + "=" * 80)
        print(f"Overall Status: {'✅ ALL TARGETS MET' if report['summary']['overall_pass'] else '❌ SOME TARGETS MISSED'}")
        print("=" * 80)
        
        return report


async def main():
    """Main entry point for profiling script."""
    profiler = AgenticQueryProfiler()
    report = await profiler.run_performance_suite()
    
    # Optionally save report to file
    import json
    with open("performance_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Report saved to: performance_report.json")
    
    # Close client
    await profiler.client.aclose()
    
    return report


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
