"""
SimplyHired India job scraper using Selenium.

URL pattern: https://www.simplyhired.co.in/search?q={role}&l=India
Extracts: title, company, location, salary (parsed to int), link, description, required_skills, education, platform
"""
import re
import time
import logging
from datetime import datetime, timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)

logger = logging.getLogger(__name__)

LIMIT = 30
PAGE_WAIT = 10


def _parse_salary(salary_text: str) -> int | None:
    """
    Convert salary strings to monthly integer (INR).
    Examples:
      "₹50,000 a month"         → 50000
      "₹6,00,000 a year"        → 50000
      "From ₹40,000 a month"    → 40000
      "₹50,000 - ₹60,000 a month" → 55000
    """
    if not salary_text:
        return None
    try:
        text = salary_text.replace("From", "").replace("Up to", "").strip()
        period = "month"
        if "a year" in text:
            period = "year"
        nums = re.findall(r"[\d,]+", text)
        if not nums:
            return None
        amounts = [float(n.replace(",", "")) for n in nums]
        avg = sum(amounts) / len(amounts)
        if period == "year":
            avg /= 12
        return int(avg)
    except Exception:
        return None


def _safe_text(driver_or_el, by, selector, default="") -> str:
    try:
        return driver_or_el.find_element(by, selector).text.strip()
    except NoSuchElementException:
        return default


def _extract_skills_from_text(text: str) -> list[str]:
    """Extract skill keywords from description text using common tech patterns."""
    tech_keywords = [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue",
        "Node.js", "Django", "Flask", "FastAPI", "Spring", "SQL", "MySQL",
        "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "Azure",
        "GCP", "Git", "Linux", "REST", "API", "HTML", "CSS", "TensorFlow",
        "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Machine Learning", "Deep Learning",
        "NLP", "Data Analysis", "Power BI", "Tableau", "Excel", "C++", "C#", "Go",
        "Rust", "Kotlin", "Swift", "Flutter", "React Native", "DevOps", "CI/CD",
        "Jenkins", "Terraform", "Ansible", "R", "MATLAB", "Spark", "Hadoop",
    ]
    found = []
    text_lower = text.lower()
    for kw in tech_keywords:
        if kw.lower() in text_lower:
            found.append(kw)
        if len(found) >= 10:
            break
    return found


def _extract_education_from_text(text: str) -> str:
    """Extract education requirements from description text."""
    patterns = [
        r"(B\.?Tech|B\.?E|B\.?Sc|Bachelor[']?s?|Master[']?s?|M\.?Tech|M\.?Sc|MBA|Ph\.?D|MCA|BCA|Diploma)[^\n.]*",
        r"(UG|PG)\s*:\s*[^\n]+",
        r"Education\s*:\s*[^\n]+",
        r"degree in [^\n.]+",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()[:200]
    return ""


def parse(role: str, driver) -> list[dict]:
    """
    Scrape SimplyHired India for jobs matching `role`.
    Returns a list of job dicts ready for MongoDB insertion.
    """
    jobs: list[dict] = []
    seen_links: set[str] = set()
    page = 1

    logger.info(f"[SimplyHired] Starting scrape for role='{role}'")

    while len(jobs) < LIMIT:
        encoded_role = role.replace(" ", "+")
        url = (
            f"https://www.simplyhired.co.in/search?q={encoded_role}&l=India"
            if page == 1
            else f"https://www.simplyhired.co.in/search?q={encoded_role}&l=India&pn={page}"
        )

        try:
            driver.get(url)
            WebDriverWait(driver, PAGE_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='searchSerpJob']"))
            )
        except TimeoutException:
            logger.warning(f"[SimplyHired] Timeout on page {page}, stopping.")
            break

        cards = driver.find_elements(By.CSS_SELECTOR, "[data-testid='searchSerpJob']")
        if not cards:
            logger.info(f"[SimplyHired] No cards on page {page}, stopping.")
            break

        page_jobs = 0
        for card in cards:
            if len(jobs) >= LIMIT:
                break
            try:
                # Click card to reveal description panel
                card.click()
                time.sleep(1.2)

                title = _safe_text(card, By.CSS_SELECTOR, "[data-testid='searchSerpJobTitle']")
                company = _safe_text(card, By.CSS_SELECTOR, "[data-testid='companyName']")
                location = _safe_text(card, By.CSS_SELECTOR, "[data-testid='searchSerpJobLocation']")
                salary_raw = _safe_text(card, By.CSS_SELECTOR, "[data-testid='searchSerpJobSalaryConfirmed']")

                try:
                    link_el = card.find_element(By.CSS_SELECTOR, "a[data-testid='searchSerpJobTitleLink']")
                    link = link_el.get_attribute("href") or ""
                except NoSuchElementException:
                    try:
                        link_el = card.find_element(By.CSS_SELECTOR, "[data-testid='searchSerpJobTitle']")
                        link = link_el.get_attribute("href")
                        if not link:
                            link = link_el.find_element(By.TAG_NAME, "a").get_attribute("href") or ""
                    except NoSuchElementException:
                        link = ""

                if not title or link in seen_links:
                    continue

                # Get full description from the right side panel
                description = ""
                try:
                    desc_panel = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "[data-testid='viewJobBodyJobFullDescriptionContent']")
                        )
                    )
                    description = desc_panel.text[:2000]
                except TimeoutException:
                    pass

                # Extract skills and education from description text
                required_skills = _extract_skills_from_text(description)
                education = _extract_education_from_text(description)

                # Also try extracting skills from qualifications panel if present
                try:
                    qual_items = driver.find_elements(
                        By.CSS_SELECTOR,
                        "[data-testid='viewJobQualificationsContainer'] li"
                    )
                    if qual_items:
                        qual_text = " ".join([el.text for el in qual_items])
                        extra_skills = _extract_skills_from_text(qual_text)
                        for s in extra_skills:
                            if s not in required_skills:
                                required_skills.append(s)
                        required_skills = required_skills[:10]
                        if not education:
                            education = _extract_education_from_text(qual_text)
                except Exception:
                    pass

                seen_links.add(link)
                jobs.append({
                    "name": title,
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": _parse_salary(salary_raw),
                    "salary_text": salary_raw or None,
                    "link": link,
                    "description": description,
                    "required_skills": required_skills,
                    "education": education,
                    "platform": "simplyhired",
                    "scraped_at": datetime.now(timezone.utc),
                })
                page_jobs += 1

            except StaleElementReferenceException:
                continue
            except Exception as e:
                logger.debug(f"[SimplyHired] Error parsing card: {e}")
                continue

        logger.info(f"[SimplyHired] Page {page}: collected {page_jobs} jobs (total {len(jobs)})")

        if page_jobs == 0:
            logger.info(f"[SimplyHired] No new jobs collected on page {page}, stopping.")
            break

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "[aria-label='next']")
            if not next_btn.is_enabled():
                break
        except NoSuchElementException:
            break

        page += 1
        time.sleep(1.5)

    logger.info(f"[SimplyHired] Done — {len(jobs)} jobs scraped.")
    return jobs
