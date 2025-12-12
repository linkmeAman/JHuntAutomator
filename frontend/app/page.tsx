'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { fetchJobs, triggerRescan, fetchRuns, Job, CrawlResult, CrawlRun } from '@/lib/api';
import JobCard from '@/components/JobCard';
import FilterBar from '@/components/FilterBar';

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filteredJobs, setFilteredJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<CrawlResult | null>(null);
  const [lastRun, setLastRun] = useState<CrawlRun | null>(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [appliedFilter, setAppliedFilter] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    loadJobs();
    loadLastRun();
  }, []);

  useEffect(() => {
    filterJobs();
  }, [jobs, searchQuery, locationFilter, appliedFilter]);

  const loadJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchJobs();
      setJobs(data);
    } catch (err) {
      setError('Failed to load jobs. Make sure the backend is running.');
      console.error('Error loading jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadLastRun = async () => {
    try {
      const runs = await fetchRuns({ limit: 1 });
      setLastRun(runs[0] || null);
    } catch (err) {
      console.error('Error loading runs:', err);
    }
  };

  const filterJobs = () => {
    let filtered = [...jobs];

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        job =>
          job.title.toLowerCase().includes(query) ||
          job.company.toLowerCase().includes(query) ||
          job.description.toLowerCase().includes(query)
      );
    }

    if (locationFilter) {
      const location = locationFilter.toLowerCase();
      filtered = filtered.filter(job => job.location.toLowerCase().includes(location));
    }

    if (appliedFilter !== undefined) {
      filtered = filtered.filter(job => job.applied === appliedFilter);
    }

    setFilteredJobs(filtered);
  };

  const handleRescan = async () => {
    try {
      setScanning(true);
      setScanResult(null);
      const result = await triggerRescan();
      setScanResult(result);
      await loadJobs();
      await loadLastRun();
    } catch (err) {
      setError('Failed to trigger rescan. Make sure the backend is running.');
      console.error('Error triggering rescan:', err);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">IT Job Search</h1>
              <p className="mt-1 text-sm text-gray-600">Automated daily job discovery</p>
            </div>
            <nav className="flex space-x-4">
              <Link
                href="/"
                className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md"
              >
                Dashboard
              </Link>
              <Link
                href="/settings"
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md"
              >
                Settings
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {scanResult && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">{scanResult.message}</h3>
                <div className="mt-2 text-sm text-green-700">
                  <p>Found {scanResult.jobs_found} jobs, added {scanResult.jobs_added} new jobs to the database.</p>
                </div>
              </div>
              <button
                onClick={() => setScanResult(null)}
                className="ml-auto -mx-1.5 -my-1.5 bg-green-50 text-green-500 rounded-lg p-1.5 hover:bg-green-100"
              >
                <span className="sr-only">Dismiss</span>
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">{error}</h3>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-auto -mx-1.5 -my-1.5 bg-red-50 text-red-500 rounded-lg p-1.5 hover:bg-red-100"
              >
                <span className="sr-only">Dismiss</span>
                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        )}

        <FilterBar
          onSearch={setSearchQuery}
          onLocationFilter={setLocationFilter}
          onAppliedFilter={setAppliedFilter}
          onRescan={handleRescan}
          isScanning={scanning}
        />

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">
            {filteredJobs.length} Job{filteredJobs.length !== 1 ? 's' : ''} Found
          </h2>
          <div className="text-sm text-gray-500">
            Sorted by relevance score
          </div>
        </div>

        {lastRun && (
          <div className="mb-6 bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Last Crawl</p>
                <p className="text-lg font-semibold text-gray-900">{new Date(lastRun.started_at).toLocaleString()}</p>
                <p className="text-sm text-gray-600">Inserted {lastRun.inserted_new_count} / Fetched {lastRun.fetched_count}</p>
              </div>
              <div className="text-sm text-gray-600">
                Failures: {lastRun.sources_failed.length}
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No jobs found</h3>
            <p className="mt-1 text-sm text-gray-500">Try adjusting your search filters or trigger a new scan.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredJobs.map(job => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
