from duckduckgo_search import DDGS
import logging
import requests
from bs4 import BeautifulSoup

# قائمة المواقع الموثوقة للبحث فيها عن معلومات الرحلات
TRUSTED_SITES = [
    "tourscanner.com",
    "getyourguide.com",
    "viator.com",
    "tripadvisor.com",
    "tiqets.com",
    "headout.com",
    "trip.com",
    "ftstravels.com"  # موقع الشركة الرسمي
]

AGENCY_DOMAINS = {
    "getyourguide": "getyourguide.com",
    "viator": "viator.com",
    "headout": "headout.com",
    "tiqets": "tiqets.com",
    "trip.com": "trip.com",
    "expedia": "expedia.com",
    "fts": "ftstravels.com",
    "fts travels": "ftstravels.com"
}

def fetch_page_content(url):
    """
    Simulates a browser visit to fetch key content from the page.
    Acts as a 'Headless Scraper' to read the full brochure.
    """
    try:
        # Use a real browser User-Agent to avoid simple blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        logging.info(f"Opening URL deeply: {url}")
        print(f"🌍 DEEP DIVE: Opening Official URL -> {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove scripts, styles, navigation, footer to focus on content
        for script in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            script.decompose()
            
        # Get text
        text = soup.get_text(separator='\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        print(f"✅ DEEP DIVE SUCCESS: Extracted {len(text)} chars from page.")
        
        # Limit length to avoid overwhelming the AI context window
        # We take the first 5000 chars which usually contain the description and inclusions
        return text[:5000] 
    except Exception as e:
        logging.warning(f"Failed to fetch content from {url}: {e}")
        return None

def search_agency_specific(agency_name, trip_name, query_details, max_results=3):
    """
    Search strictly within the Agency's domain.
    """
    domain = None
    agency_lower = agency_name.lower()
    
    # Find domain
    for key, url in AGENCY_DOMAINS.items():
        if key in agency_lower:
            domain = url
            break
    
    # If Agency domain not found, default to FTS
    if not domain:
        domain = "ftstravels.com"
        
    results = []
    
    # STRATEGY 1: Search for YOUR Company's Trip on that Platform first
    # Example: site:getyourguide.com "FTS Travels" "Luxor Trip"
    company_specific_query = f'site:{domain} "FTS Travels" {trip_name} {query_details}'
    logging.info(f"Executing Agency Strategy 1 (Company Specific): {company_specific_query}")
    
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(company_specific_query, max_results=2))
            for r in raw_results:
                results.append(f"Source: {agency_name} (FTS Listing) - {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
    except Exception as e:
        logging.warning(f"Agency Strategy 1 failed: {e}")

    # STRATEGY 2: If no specific company listing found, search for the Trip generally on that Platform
    if not results:
        general_platform_query = f'site:{domain} {trip_name} {query_details}'
        logging.info(f"Executing Agency Strategy 2 (General Platform): {general_platform_query}")
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(general_platform_query, max_results=max_results))
                for r in raw_results:
                    results.append(f"Source: {agency_name} (General) - {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")
        except Exception as e:
             logging.error(f"Agency Strategy 2 failed: {e}")

    return "\n---\n".join(results)

def search_travel_info(query, max_results=3):
    """
    يقوم بالبحث في الإنترنت عن استفسار العميل، مع التركيز على منصات السفر الموثوقة.
    INCLUDES DEEP SCRAPING for Official Site results.
    """
    results = []
    
    # 1. Search specifically for the Trip Product on OTAs (Broad Search)
    # This helps find the "Real Trip" page (Itinerary, Meeting Point) even if FTS isn't mentioned.
    logging.info(f"Searching web for: {query}")

    try:
        with DDGS() as ddgs:
            # STRATEGY 0: PRIORITY SEARCH - OFFICIAL COMPANY WEBSITE
            # We first try to find the answer on the official website ONLY.
            official_query = f"site:ftstravels.com {query}"
            logging.info(f"Executing Official Site Search: {official_query}")
            official_results = list(ddgs.text(official_query, max_results=3))
            
            for r in official_results:
                title = r.get('title', '')
                link = r.get('href', '')
                snippet = r.get('body', '')
                
                # --- DEEP DIVE FEATURE ---
                # If it's the official site, let's open the page and read it!
                page_content = fetch_page_content(link)
                if page_content:
                    # Append the FULL content (truncated) instead of just the snippet
                    results.append(f"Source: OFFICIAL WEBSITE (FULL CONTENT) - {title}\nURL: {link}\n--- PAGE CONTENT START ---\n{page_content}\n--- PAGE CONTENT END ---\n")
                else:
                    results.append(f"Source: OFFICIAL WEBSITE ({title})\nURL: {link}\nSnippet: {snippet}\n")

            # Strategy A: Direct Search on Trusted Platforms (Best for finding Product Details)
            # Only if we need more info or official site didn't give enough (e.g. < 2 results)
            if len(results) < 2:
                # We search for the query + key platforms
                platform_query = f"{query} site:tourscanner.com OR site:getyourguide.com OR site:viator.com OR site:tripadvisor.com"
                
                logging.info(f"Executing Platform Search: {platform_query}")
                platform_results = list(ddgs.text(platform_query, max_results=3))
                
                for r in platform_results:
                    # Avoid duplicates from official site if by chance appeared
                    if not any(r.get('href') in res for res in results):
                        title = r.get('title', '')
                        link = r.get('href', '')
                        snippet = r.get('body', '')
                        results.append(f"Source: OTA/Aggregator ({title})\nURL: {link}\nSnippet: {snippet}\n")

            # Strategy B: General Search with Company Context (If specific product not found or query is general)
            if len(results) < 2:
                if "fts" not in query.lower():
                    general_query = f"{query} FTS Travels Hurghada"
                else:
                    general_query = query
                
                logging.info(f"Executing General Context Search: {general_query}")
                general_results = list(ddgs.text(general_query, max_results=3))
                
                for r in general_results:
                    # Avoid duplicates
                    if not any(r.get('href') in res for res in results):
                        results.append(f"Source: General Web ({r.get('title')})\nURL: {r.get('href')}\nSnippet: {r.get('body')}\n")

    except Exception as e:
        logging.error(f"Web search failed: {e}")
        return f"Error performing web search: {str(e)}"

    if not results:
        return "No relevant information found on the web."

    return "\n---\n".join(results[:max_results+2]) # Return a bit more if available

if __name__ == "__main__":
    # Test the search tool
    logging.basicConfig(level=logging.INFO)
    print(search_travel_info("Orange Bay trip price for kids"))
