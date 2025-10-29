"""
LinkedIn Image Downloader - Simple Version
=============================================

This script downloads LinkedIn post images.

HOW TO USE:
1. Paste your post JSON data in 'post_data.json'
2. Add your LinkedIn cookies (li_at, JSESSIONID)
3. Run: python download_images.py
4. Images will be saved as: image_1.jpg, image_2.jpg, etc.

GET YOUR COOKIES:
1. Go to LinkedIn.com and login
2. Press F12 (Developer Tools)
3. Go to Application tab
4. Click Cookies
5. Copy value of 'li_at' and 'JSESSIONID'
"""

import json
import requests
from datetime import datetime

def download_linkedin_images(json_file, cookies):
    """
    Download all images from LinkedIn post JSON
    
    Args:
        json_file: Path to post_data.json
        cookies: Dict with 'li_at' and 'JSESSIONID'
    """
    
    print("\n" + "="*60)
    print("LinkedIn Image Downloader")
    print("="*60)
    
    # Load JSON file
    try:
        with open(json_file, 'r') as f:
            post_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_file}")
        return
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON file")
        return
    
    # Get images from JSON
    images = post_data.get('imageComponent', {}).get('images', [])
    
    if not images:
        print("❌ No images found in JSON file")
        return
    
    print(f"✓ Found {len(images)} images\n")
    
    # Download each image
    downloaded = 0
    
    for idx, image in enumerate(images, 1):
        print(f"📸 Image {idx}:")
        
        try:
            # Get the vectorImage data
            vector_image = image['attributes'][0]['detailData']['vectorImage']
            root_url = vector_image['rootUrl']
            artifacts = vector_image['artifacts']
            
            # Find best quality (largest width)
            best = max(artifacts, key=lambda x: x['width'])
            
            # Build complete URL
            complete_url = root_url + best['fileIdentifyingUrlPathSegment']
            
            print(f"   Quality: {best['width']}x{best['height']}")
            print(f"   Downloading...", end="")
            
            # Download image with authentication
            response = requests.get(
                complete_url,
                cookies=cookies,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.linkedin.com/'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                # Save image
                filename = f"image_{idx}.jpg"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f" ✅ Saved as {filename}")
                downloaded += 1
            else:
                print(f" ❌ HTTP Error {response.status_code}")
        
        except Exception as e:
            print(f" ❌ Error: {str(e)}")
        
        print()
    
    print("="*60)
    print(f"✅ Downloaded {downloaded}/{len(images)} images")
    print("="*60 + "\n")


# Your LinkedIn cookies - GET THESE FROM BROWSER
# Instructions above ↑
COOKIES = {
    'li_at': 'AQEDAWA6xS8Dq8DQAAABmis9O1AAAAGaT0m_UE4Apd4ndhUoehRndLUbS5ysTnSU8E6VLBKDgGOuxsdiJa9wU8FTj8iISYWj1TSgTUy6K2XfR6vYWu-6lF7sdx_vjjKknMr5Gk0vq883LR7PXDtjd8vC',      # ← Replace this
    'JSESSIONID': 'ajax:8343742463670370208'  # ← Replace this
}


if __name__ == "__main__":
    
    # Check if cookies are set
    if 'PASTE_YOUR' in COOKIES['li_at'] or 'PASTE_YOUR' in COOKIES['JSESSIONID']:
        print("\n" + "⚠️ "*20)
        print("❌ COOKIES NOT SET!")
        print("⚠️ "*20)
        print("\n📋 STEP 1: Get your LinkedIn cookies")
        print("   a) Go to LinkedIn.com (login if needed)")
        print("   b) Open DevTools (F12)")
        print("   c) Go to 'Application' tab")
        print("   d) Click 'Cookies'")
        print("   e) Find 'li_at' and copy the entire VALUE")
        print("   f) Find 'JSESSIONID' and copy the entire VALUE")
        print("\n📝 STEP 2: Replace in code")
        print("   Replace:")
        print("   'PASTE_YOUR_LI_AT_HERE' with your li_at value")
        print("   'PASTE_YOUR_JSESSIONID_HERE' with your JSESSIONID value")
        print("\n▶️  STEP 3: Run again")
        print("   python download_images.py")
        print("\n" + "⚠️ "*20 + "\n")
    else:
        # Download images
        download_linkedin_images('post_data.json', COOKIES)
