#!/usr/bin/env python3
"""
Enhanced LinkedIn Profile Activity Parser with Video Extraction
Fixed deduplication and enhanced video/media extraction including *videoPlayMetadata
"""

import json
import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
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


class EnhancedLinkedInParser:
    """Enhanced parser with proper video extraction"""
    
    def __init__(self, json_file_path: str):
        self.json_file_path = Path(json_file_path)
        self.data = self._load_json()
        self.seen_post_ids: Set[str] = set()  # Track seen post IDs to avoid duplicates
        
    def _load_json(self) -> Dict[str, Any]:
        """Load and parse the JSON file"""
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
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
            # Construct LinkedIn video URL (this is a common format)
            video_url = f"https://media.licdn.com/dms/video/{asset_id}"
            
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
                                vector_img_info = self._parse_vector_image(detail_data['vectorImage'])
                                if vector_img_info:
                                    media_info.url = vector_img_info.url
                                    media_info.dimensions = vector_img_info.dimensions
                                    break
                    
                    media_list.append(media_info)
        
        # ENHANCED VIDEO EXTRACTION - Check multiple locations
        
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
                title=external_video.get('title'),
                description=external_video.get('description'),
                url=nav_context.get('actionTarget') if isinstance(nav_context, dict) else None
            )
            media_list.append(media_info)
        
        # 5. Check for videos embedded in other components
        if 'media' in content:
            media_items = content['media']
            if isinstance(media_items, list):
                for item in media_items:
                    if isinstance(item, dict):
                        # Check for video media types
                        if any(video_type in str(item.get('mediaType', '')).lower() 
                              for video_type in ['video', 'mp4', 'avi', 'mov']):
                            media_info = MediaInfo(
                                media_type="video",
                                title=item.get('title'),
                                description=item.get('description'),
                                url=item.get('url') or item.get('src')
                            )
                            media_list.append(media_info)
        
        # Check for articles
        article = content.get('articleComponent')
        if article and isinstance(article, dict):
            nav_context = article.get('navigationContext', {})
            media_info = MediaInfo(
                media_type="article",
                title=article.get('title'),
                description=article.get('description'),
                url=nav_context.get('actionTarget') if isinstance(nav_context, dict) else None
            )
            media_list.append(media_info)
        
        # Check for documents
        document = content.get('documentComponent')
        if document and isinstance(document, dict):
            doc_data = document.get('document', {})
            total_pages = doc_data.get('totalPageCount', 'Unknown')
            media_info = MediaInfo(
                media_type="document",
                title=doc_data.get('title'),
                description=f"Pages: {total_pages}",
                url=doc_data.get('manifestUrl')
            )
            media_list.append(media_info)
        
        return media_list
    
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
        key_content = f"{post_data.get('author', {})}_{post_data.get('timestamp', {})}_{post_data.get('commentary', {})}"
        return str(hash(key_content))
    
    def _parse_single_post_enhanced(self, post_data: Dict[str, Any]) -> Optional[PostInfo]:
        """Enhanced single post parsing with video extraction"""
        try:
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
            
            # Extract media from content
            content = post_data.get('content', {})
            if isinstance(content, dict):
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
    
    def _find_text_anywhere(self, data: Any) -> Optional[str]:
        """Search for text content anywhere in the data structure"""
        if isinstance(data, dict):
            # Look for common text fields
            for key in ['text', 'commentary', 'description', 'title', 'content']:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and len(value) > 10:
                        return value
                    elif isinstance(value, dict) and 'text' in value:
                        return value['text']
                    elif isinstance(value, dict):
                        result = self._find_text_anywhere(value)
                        if result:
                            return result
            
            # Recursively search
            for value in data.values():
                result = self._find_text_anywhere(value)
                if result:
                    return result
                    
        elif isinstance(data, list):
            for item in data:
                result = self._find_text_anywhere(item)
                if result:
                    return result
        
        return None
    
    def parse_posts_enhanced(self) -> List[PostInfo]:
        """Enhanced method to parse posts with video extraction"""
        posts = []
        
        # Search through the entire data structure for posts
        self._search_for_posts_recursive_enhanced(self.data, posts)
        
        return posts
    
    def _search_for_posts_recursive_enhanced(self, data: Any, posts: List[PostInfo]):
        """Recursively search for posts in the data structure with video support"""
        if isinstance(data, dict):
            # Check if this is a post/update
            if data.get('$type') == 'com.linkedin.voyager.dash.feed.Update':
                post_info = self._parse_single_post_enhanced(data)
                if post_info:
                    posts.append(post_info)
            
            # Recursively search through all values
            for value in data.values():
                self._search_for_posts_recursive_enhanced(value, posts)
                
        elif isinstance(data, list):
            for item in data:
                self._search_for_posts_recursive_enhanced(item, posts)
    
    def get_enhanced_summary(self) -> Dict[str, Any]:
        """Get enhanced summary of the parsed data"""
        posts = self.parse_posts_enhanced()
        
        total_posts = len(posts)
        posts_with_media = sum(1 for post in posts if post.media)
        total_media_items = sum(len(post.media) for post in posts)
        
        media_types = {}
        for post in posts:
            for media in post.media:
                media_type = media.media_type
                media_types[media_type] = media_types.get(media_type, 0) + 1
        
        return {
            'total_posts': total_posts,
            'posts_with_media': posts_with_media,
            'total_media_items': total_media_items,
            'media_types': media_types,
            'posts': posts
        }
    
    def print_enhanced_summary(self):
        """Print enhanced formatted summary"""
        summary = self.get_enhanced_summary()
        
        print("=" * 80)
        print("LINKEDIN PROFILE ACTIVITY ANALYSIS - ENHANCED VERSION")
        print("=" * 80)
        print(f"Total Posts Found: {summary['total_posts']}")
        print(f"Posts with Media: {summary['posts_with_media']}")
        print(f"Total Media Items: {summary['total_media_items']}")
        
        if summary['media_types']:
            print("\nMedia Types Distribution:")
            for media_type, count in summary['media_types'].items():
                print(f"  - {media_type}: {count}")
        
        print("\n" + "=" * 80)
        print("DETAILED POST INFORMATION")
        print("=" * 80)
        
        for i, post in enumerate(summary['posts'], 1):
            print(f"\nPOST #{i}")
            print(f"ID: {post.post_id}")
            if post.author_name:
                print(f"Author: {post.author_name}")
            if post.timestamp:
                print(f"Timestamp: {post.timestamp}")
            if post.post_text:
                text_preview = post.post_text[:300] + "..." if len(post.post_text) > 300 else post.post_text
                print(f"Text: {text_preview}")
            if post.media:
                print(f"Media ({len(post.media)} items):")
                for j, media in enumerate(post.media, 1):
                    media_desc = f"    {j}. {media.media_type}"
                    if media.title:
                        media_desc += f" - {media.title}"
                    if media.description:
                        media_desc += f" - {media.description}"
                    if media.dimensions:
                        media_desc += f" ({media.dimensions})"
                    if media.url:
                        url_short = media.url[:80] + "..." if len(media.url) > 80 else media.url
                        media_desc += f" - {url_short}"
                    print(media_desc)
            if post.post_url:
                print(f"Post URL: {post.post_url}")
            print("-" * 60)


def main():
    """Main function"""
    json_file = "linkedin_profile_activity.json"
    
    try:
        parser = EnhancedLinkedInParser(json_file)
        parser.print_enhanced_summary()
        
        # Save enhanced results
        summary = parser.get_enhanced_summary()
        output_file = "linkedin_posts_enhanced.json"
        
        # Convert to JSON-serializable format
        posts_data = []
        for post in summary['posts']:
            post_dict = {
                'post_id': post.post_id,
                'author_name': post.author_name,
                'post_text': post.post_text,
                'timestamp': post.timestamp,
                'post_url': post.post_url,
                'media': [
                    {
                        'media_type': media.media_type,
                        'title': media.title,
                        'description': media.description,
                        'url': media.url,
                        'dimensions': media.dimensions,
                        'accessibility_text': media.accessibility_text
                    }
                    for media in post.media
                ]
            }
            posts_data.append(post_dict)
        
        detailed_output = {
            'summary': {
                'total_posts': summary['total_posts'],
                'posts_with_media': summary['posts_with_media'],
                'total_media_items': summary['total_media_items'],
                'media_types': summary['media_types']
            },
            'posts': posts_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_output, f, indent=2, ensure_ascii=False)
        
        print(f"\n\nEnhanced results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()