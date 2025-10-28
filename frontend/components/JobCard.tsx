'use client';

import Link from 'next/link';
import { Job } from '@/lib/api';

interface JobCardProps {
  job: Job;
}

export default function JobCard({ job }: JobCardProps) {
  return (
    <Link href={`/jobs/${job.id}`}>
      <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer border border-gray-200">
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-gray-900 mb-1">{job.title}</h3>
            <p className="text-gray-700 font-medium">{job.company}</p>
          </div>
          <div className="flex flex-col items-end ml-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              Score: {job.relevance_score.toFixed(1)}
            </span>
            {job.applied && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 mt-2">
                Applied
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-center text-sm text-gray-600 mb-3">
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          {job.location}
          <span className="mx-2">•</span>
          <span className="text-gray-500">{job.source}</span>
        </div>
        
        {job.keywords_matched && (
          <div className="flex flex-wrap gap-2 mb-3">
            {job.keywords_matched.split(', ').slice(0, 5).map((keyword, index) => (
              <span key={index} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
                {keyword}
              </span>
            ))}
          </div>
        )}
        
        <p className="text-gray-600 text-sm line-clamp-2">{job.description}</p>
        
        <div className="mt-4 text-xs text-gray-500">
          Posted: {new Date(job.created_at).toLocaleDateString()}
        </div>
      </div>
    </Link>
  );
}
