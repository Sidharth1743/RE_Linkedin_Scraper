#!/usr/bin/env python3
"""
Complete LinkedIn Profile Activity Parser
Parses LinkedIn profile activity JSON and extracts posts with media (images and videos)

Features:
- Extracts posts without duplicates
- Handles both images and videos
- Generates proper LinkedIn video URLs
- Outputs clean JSON and console summary
- Self-contained, no external dependencies

Usage:
    python linkedin_parser_complete.py [json_file_path]

If no file path provided, defaults to: user_input_files/linkedin_profile_activity.json
"""

import json
import re
import time
import sys
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MediaInfo:
    """Information about media associated with a post"""
    media_type: str  # image, video, article, document, etc.
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    dimensions: Optional[str] = None  # width x height for images/videos
    accessibility_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class PostInfo:
    """Information about a LinkedIn post"""
    post_id: str
    author_name: Optional[str] = None
    post_text: Optional[str] = None
    timestamp: Optional[str] = None
    media: List[MediaInfo] = None
    post_url: Optional[str] = None
    
    def __post_init__(self):
        if self.media is None:
            self.media = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'post_id': self.post_id,
            'author_name': self.author_name,
            'post_text': self.post_text,
            'timestamp': self.timestamp,
            'media': [media.to_dict() for media in self.media],
            'post_url': self.post_url
        }


