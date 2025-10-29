#!/usr/bin/env python3
"""
Enhanced LinkedIn Content Extractor
Extracts post text and associates it with corresponding media URLs
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from pathlib import Path
import sys

class EnhancedLinkedInExtractor:
    def __init__(self, json_file_path: str, output_dir: str = "enhanced_extracted_content"):
        self.json_file_path = json_file_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "posts").mkdir(exist_ok=True)
        (self.output_dir / "media_urls").mkdir(exist_ok=True)
        (self.output_dir / "combined").mkdir(exist_ok=True)
        
        self.posts_data = []
        
    def load_and_clean_data(self) -> str:
        """Load and clean the JSON data"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                # Clean problematic characters
                content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
                return content
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            sys.exit(1)
    
    def find_complete_posts(self, content: str) -> List[Dict[str, Any]]:
        """Find complete posts by looking for post structures"""
        posts = []
        
        # Look for post patterns using URNs and activity IDs
        post_pattern = r'"updateUrn":\s*"urn:li:fsd_update:\([^)]*activity:([^)]*)\)"'
        urn_matches = re.findall(post_pattern, content)
        
        # Look for patterns that indicate post content sections
        # Split content into potential post sections
        sections = re.split(r'"updateUrn":\s*"urn:li:fsd_update', content)
        
        for i, section in enumerate(sections[1:], 1):  # Skip first empty section
            # Extract text content from this section
            text_pattern = r'"text":\s*"([^"]*(?:\\.[^"]*)*)"'
            texts = re.findall(text_pattern, section)
            
            # Extract URLs from this section
            url_pattern = r'https?://[^\s"\'<>]+'
            urls = re.findall(url_pattern, section)
            
            # Filter and categorize URLs
            image_urls = []
            video_urls = []
            other_urls = []
            
            for url in urls:
                url_lower = url.lower()
                if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', 'media', 'image', 'thumbnail']):
                    image_urls.append(url)
                elif any(ext in url_lower for ext in ['.mp4', 'video', 'media', 'stream', 'playlist']):
                    video_urls.append(url)
                else:
                    other_urls.append(url)
            
            # Only include sections that have meaningful content
            meaningful_texts = []
            for text in texts:
                # Filter out profile info and empty content
                if (text.strip() and 
                    not any(skip in text.lower() for skip in ['emmy award', 'robert herjavec', 'entrepreneur', 'shark tank']) and
                    len(text.strip()) > 10):
                    meaningful_texts.append(text.strip())
            
            if meaningful_texts or image_urls or video_urls:
                post_id = f"post_{i}"
                if urn_matches and i-1 < len(urn_matches):
                    post_id = f"post_{urn_matches[i-1]}"
                
                posts.append({
                    'post_id': post_id,
                    'text_content': meaningful_texts,
                    'image_urls': list(set(image_urls)),
                    'video_urls': list(set(video_urls)),
                    'other_urls': list(set(other_urls)),
                    'section_number': i
                })
        
        return posts
    
    def extract_by_pattern_matching(self, content: str) -> List[Dict[str, Any]]:
        """Alternative extraction using pattern matching"""
        posts = []
        
        # Look for distinct post blocks by finding timestamps or "mo" indicators
        post_blocks = re.split(r'\d+mo\s+•', content)
        
        for i, block in enumerate(post_blocks[1:], 1):  # Skip first empty block
            # Extract text content
            text_pattern = r'"text":\s*"([^"]*(?:\\.[^"]*)*)"'
            texts = re.findall(text_pattern, block)
            
            # Extract URLs
            url_pattern = r'https?://[^\s"\'<>]+'
            urls = re.findall(url_pattern, block)
            
            # Categorize URLs
            image_urls = [url for url in urls if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', 'thumbnail', 'media'])]
            video_urls = [url for url in urls if any(ext in url.lower() for ext in ['.mp4', 'video', 'playlist', 'stream'])]
            
            # Filter meaningful texts
            meaningful_texts = []
            for text in texts:
                cleaned_text = text.replace('\\n', ' ').strip()
                if (cleaned_text and 
                    not any(skip in cleaned_text.lower() for skip in ['emmy award', 'robert herjavec', 'entrepreneur', 'shark tank']) and
                    len(cleaned_text) > 10 and
                    not cleaned_text.startswith('   •')):
                    meaningful_texts.append(cleaned_text)
            
            if meaningful_texts or image_urls or video_urls:
                posts.append({
                    'post_id': f"post_{i}",
                    'text_content': meaningful_texts,
                    'image_urls': list(set(image_urls)),
                    'video_urls': list(set(video_urls)),
                    'other_urls': urls,
                    'block_number': i
                })
        
        return posts
    
    def group_content_by_sections(self, content: str) -> List[Dict[str, Any]]:
        """Group content by finding distinct sections"""
        posts = []
        
        # Split content into sections using different delimiters
        # Look for patterns that indicate new posts
        sections = re.split(r'(?=\d+mo\s+•)|(?="updateUrn")|(?=Emmy Award Winner)', content)
        
        current_post = None
        post_counter = 0
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
                
            # Check if this section starts a new post
            if ('mo •' in section or 'updateUrn' in section or 
                ('Emmy Award Winner' in section and post_counter == 0)):
                
                # Save previous post if it has content
                if current_post and (current_post['text_content'] or 
                                   current_post['image_urls'] or 
                                   current_post['video_urls']):
                    posts.append(current_post)
                
                # Start new post
                post_counter += 1
                current_post = {
                    'post_id': f"post_{post_counter}",
                    'text_content': [],
                    'image_urls': [],
                    'video_urls': [],
                    'other_urls': []
                }
            
            if current_post:
                # Extract text from this section
                text_matches = re.findall(r'"text":\s*"([^"]*(?:\\.[^"]*)*)"', section)
                for text in text_matches:
                    cleaned_text = text.replace('\\n', ' ').strip()
                    if (cleaned_text and 
                        not any(skip in cleaned_text.lower() for skip in ['emmy award', 'robert herjavec', 'entrepreneur', 'shark tank', '   •']) and
                        len(cleaned_text) > 10):
                        current_post['text_content'].append(cleaned_text)
                
                # Extract URLs from this section
                url_matches = re.findall(r'https?://[^\s"\'<>]+', section)
                for url in url_matches:
                    url_lower = url.lower()
                    if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', 'thumbnail', 'media']) and url_lower not in [u.lower() for u in current_post['image_urls']]:
                        current_post['image_urls'].append(url)
                    elif any(ext in url_lower for ext in ['.mp4', 'video', 'playlist', 'stream']) and url_lower not in [u.lower() for u in current_post['video_urls']]:
                        current_post['video_urls'].append(url)
                    elif url not in current_post['other_urls']:
                        current_post['other_urls'].append(url)
        
        # Add the last post
        if current_post and (current_post['text_content'] or 
                           current_post['image_urls'] or 
                           current_post['video_urls']):
            posts.append(current_post)
        
        return posts
    
    def extract_all_content(self):
        """Main extraction method"""
        print("🔍 Starting enhanced LinkedIn content extraction...")
        
        # Load content
        content = self.load_and_clean_data()
        
        # Try multiple extraction methods
        methods = [
            ("Pattern Matching", self.extract_by_pattern_matching),
            ("Section Grouping", self.group_content_by_sections),
            ("URN-based", self.find_complete_posts)
        ]
        
        best_method = None
        max_content = 0
        
        for method_name, method_func in methods:
            try:
                print(f"🔧 Trying {method_name} method...")
                posts = method_func(content)
                
                total_content = sum(len(post['text_content']) + len(post['image_urls']) + len(post['video_urls']) 
                                  for post in posts)
                print(f"  📊 Found {len(posts)} posts with {total_content} total content items")
                
                if total_content > max_content:
                    max_content = total_content
                    best_method = posts
                    
            except Exception as e:
                print(f"  ❌ {method_name} failed: {e}")
                continue
        
        if best_method:
            self.posts_data = best_method
            print(f"✅ Selected best method with {len(self.posts_data)} posts")
        else:
            print("❌ All extraction methods failed")
            sys.exit(1)
    
    def save_extracted_content(self):
        """Save all extracted content organized by post"""
        print("💾 Saving organized content...")
        
        # Save combined data
        combined_file = self.output_dir / "combined" / "all_posts_with_media.json"
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(self.posts_data, f, indent=2, ensure_ascii=False)
        
        # Save individual post files
        for post in self.posts_data:
            post_id = post['post_id']
            
            # Create comprehensive post file
            post_file = self.output_dir / "posts" / f"{post_id}_complete.txt"
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(f"POST ID: {post_id}\n")
                f.write("=" * 60 + "\n\n")
                
                # Text content
                if post['text_content']:
                    f.write("📝 TEXT CONTENT:\n")
                    f.write("-" * 30 + "\n")
                    for i, text in enumerate(post['text_content'], 1):
                        f.write(f"{i}. {text}\n\n")
                else:
                    f.write("📝 TEXT CONTENT: None found\n\n")
                
                # Image URLs
                if post['image_urls']:
                    f.write("🖼️  ASSOCIATED IMAGES:\n")
                    f.write("-" * 30 + "\n")
                    for i, url in enumerate(post['image_urls'], 1):
                        f.write(f"{i}. {url}\n")
                    f.write("\n")
                else:
                    f.write("🖼️  ASSOCIATED IMAGES: None found\n\n")
                
                # Video URLs
                if post['video_urls']:
                    f.write("🎬 ASSOCIATED VIDEOS:\n")
                    f.write("-" * 30 + "\n")
                    for i, url in enumerate(post['video_urls'], 1):
                        f.write(f"{i}. {url}\n")
                    f.write("\n")
                else:
                    f.write("🎬 ASSOCIATED VIDEOS: None found\n\n")
                
                # Other URLs
                if post.get('other_urls'):
                    f.write("🔗 OTHER URLs:\n")
                    f.write("-" * 30 + "\n")
                    for i, url in enumerate(post['other_urls'], 1):
                        f.write(f"{i}. {url}\n")
                    f.write("\n")
            
            # Save only media URLs
            media_file = self.output_dir / "media_urls" / f"{post_id}_media_only.txt"
            with open(media_file, 'w', encoding='utf-8') as f:
                f.write(f"POST ID: {post_id}\n")
                f.write("=" * 40 + "\n\n")
                
                if post['image_urls']:
                    f.write("IMAGES:\n")
                    for url in post['image_urls']:
                        f.write(f"{url}\n")
                    f.write("\n")
                
                if post['video_urls']:
                    f.write("VIDEOS:\n")
                    for url in post['video_urls']:
                        f.write(f"{url}\n")
                    f.write("\n")
        
        # Create summary
        summary_file = self.output_dir / "extraction_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("ENHANCED LINKEDIN CONTENT EXTRACTION SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total posts found: {len(self.posts_data)}\n\n")
            
            total_texts = sum(len(post['text_content']) for post in self.posts_data)
            total_images = sum(len(post['image_urls']) for post in self.posts_data)
            total_videos = sum(len(post['video_urls']) for post in self.posts_data)
            
            f.write(f"Total text extracts: {total_texts}\n")
            f.write(f"Total image URLs: {total_images}\n")
            f.write(f"Total video URLs: {total_videos}\n\n")
            
            for i, post in enumerate(self.posts_data, 1):
                f.write(f"POST {i} ({post['post_id']}):\n")
                f.write(f"  Text segments: {len(post['text_content'])}\n")
                f.write(f"  Images: {len(post['image_urls'])}\n")
                f.write(f"  Videos: {len(post['video_urls'])}\n")
                if post['text_content']:
                    f.write(f"  Preview: {post['text_content'][0][:50]}...\n")
                f.write("\n")
        
        print(f"✅ Content saved to {self.output_dir}")
        print(f"📁 Main file: {combined_file}")
    
    def print_results(self):
        """Print results summary"""
        print("\n" + "="*70)
        print("📋 ENHANCED EXTRACTION RESULTS")
        print("="*70)
        
        for i, post in enumerate(self.posts_data, 1):
            print(f"\n🔸 POST {i} ({post['post_id']})")
            print("-" * 50)
            
            if post['text_content']:
                print("📝 TEXT:")
                for j, text in enumerate(post['text_content'], 1):
                    preview = text[:80] + "..." if len(text) > 80 else text
                    print(f"  {j}. {preview}")
            
            if post['image_urls']:
                print(f"🖼️  IMAGES: {len(post['image_urls'])} found")
            
            if post['video_urls']:
                print(f"🎬 VIDEOS: {len(post['video_urls'])} found")
        
        print(f"\n📊 FINAL SUMMARY:")
        print(f"Total posts: {len(self.posts_data)}")
        total_texts = sum(len(post['text_content']) for post in self.posts_data)
        total_images = sum(len(post['image_urls']) for post in self.posts_data)
        total_videos = sum(len(post['video_urls']) for post in self.posts_data)
        print(f"Total text segments: {total_texts}")
        print(f"Total image URLs: {total_images}")
        print(f"Total video URLs: {total_videos}")

def main():
    """Main function"""
    input_file = "ql.txt"
    output_directory = "enhanced_extracted_content"
    
    print("🚀 Enhanced LinkedIn Content Extractor")
    print("="*60)
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return
    
    # Create extractor instance
    extractor = EnhancedLinkedInExtractor(input_file, output_directory)
    
    try:
        # Extract all content
        extractor.extract_all_content()
        
        # Save to files
        extractor.save_extracted_content()
        
        # Print results to console
        extractor.print_results()
        
        print(f"\n✅ Enhanced extraction completed!")
        print(f"📁 Check '{output_directory}' folder for organized content")
        print(f"📄 Each post now has text associated with its media!")
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()