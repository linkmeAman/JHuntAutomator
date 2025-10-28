import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import logging
from .schemas import JobCreate
from .models import Job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobCrawler:
    def __init__(self, keywords: List[str], locations: List[str], max_jobs: int = 50):
        self.keywords = keywords
        self.locations = locations
        self.max_jobs = max_jobs
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
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
                                job_hash = Job.generate_hash(title, company, job_url)
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
    
    def crawl_weworkremotely(self) -> List[JobCreate]:
        """Crawl WeWorkRemotely job board"""
        jobs = []
        try:
            url = "https://weworkremotely.com/categories/remote-programming-jobs"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                job_listings = soup.find_all('li', class_='feature')
                
                for job in job_listings[:self.max_jobs]:
                    try:
                        title_elem = job.find('span', class_='title')
                        company_elem = job.find('span', class_='company')
                        link_elem = job.find('a')
                        
                        if title_elem and company_elem and link_elem:
                            title = title_elem.text.strip()
                            company = company_elem.text.strip()
                            location = "Remote"
                            job_url = f"https://weworkremotely.com{link_elem['href']}"
                            
                            region = job.find('span', class_='region')
                            description = title
                            if region:
                                description += f" | {region.text.strip()}"
                            
                            job_data = {
                                "title": title,
                                "company": company,
                                "location": location,
                                "description": description,
                                "url": job_url,
                                "source": "WeWorkRemotely"
                            }
                            
                            score, keywords_matched = self.calculate_relevance_score(job_data)
                            
                            if score > 0:
                                job_hash = Job.generate_hash(title, company, job_url)
                                jobs.append(JobCreate(
                                    **job_data,
                                    job_hash=job_hash,
                                    relevance_score=score,
                                    keywords_matched=keywords_matched
                                ))
                    except Exception as e:
                        logger.error(f"Error parsing WeWorkRemotely job: {e}")
                        continue
                
                logger.info(f"WeWorkRemotely: Found {len(jobs)} relevant jobs")
            
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error crawling WeWorkRemotely: {e}")
        
        return jobs
    
    def crawl_all_sources(self, enabled_sources: dict) -> List[JobCreate]:
        """Crawl all enabled job sources"""
        all_jobs = []
        
        if enabled_sources.get("remoteok", True):
            all_jobs.extend(self.crawl_remoteok())
        
        if enabled_sources.get("weworkremotely", True):
            all_jobs.extend(self.crawl_weworkremotely())
        
        all_jobs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Total jobs found across all sources: {len(all_jobs)}")
        return all_jobs
