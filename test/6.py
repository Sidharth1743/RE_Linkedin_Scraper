"""
LinkedIn Image URL Extractor
=============================

This script extracts complete, working image URLs from LinkedIn API responses.
It handles the nested JSON structure and combines root URLs with path segments.

Author: AI Assistant
Date: 2025
"""

import json
from typing import List, Dict, Optional
from datetime import datetime


class LinkedInImageExtractor:
    """
    Extract complete, authenticated image URLs from LinkedIn API responses.
    
    How it works:
    1. LinkedIn API returns imageComponent with nested vectorImage data
    2. Each image has a rootUrl (incomplete) and artifacts (size variants)
    3. We combine rootUrl + fileIdentifyingUrlPathSegment for complete URLs
    4. The path segment contains: size, auth token, expiry parameters
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the extractor
        
        Args:
            verbose: Print debug information
        """
        self.images = []
        self.verbose = verbose
    
    def extract_urls(self, post_data: Dict) -> List[Dict]:
        """
        Extract image URLs from LinkedIn post JSON data.
        
        Args:
            post_data: Dictionary containing imageComponent from LinkedIn API
                      Expected structure:
                      {
                          "imageComponent": {
                              "images": [...]
                          }
                      }
            
        Returns:
            List of dictionaries with extracted image data and URLs
            
        Example:
            extractor = LinkedInImageExtractor()
            urls = extractor.extract_urls(post_json)
        """
        self.images = []
        
        # Navigate to imageComponent -> images array
        images = post_data.get('imageComponent', {}).get('images', [])
        
        if not images:
            if self.verbose:
                print("❌ No images found in post data")
            return self.images
        
        if self.verbose:
            print(f"✓ Found {len(images)} images")
        
        for idx, image in enumerate(images, 1):
            image_info = self._process_single_image(image, idx)
            if image_info:
                self.images.append(image_info)
        
        return self.images
    
    def _process_single_image(self, image: Dict, index: int) -> Optional[Dict]:
        """
        Process a single image object and extract all size variants.
        
        LinkedIn's nested structure:
        image
        └── attributes[0]
            └── detailData
                └── vectorImage
                    ├── rootUrl (e.g., "https://media.licdn.com/dms/image/v2/...")
                    ├── digitalmediaAsset (unique ID)
                    └── artifacts[] (different sizes)
                        └── fileIdentifyingUrlPathSegment (size + auth params)
        
        Args:
            image: Single image object from LinkedIn API
            index: Image number in the post
            
        Returns:
            Dictionary with image metadata and all URL variants
        """
        try:
            # Navigate deep into nested structure
            attributes = image.get('attributes', [])
            if not attributes:
                return None
            
            detail_data = attributes[0].get('detailData', {})
            vector_image = detail_data.get('vectorImage', {})
            
            if not vector_image:
                return None
            
            # Extract core data
            root_url = vector_image.get('rootUrl', '')
            media_asset = vector_image.get('digitalmediaAsset', '')
            artifacts = vector_image.get('artifacts', [])
            
            if not root_url or not artifacts:
                return None
            
            # Build complete URLs for each size variant
            urls = {}
            for artifact in artifacts:
                width = artifact.get('width', 0)
                height = artifact.get('height', 0)
                path_segment = artifact.get('fileIdentifyingUrlPathSegment', '')
                expires_at = artifact.get('expiresAt', 0)
                
                # KEY STEP: Combine root URL with path segment
                # This is where the magic happens!
                complete_url = root_url + path_segment
                
                resolution = f"{width}x{height}"
                urls[resolution] = {
                    'url': complete_url,
                    'width': width,
                    'height': height,
                    'expires_at': expires_at,
                    'expires_date': self._format_timestamp(expires_at)
                }
            
            return {
                'image_number': index,
                'media_asset': media_asset,
                'root_url': root_url,
                'urls': urls,
                'available_sizes': sorted(
                    list(urls.keys()),
                    key=lambda x: int(x.split('x')[0]),
                    reverse=True
                )
            }
            
        except (KeyError, IndexError, TypeError) as e:
            if self.verbose:
                print(f"❌ Error processing image {index}: {e}")
            return None
    
    def _format_timestamp(self, timestamp_ms: int) -> str:
        """Convert milliseconds to readable date"""
        if not timestamp_ms:
            return "Unknown"
        try:
            return datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d')
        except:
            return "Invalid"
    
    def get_best_quality(self) -> List[Dict]:
        """
        Get the highest quality (largest resolution) URL for each image.
        
        Returns:
            List of dictionaries with best quality URLs
            
        Example:
            best = extractor.get_best_quality()
            for item in best:
                print(f"Image {item['image']}: {item['url']}")
        """
        best = []
        for img in self.images:
            if not img['urls']:
                continue
            
            # Find largest width
            largest = max(img['urls'].values(), key=lambda x: x['width'])
            best.append({
                'image': img['image_number'],
                'resolution': f"{largest['width']}x{largest['height']}",
                'url': largest['url'],
                'expires': largest['expires_date']
            })
        return best
    
    def get_url_by_size(self, image_num: int, width: int) -> Optional[str]:
        """
        Get URL for specific image and approximate width.
        
        Args:
            image_num: Image number (1-indexed)
            width: Desired width (will get closest available)
            
        Returns:
            Complete URL string or None
            
        Example:
            url = extractor.get_url_by_size(1, 800)
        """
        if image_num > len(self.images):
            return None
        
        img = self.images[image_num - 1]
        
        # Find closest width
        closest = min(
            img['urls'].values(),
            key=lambda x: abs(x['width'] - width)
        )
        
        return closest['url']
    
    def print_all_urls(self, max_width: int = 85):
        """
        Pretty print all extracted URLs with formatting.
        
        Args:
            max_width: Terminal width for formatting
        """
        print("=" * max_width)
        print("LINKEDIN IMAGE URL EXTRACTION RESULTS")
        print("=" * max_width)
        
        if not self.images:
            print("No images extracted!")
            return
        
        for img in self.images:
            print(f"\n📸 IMAGE {img['image_number']}")
            print(f"   Asset ID: {img['media_asset']}")
            print(f"   Available sizes: {', '.join(img['available_sizes'])}")
            print("\n   URLs (sorted by quality):")
            
            # Sort by width descending (largest first)
            sorted_urls = sorted(
                img['urls'].items(),
                key=lambda x: x[1]['width'],
                reverse=True
            )
            
            for resolution, data in sorted_urls:
                print(f"\n   [{resolution}]")
                print(f"   Expires: {data['expires_date']}")
                print(f"   {data['url'][:80]}...")
        
        print("\n" + "=" * max_width)
    
    def export_to_json(self, filename: str = "linkedin_urls.json"):
        """
        Export all extracted data to JSON file.
        
        Args:
            filename: Output filename
            
        Example:
            extractor.export_to_json("my_urls.json")
        """
        export_data = {
            'total_images': len(self.images),
            'extraction_date': datetime.now().isoformat(),
            'images': self.images
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✅ Exported to {filename}")
    
    def export_to_csv(self, filename: str = "linkedin_urls.csv"):
        """
        Export best quality URLs to CSV for easy use.
        
        Args:
            filename: Output filename
        """
        import csv
        
        best = self.get_best_quality()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Image', 'Resolution', 'Expires', 'URL'])
            writer.writeheader()
            
            for item in best:
                writer.writerow({
                    'Image': item['image'],
                    'Resolution': item['resolution'],
                    'Expires': item['expires'],
                    'URL': item['url']
                })
        
        if self.verbose:
            print(f"✅ Exported to {filename}")


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic():
    """Basic usage example"""
    
    # Load your LinkedIn post data
    with open('post_data.json', 'r') as f:
        post_data = json.load(f)
    
    # Create extractor
    extractor = LinkedInImageExtractor(verbose=True)
    
    # Extract URLs
    extractor.extract_urls(post_data)
    
    # Print results
    extractor.print_all_urls()
    
    # Get best quality URLs
    best = extractor.get_best_quality()
    for item in best:
        print(f"\nImage {item['image']}: {item['url']}")


def example_advanced():
    """Advanced usage with filtering and export"""
    
    with open('post_data.json', 'r') as f:
        post_data = json.load(f)
    
    extractor = LinkedInImageExtractor()
    extractor.extract_urls(post_data)
    
    # Get specific size
    url_800px = extractor.get_url_by_size(image_num=1, width=800)
    if url_800px:
        print(f"800px image URL: {url_800px}")
    
    # Export to multiple formats
    extractor.export_to_json('images.json')
    extractor.export_to_csv('images.csv')
    
    # Access raw data
    for img in extractor.images:
        print(f"Image {img['image_number']} has {len(img['urls'])} sizes")


def example_download():
    """Download images using extracted URLs"""
    
    import requests
    
    with open('post_data.json', 'r') as f:
        post_data = json.load(f)
    
    extractor = LinkedInImageExtractor()
    extractor.extract_urls(post_data)
    
    # Get LinkedIn session cookies
    cookies = {
        'li_at': 'AQEDAWA6xS8Dq8DQAAABmis9O1AAAAGaT0m_UE4Apd4ndhUoehRndLUbS5ysTnSU8E6VLBKDgGOuxsdiJa9wU8FTj8iISYWj1TSgTUy6K2XfR6vYWu-6lF7sdx_vjjKknMr5Gk0vq883LR7PXDtjd8vC',
        'JSESSIONID': 'ajax:8343742463670370208'
    }
    
    # Download best quality images
    best = extractor.get_best_quality()
    for item in best:
        try:
            response = requests.get(
                item['url'],
                cookies=cookies,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            
            if response.status_code == 200:
                filename = f"image_{item['image']}.jpg"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded: {filename}")
            else:
                print(f"❌ Failed to download image {item['image']}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("LinkedIn Image URL Extractor")
    print("=" * 85)
    print("\nTo use this script:")
    print("1. Save your post JSON data to 'post_data.json'")
    print("2. Run: python linkedin_url_extract.py")
    print("3. Or import and use: from linkedin_url_extract import LinkedInImageExtractor")
    print("\nSee example functions for usage patterns")