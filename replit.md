# Automated IT Job Search System

## Overview

A full-stack automated job discovery engine that crawls popular job boards daily, filters IT positions by keywords, and presents curated opportunities through a modern web dashboard. The system runs completely free using open-source tools and stores all data locally.

## Project Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Browser   │ ◄─────► │   Next.js    │ ◄─────► │   FastAPI    │
│             │         │   Frontend   │   HTTP  │   Backend    │
└─────────────┘         │  (Port 5000) │   API   │  (Port 8000) │
                        └──────────────┘         └──────┬───────┘
                                                        │
                                                        ▼
                                                  ┌──────────┐
                                                  │  SQLite  │
                                                  │ Database │
                                                  └──────────┘
```

### Technology Stack

**Backend (Python)**
- **FastAPI**: High-performance async web framework for REST API
- **SQLAlchemy**: ORM for database operations
- **BeautifulSoup4**: HTML parsing and web scraping
- **Requests**: HTTP client for web requests
- **APScheduler**: Background task scheduling for daily crawls
- **SQLite**: Lightweight file-based database
- **Uvicorn**: ASGI server

**Frontend (JavaScript/TypeScript)**
- **Next.js 16**: React framework with server-side rendering
- **React 19**: UI library
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **TypeScript**: Type-safe JavaScript

## Features

### Core Functionality

1. **Automated Daily Crawling**
   - Scheduled crawls at configurable time (default: 7:00 AM)
   - Scrapes multiple job boards: RemoteOK, WeWorkRemotely
   - Respects rate limits and implements polite scraping

2. **Keyword-Based Filtering**
   - Customizable keyword list for IT skills (Python, JavaScript, React, etc.)
   - Relevance scoring algorithm (2 points for title match, 1 point for description match)
   - Only stores jobs matching at least one keyword

3. **Job Management**
   - View all discovered jobs with search and filtering
   - Mark jobs as "Applied" to track applications
   - Add personal notes to each job listing
   - Deduplication prevents storing the same job twice

4. **Settings Management**
   - Configure keywords for filtering
   - Set preferred locations
   - Enable/disable specific job sources
   - Customize daily crawl schedule

### API Endpoints

- `GET /api/jobs` - Retrieve job listings with optional filters (search, location, applied status)
- `GET /api/jobs/{id}` - Get detailed information for a specific job
- `PATCH /api/jobs/{id}` - Update job (mark as applied, add notes)
- `POST /api/rescan` - Manually trigger job crawling
- `GET /api/settings` - Get current settings
- `PUT /api/settings` - Update settings (keywords, locations, sources, schedule)
- `GET /api/stats` - Get job statistics (total, applied, pending, by source)

## Getting Started

### Prerequisites

Both Python 3.11+ and Node.js 20+ are already installed in this Replit environment.

### Running the Application

The application is configured to run automatically with two workflows:

1. **Backend API** (Port 8000): FastAPI server with database, crawler, and scheduler
2. **Frontend** (Port 5000): Next.js development server

Both workflows start automatically. To manually restart them:
- Use the Replit workflows panel to restart either service
- Or run manually:
  ```bash
  # Backend
  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
  
  # Frontend
  cd frontend && npm run dev
  ```

### First-Time Setup

1. **Configure Keywords**: Visit `/settings` and add your IT skills/keywords
2. **Trigger Initial Crawl**: Click "Rescan Jobs" button on the dashboard
3. **Review Jobs**: Browse discovered jobs on the homepage
4. **Track Applications**: Mark jobs as applied and add notes

## Project Structure

```
.
├── backend/
│   ├── main.py           # FastAPI application and API endpoints
│   ├── models.py         # SQLAlchemy database models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── database.py       # Database configuration and session management
│   ├── crawler.py        # Web scraping logic for job boards
│   ├── scheduler.py      # APScheduler setup for daily crawls
│   └── config.py         # Configuration settings
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Dashboard with job listings
│   │   ├── jobs/[id]/page.tsx    # Job detail page
│   │   ├── settings/page.tsx     # Settings page
│   │   └── layout.tsx            # Root layout
│   ├── components/
│   │   ├── JobCard.tsx          # Job listing card component
│   │   └── FilterBar.tsx        # Search and filter component
│   ├── lib/
│   │   └── api.ts               # API client and TypeScript types
│   └── package.json
│
├── jobs.db               # SQLite database (created automatically)
└── replit.md            # This documentation file
```

## Database Schema

### Jobs Table
- `id`: Primary key
- `job_hash`: Unique hash for deduplication (MD5 of title+company+url)
- `title`: Job title
- `company`: Company name
- `location`: Job location
- `description`: Full job description
- `requirements`: Job requirements (optional)
- `url`: Original job posting URL
- `source`: Job board source (RemoteOK, WeWorkRemotely, etc.)
- `post_date`: When job was posted (if available)
- `relevance_score`: Calculated relevance based on keyword matching
- `keywords_matched`: Comma-separated list of matched keywords
- `applied`: Boolean flag for application status
- `notes`: Personal notes about the job
- `created_at`: When job was added to database
- `updated_at`: Last update timestamp

### Settings Table
- `key`: Setting name (keywords, locations, sources, schedule)
- `value`: JSON-encoded setting value
- `updated_at`: Last update timestamp

## Web Scraping Implementation

### Current Sources

1. **RemoteOK** (`https://remoteok.com/remote-dev-jobs`)
   - Scrapes job listings from tech job board
   - Extracts: title, company, location, tags/description, URL

