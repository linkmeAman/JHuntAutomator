'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { fetchSettings, updateSettings, fetchRuns, fetchSourceStates, Settings, CrawlRun, SourceStateView } from '@/lib/api';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [runs, setRuns] = useState<CrawlRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [sourceStates, setSourceStates] = useState<SourceStateView[]>([]);
  const [sourceStatesLoading, setSourceStatesLoading] = useState(true);
  const [sourceStatesError, setSourceStatesError] = useState<string | null>(null);
  
  const [newKeyword, setNewKeyword] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [newBoardName, setNewBoardName] = useState('');
  const [newBoardUrl, setNewBoardUrl] = useState('');
  const [linkedinMode, setLinkedinMode] = useState<'email' | 'whitelist_crawl'>('email');

  useEffect(() => {
    loadSettings();
    loadRuns();
    loadSourceStates();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await fetchSettings();
      const normalized = {
        ...data,
        india_mode: data.india_mode ?? false,
        linkedin_mode: (data.linkedin_mode as 'email' | 'whitelist_crawl') || 'email',
        linkedin_email:
          data.linkedin_email || { imap: { host: '', port: 993, username: '' }, query: '', max_emails_per_run: 30 },
        linkedin_crawl: data.linkedin_crawl || { allowed: false, seed_urls: [], max_pages: 2, min_delay_sec: 3 },
      };
      setSettings(normalized);
      setLinkedinMode(normalized.linkedin_mode);
    } catch (err) {
      setError('Failed to load settings');
      console.error('Error loading settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadRuns = async () => {
    try {
      setRunsLoading(true);
      setRunsError(null);
      const data = await fetchRuns({ limit: 10 });
      setRuns(data);
    } catch (err) {
      setRunsError('Failed to load recent runs');
      console.error('Error loading runs:', err);
    } finally {
      setRunsLoading(false);
    }
  };

  const loadSourceStates = async () => {
    try {
      setSourceStatesLoading(true);
      setSourceStatesError(null);
      const data = await fetchSourceStates();
      setSourceStates(data);
    } catch (err) {
      setSourceStatesError('Failed to load source health');
      console.error('Error loading source states:', err);
    } finally {
      setSourceStatesLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);
      await updateSettings(settings);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError('Failed to save settings');
      console.error('Error saving settings:', err);
    } finally {
      setSaving(false);
    }
  };

  const addKeyword = () => {
    if (!newKeyword.trim() || !settings) return;
    if (!settings.keywords.includes(newKeyword.trim())) {
      setSettings({
        ...settings,
        keywords: [...settings.keywords, newKeyword.trim()]
      });
    }
    setNewKeyword('');
  };

  const removeKeyword = (keyword: string) => {
    if (!settings) return;
    setSettings({
      ...settings,
      keywords: settings.keywords.filter(k => k !== keyword)
    });
  };

  const addLocation = () => {
    if (!newLocation.trim() || !settings) return;
    if (!settings.locations.includes(newLocation.trim())) {
      setSettings({
        ...settings,
        locations: [...settings.locations, newLocation.trim()]
      });
    }
    setNewLocation('');
  };

  const removeLocation = (location: string) => {
    if (!settings) return;
    setSettings({
      ...settings,
      locations: settings.locations.filter(l => l !== location)
    });
  };

  const sourceGroups = [
    {
      title: 'Remote / Global',
      sources: ['remoteok', 'weworkremotely', 'greenhouse', 'remotive', 'workingnomads', 'remote_co'],
    },
    {
      title: 'India',
      sources: ['naukri', 'shine', 'timesjobs'],
    },
    {
      title: 'Restricted',
      sources: ['linkedin', 'glassdoor', 'wellfound', 'yc'],
      hint: 'LinkedIn imports via email alerts; direct crawl requires permission. Others restricted; enable only with official access.',
    },
  ];

  const toggleSource = (source: string) => {
    if (!settings) return;
    setSettings({
      ...settings,
      sources: {
        ...settings.sources,
        [source]: !settings.sources[source]
      }
    });
  };
  const setIndiaMode = (value: boolean) => {
    if (!settings) return;
    const updatedSources = { ...settings.sources };
    if (value) {
      ["naukri", "shine", "timesjobs"].forEach((src) => (updatedSources[src] = true));
      if (!settings.locations.includes("India")) {
        setSettings({
          ...settings,
          india_mode: value,
          sources: updatedSources,
          locations: [...settings.locations, "India"],
        });
        return;
      }
    }
    setSettings({ ...settings, india_mode: value, sources: updatedSources });
  };

  const addBoard = () => {
    if (!settings) return;
    if (!newBoardUrl.trim()) return;
    const name = newBoardName.trim() || newBoardUrl.trim();
    const board = { name, board_url: newBoardUrl.trim() };
    setSettings({
      ...settings,
      greenhouse_boards: [...(settings.greenhouse_boards || []), board],
    });
    setNewBoardName('');
    setNewBoardUrl('');
  };

  const removeBoard = (boardUrl: string) => {
    if (!settings) return;
    setSettings({
      ...settings,
      greenhouse_boards: (settings.greenhouse_boards || []).filter((b) => b.board_url !== boardUrl),
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!settings) return null;

  const safeLinkedInEmail = settings.linkedin_email || { imap: { host: '', port: 993, username: '' }, query: '' };
  const safeLinkedInCrawl = settings.linkedin_crawl || { allowed: false, seed_urls: [] };

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
            <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">LinkedIn</h2>
            <p className="text-sm text-gray-600 mb-4">
              LinkedIn imports via email alerts (recommended). Direct crawling requires explicit permission/whitelisting.
            </p>

            <div className="mb-4">
              <label className="text-sm font-medium text-gray-700 mb-2 block">Mode</label>
              <select
                value={linkedinMode}
                onChange={(e) => {
                  const mode = e.target.value as 'email' | 'whitelist_crawl';
                  setLinkedinMode(mode);
                  setSettings(settings ? { ...settings, linkedin_mode: mode } : null);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="email">Email (recommended)</option>
                <option value="whitelist_crawl">Whitelisted Crawl (requires permission)</option>
              </select>
            </div>

            {linkedinMode === 'email' && settings && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">IMAP Host</label>
                  <input
                    value={safeLinkedInEmail.imap?.host || ''}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        linkedin_email: {
                          ...safeLinkedInEmail,
                          imap: { ...(safeLinkedInEmail.imap || {}), host: e.target.value },
                        },
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">IMAP Port</label>
                    <input
                      type="number"
                      value={safeLinkedInEmail.imap?.port || 993}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          linkedin_email: {
                            ...safeLinkedInEmail,
                            imap: { ...(safeLinkedInEmail.imap || {}), port: parseInt(e.target.value) },
                          },
                        })
                      }
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">IMAP Username</label>
                    <input
                      value={safeLinkedInEmail.imap?.username || ''}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          linkedin_email: {
                            ...safeLinkedInEmail,
                            imap: { ...(safeLinkedInEmail.imap || {}), username: e.target.value },
                          },
                        })
                      }
                      className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Search Query</label>
                  <input
                    value={safeLinkedInEmail.query || ''}
                    onChange={(e) =>
                      setSettings({ ...settings, linkedin_email: { ...safeLinkedInEmail, query: e.target.value } })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
                  />
                  <p className="text-xs text-gray-500 mt-1">Default: from:jobalerts-noreply@linkedin.com OR subject:(Job Alert) newer_than:7d</p>
                </div>
              </div>
            )}

            {linkedinMode === 'whitelist_crawl' && settings && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={safeLinkedInCrawl.allowed}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        linkedin_crawl: { ...safeLinkedInCrawl, allowed: e.target.checked },
                      })
                    }
                  />
                  <span className="text-sm text-gray-800">I have explicit LinkedIn crawl permission (whitelisted).</span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Seed URLs (one per line)</label>
                  <textarea
                    value={(safeLinkedInCrawl.seed_urls || []).join('\n')}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        linkedin_crawl: { ...safeLinkedInCrawl, seed_urls: e.target.value.split('\n') },
                      })
                    }
                    rows={3}
                    className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
                  />
                  <p className="text-xs text-red-600 mt-1">Use only your own search URLs. Do not crawl without approval.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-green-400 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-sm font-medium text-green-800">Settings saved successfully!</p>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm font-medium text-red-800">{error}</p>
          </div>
        )}

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Search Keywords</h2>
            <p className="text-sm text-gray-600 mb-4">
              Add keywords to filter job postings. Jobs matching these keywords will receive higher relevance scores.
            </p>
            
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
                placeholder="Add a keyword (e.g., Python, React, AWS)"
                className="flex-1 px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={addKeyword}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Add
              </button>
            </div>
            
            <div className="flex flex-wrap gap-2">
              {settings.keywords.map((keyword, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                >
                  {keyword}
                  <button
                    onClick={() => removeKeyword(keyword)}
                    className="ml-2 text-blue-600 hover:text-blue-800"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Preferred Locations</h2>
            <p className="text-sm text-gray-600 mb-4">
              Specify locations you're interested in (e.g., "Remote", "New York", "San Francisco").
            </p>
            
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newLocation}
                onChange={(e) => setNewLocation(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addLocation()}
                placeholder="Add a location"
                className="flex-1 px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 shadow-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={addLocation}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Add
              </button>
            </div>
            
            <div className="flex flex-wrap gap-2">
              {settings.locations.map((location, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800"
                >
                  {location}
                  <button
                    onClick={() => removeLocation(location)}
                    className="ml-2 text-green-600 hover:text-green-800"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Job Sources</h2>
            <p className="text-sm text-gray-600 mb-4">
              Enable or disable job boards to crawl.
            </p>
              <div className="mb-4 flex items-center justify-between p-3 rounded-md border border-gray-200 bg-gray-50">
              <div>
                <p className="text-sm font-medium text-gray-900">India Mode</p>
                <p className="text-xs text-gray-600">Auto-selects India portals; you can still override manually.</p>
              </div>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={!!settings.india_mode}
                  onChange={(e) => setIndiaMode(e.target.checked)}
                />
                <div className={`w-10 h-5 rounded-full ${settings.india_mode ? 'bg-blue-600' : 'bg-gray-300'}`}>
                  <div className={`h-5 w-5 bg-white rounded-full shadow transform ${settings.india_mode ? 'translate-x-5' : 'translate-x-0'}`}></div>
                </div>
              </label>
            </div>

            <div className="space-y-6">
              {sourceGroups.map((group) => (
                <div key={group.title}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-gray-900">{group.title}</p>
                    {group.hint && <p className="text-xs text-gray-500">{group.hint}</p>}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {group.sources.map((source) => (
                      <label key={source} className="flex items-center space-x-2 rounded-md border border-gray-200 px-3 py-2">
                        <input
                          type="checkbox"
                          checked={settings.sources[source] ?? false}
                          onChange={() => toggleSource(source)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm text-gray-800 capitalize">{source.replace(/_/g, ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Greenhouse Boards</h2>
            <p className="text-sm text-gray-600 mb-4">
              Manage company boards without editing environment variables.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <input
                type="text"
                placeholder="Board name (optional)"
                value={newBoardName}
                onChange={(e) => setNewBoardName(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <input
                type="url"
                placeholder="Board URL (https://boards.greenhouse.io/...)"
                value={newBoardUrl}
                onChange={(e) => setNewBoardUrl(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                onClick={addBoard}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                disabled={!newBoardUrl.trim()}
              >
                Add Board
              </button>
            </div>

            <div className="space-y-2">
              {(settings.greenhouse_boards || []).map((board, idx) => (
                <div key={`${board.board_url}-${idx}`} className="flex items-center justify-between border border-gray-200 rounded-md px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{board.name}</p>
                    <p className="text-xs text-gray-600">{board.board_url}</p>
                  </div>
                  <button
                    onClick={() => removeBoard(board.board_url)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                </div>
              ))}
              {(settings.greenhouse_boards || []).length === 0 && (
                <p className="text-sm text-gray-600">No boards configured.</p>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Crawl Schedule</h2>
            <p className="text-sm text-gray-600 mb-4">
              Set the time for daily automatic job crawling.
            </p>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="hour" className="block text-sm font-medium text-gray-700 mb-2">
                  Hour (0-23)
                </label>
                <input
                  type="number"
                  id="hour"
                  min="0"
                  max="23"
                  value={settings.crawl_hour}
                  onChange={(e) => setSettings({ ...settings, crawl_hour: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label htmlFor="minute" className="block text-sm font-medium text-gray-700 mb-2">
                  Minute (0-59)
                </label>
                <input
                  type="number"
                  id="minute"
                  min="0"
                  max="59"
                  value={settings.crawl_minute}
                  onChange={(e) => setSettings({ ...settings, crawl_minute: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              Daily crawl will run at {settings.crawl_hour.toString().padStart(2, '0')}:{settings.crawl_minute.toString().padStart(2, '0')}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Source Health</h2>
                <p className="text-sm text-gray-600">Cooldowns, cursors, and last metrics</p>
              </div>
              <button
                onClick={loadSourceStates}
                className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
              >
                Refresh
              </button>
            </div>
            {sourceStatesError && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                {sourceStatesError}
              </div>
            )}
            {sourceStatesLoading ? (
              <div className="flex justify-center items-center py-6">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
              </div>
            ) : sourceStates.length === 0 ? (
              <p className="text-sm text-gray-600">No source state records yet.</p>
            ) : (
              <div className="overflow-auto">
                <table className="min-w-full text-sm text-left text-gray-700">
                  <thead>
                    <tr>
                      <th className="px-3 py-2 font-semibold">Source</th>
                      <th className="px-3 py-2 font-semibold">Last Success</th>
                      <th className="px-3 py-2 font-semibold">Cooldown Until</th>
                      <th className="px-3 py-2 font-semibold">Last Max Post Date</th>
                      <th className="px-3 py-2 font-semibold">Dedup Ratio Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourceStates.map((state) => {
                      const metrics = state.last_metrics || {};
                      const errors: string[] = metrics.errors || [];
                      const stopNote = errors.find((e) => e.includes('stop_on_seen_ratio'));
                      return (
                        <tr key={state.source_id} className="border-t border-gray-200">
                          <td className="px-3 py-2 font-semibold text-gray-900">{state.source_id}</td>
                          <td className="px-3 py-2">{state.last_success_at ? new Date(state.last_success_at).toLocaleString() : '—'}</td>
                          <td className="px-3 py-2 text-red-600">
                            {state.cooldown_until ? new Date(state.cooldown_until).toLocaleString() : '—'}
                          </td>
                          <td className="px-3 py-2">{state.last_max_post_date_seen || '—'}</td>
                          <td className="px-3 py-2 text-xs text-gray-600">{stopNote || '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Recent Runs</h2>
                <p className="text-sm text-gray-600">Last 10 crawls with outcomes</p>
              </div>
              <button
                onClick={loadRuns}
                className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
              >
                Refresh
              </button>
            </div>

            {runsError && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                {runsError}
              </div>
            )}

            {runsLoading ? (
              <div className="flex justify-center items-center py-6">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
              </div>
            ) : runs.length === 0 ? (
              <p className="text-sm text-gray-600">No crawl history yet.</p>
            ) : (
              <div className="space-y-4">
                {runs.map((run) => (
                  <div key={run.run_id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex flex-wrap justify-between gap-4">
                      <div>
                        <p className="text-sm text-gray-500">
                          Started {new Date(run.started_at).toLocaleString()}
                        </p>
                        <p className="text-lg font-semibold text-gray-900">
                          {run.inserted_new_count} new / {run.fetched_count} fetched
                        </p>
                        <p className="text-sm text-gray-600">
                          Duration: {run.duration_ms ? `${Math.round(run.duration_ms / 1000)}s` : '—'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">
                          Sources: {run.sources_succeeded.length} ok / {run.sources_failed.length} failed
                        </p>
                        {run.sources_failed.length > 0 && (
                          <p className="text-sm text-red-600 mt-1">
                            {run.sources_failed.map((f) => f.source).join(', ')}
                          </p>
                        )}
                      </div>
                    </div>
                    {run.errors_summary && (
                      <p className="mt-2 text-sm text-red-700 bg-red-50 px-2 py-1 rounded">
                        {run.errors_summary}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3">
            <Link
              href="/"
              className="px-6 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </Link>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
