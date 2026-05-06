import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Metric, TimeBucket } from '../types'
import { api } from '../services/api'
import analyticsService from '../services/analytics'
import GatewayFilter from '../components/analytics/GatewayFilter'
import MetricsChart from '../components/analytics/MetricsChart'
import MetricsTable from '../components/analytics/MetricsTable'
import TimeBucketSelector from '../components/analytics/TimeBucketSelector'
import TransactionalLogViewer from '../components/analytics/TransactionalLogViewer'
import Card from '../components/common/Card'
import Loading from '../components/common/Loading'
import Error from '../components/common/Error'

const Analytics = () => {
  const [selectedGatewayId, setSelectedGatewayId] = useState<string | undefined>()
  const [selectedMetric, setSelectedMetric] = useState<Metric | null>(null)
  const [timeBucket, setTimeBucket] = useState<TimeBucket>('1h')
  const [view, setView] = useState<'metrics' | 'logs'>('metrics')

  const metricsQueryParams = useMemo(
    () => ({
      gateway_id: selectedGatewayId,
      time_bucket: timeBucket,
      limit: 50,
    }),
    [selectedGatewayId, timeBucket]
  )

  const {
    data: gatewaysResponse,
    isLoading: gatewaysLoading,
    error: gatewaysError,
  } = useQuery({
    queryKey: ['gateways'],
    queryFn: () => api.gateways.list(),
    refetchInterval: 30000,
  })

  const {
    data: metricsResponse,
    isLoading: metricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ['analytics-metrics', metricsQueryParams],
    queryFn: () => analyticsService.getMetrics(metricsQueryParams),
    refetchInterval: 30000,
  })

  const {
    data: logsResponse,
    isLoading: logsLoading,
    error: logsError,
  } = useQuery({
    queryKey: ['analytics-logs', selectedMetric?.id, metricsQueryParams],
    queryFn: () =>
      analyticsService.getLogsForMetric(selectedMetric!.id, {
        gateway_id: selectedGatewayId,
        time_bucket: timeBucket,
        limit: 100,
      }),
    enabled: Boolean(selectedMetric),
    refetchInterval: 30000,
  })

  const gateways = gatewaysResponse?.items || gatewaysResponse || []
  const metrics = metricsResponse?.items || []
  const logs = logsResponse?.items || []

  const summary = useMemo(() => {
    const totalRequests = metrics.reduce((sum, metric) => sum + metric.request_count, 0)
    const totalFailures = metrics.reduce((sum, metric) => sum + metric.failure_count, 0)
    const avgP95 =
      metrics.length > 0
        ? metrics.reduce((sum, metric) => sum + metric.response_time_p95, 0) / metrics.length
        : 0

    return {
      totalRequests,
      totalFailures,
      avgP95,
    }
  }, [metrics])

  if (gatewaysLoading && metricsLoading) {
    return (
      <div className="p-6">
        <Loading message="Loading analytics dashboard..." />
      </div>
    )
  }

  if (gatewaysError || metricsError) {
    return (
      <div className="p-6">
        <Error
          message="Failed to load analytics data"
          onRetry={() => {
            refetchMetrics()
          }}
        />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">API Analytics</h1>
        <p className="mt-2 text-sm text-gray-600">
          Explore aggregated gateway metrics and drill down into transactional logs
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <GatewayFilter
          gateways={gateways}
          value={selectedGatewayId}
          onChange={(gatewayId) => {
            setSelectedGatewayId(gatewayId)
            setSelectedMetric(null)
            setView('metrics')
          }}
        />
        <TimeBucketSelector
          value={timeBucket}
          onChange={(nextBucket) => {
            setTimeBucket(nextBucket)
            setSelectedMetric(null)
            setView('metrics')
          }}
        />
        <Card title="Summary" padding="sm">
          <dl className="space-y-2 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-gray-500">Total Requests</dt>
              <dd className="font-semibold text-gray-900">
                {summary.totalRequests.toLocaleString()}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-gray-500">Total Failures</dt>
              <dd className="font-semibold text-gray-900">
                {summary.totalFailures.toLocaleString()}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-gray-500">Average P95</dt>
              <dd className="font-semibold text-gray-900">
                {summary.avgP95.toFixed(1)} ms
              </dd>
            </div>
          </dl>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <MetricsChart
          metrics={metrics}
          onSelectMetric={(metric) => {
            setSelectedMetric(metric)
            setView('logs')
          }}
        />
        <Card
          title="Metrics Table"
          subtitle="Select a row to inspect related raw log events"
        >
          <MetricsTable
            metrics={metrics}
            loading={metricsLoading}
            onSelectMetric={(metric) => {
              setSelectedMetric(metric)
              setView('logs')
            }}
          />
        </Card>
      </div>

      <Card
        title="Drill-Down Logs"
        subtitle={
          selectedMetric
            ? `Showing logs for metric bucket captured at ${new Date(
                selectedMetric.timestamp
              ).toLocaleString()}`
            : 'Select a metric bucket from the chart or table to inspect raw transactional logs'
        }
      >
        <div className="mb-4 flex items-center justify-between gap-4 rounded-md border border-gray-200 bg-gray-50 px-4 py-3">
          <div className="text-sm text-gray-600">
            <span className="font-medium text-gray-900">Navigation:</span>{' '}
            <button
              type="button"
              onClick={() => setView('metrics')}
              className={`${
                view === 'metrics' ? 'text-blue-600 font-semibold' : 'text-gray-600'
              }`}
            >
              Metrics
            </button>
            <span className="mx-2 text-gray-400">→</span>
            <button
              type="button"
              onClick={() => {
                if (selectedMetric) {
                  setView('logs')
                }
              }}
              className={`${
                view === 'logs' ? 'text-blue-600 font-semibold' : 'text-gray-600'
              } disabled:cursor-not-allowed disabled:text-gray-400`}
              disabled={!selectedMetric}
            >
              Logs
            </button>
          </div>
          {view === 'logs' && selectedMetric ? (
            <button
              type="button"
              onClick={() => setView('metrics')}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 transition hover:bg-white"
            >
              Back to metrics
            </button>
          ) : null}
        </div>

        {view === 'logs' && selectedMetric && logsError ? (
          <Error
            type="warning"
            message="Failed to load drill-down logs for the selected metric"
          />
        ) : view === 'logs' && selectedMetric ? (
          <TransactionalLogViewer logs={logs} loading={logsLoading} />
        ) : (
          <div className="py-8 text-sm text-gray-500">
            Drill-down results will appear here after selecting a metric bucket.
          </div>
        )}
      </Card>
    </div>
  )
}

export default Analytics

// Made with Bob
