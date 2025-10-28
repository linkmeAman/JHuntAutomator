'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchJob, updateJob, Job } from '@/lib/api';

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (params.id) {
      loadJob(Number(params.id));
    }
  }, [params.id]);

  const loadJob = async (id: number) => {
    try {
      setLoading(true);
      const data = await fetchJob(id);
      setJob(data);
      setNotes(data.notes || '');
    } catch (err) {
      setError('Failed to load job details');
      console.error('Error loading job:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleApplied = async () => {
    if (!job) return;
    
    try {
      setSaving(true);
      const updated = await updateJob(job.id, { applied: !job.applied });
      setJob(updated);
    } catch (err) {
      console.error('Error updating job:', err);
      setError('Failed to update job status');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!job) return;
    
    try {
      setSaving(true);
      const updated = await updateJob(job.id, { notes });
      setJob(updated);
    } catch (err) {
      console.error('Error saving notes:', err);
      setError('Failed to save notes');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">{error}</h3>
          <Link href="/" className="text-blue-600 hover:text-blue-800">
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center">
            <Link href="/" className="mr-4 text-gray-600 hover:text-gray-900">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">Job Details</h1>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="border-b border-gray-200 pb-6 mb-6">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">{job.title}</h2>
                <p className="text-xl text-gray-700 mb-2">{job.company}</p>
              </div>
              <div className="flex flex-col items-end">
                <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-blue-100 text-blue-800 mb-2">
                  Score: {job.relevance_score.toFixed(1)}
                </span>
                {job.applied && (
                  <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    Applied
                  </span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
              <div className="flex items-center">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {job.location}
              </div>
              <div className="flex items-center">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
                {job.source}
              </div>
              <div className="flex items-center">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Added {new Date(job.created_at).toLocaleDateString()}
              </div>
            </div>

            {job.keywords_matched && (
              <div className="flex flex-wrap gap-2 mb-4">
                {job.keywords_matched.split(', ').map((keyword, index) => (
                  <span key={index} className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
                    {keyword}
                  </span>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={handleToggleApplied}
                disabled={saving}
                className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
                  job.applied
                    ? 'bg-gray-600 hover:bg-gray-700'
                    : 'bg-green-600 hover:bg-green-700'
                } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50`}
              >
                {job.applied ? 'Mark as Not Applied' : 'Mark as Applied'}
              </button>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Apply Now
                <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Description</h3>
            <div className="prose prose-blue max-w-none">
              <p className="text-gray-700 whitespace-pre-wrap">{job.description}</p>
            </div>
          </div>

          {job.requirements && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Requirements</h3>
              <div className="prose prose-blue max-w-none">
                <p className="text-gray-700 whitespace-pre-wrap">{job.requirements}</p>
              </div>
            </div>
          )}

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Personal Notes</h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="Add your notes about this job..."
            />
            <button
              onClick={handleSaveNotes}
              disabled={saving}
              className="mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              Save Notes
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
