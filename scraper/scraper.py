# import asyncio
# import re
# from playwright.async_api import async_playwright
# from bs4 import BeautifulSoup

# # --- CONFIGURATION ---
# # Add your target URLs here
# TARGET_URLS = [
#     "https://bankofmaharashtra.in/",
#     "https://bankofmaharashtra.bank.in/personal-banking/loans/personal-loan"
#     # Add more URLs as needed, e.g.:
#     # "https://bankofmaharashtra.in/personal-banking/loans/personal-loan",
# ]
# OUTPUT_FILE = "scraped_data.txt"

# async def auto_scroll(page):
#     """Scrolls down the page to trigger lazy loading."""
#     print("Starting auto-scroll...")
#     try:
#         last_height = await page.evaluate("document.body.scrollHeight")
        
#         while True:
#             await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
#             await page.wait_for_timeout(2000)  # Wait for content to load
            
#             new_height = await page.evaluate("document.body.scrollHeight")
#             if new_height == last_height:
#                 break
#             last_height = new_height
#         print("Auto-scroll complete.")
#     except Exception as e:
#         print(f"Auto-scroll failed: {e}")

# async def clean_text(text):
#     """Cleans the extracted text."""
#     lines = [line.strip() for line in text.splitlines() if line.strip()]
#     cleaned = "\n".join(lines)
#     return cleaned

# async def scrape_single_url(page, url):
#     """Scrapes a single URL using the provided page context."""
#     print(f"Navigating to page: {url}")
#     # Set default navigation timeout to 2 minutes
#     page.set_default_navigation_timeout(120000)

#     try:
#         # Go to URL
#         await page.goto(url, wait_until="domcontentloaded")
        
#         print("Waiting for initial load...")
#         try:
#             await page.wait_for_load_state("networkidle", timeout=10000)
#         except Exception:
#             print("Network idle timeout (non-critical), continuing...")

#         # Handle dynamic content
#         await auto_scroll(page)

#         # Get page content
#         content = await page.content()
#         soup = BeautifulSoup(content, "html.parser")
        
#         # Remove scripts and styles
#         for script in soup(["script", "style", "noscript", "iframe"]):
#             script.extract()

#         text = soup.get_text(separator="\n")
#         return await clean_text(text)

#     except Exception as e:
#         print(f"Error scraping {url}: {e}")
#         return None

# async def main():
#     print(f"Starting scraper for {len(TARGET_URLS)} URLs...")
    
#     # clear output file first or append? User asked to "save it", usually implies simple write or overwrite.
#     # Let's overwrite for a fresh run, but append for each url in the run.
#     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#         f.write(f"--- SCRAPED DATA REPORT ---\n")

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         context = await browser.new_context(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#         )
        
#         for url in TARGET_URLS:
#             page = await context.new_page()
#             data = await scrape_single_url(page, url)
            
#             if data:
#                 with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
#                     f.write(f"\n\n{'='*50}\nSRC: {url}\n{'='*50}\n\n")
#                     f.write(data)
#                 print(f"Saved data for: {url}")
            
#             await page.close()
#             await asyncio.sleep(1) # Polite delay

#         await browser.close()
#     print(f"All done! Check {OUTPUT_FILE}")

# if __name__ == "__main__":
#     asyncio.run(main())