2. **WeWorkRemotely** (`https://weworkremotely.com/categories/remote-programming-jobs`)
   - Focuses on remote programming positions
   - Extracts: title, company, region, URL

### Scraping Ethics & Best Practices

- Respects `robots.txt` (check manually before deploying)
- Implements 2-second delays between requests to avoid overwhelming servers
- Uses proper User-Agent headers
- Handles errors gracefully (retries, logging)
- Only stores jobs matching user keywords (reduces data volume)

### Adding New Job Sources

To add a new job board:

1. Create a new method in `backend/crawler.py`:
   ```python
   def crawl_newsite(self) -> List[JobCreate]:
       # Fetch and parse HTML
       # Extract job data
       # Calculate relevance score
       # Return JobCreate objects
   ```

2. Add to `crawl_all_sources()` method
3. Add source to `config.py` JOB_SOURCES dict
4. Update frontend settings page to include new source

## Relevance Scoring Algorithm

Jobs are scored based on keyword matching:
- **Title match**: +2.0 points per keyword
- **Description match**: +1.0 point per keyword
- Jobs with score 0 are filtered out (not stored)

Example: A job with title "Python Developer" and description mentioning "React, Django":
- If keywords include ["Python", "React", "Django"]
- Score = 2.0 (Python in title) + 1.0 (React in desc) + 1.0 (Django in desc) = 4.0

## Scheduled Automation

The system uses APScheduler to run daily crawls automatically:

- **Default Schedule**: 7:00 AM daily
- **Configurable**: Change time in Settings page
- **Runs on startup**: Scheduler starts when backend launches
- **Background execution**: Non-blocking async tasks
- **Persistent**: Schedule saved to database

To modify schedule:
1. Go to Settings page
2. Change "Crawl Schedule" hour/minute
3. Click "Save Settings"
4. Restart backend workflow for changes to take effect

## Configuration

### Backend Configuration (`backend/config.py`)

```python
class Settings:
    DATABASE_URL: str = "sqlite:///./jobs.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    DEFAULT_KEYWORDS: List[str] = [
        "Python", "JavaScript", "React", "Node.js", "FastAPI",
        "Software Engineer", "Full Stack", "Backend", "Frontend",
        "DevOps", "Data Engineer", "Machine Learning", "AI"
    ]
    
    DEFAULT_LOCATIONS: List[str] = ["Remote", "United States"]
    
    CRAWL_SCHEDULE_HOUR: int = 7
    CRAWL_SCHEDULE_MINUTE: int = 0
    
    MAX_JOBS_PER_SOURCE: int = 50
```

### Frontend Configuration

API URL is configured in `frontend/next.config.ts`:
```typescript
env: {
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
}
```

