'use client';

import { useState } from 'react';

interface FilterBarProps {
  onSearch: (query: string) => void;
  onLocationFilter: (location: string) => void;
  onAppliedFilter: (applied: boolean | undefined) => void;
  onRescan: () => void;
  isScanning: boolean;
}

export default function FilterBar({ onSearch, onLocationFilter, onAppliedFilter, onRescan, isScanning }: FilterBarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [location, setLocation] = useState('');
  const [appliedFilter, setAppliedFilter] = useState<string>('all');

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    onSearch(value);
  };

  const handleLocationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocation(value);
    onLocationFilter(value);
  };

  const handleAppliedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setAppliedFilter(value);
    onAppliedFilter(value === 'all' ? undefined : value === 'applied');
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-2">
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-2">
            Search
          </label>
          <input
            id="search"
            type="text"
            placeholder="Search jobs by title, company, or keywords..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="w-full px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
          />
        </div>
        
        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-2">
            Location
          </label>
          <input
            id="location"
            type="text"
            placeholder="Filter by location..."
            value={location}
            onChange={handleLocationChange}
            className="w-full px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
          />
        </div>
        
        <div>
          <label htmlFor="applied" className="block text-sm font-medium text-gray-700 mb-2">
            Status
          </label>
          <select
            id="applied"
            value={appliedFilter}
            onChange={handleAppliedChange}
            className="w-full px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Jobs</option>
            <option value="pending">Not Applied</option>
            <option value="applied">Applied</option>
          </select>
        </div>
      </div>
      
      <div className="mt-4 flex justify-end">
        <button
          onClick={onRescan}
          disabled={isScanning}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isScanning ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Scanning...
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Rescan Jobs
            </>
          )}
        </button>
      </div>
    </div>
  );
}