class LinkedInParser:
    """Complete LinkedIn profile activity parser"""
    
    def __init__(self, json_file_path: str):
        self.json_file_path = Path(json_file_path)
        self.data = self._load_json()
        self.seen_post_ids: Set[str] = set()  # Track seen post IDs to avoid duplicates
        
    def _load_json(self) -> Dict[str, Any]:
        """Load and parse the JSON file"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File {self.json_file_path} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON file - {e}")
            sys.exit(1)
    
    def _extract_text_from_text_vm(self, text_vm: Dict[str, Any]) -> str:
        """Extract plain text from LinkedIn's text view model format"""
        if not isinstance(text_vm, dict):
            return ""
        
        text = text_vm.get('text', '')
        if not text:
            return ""
        
        return text
    
    def _parse_vector_image(self, vector_image: Dict[str, Any]) -> Optional[MediaInfo]:
        """Parse vector image data to extract media info"""
        if not isinstance(vector_image, dict):
            return None
        
        media_info = MediaInfo(
            media_type="image",
            title=None,
            description=None,
            url=vector_image.get('rootUrl')
        )
        
        # Extract dimensions from artifacts
        artifacts = vector_image.get('artifacts', [])
        if artifacts:
            # Get the largest resolution
            largest = max(artifacts, key=lambda x: x.get('width', 0) * x.get('height', 0))
            width = largest.get('width')
            height = largest.get('height')
            if width and height:
                media_info.dimensions = f"{width}x{height}"
        
        return media_info
    
    def _parse_video_from_metadata(self, video_urn: str) -> Optional[MediaInfo]:
        """Parse video from digital media asset URN"""
        if not video_urn or not isinstance(video_urn, str):
            return None
            
        # Extract the asset ID from URN like "urn:li:digitalmediaAsset:D5610AQFsK8-ijAbvOg"
        if ':digitalmediaAsset:' in video_urn:
            asset_id = video_urn.split(':digitalmediaAsset:')[-1]
            
            # Construct LinkedIn video URL with proper format
            # Format: https://dms.licdn.com/playlist/vid/v2/{asset_id}/{format}/{quality_id}/{sequence}/{timestamp}?e={expiration}&v=beta&t={token}
            current_time = int(time.time() * 1000)  # Current timestamp in milliseconds
            future_time = current_time + (365 * 24 * 60 * 60 * 1000)  # Add 1 year in milliseconds
            
            video_url = f"https://dms.licdn.com/playlist/vid/v2/{asset_id}/mp4-640p-30fp-crf28/B56Zg4RjylG0Aw-/0/{current_time}?e={future_time}&v=beta&t=generated_token"
            
            return MediaInfo(
                media_type="video",
                title=None,
                description="LinkedIn video content",
                url=video_url,
                dimensions=None  # Video dimensions not available from URN alone
            )
        
        return None
    
    def _extract_media_from_content(self, content: Dict[str, Any]) -> List[MediaInfo]:
        """Enhanced media extraction with video metadata support"""
        media_list = []
        
        if not isinstance(content, dict):
            return media_list
        
        # Check for images in imageComponent
        image_component = content.get('imageComponent')
        if image_component and isinstance(image_component, dict):
            images = image_component.get('images', [])
            for img in images:
                if isinstance(img, dict):
                    media_info = MediaInfo(
                        media_type="image",
                        title=None,
                        description=img.get('accessibilityText'),
                        url=None,
                        accessibility_text=img.get('accessibilityText')
                    )
                    
                    # Extract image details from attributes
                    attributes = img.get('attributes', [])
                    for attr in attributes:
                        if isinstance(attr, dict) and attr.get('detailData'):
                            detail_data = attr['detailData']
                            
                            # Extract vector image data
                            if detail_data.get('vectorImage'):
                                vector_info = self._parse_vector_image(detail_data['vectorImage'])
                                if vector_info:
                                    media_info.url = vector_info.url
                                    media_info.dimensions = vector_info.dimensions
                                    break
                    
                    media_list.append(media_info)
        
        # 1. Check for *videoPlayMetadata (the actual video data)
        video_metadata_keys = [key for key in content.keys() if 'videoPlayMetadata' in key]
        for key in video_metadata_keys:
            video_urn = content[key]
            if video_urn:
                video_info = self._parse_video_from_metadata(video_urn)
                if video_info:
                    media_list.append(video_info)
        
        # 2. Check linkedInVideoComponent
        linkedin_video = content.get('linkedInVideoComponent')
        if linkedin_video and isinstance(linkedin_video, dict):
            # Look for *videoPlayMetadata specifically within linkedInVideoComponent
            video_metadata = linkedin_video.get('*videoPlayMetadata')
            if video_metadata:
                video_info = self._parse_video_from_metadata(video_metadata)
                if video_info:
                    media_list.append(video_info)
            
            # Also check for videoPlayMetadata (without asterisk)
            video_data = linkedin_video.get('videoPlayMetadata')
            if video_data and isinstance(video_data, dict):
                # Look for video asset references within the video data
                for key, value in video_data.items():
                    if 'digitalmediaAsset' in str(value):
                        video_info = self._parse_video_from_metadata(value)
                        if video_info:
                            media_list.append(video_info)
        
        # 3. Check for videos in content with different structures
        for key in ['videoComponent', 'nativeVideo', 'embeddedVideo']:
            video_component = content.get(key)
            if video_component and isinstance(video_component, dict):
                # Try different video data extraction methods
                video_data = video_component.get('videoPlayMetadata') or video_component.get('videoData') or video_component
                
                # Look for digital media asset references
                for sub_key, sub_value in video_data.items():
                    if 'digitalmediaAsset' in str(sub_value):
                        video_info = self._parse_video_from_metadata(sub_value)
                        if video_info:
                            media_list.append(video_info)
        
        # 4. Check for external videos
        external_video = content.get('externalVideoComponent')
        if external_video and isinstance(external_video, dict):
            nav_context = external_video.get('navigationContext', {})
            media_info = MediaInfo(
                media_type="external_video",
                title=nav_context.get('title'),
                description=nav_context.get('description'),
                url=nav_context.get('url'),
                dimensions=None
            )
            if media_info.url:
                media_list.append(media_info)
        
        # 5. Look for URN references in media references
        media_ref = content.get('media')
        if media_ref and isinstance(media_ref, dict):
            for key, value in media_ref.items():
                if 'digitalmediaAsset' in str(value):
                    video_info = self._parse_video_from_metadata(value)
                    if video_info:
                        media_list.append(video_info)
        
        # 6. Search recursively in content for digital media asset references
        self._search_digital_media_assets(content, media_list)
        
        return media_list
    
    def _search_digital_media_assets(self, obj: Any, media_list: List[MediaInfo]):
        """Recursively search for digital media asset references"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and 'urn:li:digitalmediaAsset:' in value:
                    video_info = self._parse_video_from_metadata(value)
                    if video_info:
                        # Avoid duplicates
                        if not any(m.url == video_info.url for m in media_list):
                            media_list.append(video_info)
                elif isinstance(value, (dict, list)):
                    self._search_digital_media_assets(value, media_list)
        elif isinstance(obj, list):
            for item in obj:
                self._search_digital_media_assets(item, media_list)
    
    def _extract_post_id(self, post_data: Dict[str, Any]) -> str:
        """Extract unique post ID from post data"""
        # Try entityUrn first
        entity_urn = post_data.get('entityUrn', '')
        if entity_urn:
            if ':activity:' in entity_urn:
                return entity_urn.split(':activity:')[-1]
            elif 'urn:li:activity:' in entity_urn:
                return entity_urn.split(':activity:')[-1]
            else:
                return entity_urn.split(':')[-1]
        
        # Try other ID fields
        for id_field in ['activityUrn', 'updateUrn', 'postUrn']:
            urn = post_data.get(id_field, '')
            if urn and ':activity:' in urn:
                return urn.split(':activity:')[-1]
        
        # Fallback: create hash from key content
        key_content = f"{post_data.get('actor', {})}_{post_data.get('timestamp', {})}_{post_data.get('commentary', {})}"
        return str(hash(key_content))
    
    def _find_text_anywhere(self, data: Any) -> str:
        """Find text content anywhere in the data structure"""
        if isinstance(data, dict):
            # Check common text fields
            for key in ['text', 'commentary', 'description', 'title', 'content']:
                if key in data:
                    text_data = data[key]
                    if isinstance(text_data, str):
                        return text_data
                    elif isinstance(text_data, dict):
                        text = text_data.get('text')
                        if text:
                            return str(text)
            
            # Recursively search in values
            for value in data.values():
                text = self._find_text_anywhere(value)
                if text and len(text.strip()) > 10:
                    return text
        elif isinstance(data, list):
            for item in data:
                text = self._find_text_anywhere(item)
                if text and len(text.strip()) > 10:
                    return text
        return ""
    
    def _extract_post_info(self, post_data: Dict[str, Any]) -> Optional[PostInfo]:
        """Extract post information from LinkedIn post data"""
        try:
            if not isinstance(post_data, dict):
                return None
            
            # Extract unique post ID
            post_id = self._extract_post_id(post_data)
            
            # Skip if we've already seen this post ID (deduplication)
            if post_id in self.seen_post_ids:
                return None
            self.seen_post_ids.add(post_id)
            
            # Initialize post info
            post_info = PostInfo(post_id=post_id)
            
            # Extract author information from actor component
            actor = post_data.get('actor', {})
            if isinstance(actor, dict):
                name_data = actor.get('name')
                if isinstance(name_data, dict):
                    post_info.author_name = name_data.get('text')
                
                # Extract timestamp from subDescription
                sub_desc = actor.get('subDescription')
                if isinstance(sub_desc, dict):
                    post_info.timestamp = sub_desc.get('text')
            
            # Extract post text from commentary
            commentary = post_data.get('commentary', {})
            if isinstance(commentary, dict):
                text_data = commentary.get('text')
                if isinstance(text_data, dict):
                    post_info.post_text = self._extract_text_from_text_vm(text_data)
                elif isinstance(text_data, str):
                    post_info.post_text = text_data
            
            # Extract media from content
            content = post_data.get('content', {})
            if content:
                post_info.media = self._extract_media_from_content(content)
            
            # Extract post URL from socialContent
            social_content = post_data.get('socialContent', {})
            if isinstance(social_content, dict):
                post_info.post_url = social_content.get('shareUrl')
            
            # If we still don't have text, try to find it in other locations
            if not post_info.post_text:
                post_info.post_text = self._find_text_anywhere(post_data)
            
            # Only return post if it has meaningful content
            return post_info if (post_info.post_text and len(post_info.post_text.strip()) > 10) else None
            
        except Exception as e:
            print(f"Error parsing post: {e}")
            return None
    
    def _search_for_posts_recursive(self, data: Any, posts: List[PostInfo]):
        """Recursively search for posts in the data structure"""
        if isinstance(data, dict):
            # Check if this is a post/update
            if data.get('$type') == 'com.linkedin.voyager.dash.feed.Update':
                post_info = self._extract_post_info(data)
                if post_info:
                    posts.append(post_info)
            
            # Recursively search through all values
            for value in data.values():
                self._search_for_posts_recursive(value, posts)
                
        elif isinstance(data, list):
            for item in data:
                self._search_for_posts_recursive(item, posts)
    
    def parse_posts(self) -> List[PostInfo]:
        """Parse all posts from the JSON data"""
        self.seen_post_ids.clear()  # Clear for fresh parsing
        posts = []
        self._search_for_posts_recursive(self.data, posts)
        return posts
    
    def generate_summary(self, posts: List[PostInfo]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total_posts = len(posts)
        posts_with_media = sum(1 for post in posts if post.media)
        
        media_types = {}
        total_media_items = 0
        
        for post in posts:
            for media in post.media:
                total_media_items += 1
                media_type = media.media_type
                media_types[media_type] = media_types.get(media_type, 0) + 1
        
        return {
            "total_posts": total_posts,
            "posts_with_media": posts_with_media,
            "total_media_items": total_media_items,
            "media_types": media_types
        }
    
    def save_to_json(self, posts: List[PostInfo], output_file: str = None) -> str:
        """Save posts to JSON file"""
        if output_file is None:
            output_file = "linkedin_posts_extracted.json"
        
        summary = self.generate_summary(posts)
        
        output_data = {
            "summary": summary,
            "posts": [post.to_dict() for post in posts]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return str(output_file)
    
    def print_summary(self, posts: List[PostInfo]):
        """Print detailed summary to console"""
        summary = self.generate_summary(posts)
        
        print("=" * 80)
        print("LINKEDIN PROFILE ACTIVITY ANALYSIS")
        print("=" * 80)
        print(f"Total Posts Found: {summary['total_posts']}")
        print(f"Posts with Media: {summary['posts_with_media']}")
        print(f"Total Media Items: {summary['total_media_items']}")
        print()
        print("Media Types Distribution:")
        for media_type, count in summary['media_types'].items():
            print(f"  - {media_type}: {count}")
        print()
        print("=" * 80)
        print("DETAILED POST INFORMATION")
        print("=" * 80)
        print()
        
        for i, post in enumerate(posts, 1):
            print(f"POST #{i}")
            print(f"ID: {post.post_id}")
            if post.author_name:
                print(f"Author: {post.author_name}")
            if post.timestamp:
                print(f"Timestamp: {post.timestamp}")
            if post.post_text:
                # Truncate long text for display
                display_text = post.post_text[:200] + "..." if len(post.post_text) > 200 else post.post_text
                print(f"Text: {display_text}")
            
            if post.media:
                print(f"Media ({len(post.media)} items):")
                for j, media in enumerate(post.media, 1):
                    media_desc = media.description or "No description"
                    dimensions = f" ({media.dimensions})" if media.dimensions else ""
                    url_preview = media.url[:50] + "..." if media.url and len(media.url) > 50 else media.url
                    print(f"    {j}. {media.media_type} - {media_desc}{dimensions} - {url_preview}")
            
            if post.post_url:
                print(f"Post URL: {post.post_url}")
            
            print("-" * 64)
            print()


def main():
    """Main function"""
    # Determine input file path
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "linkedin_profile_activity.json"
    
    print(f"Parsing LinkedIn profile activity from: {input_file}")
    print()
    
    # Initialize parser
    parser = LinkedInParser(input_file)
    
    # Parse posts
    print("Extracting posts...")
    posts = parser.parse_posts()
    
    if not posts:
        print("No posts found in the JSON file.")
        return
    
    # Generate JSON output
    output_file = parser.save_to_json(posts)
    print(f"Posts extracted and saved to: {output_file}")
    
    # Print detailed summary
    parser.print_summary(posts)


if __name__ == "__main__":
    main()