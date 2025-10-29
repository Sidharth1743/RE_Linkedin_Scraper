# LinkedIn Profile Scraper - Extract Specific Profile Link
# Targets: index 10 OR class "update-components-actor__image"

from playwright.sync_api import sync_playwright
import time
import random
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Optional


class LinkedInScraper:
    """
    LinkedIn scraper that extracts specific profile href link
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.p = None
    
    def save_cookies_safely(self, user_agent=None):
        """Safe cookie saving with proper error handling"""
        try:
            cookie_dir = "linkedin_cookies"
            os.makedirs(cookie_dir, exist_ok=True)
            
            cookies = self.context.cookies()
            cookie_data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
                "user_agent": user_agent,
                "cookie_count": len(cookies)
            }
            
            cookie_file = os.path.join(cookie_dir, "linkedin_session.json")
            with open(cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            print(f"🍪 Successfully saved {len(cookies)} cookies")
            return True
            
        except Exception as e:
            print(f"❌ Error saving cookies: {e}")
            return False
    
    def load_cookies_safely(self, cookie_file="linkedin_cookies/linkedin_session.json"):
        """Safe cookie loading with proper error handling"""
        try:
            if not os.path.exists(cookie_file):
                print("📝 No saved cookies found")
                return False
            
            with open(cookie_file, 'r') as f:
                cookie_data = json.load(f)
            
            expires_at_str = cookie_data.get('expires_at', '')
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() > expires_at:
                        print("⏰ Saved cookies have expired")
                        return False
                except Exception as e:
                    print(f"⚠️ Error checking cookie expiry: {e}")
                    return False
            
            cookies = cookie_data.get('cookies', [])
            if cookies:
                self.context.add_cookies(cookies)
                print(f"🍪 Loaded {len(cookies)} cookies")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            return False
    
    def check_session_validity(self):
        """Check if the current session is still valid"""
        try:
            print("🔍 Checking session validity...")
            
            self.page.goto("https://www.linkedin.com/feed/", 
                     wait_until="domcontentloaded", 
                     timeout=20000)
            
            time.sleep(3)
            
            if 'login' in self.page.url.lower():
                print("❌ Session invalid - redirected to login")
                return False
            
            auth_selectors = [
                '.global-nav__me',
                '.feed-identity-module', 
                '.global-nav',
                '.global-nav__primary-items'
            ]
            
            for selector in auth_selectors:
                try:
                    if self.page.locator(selector).is_visible(timeout=2000):
                        print(f"✅ Found authenticated element: {selector}")
                        return True
                except:
                    continue
            
            if "linkedin.com" in self.page.url and "login" not in self.page.url:
                print("✅ Session appears valid")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking session: {e}")
            return False
    
    def login_to_linkedin(self):
        """Complete LinkedIn login process"""
        print("🚀 Starting LinkedIn login process...")
        
        try:
            user_agent_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
            print("🌐 Launching browser...")
            self.browser = self.p.chromium.launch(
                headless=True,
                slow_mo=200,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            
            self.context = self.browser.new_context(
                user_agent=user_agent_string,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            self.page = self.context.new_page()
            print("✅ Browser setup complete")
            
            # Try loading saved cookies first
            if self.load_cookies_safely():
                print("🔄 Checking saved session...")
                if self.check_session_validity():
                    print("✅ Using saved session - already logged in!")
                    return True
                else:
                    print("⚠️ Saved session invalid, proceeding with login...")
            
            # Manual login process
            print("🔐 Starting manual login process...")
            
            print("📱 Navigating to LinkedIn login page...")
            self.page.goto("https://www.linkedin.com/login", 
                     timeout=60000,
                     wait_until="domcontentloaded")
            
            print("⏳ Waiting for login form...")
            self.page.wait_for_selector("#username", timeout=30000)
            
            email = os.getenv("LINKEDIN_EMAIL") or input("Enter LinkedIn email: ")
            password = os.getenv("LINKEDIN_PASSWORD") or input("Enter LinkedIn password: ")
            
            if not email or not password:
                print("❌ Email and password are required")
                return False
            
            print("📝 Entering login credentials...")
            
            self.page.fill("#username", "")
            time.sleep(0.5)
            self.page.type("#username", email, delay=150)
            
            time.sleep(random.uniform(1, 2))
            
            self.page.fill("#password", "")
            time.sleep(0.5)
            self.page.type("#password", password, delay=120)
            
            print("⏳ Pausing before submitting...")
            time.sleep(random.uniform(2, 4))
            
            print("🔐 Clicking login button...")
            self.page.click('button[type="submit"]')
            
            print("⏳ Waiting for login response...")
            time.sleep(random.uniform(3, 6))
            
            current_url = self.page.url.lower()
            if any(x in current_url for x in ['challenge', 'captcha', 'security']):
                print("⚠️ Security challenge detected!")
                print("🔐 Please complete the security challenge manually in the browser...")
                print("Press Enter after completing the challenge...")
                input()
            
            if self.check_session_validity():
                print("✅ Login successful!")
                
                user_agent_string = self.page.evaluate("navigator.userAgent")
                self.save_cookies_safely(user_agent_string)
                
                return True
            else:
                print("❌ Login failed - please check credentials")
                return False
                
        except Exception as e:
            print(f"❌ Error during login process: {e}")
            return False
    
    def get_profile_href_link(self, username: str) -> Optional[str]:
        """
        Navigate to user's profile and extract the specific profile href link
        Targets the link at index 10 OR with class "update-components-actor__image"
        
        Args:
            username: LinkedIn username or profile URL identifier
        
        Returns:
            The extracted profile href link, or None if not found
        """
        try:
            print(f"\n🔗 Fetching profile link for user: {username}")
            
            # Construct LinkedIn profile URL
            if username.startswith("http"):
                profile_url = username
            elif "/" in username:
                profile_url = f"https://www.linkedin.com/{username}"
            else:
                profile_url = f"https://www.linkedin.com/in/{username}"
            
            profile_url = profile_url.rstrip('/')
            
            print(f"📱 Navigating to: {profile_url}")
            self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            
            time.sleep(3)
            
            if 'login' in self.page.url.lower():
                print("❌ Redirected to login - session may have expired")
                return None
            
            # Extract profile name
            profile_name = None
            try:
                name_selectors = ['h1 span[dir="ltr"]', 'h1']
                for selector in name_selectors:
                    try:
                        element = self.page.locator(selector)
                        if element.is_visible(timeout=2000):
                            profile_name = element.text_content().strip()
                            if profile_name:
                                break
                    except:
                        continue
            except:
                pass
            
            print(f"👤 Profile name: {profile_name or 'Unknown'}")
            
            # METHOD 1: Try to find by class "update-components-actor__image"
            print("\n🔍 Method 1: Searching by class 'update-components-actor__image'...")
            try:
                target_selector = 'a.update-components-actor__image[href]'
                element = self.page.locator(target_selector).first
                
                if element.is_visible(timeout=5000):
                    href = element.get_attribute('href')
                    if href:
                        print(f"✅ Found href by class selector!")
                        print(f"🔗 Profile Link: {href}")
                        return href
            except Exception as e:
                print(f"⚠️ Method 1 failed: {e}")
            
            # METHOD 2: Look for specific pattern in class name
            print("\n🔍 Method 2: Searching by class pattern 'SJEYEKQzirtEAeMdweWaSusuMVTjJkHSVBDAA'...")
            try:
                # Find all links and check class attribute
                all_links = self.page.locator('a[href]')
                count = all_links.count()
                
                for i in range(count):
                    element = all_links.nth(i)
                    class_attr = element.get_attribute('class') or ""
                    
                    # Check if it contains the target class
                    if "SJEYEKQzirtEAeMdweWaSusuMVTjJkHSVBDAA" in class_attr or "update-components-actor__image" in class_attr:
                        href = element.get_attribute('href')
                        if href and '/in/' in href:
                            print(f"✅ Found href by class pattern at index {i}!")
                            print(f"🔗 Profile Link: {href}")
                            return href
            except Exception as e:
                print(f"⚠️ Method 2 failed: {e}")
            
            # METHOD 3: Find by index 10
            print("\n🔍 Method 3: Trying index 10...")
            try:
                all_links = self.page.locator('a[href]')
                if all_links.count() > 10:
                    element = all_links.nth(10)
                    href = element.get_attribute('href')
                    aria_label = element.get_attribute('aria-label') or ""
                    
                    # Verify it's a profile link
                    if href and '/in/' in href:
                        print(f"✅ Found href at index 10!")
                        print(f"🔗 Profile Link: {href}")
                        print(f"🏷️  aria-label: {aria_label}")
                        return href
            except Exception as e:
                print(f"⚠️ Method 3 failed: {e}")
            
            # METHOD 4: Find by aria-label containing profile name
            print("\n🔍 Method 4: Searching by aria-label with profile name...")
            try:
                if profile_name:
                    # Look for links with aria-label containing "View {name}"
                    selector = f'a[aria-label*="View {profile_name}"][href]'
                    element = self.page.locator(selector).first
                    
                    if element.is_visible(timeout=3000):
                        href = element.get_attribute('href')
                        if href and '/in/' in href:
                            print(f"✅ Found href by aria-label!")
                            print(f"🔗 Profile Link: {href}")
                            return href
            except Exception as e:
                print(f"⚠️ Method 4 failed: {e}")
            
            print("\n❌ Could not extract the specific profile href link")
            return None
            
        except Exception as e:
            print(f"❌ Error fetching profile: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_profile_link(self, username: str, href: str):
        """Save extracted profile link to file"""
        try:
            output_dir = "linkedin_data"
            os.makedirs(output_dir, exist_ok=True)
            
            data = {
                "username": username,
                "profile_href": href,
                "extracted_at": datetime.now().isoformat()
            }
            
            # Save as JSON
            json_file = os.path.join(output_dir, f"profile_link_{username.replace('/', '_')}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Save as TXT (just the href)
            txt_file = os.path.join(output_dir, f"profile_link_{username.replace('/', '_')}.txt")
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(href)
            
            print(f"\n💾 Profile link saved to:")
            print(f"   📄 {json_file}")
            print(f"   📄 {txt_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving profile link: {e}")
            return False
    
    def close(self):
        """Properly close browser and Playwright instance"""
        try:
            if self.browser:
                self.browser.close()
                print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")
    
    def run(self):
        """Main execution function"""
        try:
            print("="*80)
            print("🔗 LinkedIn Profile Link Extractor")
            print("   Targets: update-components-actor__image class OR index 10")
            print("="*80)
            
            # Initialize Playwright
            self.p = sync_playwright().start()
            print("✅ Playwright started")
            
            # Login to LinkedIn
            if not self.login_to_linkedin():
                print("❌ Login failed")
                return False
            
            print("\n✅ Successfully logged in to LinkedIn")
            
            # Get target username
            target_username = input("\n📝 Enter LinkedIn username or profile URL: ").strip()
            
            if not target_username:
                print("❌ Username cannot be empty")
                return False
            
            # Extract the specific profile href link
            profile_href = self.get_profile_href_link(target_username)
            
            if profile_href:
                print("\n" + "="*80)
                print("✅ SUCCESSFULLY EXTRACTED PROFILE LINK")
                print("="*80)
                print(f"\n🔗 {profile_href}\n")
                
                # Save to file
                self.save_profile_link(target_username, profile_href)
                
                print("\n✅ Extraction completed successfully!")
                return True
            else:
                print("❌ Failed to extract profile href link")
                return False
            
        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted by user")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Always close Playwright
            print("\n🔄 Cleaning up...")
            self.close()
            if self.p:
                self.p.stop()
                print("✅ Playwright stopped")


def main():
    """Entry point for the script"""
    scraper = LinkedInScraper()
    success = scraper.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()