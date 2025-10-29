from linkedin_parser_enhanced import EnhancedLinkedInParser
import json

# Parse the data
parser = EnhancedLinkedInParser('linkedin_profile_activity.json')
summary = parser.get_enhanced_summary()

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

# Create final output
detailed_output = {
    'summary': {
        'total_posts': summary['total_posts'],
        'posts_with_media': summary['posts_with_media'],
        'total_media_items': summary['total_media_items'],
        'media_types': summary['media_types']
    },
    'posts': posts_data
}

# Write to file
output_file = 'linkedin_posts_final_fixed.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(detailed_output, f, indent=2, ensure_ascii=False)

print(f'Successfully wrote {len(posts_data)} posts to {output_file}')
print(f'Summary: {summary}')