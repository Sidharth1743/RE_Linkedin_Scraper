# LinkedIn Profile Activity Fetcher
# Extracts profileUrn and fetches activity using GraphQL API with dynamic headers

from playwright.sync_api import sync_playwright
import time
import random
import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote


class LinkedInActivityFetcher:
    """
    LinkedIn scraper that extracts profileUrn and fetches profile activity
    using dynamic headers captured from network requests
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.p = None
        self.captured_headers = {}
        self.captured_cookies = {}

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
                     timeout=30000)

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

    def setup_network_interception(self):
        """Set up network request interception to capture headers"""
        print("🔧 Setting up network interception...")

        def handle_request(request):
            """Capture headers from voyager API requests"""
            url = request.url

            # Capture voyager API requests
            if 'voyager/api' in url or 'voyagerFeed' in url:
                headers = request.headers

                # Store all headers
                self.captured_headers = {
                    'accept': headers.get('accept', 'application/vnd.linkedin.normalized+json+2.1'),
                    'accept-language': headers.get('accept-language', 'en-US,en;q=0.8'),
                    'cache-control': headers.get('cache-control', 'no-cache'),
                    'csrf-token': headers.get('csrf-token', ''),
                    'pragma': headers.get('pragma', 'no-cache'),
                    'priority': headers.get('priority', 'u=1, i'),
                    'referer': headers.get('referer', ''),
                    'sec-ch-ua': headers.get('sec-ch-ua', ''),
                    'sec-ch-ua-mobile': headers.get('sec-ch-ua-mobile', '?0'),
                    'sec-ch-ua-platform': headers.get('sec-ch-ua-platform', ''),
                    'sec-fetch-dest': headers.get('sec-fetch-dest', 'empty'),
                    'sec-fetch-mode': headers.get('sec-fetch-mode', 'cors'),
                    'sec-fetch-site': headers.get('sec-fetch-site', 'same-origin'),
                    'user-agent': headers.get('user-agent', ''),
                    'x-li-lang': headers.get('x-li-lang', 'en_US'),
                    'x-li-page-instance': headers.get('x-li-page-instance', ''),
                    'x-li-track': headers.get('x-li-track', ''),
                    'x-restli-protocol-version': headers.get('x-restli-protocol-version', '2.0.0')
                }

                print(f"📡 Captured headers from: {url[:80]}...")

        # Listen to requests
        self.page.on("request", handle_request)
        print("✅ Network interception enabled")

    def extract_profile_urn(self, username: str) -> Optional[str]:
        """
        Navigate to user's profile and extract the profileUrn from miniProfileUrn parameter

        Args:
            username: LinkedIn username or profile URL identifier

        Returns:
            The extracted profileUrn (e.g., urn:li:fsd_profile:AACoAAAA8MrEBYl...), or None if not found
        """
        try:
            print(f"\n🔗 Extracting profileUrn for user: {username}")

            # Construct LinkedIn profile URL
            if username.startswith("http"):
                profile_url = username
            elif "/" in username:
                profile_url = f"https://www.linkedin.com/{username}"
            else:
                profile_url = f"https://www.linkedin.com/in/{username}"

            profile_url = profile_url.rstrip('/')

            # Set up network interception before navigating
            self.setup_network_interception()

            print(f"📱 Navigating to: {profile_url}")
            self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for page to load and network requests to fire
            time.sleep(5)

            if 'login' in self.page.url.lower():
                print("❌ Redirected to login - session may have expired")
                return None

            # METHOD 1: Extract from URL parameters (miniProfileUrn)
            print("\n🔍 Method 1: Extracting from page links with miniProfileUrn...")
            try:
                # Get all links on the page
                page_content = self.page.content()

                # Find miniProfileUrn in the HTML
                urn_pattern = r'miniProfileUrn=([^&"\s]+)'
                matches = re.findall(urn_pattern, page_content)

                if matches:
                    # URL decode the URN
                    encoded_urn = matches[0]
                    decoded_urn = unquote(encoded_urn)
                    print(f"✅ Found profileUrn from miniProfileUrn: {decoded_urn}")
                    return decoded_urn
            except Exception as e:
                print(f"⚠️ Method 1 failed: {e}")

            # METHOD 2: Extract from network requests
            print("\n🔍 Method 2: Extracting from network requests...")
            try:
                # Trigger some activity to generate API requests
                # Scroll down to trigger lazy loading
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(2)

                # Check if we captured the URN from network requests
                # Look through the page source for API calls
                page_source = self.page.content()
                urn_pattern = r'urn%3Ali%3Afsd_profile%3A([^&"\s]+)'
                matches = re.findall(urn_pattern, page_source)

                if matches:
                    full_urn = f"urn:li:fsd_profile:{matches[0]}"
                    print(f"✅ Found profileUrn from network data: {full_urn}")
                    return full_urn
            except Exception as e:
                print(f"⚠️ Method 2 failed: {e}")

            # METHOD 3: Extract from current page URL
            print("\n🔍 Method 3: Checking current page URL...")
            try:
                current_url = self.page.url
                parsed = urlparse(current_url)
                query_params = parse_qs(parsed.query)

                if 'miniProfileUrn' in query_params:
                    urn = unquote(query_params['miniProfileUrn'][0])
                    print(f"✅ Found profileUrn from current URL: {urn}")
                    return urn
            except Exception as e:
                print(f"⚠️ Method 3 failed: {e}")

            print("\n❌ Could not extract profileUrn from profile")
            return None

        except Exception as e:
            print(f"❌ Error extracting profileUrn: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_cookies_dict(self):
        """Convert browser cookies to dictionary format for requests - matching test/request_sender.py format"""
        try:
            cookies = self.context.cookies()
            cookie_dict = {}
            for cookie in cookies:
                # Strip quotes from cookie values like in test/request_sender.py
                value = cookie['value'].strip('"')
                cookie_dict[cookie['name']] = value
            return cookie_dict
        except Exception as e:
            print(f"⚠️ Error getting cookies: {e}")
            return {}

    def extract_pagination_token(self, activity_data: dict) -> Optional[str]:
        """
        Extract pagination token from API response

        Args:
            activity_data: The API response JSON

        Returns:
            The pagination token string, or None if not found
        """
        try:
            token = activity_data.get('data', {}).get('data', {}).get(
                'feedDashProfileUpdatesByMemberShareFeed', {}
            ).get('metadata', {}).get('paginationToken')

            if token:
                print(f"✅ Found pagination token: {token[:50]}...")
                return token
            else:
                print("⚠️ No pagination token found in response")
                return None
        except Exception as e:
            print(f"❌ Error extracting pagination token: {e}")
            return None

    def fetch_profile_activity(self, profile_urn: str, count: int = 20, start: int = 0, pagination_token: Optional[str] = None) -> Optional[dict]:
        """
        Fetch profile activity using the GraphQL API - using same method as test/request_sender.py

        Args:
            profile_urn: The profileUrn (e.g., urn:li:fsd_profile:AACoAAAA8MrEBYl...)
            count: Number of activities to fetch
            start: Starting offset
            pagination_token: Optional pagination token for fetching next pages

        Returns:
            JSON response from the API, or None if failed
        """
        try:
            import requests
            from urllib.parse import quote

            print(f"\n🚀 Fetching profile activity...")
            print(f"   ProfileUrn: {profile_urn}")
            print(f"   Count: {count}, Start: {start}")
            if pagination_token:
                print(f"   Pagination Token: {pagination_token[:50]}...")

            # Get cookies from browser - same format as test/request_sender.py
            cookies = self.get_cookies_dict()

            # Get CSRF token from JSESSIONID cookie (already stripped of quotes in get_cookies_dict)
            csrf_token = cookies.get('JSESSIONID', '')

            if not csrf_token:
                print("⚠️ Warning: No CSRF token found in cookies")

            # Get user agent and platform from page
            user_agent = self.page.evaluate("navigator.userAgent")
            platform = self.page.evaluate("navigator.platform")

            # Determine platform string for sec-ch-ua-platform
            if 'Linux' in platform:
                platform_header = '"Linux"'
            elif 'Win' in platform:
                platform_header = '"Windows"'
            elif 'Mac' in platform:
                platform_header = '"macOS"'
            else:
                platform_header = '"Linux"'

            # Build headers exactly like test/request_sender.py
            headers = {
                'accept': 'application/vnd.linkedin.normalized+json+2.1',
                'accept-language': 'en-US,en;q=0.8',
                'cache-control': 'no-cache',
                'csrf-token': csrf_token,
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': self.page.url,
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

            # URL encode the profileUrn
            encoded_urn = quote(profile_urn, safe='')

            # Construct the GraphQL API URL
            if pagination_token:
                # URL with pagination token for second page onwards
                encoded_token = quote(pagination_token, safe='')
                url = f"https://www.linkedin.com/voyager/api/graphql?variables=(count:{count},start:{start},profileUrn:{encoded_urn},paginationToken:{encoded_token})&queryId=voyagerFeedDashProfileUpdates.4af00b28d60ed0f1488018948daad822"
            else:
                # First page URL without pagination token
                url = f"https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(count:{count},start:{start},profileUrn:{encoded_urn})&queryId=voyagerFeedDashProfileUpdates.4af00b28d60ed0f1488018948daad822"

            print(f"\n📡 Making API request (same method as test/request_sender.py)...")
            print(f"   URL: {url[:100]}...")
            print(f"   CSRF Token: {csrf_token[:20]}..." if csrf_token else "   CSRF Token: (empty)")

            # Make the request exactly like test/request_sender.py
            response = requests.get(url, headers=headers, cookies=cookies)

            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✅ Successfully fetched profile activity!")
                try:
                    return response.json()
                except Exception as json_error:
                    print(f"⚠️ Error parsing JSON: {json_error}")
                    print(f"   Response text: {response.text[:200]}...")
                    return None
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"   Response: {response.text[:500]}...")
                return None

        except Exception as e:
            print(f"❌ Error fetching profile activity: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_video_url(self, item: dict, included: list, prefer_640p: bool = True) -> str:
        """
        Extract video URL from a post item by following the reference chain

        Args:
            item: The Update object from included array
            included: The full included array to lookup references
            prefer_640p: Prefer 640p resolution, fallback to 720p if not available

        Returns:
            Video URL string, or empty string if no video found
        """
        try:
            # Step 1: Get the video reference URN from content.linkedInVideoComponent.*videoPlayMetadata
            content = item.get('content', {})
            video_component = content.get('linkedInVideoComponent', {})
            video_ref = video_component.get('*videoPlayMetadata', '')

            if not video_ref:
                return ''

            # Step 2: Look up the video reference in included array to find VideoPlayMetadata
            video_metadata = None
            for inc_item in included:
                if inc_item.get('entityUrn') == video_ref:
                    video_metadata = inc_item
                    break

            if not video_metadata:
                return ''

            # Step 3: Get progressiveStreams array
            progressive_streams = video_metadata.get('progressiveStreams', [])

            if not progressive_streams:
                return ''

            # Step 4: Find the preferred resolution (640p or 720p)
            video_url_640p = ''
            video_url_720p = ''
            video_url_fallback = ''

            for stream in progressive_streams:
                width = stream.get('width', 0)
                height = stream.get('height', 0)
                streaming_locations = stream.get('streamingLocations', [])

                if not streaming_locations:
                    continue

                url = streaming_locations[0].get('url', '')

                if not url:
                    continue

                # Store first URL as fallback
                if not video_url_fallback:
                    video_url_fallback = url

                # Check for 640p (width=640 or height=640)
                if width == 640 or height == 640:
                    video_url_640p = url

                # Check for 720p (width=720 or height=720)
                if width == 720 or height == 720:
                    video_url_720p = url

            # Return in priority order: 640p -> 720p -> any fallback
            if prefer_640p:
                return video_url_640p or video_url_720p or video_url_fallback
            else:
                return video_url_720p or video_url_640p or video_url_fallback

        except Exception as e:
            print(f"   ⚠️ Error extracting video URL: {e}")
            return ''

    def extract_image_urls(self, item: dict) -> list:
        """
        Extract all image URLs from a post's imageComponent

        Args:
            item: The Update object from included array

        Returns:
            List of image URL strings (best quality for each image), or empty list if no images
        """
        try:
            # Step 1: Get imageComponent from content
            content = item.get('content', {})
            image_component = content.get('imageComponent', {})
            images = image_component.get('images', [])

            if not images:
                return []

            # Step 2: Extract URL from each image (best quality)
            image_urls = []

            for image in images:
                try:
                    # Navigate to vectorImage
                    attributes = image.get('attributes', [])
                    if not attributes:
                        continue

                    detail_data = attributes[0].get('detailData', {})
                    vector_image = detail_data.get('vectorImage', {})

                    root_url = vector_image.get('rootUrl', '')
                    artifacts = vector_image.get('artifacts', [])

                    if not root_url or not artifacts:
                        continue

                    # Find artifact with largest width (best quality)
                    best_artifact = max(artifacts, key=lambda x: x.get('width', 0))
                    file_segment = best_artifact.get('fileIdentifyingUrlPathSegment', '')

                    if not file_segment:
                        continue

                    # Construct complete URL
                    complete_url = root_url + file_segment
                    image_urls.append(complete_url)

                except Exception as e:
                    print(f"   ⚠️ Error extracting individual image: {e}")
                    continue

            return image_urls

        except Exception as e:
            print(f"   ⚠️ Error extracting image URLs: {e}")
            return []

    def extract_posts_from_response(self, activity_data: dict):
        """
        Extract individual posts from API response in correct LinkedIn order

        Args:
            activity_data: The full API response

        Returns:
            List of post dictionaries with extracted information (ordered)
        """
        try:
            posts = []

            # Get the ordered list of post URNs from *elements
            elements = activity_data.get('data', {}).get('data', {}).get(
                'feedDashProfileUpdatesByMemberShareFeed', {}
            ).get('*elements', [])

            if not elements:
                print("⚠️ No '*elements' array found in response")
                return posts

            # Navigate to included array which contains all the post objects
            included = activity_data.get('included', [])

            if not included:
                print("⚠️ No 'included' array found in response")
                return posts

            # Build a lookup dictionary: entityUrn -> post data
            post_lookup = {}
            for item in included:
                if item.get('$type') == 'com.linkedin.voyager.dash.feed.Update':
                    entity_urn = item.get('entityUrn', '')
                    if entity_urn:
                        post_lookup[entity_urn] = item

            print(f"   Found {len(post_lookup)} Update objects in included array")

            # Now iterate through elements in order and extract post info
            for idx, element_urn in enumerate(elements, 1):
                # Look up this URN in the post_lookup
                item = post_lookup.get(element_urn)

                if not item:
                    print(f"   ⚠️ Post {idx}: URN not found in included array: {element_urn[:80]}...")
                    continue

                # Extract post information
                post_info = {}

                # Entity URN
                post_info['entity_urn'] = item.get('entityUrn', '')

                # Activity URN from metadata
                metadata = item.get('metadata', {})
                post_info['activity_urn'] = metadata.get('backendUrn', '')
                post_info['share_urn'] = metadata.get('shareUrn', '')

                # Post text from commentary
                commentary = item.get('commentary', {})
                text_obj = commentary.get('text', {})
                post_info['post_text'] = text_obj.get('text', '')

                # Post URL
                social_content = item.get('socialContent', {})
                post_info['post_url'] = social_content.get('shareUrl', '')

                # Author information from actor
                actor = item.get('actor', {})
                post_info['author_profile_urn'] = ''

                # Try to extract author profile URN from actor image
                try:
                    image = actor.get('image', {})
                    attributes = image.get('attributes', [])
                    if attributes:
                        detail_data = attributes[0].get('detailData', {})
                        non_entity_profile = detail_data.get('nonEntityProfilePicture', {})
                        profile_ref = non_entity_profile.get('*profile', '')
                        if profile_ref:
                            post_info['author_profile_urn'] = profile_ref
                except:
                    pass

                # Actor name and description
                actor_name = actor.get('name', {})
                post_info['author_name'] = actor_name.get('text', '') if isinstance(actor_name, dict) else ''

                actor_description = actor.get('description', {})
                post_info['author_headline'] = actor_description.get('text', '') if isinstance(actor_description, dict) else ''

                # Navigation URL (author profile link)
                nav_context = actor.get('navigationContext', {})
                post_info['author_profile_url'] = nav_context.get('actionTarget', '')

                # Extract video URL (640p preferred, fallback to 720p)
                video_url = self.extract_video_url(item, included, prefer_640p=True)
                post_info['video_url_640p'] = video_url

                # Extract image URLs (all images with best quality)
                image_urls = self.extract_image_urls(item)
                post_info['image_urls'] = image_urls

                # Add post number based on order
                post_info['post_order'] = idx

                # Only add post if it has some content
                if post_info.get('post_text') or post_info.get('post_url'):
                    posts.append(post_info)

            print(f"✅ Extracted {len(posts)} posts in correct order from response")
            return posts

        except Exception as e:
            print(f"❌ Error extracting posts: {e}")
            import traceback
            traceback.print_exc()
            return []

    def download_image(self, url: str, output_path: str, max_retries: int = 3) -> bool:
        """
        Download an image from LinkedIn with authentication and retry logic

        Args:
            url: Image URL
            output_path: Where to save the image
            max_retries: Number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        import requests

        # Get cookies from browser context
        cookies = self.get_cookies_dict()

        headers = {
            'User-Agent': self.page.evaluate("navigator.userAgent") if self.page else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.linkedin.com/'
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    cookies=cookies,
                    headers=headers,
                    timeout=30,
                    stream=True
                )

                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return True
                else:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return False

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                print(f"   ❌ Error downloading image: {e}")
                return False

        return False

    def download_video(self, url: str, output_path: str, max_retries: int = 3) -> bool:
        """
        Download a video from LinkedIn with progress tracking and retry logic

        Args:
            url: Video URL
            output_path: Where to save the video
            max_retries: Number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        import requests

        # Get cookies from browser context
        cookies = self.get_cookies_dict()

        headers = {
            'User-Agent': self.page.evaluate("navigator.userAgent") if self.page else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.linkedin.com/'
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    cookies=cookies,
                    headers=headers,
                    timeout=60,
                    stream=True
                )

                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Show progress for large files
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if downloaded % (1024 * 1024) == 0:  # Update every MB
                                    print(f"      Progress: {progress:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)", end='\r')

                    if total_size > 0:
                        print(f"      Progress: 100.0% ({total_size // (1024*1024)}MB / {total_size // (1024*1024)}MB)")
                    return True
                else:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return False

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                print(f"   ❌ Error downloading video: {e}")
                return False

        return False

    def save_post_text(self, post_text: str, output_path: str) -> bool:
        """
        Save post text to a file

        Args:
            post_text: The post text content
            output_path: Where to save the text file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(post_text)
            return True
        except Exception as e:
            print(f"   ❌ Error saving text: {e}")
            return False

    def download_media_for_posts(self, all_posts_data: list, session_dir: str):
        """
        Download all media (text, images, videos) for the extracted posts

        Args:
            all_posts_data: List of all post dictionaries
            session_dir: Session directory path
        """
        try:
            print("\n" + "="*80)
            print("📥 DOWNLOADING MEDIA FILES")
            print("="*80)

            # Create media directories
            text_dir = os.path.join(session_dir, "extracted_text")
            images_dir = os.path.join(session_dir, "images")
            videos_dir = os.path.join(session_dir, "videos")

            os.makedirs(text_dir, exist_ok=True)
            os.makedirs(images_dir, exist_ok=True)
            os.makedirs(videos_dir, exist_ok=True)

            # Track statistics
            stats = {
                'text_saved': 0,
                'text_failed': 0,
                'images_downloaded': 0,
                'images_failed': 0,
                'videos_downloaded': 0,
                'videos_failed': 0
            }

            total_posts = len(all_posts_data)

            for post in all_posts_data:
                post_number = post.get('post_order', 0)
                print(f"\n📄 Post #{post_number} ({post_number}/{total_posts}):")

                # 1. Save text
                post_text = post.get('post_text', '')
                if post_text:
                    text_path = os.path.join(text_dir, f"post_{post_number}.txt")
                    print(f"   📝 Saving text...", end=" ")
                    if self.save_post_text(post_text, text_path):
                        print("✅")
                        stats['text_saved'] += 1
                    else:
                        print("❌")
                        stats['text_failed'] += 1

                # 2. Download images
                image_urls = post.get('image_urls', [])
                if image_urls:
                    print(f"   🖼️  Downloading {len(image_urls)} image(s):")
                    for idx, img_url in enumerate(image_urls, 1):
                        img_filename = f"post_{post_number}_image_{idx}.jpg"
                        img_path = os.path.join(images_dir, img_filename)
                        print(f"      Image {idx}/{len(image_urls)}...", end=" ")
                        if self.download_image(img_url, img_path):
                            print("✅")
                            stats['images_downloaded'] += 1
                        else:
                            print("❌")
                            stats['images_failed'] += 1

                # 3. Download video
                video_url = post.get('video_url_640p', '')
                if video_url:
                    video_filename = f"post_{post_number}_video.mp4"
                    video_path = os.path.join(videos_dir, video_filename)
                    print(f"   🎥 Downloading video...")
                    if self.download_video(video_url, video_path):
                        print(f"      ✅ Video saved")
                        stats['videos_downloaded'] += 1
                    else:
                        print(f"      ❌ Video download failed")
                        stats['videos_failed'] += 1

            # Print summary
            print("\n" + "="*80)
            print("✅ MEDIA DOWNLOAD COMPLETED")
            print("="*80)
            print(f"\n📊 Download Statistics:")
            print(f"   📝 Text files:")
            print(f"      - Saved: {stats['text_saved']}")
            print(f"      - Failed: {stats['text_failed']}")
            print(f"   🖼️  Images:")
            print(f"      - Downloaded: {stats['images_downloaded']}")
            print(f"      - Failed: {stats['images_failed']}")
            print(f"   🎥 Videos:")
            print(f"      - Downloaded: {stats['videos_downloaded']}")
            print(f"      - Failed: {stats['videos_failed']}")
            print(f"\n📁 Media saved in:")
            print(f"   - Text: {text_dir}/")
            print(f"   - Images: {images_dir}/")
            print(f"   - Videos: {videos_dir}/")

        except Exception as e:
            print(f"❌ Error downloading media: {e}")
            import traceback
            traceback.print_exc()

    def save_individual_post(self, post_data: dict, range_str: str, post_number: int, username: str, output_dir: str):
        """
        Save a single post to a JSON file

        Args:
            post_data: Dictionary containing post information
            range_str: Range string like "0-20"
            post_number: Post number within the range (1-20)
            username: Target username
            output_dir: Directory to save files

        Returns:
            File path if successful, None otherwise
        """
        try:
            # Create filename (simpler since already in session directory)
            filename = f"post_{post_number}.json"
            filepath = os.path.join(output_dir, filename)

            # Save post data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(post_data, f, indent=2, ensure_ascii=False)

            return filepath

        except Exception as e:
            print(f"❌ Error saving post {post_number}: {e}")
            return None

    def create_media_summary(self, all_posts: list, username: str, output_dir: str) -> Optional[str]:
        """
        Create a summary file with all posts and their media links (videos + images)

        Args:
            all_posts: List of all post dictionaries
            username: Target username
            output_dir: Directory to save the summary file

        Returns:
            File path if successful, None otherwise
        """
        try:
            # Filter posts by media type
            posts_with_videos = [post for post in all_posts if post.get('video_url_640p')]
            posts_with_images = [post for post in all_posts if post.get('image_urls')]
            posts_with_any_media = [post for post in all_posts if post.get('video_url_640p') or post.get('image_urls')]
            posts_without_media = [post for post in all_posts if not post.get('video_url_640p') and not post.get('image_urls')]

            # Count total images
            total_images = sum(len(post.get('image_urls', [])) for post in all_posts)

            # Create filename (simple since directory already has timestamp)
            filename = "media_summary.json"
            filepath = os.path.join(output_dir, filename)

            # Create summary data
            summary_data = {
                "username": username,
                "generated_at": datetime.now().isoformat(),
                "total_posts": len(all_posts),
                "posts_with_video": len(posts_with_videos),
                "posts_with_images": len(posts_with_images),
                "posts_with_any_media": len(posts_with_any_media),
                "posts_without_media": len(posts_without_media),
                "total_images": total_images,
                "posts": []
            }

            # Add all posts with relevant info
            for post in all_posts:
                image_urls = post.get('image_urls', [])
                post_summary = {
                    "post_number": post.get('post_order', 0),
                    "post_text": post.get('post_text', ''),
                    "post_url": post.get('post_url', ''),
                    "video_url_640p": post.get('video_url_640p', ''),
                    "image_urls": image_urls,
                    "has_video": bool(post.get('video_url_640p')),
                    "has_images": bool(image_urls),
                    "image_count": len(image_urls),
                    "author_name": post.get('author_name', ''),
                    "author_profile_url": post.get('author_profile_url', '')
                }
                summary_data["posts"].append(post_summary)

            # Save summary file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)

            print(f"\n📋 Media Summary Created:")
            print(f"   File: {filepath}")
            print(f"   Total posts: {len(all_posts)}")
            print(f"   Posts with video: {len(posts_with_videos)}")
            print(f"   Posts with images: {len(posts_with_images)} ({total_images} total images)")
            print(f"   Posts with any media: {len(posts_with_any_media)}")
            print(f"   Posts without media: {len(posts_without_media)}")

            return filepath

        except Exception as e:
            print(f"❌ Error creating media summary: {e}")
            import traceback
            traceback.print_exc()
            return None

    def process_posts_from_files(self, saved_files: list, username: str):
        """
        Process all saved JSON files and extract individual posts

        Args:
            saved_files: List of tuples [(range_str, filepath), ...]
            username: Target username

        Returns:
            Tuple of (number of posts extracted, list of all posts data)
        """
        try:
            print("\n" + "="*80)
            print("📝 EXTRACTING INDIVIDUAL POSTS")
            print("="*80)

            # Create posts output directory within session directory
            session_dir = getattr(self, 'session_dir', 'linkedin_data')
            posts_dir = os.path.join(session_dir, "posts")
            os.makedirs(posts_dir, exist_ok=True)

            total_posts_extracted = 0
            all_post_files = []
            all_posts_data = []  # Collect all posts for video summary

            # Process each range file
            for range_str, filepath in saved_files:
                print(f"\n📄 Processing range {range_str}: {os.path.basename(filepath)}")

                # Parse range to get start value (for global post numbering)
                range_start = int(range_str.split('-')[0])

                # Load the JSON file
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract posts from this response
                activity_data = data.get('activity_data', {})
                posts = self.extract_posts_from_response(activity_data)

                if not posts:
                    print(f"   ⚠️ No posts found in range {range_str}")
                    continue

                # Save each post to separate file
                print(f"   💾 Saving {len(posts)} posts...")
                for post_data in posts:
                    # Calculate global post number: range_start + post_order
                    # Example: Range 0-20, post_order=1 → global #1
                    #          Range 20-40, post_order=1 → global #21
                    post_order = post_data.get('post_order', 0)
                    global_post_number = range_start + post_order

                    # Update post_order to global number
                    post_data['post_order'] = global_post_number

                    post_filepath = self.save_individual_post(
                        post_data,
                        range_str,
                        global_post_number,
                        username,
                        posts_dir
                    )

                    if post_filepath:
                        all_post_files.append(post_filepath)
                        all_posts_data.append(post_data)  # Collect for summary
                        total_posts_extracted += 1

                print(f"   ✅ Saved {len(posts)} posts from range {range_str} (in LinkedIn order)")

            # Print summary
            print("\n" + "="*80)
            print("✅ POST EXTRACTION COMPLETED")
            print("="*80)
            print(f"\n📦 Total posts extracted: {total_posts_extracted}")
            print(f"📁 Posts saved in: {posts_dir}/")

            # Create media summary file (videos + images)
            if all_posts_data:
                self.create_media_summary(all_posts_data, username, session_dir)

            return total_posts_extracted, all_posts_data

        except Exception as e:
            print(f"❌ Error processing posts: {e}")
            import traceback
            traceback.print_exc()
            return 0, []

    def save_activity_data(self, username: str, profile_urn: str, activity_data: dict, page: int = 1, range_str: str = None):
        """Save profile activity data to JSON file"""
        try:
            # Use session directory (created in run() method)
            output_dir = getattr(self, 'session_dir', 'linkedin_data')
            os.makedirs(output_dir, exist_ok=True)

            # Create filename
            safe_username = username.replace('/', '_').replace(':', '_').replace('https___www.linkedin.com_in_', '')

            if range_str:
                filename = f"activity_range{range_str.replace('-', '_')}.json"
            else:
                filename = f"activity_page{page}.json"

            filepath = os.path.join(output_dir, filename)

            # Prepare data to save
            output_data = {
                "username": username,
                "profile_urn": profile_urn,
                "page": page,
                "range": range_str,
                "fetched_at": datetime.now().isoformat(),
                "activity_data": activity_data
            }

            # Save as JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"💾 Saved: {filepath}")

            return filepath

        except Exception as e:
            print(f"❌ Error saving activity data: {e}")
            return None

    def close(self):
        """Properly close browser and Playwright instance"""
        try:
            if self.browser:
                self.browser.close()
                print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")

    def parse_ranges(self, ranges_input: str, increment: int = 20):
        """
        Parse user input and auto-generate all ranges from 0 to target.

        Examples:
            Input: "60" or "40-60" → Generates: [(0,20), (20,40), (40,60)]
            Input: "80" or "60-80" → Generates: [(0,20), (20,40), (40,60), (60,80)]

        Args:
            ranges_input: String like "60", "40-60", "80", "100"
            increment: Size of each range (default: 20)

        Returns:
            List of tuples [(start, end), (start, end), ...]
        """
        try:
            ranges_input = ranges_input.strip()

            # Parse the target end value
            if '-' in ranges_input:
                # Format: "40-60" → extract the end value (60)
                parts = ranges_input.split('-')
                target_end = int(parts[-1].strip())
            else:
                # Format: "60" → use as end value
                target_end = int(ranges_input)

            # Generate all ranges from 0 to target_end in increments
            ranges = []
            current_start = 0

            while current_start < target_end:
                current_end = current_start + increment
                if current_end > target_end:
                    current_end = target_end

                ranges.append((current_start, current_end))
                current_start = current_end

            return ranges

        except Exception as e:
            print(f"❌ Error parsing ranges: {e}")
            return []

    def run_scrape(self, target_username: str, target_range: int):
        """
        Programmatic scraping function for web app integration

        Args:
            target_username: LinkedIn username or profile URL
            target_range: Target number of posts (e.g., 60, 80, 100)

        Returns:
            Tuple of (success: bool, session_dir: str or None, error: str or None)
        """
        try:
            print("="*80)
            print("🔗 LinkedIn Profile Activity Fetcher (Web App Mode)")
            print("   Extracts profileUrn and fetches activity using GraphQL API")
            print("="*80)

            # Initialize Playwright
            self.p = sync_playwright().start()
            print("✅ Playwright started")

            # Login to LinkedIn
            if not self.login_to_linkedin():
                return False, None, "Login failed"

            print("\n✅ Successfully logged in to LinkedIn")

            # Validate username
            if not target_username:
                return False, None, "Username cannot be empty"

            # Extract profileUrn
            profile_urn = self.extract_profile_urn(target_username)

            if not profile_urn:
                return False, None, "Failed to extract profileUrn"

            print("\n" + "="*80)
            print("✅ SUCCESSFULLY EXTRACTED PROFILE URN")
            print("="*80)
            print(f"\n🔗 {profile_urn}\n")

            # Parse and auto-generate ranges
            ranges = self.parse_ranges(str(target_range))

            if not ranges:
                return False, None, f"Failed to parse target range: {target_range}"

            print(f"\n✅ Generated {len(ranges)} ranges to fetch:")
            for idx, (start, end) in enumerate(ranges, 1):
                print(f"   {idx}. Range {start}-{end}")

            # Create session-specific output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_username = target_username.replace('/', '_').replace(':', '_').replace('https___www.linkedin.com_in_', '')
            target_range_str = f"0-{ranges[-1][1]}"
            session_dir_name = f"{safe_username}_{target_range_str}_{timestamp}"
            self.session_dir = os.path.join("linkedin_data", session_dir_name)
            os.makedirs(self.session_dir, exist_ok=True)

            print(f"\n📁 Session directory created: {self.session_dir}")

            # Track pagination token and saved files
            pagination_token = None
            saved_files = []

            # Fetch each range
            for idx, (start, end) in enumerate(ranges, 1):
                count = end - start

                print("\n" + "="*80)
                print(f"📄 FETCHING RANGE {idx}: {start}-{end} (count={count})")
                print("="*80)

                if idx == 1:
                    print("   Using API without pagination token (first request)")
                    activity_data = self.fetch_profile_activity(
                        profile_urn,
                        count=count,
                        start=start,
                        pagination_token=None
                    )
                else:
                    if not pagination_token:
                        print("❌ No pagination token from previous response!")
                        break

                    print(f"   Using pagination token from previous response")
                    activity_data = self.fetch_profile_activity(
                        profile_urn,
                        count=count,
                        start=start,
                        pagination_token=pagination_token
                    )

                if not activity_data:
                    print(f"❌ Failed to fetch range {start}-{end}")
                    break

                print(f"✅ Successfully fetched range {start}-{end}")

                # Save to file
                range_str = f"{start}-{end}"
                filepath = self.save_activity_data(
                    target_username,
                    profile_urn,
                    activity_data,
                    page=idx,
                    range_str=range_str
                )

                if filepath:
                    saved_files.append((range_str, filepath))

                # Extract pagination token for next request
                pagination_token = self.extract_pagination_token(activity_data)

                if not pagination_token and idx < len(ranges):
                    print(f"⚠️ No pagination token found in response")
                    break

                time.sleep(1)

            print("\n" + "="*80)
            print("✅ RANGE FETCHING COMPLETED")
            print("="*80)

            # Extract individual posts from all fetched files
            total_posts, all_posts_data = self.process_posts_from_files(saved_files, target_username)

            # Download media files automatically
            if all_posts_data:
                self.download_media_for_posts(all_posts_data, self.session_dir)

            # Final summary
            print("\n" + "="*80)
            print("🎉 ALL TASKS COMPLETED SUCCESSFULLY")
            print("="*80)
            print(f"\n📊 Final Summary:")
            print(f"   - Ranges fetched: {len(saved_files)}")
            print(f"   - Total posts extracted: {total_posts}")
            print(f"\n📁 Session directory: {self.session_dir}/")

            return True, self.session_dir, None

        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted by user")
            return False, None, "Process interrupted by user"
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, None, error_msg
        finally:
            # Always close Playwright
            print("\n🔄 Cleaning up...")
            self.close()
            if self.p:
                self.p.stop()
                print("✅ Playwright stopped")

    def run(self):
        """Main execution function (interactive CLI mode)"""
        try:
            print("="*80)
            print("🔗 LinkedIn Profile Activity Fetcher")
            print("   Extracts profileUrn and fetches activity using GraphQL API")
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

            # Extract profileUrn
            profile_urn = self.extract_profile_urn(target_username)

            if not profile_urn:
                print("❌ Failed to extract profileUrn")
                return False

            print("\n" + "="*80)
            print("✅ SUCCESSFULLY EXTRACTED PROFILE URN")
            print("="*80)
            print(f"\n🔗 {profile_urn}\n")

            # Get target range from user
            print("\n📊 Enter target range to fetch")
            print("   Examples:")
            print("   - Enter '60' to fetch: 0-20, 20-40, 40-60")
            print("   - Enter '80' to fetch: 0-20, 20-40, 40-60, 60-80")
            print("   - Enter '100' to fetch: 0-20, 20-40, 40-60, 60-80, 80-100")
            print("\n   Note: Script will automatically generate all intermediate ranges")
            print("         First range (0-20) uses API without pagination token")
            print("         Subsequent ranges use pagination token from previous response")
            ranges_input = input("\n📝 Enter target (e.g., 60, 80, 100): ").strip()

            if not ranges_input:
                print("❌ Target cannot be empty")
                return False

            # Parse and auto-generate ranges
            ranges = self.parse_ranges(ranges_input)

            if not ranges:
                print("❌ Failed to parse target. Please enter a number (e.g., 60, 80, 100)")
                return False

            print(f"\n✅ Generated {len(ranges)} ranges to fetch:")
            for idx, (start, end) in enumerate(ranges, 1):
                print(f"   {idx}. Range {start}-{end}")

            # Create session-specific output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_username = target_username.replace('/', '_').replace(':', '_').replace('https___www.linkedin.com_in_', '')
            target_range = f"0-{ranges[-1][1]}"  # e.g., "0-60"
            session_dir_name = f"{safe_username}_{target_range}_{timestamp}"
            self.session_dir = os.path.join("linkedin_data", session_dir_name)
            os.makedirs(self.session_dir, exist_ok=True)

            print(f"\n📁 Session directory created: {self.session_dir}")

            # Track pagination token and saved files
            pagination_token = None
            saved_files = []

            # Fetch each range
            for idx, (start, end) in enumerate(ranges, 1):
                count = end - start

                print("\n" + "="*80)
                print(f"📄 FETCHING RANGE {idx}: {start}-{end} (count={count})")
                print("="*80)

                if idx == 1:
                    # First request: no pagination token
                    print("   Using API without pagination token (first request)")
                    activity_data = self.fetch_profile_activity(
                        profile_urn,
                        count=count,
                        start=start,
                        pagination_token=None
                    )
                else:
                    # Subsequent requests: use pagination token from previous response
                    if not pagination_token:
                        print("❌ No pagination token from previous response!")
                        print("   Cannot fetch further pages without token")
                        break

                    print(f"   Using pagination token from previous response")
                    activity_data = self.fetch_profile_activity(
                        profile_urn,
                        count=count,
                        start=start,
                        pagination_token=pagination_token
                    )

                # Check if request succeeded
                if not activity_data:
                    print(f"❌ Failed to fetch range {start}-{end}")
                    print(f"✅ Successfully saved {len(saved_files)} files before error")
                    break

                print(f"✅ Successfully fetched range {start}-{end}")

                # Save to file
                range_str = f"{start}-{end}"
                filepath = self.save_activity_data(
                    target_username,
                    profile_urn,
                    activity_data,
                    page=idx,
                    range_str=range_str
                )

                if filepath:
                    saved_files.append((range_str, filepath))

                # Extract pagination token for next request
                pagination_token = self.extract_pagination_token(activity_data)

                if not pagination_token and idx < len(ranges):
                    print(f"⚠️ No pagination token found in response")
                    print(f"   Cannot fetch remaining {len(ranges) - idx} ranges")
                    break

                # Small delay between requests
                time.sleep(1)

            # Print summary of fetched ranges
            print("\n" + "="*80)
            print("✅ RANGE FETCHING COMPLETED")
            print("="*80)
            print(f"\n📦 Summary: Successfully fetched and saved {len(saved_files)} ranges\n")

            for idx, (range_str, filepath) in enumerate(saved_files, 1):
                filename = os.path.basename(filepath)
                print(f"   {idx}. Range {range_str:8s} → {filename}")

            print(f"\n📁 All range files saved in: {self.session_dir}/")

            # Extract individual posts from all fetched files
            total_posts, all_posts_data = self.process_posts_from_files(saved_files, target_username)

            # Download media files (text, images, videos) automatically
            if all_posts_data:
                self.download_media_for_posts(all_posts_data, self.session_dir)

            # Final summary
            print("\n" + "="*80)
            print("🎉 ALL TASKS COMPLETED SUCCESSFULLY")
            print("="*80)
            print(f"\n📊 Final Summary:")
            print(f"   - Ranges fetched: {len(saved_files)}")
            print(f"   - Total posts extracted: {total_posts}")
            print(f"\n📁 Session output directory:")
            print(f"   {self.session_dir}/")
            print(f"\n📂 Contents:")
            print(f"   - Range files: activity_range*.json")
            print(f"   - Media summary: media_summary.json")
            print(f"   - Individual posts: posts/")
            print(f"   - Post text: extracted_text/")
            print(f"   - Images: images/")
            print(f"   - Videos: videos/")

            return True

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
    fetcher = LinkedInActivityFetcher()
    success = fetcher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
