import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { NotificationProvider } from './contexts/NotificationContext';

// Page imports
import Dashboard from './pages/Dashboard';
import APIs from './pages/APIs';
import Gateways from './pages/Gateways';
import Predictions from './pages/Predictions';
import Optimization from './pages/Optimization';
import { Query } from './pages/Query';
import { Security } from './pages/Security';
import { Compliance } from './pages/Compliance';
import Analytics from './pages/Analytics';

// Placeholder components for routes (will be implemented in user stories)
const Metrics = () => <div className="p-6"><h1 className="text-2xl font-bold">Metrics</h1></div>;
const NotFound = () => <div className="p-6"><h1 className="text-2xl font-bold">404 - Page Not Found</h1></div>;

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes (formerly cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * Main App component with routing configuration.
 * 
 * Routes:
 * - / : Dashboard (default)
 * - /apis : API Inventory
 * - /metrics : Performance Metrics
 * - /predictions : Failure Predictions
 * - /security : Security Findings
 * - /query : Natural Language Query Interface
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NotificationProvider>
        <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          {/* Navigation will be added in user story implementation */}
          <nav className="bg-white shadow-sm border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <div className="flex-shrink-0 flex items-center">
                    <h1 className="text-xl font-bold text-gray-900">
                      API Intelligence Plane
                    </h1>
                  </div>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <Link
                      to="/"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Dashboard
                    </Link>
                    <Link
                      to="/apis"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      APIs
                    </Link>
                    <Link
                      to="/gateways"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Gateways
                    </Link>                    
                    <Link
                      to="/predictions"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Predictions
                    </Link>
                    <Link
                      to="/optimization"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Optimization
                    </Link>
                    <Link
                      to="/security"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Security
                    </Link>
                    <Link
                      to="/compliance"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Compliance
                    </Link>
                    <Link
                      to="/analytics"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Analytics
                    </Link>
                    <Link
                      to="/query"
                      className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                    >
                      Query
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          {/* Main content */}
          <main>
            <Routes>
              {/* Gateway-first routes */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/gateways" element={<Gateways />} />
              <Route path="/gateways/:gatewayId" element={<Gateways />} />
              
              {/* Feature routes - support optional gateway context */}
              <Route path="/apis" element={<APIs />} />
              <Route path="/apis/detail/:apiId" element={<APIs />} />
              <Route path="/apis/:gatewayId" element={<APIs />} />
              <Route path="/predictions" element={<Predictions />} />
              <Route path="/predictions/:gatewayId" element={<Predictions />} />
              <Route path="/optimization" element={<Optimization />} />
              <Route path="/optimization/:gatewayId" element={<Optimization />} />
              <Route path="/security" element={<Security />} />
              <Route path="/security/:gatewayId" element={<Security />} />
              <Route path="/compliance" element={<Compliance />} />
              <Route path="/compliance/:gatewayId" element={<Compliance />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/analytics/:gatewayId" element={<Analytics />} />
              <Route path="/query" element={<Query />} />
              <Route path="/metrics" element={<Metrics />} />
              
              {/* Error routes */}
              <Route path="/404" element={<NotFound />} />
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </main>
        </div>
        </BrowserRouter>
      </NotificationProvider>

      {/* React Query Devtools (only in development) */}
      {/* {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />} */}
    </QueryClientProvider>
  );
}

export default App;

// Made with Bob
