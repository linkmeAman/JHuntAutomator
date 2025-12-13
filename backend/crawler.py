import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from .config import settings
from .models import Job
from .nlp import NLPScorer
from .schemas import JobCreate
from backend.crawl_engine.errors import SourceBadConfigError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobCrawler:
    def __init__(
        self,
        keywords: List[str],
        locations: List[str],
        max_jobs: int = 50,
        nlp_scorer: Optional[NLPScorer] = None,
        greenhouse_boards: Optional[List[Dict]] = None,
    ):
        self.keywords = keywords
        self.locations = locations
        self.max_jobs = max_jobs
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.nlp_scorer = nlp_scorer
        self.greenhouse_boards = greenhouse_boards or settings.GREENHOUSE_BOARDS
        
    def calculate_relevance_score(self, job_data: Dict) -> tuple:
        """Calculate relevance score based on keyword matching"""
        title = job_data.get("title", "").lower()
        description = job_data.get("description", "").lower()
        
        matched_keywords = []
        score = 0.0
        
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title:
                score += 2.0
                matched_keywords.append(keyword)
            elif keyword_lower in description:
                score += 1.0
                matched_keywords.append(keyword)

        if self.nlp_scorer:
            try:
                semantic_score = self.nlp_scorer.score(f"{job_data.get('title', '')} {job_data.get('description', '')}")
                score += semantic_score * settings.NLP_WEIGHT
            except Exception as exc:
                logger.error("Failed to compute NLP score: %s", exc)
        
        return score, ", ".join(matched_keywords)
    
    def crawl_remoteok(self) -> List[JobCreate]:
        """Crawl RemoteOK job board"""
        jobs = []
        try:
            url = "https://remoteok.com/remote-dev-jobs"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('tr', class_='job', limit=self.max_jobs)
                
                for job in job_listings[:self.max_jobs]:
                    try:
                        title_elem = job.find('h2', class_='title')
                        company_elem = job.find('h3', class_='company')
                        location_elem = job.find('div', class_='location')
                        link_elem = job.find('a', class_='preventLink')
                        
                        if title_elem and company_elem:
                            title = title_elem.text.strip()
                            company = company_elem.text.strip()
                            location = location_elem.text.strip() if location_elem else "Remote"
                            job_url = f"https://remoteok.com{link_elem['href']}" if link_elem and link_elem.get('href') else url
                            
                            description = title
                            tags = job.find_all('div', class_='tag')
                            if tags:
                                description += " | " + " ".join([tag.text.strip() for tag in tags])
                            
                            job_data = {
                                "title": title,
                                "company": company,
                                "location": location,
                                "description": description,
                                "url": job_url,
                                "source": "RemoteOK"
                            }
                            
                            score, keywords_matched = self.calculate_relevance_score(job_data)
                            
                            if score > 0:
                                job_hash = Job.generate_hash(title, company, job_url, "RemoteOK")
                                jobs.append(JobCreate(
                                    **job_data,
                                    job_hash=job_hash,
                                    relevance_score=score,
                                    keywords_matched=keywords_matched
                                ))
                    except Exception as e:
                        logger.error(f"Error parsing RemoteOK job: {e}")
                        continue
                
                logger.info(f"RemoteOK: Found {len(jobs)} relevant jobs")
            
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error crawling RemoteOK: {e}")
        
        return jobs

    def crawl_indeed(self) -> List[JobCreate]:
        """Crawl Indeed job listings using basic HTML scraping."""
        jobs: List[JobCreate] = []
        base_url = "https://www.indeed.com/jobs"
        headers = {"User-Agent": self.user_agent}

        try:
            for keyword in self.keywords:
                if len(jobs) >= self.max_jobs:
                    break
                for location in self.locations:
                    params = {
                        "q": keyword,
                        "l": location,
                        "sort": "date",
                        "limit": self.max_jobs,
                        "radius": 25,
                    }
                    response = requests.get(base_url, headers=headers, params=params, timeout=10)
                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, "html.parser")
                    job_cards = soup.select("div.job_seen_beacon")

                    for card in job_cards:
                        title_elem = card.select_one("h2.jobTitle span")
                        company_elem = card.select_one("span.companyName")
                        location_elem = card.select_one("div.companyLocation")
                        link_elem = card.select_one("a.jcs-JobTitle")
                        snippet_elem = card.select_one("div.job-snippet")

                        if not title_elem or not company_elem or not link_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        company = company_elem.get_text(strip=True)
                        location_text = location_elem.get_text(strip=True) if location_elem else location
                        url = f"https://www.indeed.com{link_elem.get('href')}"
                        description = snippet_elem.get_text(" ", strip=True) if snippet_elem else title

                        job_data = {
                            "title": title,
                            "company": company,
                            "location": location_text,
                            "description": description,
                            "url": url,
                            "source": "Indeed",
                        }

                        score, keywords_matched = self.calculate_relevance_score(job_data)
                        if score > 0:
                            job_hash = Job.generate_hash(title, company, url, "Indeed")
                            jobs.append(
                                JobCreate(
                                    **job_data,
                                    job_hash=job_hash,
                                    relevance_score=score,
                                    keywords_matched=keywords_matched,
                                )
                            )
                            if len(jobs) >= self.max_jobs:
                                break
                    time.sleep(2)
        except Exception as exc:
            logger.error("Error crawling Indeed: %s", exc)

        logger.info("Indeed: Found %s relevant jobs", len(jobs))
        return jobs

    def _greenhouse_api_from_url(self, board_url: str) -> str:
        slug = urlparse(board_url.rstrip("/")).path.rstrip("/").split("/")[-1]
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

    def crawl_greenhouse_boards(self) -> List[JobCreate]:
        """Fetch job listings from configured Greenhouse boards via JSON API."""
        jobs: List[JobCreate] = []
        headers = {"User-Agent": self.user_agent}

        for board in self.greenhouse_boards:
            if len(jobs) >= self.max_jobs:
                break

            board_url = board.get("board_url") if isinstance(board, dict) else str(board)
            board_name = board.get("name") if isinstance(board, dict) else str(board)
            api_url = self._greenhouse_api_from_url(board_url)

            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    if response.status_code == 404:
                        logger.warning("Greenhouse board %s invalid (404)", board_name)
                        raise SourceBadConfigError(f"Greenhouse board invalid: {board_name}")
                    logger.warning("Greenhouse board %s responded with %s", board_name, response.status_code)
                    continue

                data = response.json()
                for job in data.get("jobs", []):
                    title = job.get("title", "").strip()
                    absolute_url = job.get("absolute_url") or job.get("url") or board_url
                    location_data = job.get("location") or {}
                    location = location_data.get("name", "Remote")
                    content = job.get("content", "")
                    description = BeautifulSoup(content, "html.parser").get_text(" ", strip=True) or title
                    company_name = job.get("company", {}).get("name") or board_name
                    post_date = job.get("updated_at") or job.get("created_at")

                    job_data = {
                        "title": title,
                        "company": company_name,
                        "location": location,
                        "description": description,
                        "url": absolute_url,
                        "source": "Greenhouse",
                        "source_detail": board_name,
                        "post_date": post_date,
                    }

                    score, keywords_matched = self.calculate_relevance_score(job_data)
                    if score > 0:
                        job_hash = Job.generate_hash(title, company_name, absolute_url, "Greenhouse")
                        jobs.append(
                            JobCreate(
                                **job_data,
                                job_hash=job_hash,
                                relevance_score=score,
                                keywords_matched=keywords_matched,
                            )
                        )
                        if len(jobs) >= self.max_jobs:
                            break
                time.sleep(1)
            except Exception as exc:
                logger.error("Error crawling Greenhouse board %s: %s", board_name, exc)
                continue

        logger.info("Greenhouse: Found %s relevant jobs", len(jobs))
        return jobs
    
    def crawl_weworkremotely_rss(self) -> List[JobCreate]:
        """Crawl WeWorkRemotely using the stable RSS feed."""
        jobs: List[JobCreate] = []
        feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.get(feed_url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning("WeWorkRemotely RSS responded with %s", response.status_code)
                return jobs

            root = ET.fromstring(response.text)
            channel = root.find("channel")
            if channel is None:
                return jobs

            for item in channel.findall("item")[: self.max_jobs]:
                title_text = item.findtext("title", default="").strip()
                link = item.findtext("link", default=feed_url).strip()
                pub_date = item.findtext("pubDate")
                raw_description = item.findtext("description", default="")
                description = BeautifulSoup(raw_description, "html.parser").get_text(" ", strip=True)

                company = "WeWorkRemotely"
                job_title = title_text
                if ":" in title_text:
                    parts = title_text.split(":", 1)
                    company = parts[0].strip() or company
                    job_title = parts[1].strip() or job_title

                job_data = {
                    "title": job_title,
                    "company": company,
                    "location": "Remote",
                    "description": description or job_title,
                    "url": link or feed_url,
                    "source": "WeWorkRemotely",
                    "post_date": pub_date,
                }

                score, keywords_matched = self.calculate_relevance_score(job_data)
                if score > 0:
                    job_hash = Job.generate_hash(job_title, company, job_data["url"], "WeWorkRemotely")
                    jobs.append(
                        JobCreate(
                            **job_data,
                            job_hash=job_hash,
                            relevance_score=score,
                            keywords_matched=keywords_matched,
                        )
                    )

            logger.info("WeWorkRemotely RSS: Found %s relevant jobs", len(jobs))
        except Exception as exc:
            logger.error("Error crawling WeWorkRemotely RSS: %s", exc)

        return jobs
    
    def crawl_all_sources(self, enabled_sources: dict) -> List[JobCreate]:
        """Crawl all enabled job sources"""
        all_jobs = []
        
        if enabled_sources.get("remoteok", True):
            all_jobs.extend(self.crawl_remoteok())
        
        if enabled_sources.get("weworkremotely", True):
            all_jobs.extend(self.crawl_weworkremotely_rss())

        if enabled_sources.get("indeed", False):
            logger.warning(
                "Indeed scraping is brittle/ToS-sensitive; enable only for personal use."
            )
            try:
                all_jobs.extend(self.crawl_indeed())
            except Exception as exc:
                logger.error("Indeed crawl failed but run will continue: %s", exc)

        if enabled_sources.get("greenhouse", False):
            all_jobs.extend(self.crawl_greenhouse_boards())
        
        all_jobs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Total jobs found across all sources: {len(all_jobs)}")
        return all_jobs