## Usage Guide

### Dashboard Features

1. **Search Bar**: Filter jobs by title, company, or keywords
2. **Location Filter**: Find jobs in specific locations
3. **Status Filter**: Show all jobs, only unapplied, or only applied
4. **Rescan Button**: Manually trigger immediate job crawl
5. **Job Cards**: Display job info with relevance score and matched keywords

### Job Detail Page

- View complete job description and requirements
- Click "Apply Now" to open original job posting in new tab
- Mark job as "Applied" to track your applications
- Add personal notes (interview dates, contacts, etc.)

### Settings Page

1. **Search Keywords**: Add/remove IT skills and technologies to search for
2. **Preferred Locations**: Specify geographic preferences
3. **Job Sources**: Enable/disable specific job boards
4. **Crawl Schedule**: Set when daily automation runs

## Troubleshooting

### Backend Not Starting
```bash
# Check if port 8000 is already in use
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend Not Loading
```bash
# Rebuild frontend dependencies
cd frontend && npm install && npm run dev
```

### No Jobs Found After Crawl
- Job boards may have changed their HTML structure
- Keywords might be too specific (try broader terms like "Developer", "Engineer")
- Check backend logs for scraping errors
- Websites may be rate-limiting requests

### Database Locked Error
- SQLite doesn't handle concurrent writes well
- Restart backend to release locks
- For production use, consider PostgreSQL

## Future Enhancements

### Recommended Next Steps

1. **Auto-Apply Functionality**: Implement form-filling automation using Playwright
2. **Advanced NLP**: Use spaCy or transformers for semantic job matching
3. **Email Notifications**: Send daily digest of new high-relevance jobs
4. **Resume Parsing**: Auto-match resume against job requirements
5. **Application Tracking**: Full applicant tracking system (ATS) features
6. **More Job Boards**: Add Indeed, LinkedIn, Glassdoor scrapers
7. **PostgreSQL Support**: Better multi-user and concurrent access
8. **Docker Deployment**: Containerize for easy deployment
9. **Testing**: Add pytest for backend, Jest for frontend
10. **Analytics Dashboard**: Track application success rates, popular companies

### Scaling Considerations

For high-volume usage:
- Migrate from SQLite to PostgreSQL
- Add Redis for caching and session management
- Implement Celery for distributed task queue
- Deploy frontend on Vercel, backend on AWS/DigitalOcean
- Add CDN for static assets
- Implement full-text search with Elasticsearch

## License & Compliance

This is a personal job search tool. When using:

1. **Respect ToS**: Check each job board's Terms of Service before scraping
2. **Rate Limiting**: Current implementation is polite but verify with site policies
3. **Personal Use**: This tool is designed for individual job seekers, not commercial scraping
4. **Data Privacy**: All data stored locally in SQLite (no external services)
5. **No Warranty**: Use at your own risk; websites may change without notice

## Support & Contribution

### Getting Help

- Check backend logs: `/tmp/logs/Backend_API_*.log`
- Check frontend logs: `/tmp/logs/Frontend_*.log`
- Verify both workflows are running in Replit workflows panel
- Review browser console for frontend errors

### Known Limitations

- Web scraping depends on HTML structure (breaks when sites update)
- SQLite not ideal for concurrent access (single-user focus)
- No authentication (suitable for personal/local use only)
- Limited to sites that allow scraping

## Technical Notes

### Why These Technologies?

- **FastAPI**: Modern, fast, automatic API docs, excellent for async web scraping
- **Next.js**: Best-in-class React framework, great DX, fast performance
- **SQLite**: Zero configuration, perfect for single-user desktop apps
- **BeautifulSoup**: Simple, reliable HTML parsing (unlike regex approaches)
- **Tailwind CSS**: Rapid UI development without custom CSS

### Performance

- Typical crawl time: 5-15 seconds for 2 sources
- Database size: ~1-2 MB per 100 jobs
- Memory usage: Backend ~50MB, Frontend ~150MB
- Suitable for thousands of job listings

---

**Version**: 1.0.0  
**Created**: October 2025  
**Last Updated**: October 2025
