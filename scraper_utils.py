import re
import time
from typing import List, Dict, Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from googlesearch import search

# Tentative d'import de curl_cffi, sinon fallback sur requests standard
try:
    from curl_cffi import requests as http_requests
    USE_CURL = True
except ImportError:
    import requests as http_requests
    USE_CURL = False

# Regex pour emails (standard + formes avec [at])
EMAIL_STANDARD = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
EMAIL_AT_PATTERN = r'([A-Za-z0-9._%+-]+)\s*\[?\(?at\)?\]?\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})'
PHONE_REGEX = r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'

def extract_emails_from_text(text: str) -> Set[str]:
    emails = set(re.findall(EMAIL_STANDARD, text, re.IGNORECASE))
    matches = re.findall(EMAIL_AT_PATTERN, text, re.IGNORECASE)
    for local, domain in matches:
        emails.add(f"{local.lower()}@{domain.lower()}")
    return emails

def extract_phones(text: str) -> Set[str]:
    phones = re.findall(PHONE_REGEX, text)
    return {p for p in phones if len(p) > 5}

def scrape_page_contacts(url: str, timeout: int = 15) -> Dict:
    result = {"url": url, "emails": set(), "phones": set(), "error": None}
    try:
        if USE_CURL:
            response = http_requests.get(url, timeout=timeout, impersonate="chrome110")
        else:
            response = http_requests.get(url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Liens mailto: et tel:
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("mailto:"):
                email = href[7:].split('?')[0]
                result["emails"].add(email)
            elif href.startswith("tel:"):
                phone = href[4:]
                result["phones"].add(phone)
        
        # Texte visible
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        
        result["emails"].update(extract_emails_from_text(text))
        result["phones"].update(extract_phones(text))
        
    except Exception as e:
        result["error"] = f"Request or parsing error: {str(e)}"
    return result

def scrape_team_contact_urls(base_url: str, max_pages: int = 5) -> List[str]:
    keywords = ["equipe", "team", "contact", "about", "nous-contacter", "lequipe", "annuaire"]
    found_urls = set([base_url])
    try:
        if USE_CURL:
            response = http_requests.get(base_url, timeout=10, impersonate="chrome110")
        else:
            response = http_requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)
            if any(kw in href.lower() or kw in link.get_text().lower() for kw in keywords):
                found_urls.add(full_url)
            if len(found_urls) >= max_pages:
                break
    except Exception:
        pass
    return list(found_urls)

def google_dorking_for_profiles(query: str, num_results: int = 20) -> List[Dict]:
    platforms = {
        "linkedin": "site:linkedin.com/in/",
        "twitter": "site:twitter.com/",
        "facebook": "site:facebook.com/"
    }
    results = []
    for platform, dork_prefix in platforms.items():
        full_query = f"{dork_prefix} {query} (email OR contact OR téléphone OR phone)"
        try:
            for url in search(full_query, num_results=num_results//3, stop=num_results//3):
                results.append({
                    "platform": platform,
                    "url": url,
                    "title": f"Profil {platform} trouvé"
                })
                time.sleep(1)
        except Exception as e:
            results.append({"platform": platform, "url": "", "error": str(e)})
    return results

def enrich_profil_with_scraping(profile_url: str) -> Dict:
    result = {"url": profile_url, "emails": set(), "phones": set()}
    try:
        if USE_CURL:
            response = http_requests.get(profile_url, timeout=10, impersonate="chrome110")
        else:
            response = http_requests.get(profile_url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            if link["href"].startswith("mailto:"):
                result["emails"].add(link["href"][7:].split('?')[0])
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        result["emails"].update(extract_emails_from_text(text))
        result["phones"].update(extract_phones(text))
    except Exception:
        pass
    return result

def find_emails_by_domain(domain: str) -> list:
    url = "https://email-finder7.p.rapidapi.com/email-address/find-many-domain"
    headers = {
        "x-rapidapi-key": "34d123d824msh2a9d154c1b93836p10784f6jsn936ca35bc983",
        "x-rapidapi-host": "email-finder7.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    params = {"domaine": domain}   # paramètre correct
    try:
        response = http_requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Extraction selon la structure observée
            if data.get("error") is None and "payload" in data:
                payload = data["payload"]
                if "data" in payload and isinstance(payload["data"], list):
                    emails = []
                    for item in payload["data"]:
                        if "address" in item:
                            emails.append(item["address"])
                    return emails
            print("Structure inattendue :", data)
            return []
        else:
            print(f"Erreur HTTP {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []