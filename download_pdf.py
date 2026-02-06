import json
import os
import time
import requests
import random
from typing import Optional, Dict, List
from urllib.parse import quote

# Import existing classes to reuse session logic
try:
    from linkedin_activity_fetcher import LinkedInActivityFetcher
except ImportError:
    print("❌ Could not import LinkedInActivityFetcher. Make sure it's in the same directory.")
    exit(1)

class ProfilePdfDownloader(LinkedInActivityFetcher):
    """
    Extends LinkedInActivityFetcher to add PDF download capability
    """
    
    def __init__(self):
        super().__init__()
        # Query ID from user provided request
        self.QUERY_ID = "voyagerIdentityDashProfileActionsV2.ca80b3b293240baf5a00226d8d6d78a1"

    def get_pdf_download_url(self, profile_urn: str) -> Optional[str]:
        """
        Fetches the PDF download URL for a given profile URN.
        """
        try:
            print(f"\n📄 Fetching PDF download URL for: {profile_urn}")

            # Get cookies from browser - using parent class method
            # We assume browser is already launched and cookies loaded via parent methods
            cookies = self.get_cookies_dict()
            
            if not cookies and self.context:
                 cookies = {c['name']: c['value'] for c in self.context.cookies()}

            # Get CSRF token
            csrf_token = cookies.get('JSESSIONID', '').replace('"', '')

            if not csrf_token:
                print("⚠️ Warning: No CSRF token found in cookies")

            # Get user agent and platform from page if available, else defaults
            try:
                user_agent = self.page.evaluate("navigator.userAgent")
                platform = self.page.evaluate("navigator.platform")
            except:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                platform = "Linux"

            # Determine platform string
            if 'Linux' in platform:
                platform_header = '"Linux"'
            elif 'Win' in platform:
                platform_header = '"Windows"'
            elif 'Mac' in platform:
                platform_header = '"macOS"'
            else:
                platform_header = '"Linux"'

            # Build headers
            headers = {
                'accept': 'application/vnd.linkedin.normalized+json+2.1',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'content-type': 'application/json; charset=UTF-8',
                'csrf-token': csrf_token,
                'origin': 'https://www.linkedin.com',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': 'https://www.linkedin.com/',
                'sec-ch-ua': '"Chromium";v="120", "Not=A?Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': platform_header,
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': user_agent,
                'x-li-lang': 'en_US',
                'x-li-track': '{"clientVersion":"1.13.40128","mpVersion":"1.13.40128","osName":"web","timezoneOffset":5.5,"timezone":"Asia/Calcutta","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":1,"displayWidth":1920,"displayHeight":1080}',
                'x-restli-protocol-version': '2.0.0'
            }

            # Construct GraphQL URL
            # The variables need to be passed. Based on standard LinkedIn GraphQL structure.
            # Usually it's ?action=execute&queryId=...&variables=...
            # BUT the user showed a POST request.
            # Let's try POST first as per user log.
            
            url = f"https://www.linkedin.com/voyager/api/graphql?action=execute&queryId={self.QUERY_ID}"
            
            # Construct Payload
            payload = {
                "variables": {
                    "profileUrn": profile_urn
                },
                "queryId": self.QUERY_ID
            }

            print(f"📡 Making API request...")
            print(f"   URL: {url}")
            print(f"   Payload: {json.dumps(payload)}")
            
            # Using session for efficiency if possible, but requests is fine
            response = requests.post(url, headers=headers, cookies=cookies, json=payload)

            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"   Response: {response.text[:500]}...")
                return None

        except Exception as e:
            print(f"❌ Error fetching PDF URL: {e}")
            import traceback
            traceback.print_exc()
            return None

    def download_file(self, url: str, output_path: str) -> bool:
        """
        Downloads a file from a URL to the specified path using authenticated session.
        """
        try:
            print(f"⬇️ Downloading PDF to {output_path}...")
            
            # Get cookies for authentication
            cookies = self.get_cookies_dict()
            if not cookies and self.context:
                 cookies = {c['name']: c['value'] for c in self.context.cookies()}
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.linkedin.com/"
            }

            response = requests.get(url, stream=True, cookies=cookies, headers=headers)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"   ✅ Download complete")
                return True
            else:
                print(f"   ❌ Download failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Download error: {e}")
            return False

def main():
    downloader = ProfilePdfDownloader()
    
    # Define output directories
    JSON_OUTPUT_DIR = "output/pdf_json"
    PDF_OUTPUT_DIR = "output/username_pdf"
    
    # Ensure they exist (redundant if mkdir was run, but safe)
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
    
    # Needs playwright to start for cookie loading/handling
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        downloader.p = p
        
        # 1. Login/Load Session
        if not downloader.login_to_linkedin():
            print("❌ Failed to initialize session")
            return

        # 2. Target Profiles (user input)
        raw_targets = input("\n📝 Enter LinkedIn username or profile URL (comma-separated for multiple): ").strip()
        if not raw_targets:
            print("❌ No targets provided")
            return

        targets = [t.strip() for t in raw_targets.split(",") if t.strip()]
        if not targets:
            print("❌ No valid targets provided")
            return
        
        results = []

        for target in targets:
            print(f"\n⚡ Processing: {target}")
            
            # Get URN
            urn = downloader.extract_profile_urn(target)
            
            if urn:
                print(f"   URN: {urn}")
                # Get PDF Data
                pdf_data = downloader.get_pdf_download_url(urn)
                
                if pdf_data:
                    results.append({
                        "profile": target,
                        "urn": urn,
                        "data": pdf_data
                    })
                    print("   ✅ PDF data retrieved")
                    
                    # Extract Download URL and Download PDF immediately
                    try:
                        # Handle potential double nesting of 'data' which was observed in the output
                        # Standard path: pdf_data['data']['doSaveToPdf...']
                        # Observed path: pdf_data['data']['data']['doSaveToPdf...']
                        
                        root_data = pdf_data.get('data', {})
                        if 'data' in root_data:
                            root_data = root_data['data']
                            
                        action_result = root_data.get('doSaveToPdfV2IdentityDashProfileActionsV2', {})
                        download_url = action_result.get('result', {}).get('downloadUrl')
                        
                        if download_url:
                            pdf_path = os.path.join(PDF_OUTPUT_DIR, f"{target}.pdf")
                            downloader.download_file(download_url, pdf_path)
                        else:
                            print(f"   ⚠️ 'downloadUrl' not found in response structure")
                            # print(f"   Debug structure keys: {root_data.keys()}")

                    except Exception as e:
                        print(f"   ⚠️ Could not extract download URL: {e}")

                else:
                    print("   ❌ Failed to get PDF data")
            else:
                print("   ❌ Failed to resolve URN")
            
            time.sleep(random.uniform(2, 5))

        # 3. Save Results
        if results:
            json_path = os.path.join(JSON_OUTPUT_DIR, "pdf_downloads.json")
            with open(json_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Saved {len(results)} results to {json_path}")
        
        downloader.close()

if __name__ == "__main__":
    main()
