"""
LinkedIn Feed Aggregator Web App
=================================
Flask web application to aggregate and display posts from multiple LinkedIn profiles
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
from datetime import datetime
import threading
import random
import time
from user_manager import UserManager
from linkedin_activity_fetcher import LinkedInActivityFetcher

app = Flask(__name__)
user_manager = UserManager()


def extract_username_from_url(username_or_url: str) -> str:
    """Extract username slug from LinkedIn URL or return as-is if already a slug"""
    # Remove LinkedIn URL prefixes
    username = username_or_url.replace('https://www.linkedin.com/in/', '')
    username = username.replace('https://linkedin.com/in/', '')
    username = username.replace('http://www.linkedin.com/in/', '')
    username = username.replace('http://linkedin.com/in/', '')

    # Remove trailing slash
    username = username.rstrip('/')

    return username


class ScrapingStatusManager:
    """Thread-safe scraping status manager with automatic timeout handling"""
    
    TIMEOUT_SECONDS = 600  # 10 minutes
    
    def __init__(self):
        self._lock = threading.Lock()
        self._state = 'IDLE'  # IDLE, RUNNING, COMPLETED, FAILED, TIMEOUT
        self._progress = ''
        self._error = None
        self._current_user = None
        self._total_users = 0
        self._completed_users = 0
        self._started_at = None
        self._last_heartbeat = None
        self._start_timeout_monitor()
    
    def _start_timeout_monitor(self):
        """Start background thread to monitor for timeouts"""
        def monitor():
            while True:
                time.sleep(30)  # Check every 30 seconds
                with self._lock:
                    if self._state == 'RUNNING' and self._started_at:
                        elapsed = (datetime.now() - self._started_at).total_seconds()
                        if elapsed > self.TIMEOUT_SECONDS:
                            print(f"⚠️ Scraping timeout detected (running for {elapsed}s)")
                            self._state = 'TIMEOUT'
                            self._error = f'Timeout - scraping took too long ({elapsed:.0f}s)'
                            self._progress = f'Timeout after {elapsed:.0f}s'
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def start_scraping(self, username: str, total_users: int = 1):
        """Start a new scraping operation"""
        with self._lock:
            if self._state == 'RUNNING':
                # Check if it's actually stuck
                if self._started_at:
                    elapsed = (datetime.now() - self._started_at).total_seconds()
                    if elapsed > self.TIMEOUT_SECONDS:
                        print(f"⚠️ Force-resetting stuck scraping (running for {elapsed}s)")
                        self._reset_all_fields()
                    else:
                        raise ValueError('Scraping already in progress')
                else:
                    # Inconsistent state, reset
                    self._reset_all_fields()
            
            self._state = 'RUNNING'
            self._current_user = username
            self._total_users = total_users
            self._completed_users = 0
            self._progress = f'Starting scrape for {username}...'
            self._error = None
            self._started_at = datetime.now()
            self._last_heartbeat = datetime.now()
            print(f"✅ Started scraping: {username}")
    
    def update_progress(self, progress: str, current_user: str = None):
        """Update scraping progress"""
        with self._lock:
            self._progress = progress
            if current_user:
                self._current_user = current_user
            self._last_heartbeat = datetime.now()
    
    def increment_completed(self):
        """Increment completed users count"""
        with self._lock:
            self._completed_users += 1
            self._last_heartbeat = datetime.now()
    
    def complete_scraping(self, success_message: str = None):
        """Mark scraping as completed successfully"""
        with self._lock:
            if self._state == 'RUNNING':
                self._state = 'COMPLETED'
                self._progress = success_message or 'Scraping completed successfully'
                self._error = None
                print(f"✅ Scraping completed: {self._progress}")
                # Keep other fields for display, but mark as not running
    
    def fail_scraping(self, error_message: str):
        """Mark scraping as failed"""
        with self._lock:
            if self._state == 'RUNNING':
                self._state = 'FAILED'
                self._error = error_message
                self._progress = f'Failed: {error_message}'
                print(f"❌ Scraping failed: {error_message}")
    
    def ensure_cleanup(self):
        """Ensure scraping is marked as not running (for finally blocks)"""
        with self._lock:
            if self._state == 'RUNNING':
                self._state = 'FAILED'
                self._error = 'Scraping interrupted unexpectedly'
                self._progress = 'Interrupted'
                print("⚠️ Scraping cleanup: marked as failed")
    
    def reset(self, force: bool = False):
        """Reset status to idle"""
        with self._lock:
            if not force and self._state == 'RUNNING':
                # Check if actually stuck
                if self._started_at:
                    elapsed = (datetime.now() - self._started_at).total_seconds()
                    if elapsed < self.TIMEOUT_SECONDS:
                        raise ValueError('Scraping is active. Use force=True to reset anyway.')
            
            self._reset_all_fields()
            print("🔄 Status reset to idle")
    
    def _reset_all_fields(self):
        """Internal method to reset all fields"""
        self._state = 'IDLE'
        self._progress = ''
        self._error = None
        self._current_user = None
        self._total_users = 0
        self._completed_users = 0
        self._started_at = None
        self._last_heartbeat = None
    
    def get_status(self):
        """Get current status as dictionary"""
        with self._lock:
            return {
                'running': self._state == 'RUNNING',
                'state': self._state,
                'progress': self._progress,
                'error': self._error,
                'current_user': self._current_user,
                'total_users': self._total_users,
                'completed_users': self._completed_users,
                'started_at': self._started_at.isoformat() if self._started_at else None,
                'last_heartbeat': self._last_heartbeat.isoformat() if self._last_heartbeat else None
            }
    
    def is_running(self):
        """Check if scraping is currently running"""
        with self._lock:
            return self._state == 'RUNNING'


# Global status manager instance
status_manager = ScrapingStatusManager()


def load_user_session_data(username: str):
    """Load the latest session data for a specific user"""
    user = user_manager.get_user(username)
    if not user or not user.get('session_dir'):
        return None

    session_path = user['session_dir']
    if not os.path.exists(session_path):
        return None

    # Load media summary
    summary_path = os.path.join(session_path, 'media_summary.json')
    if not os.path.exists(summary_path):
        return None

    with open(summary_path, 'r', encoding='utf-8') as f:
        summary_data = json.load(f)

    # Extract username slug for URL usage
    username_slug = extract_username_from_url(username)

    # Check which media files exist for each post
    for post in summary_data['posts']:
        post_num = post['post_number']

        # Add username to post for identification
        post['source_username'] = username
        post['source_display_name'] = user['display_name']
        post['source_initials'] = user['initials']

        # Check text file
        text_path = os.path.join(session_path, 'extracted_text', f'post_{post_num}.txt')
        post['text_file_exists'] = os.path.exists(text_path)

        # Check video file
        video_path = os.path.join(session_path, 'videos', f'post_{post_num}_video.mp4')
        post['video_file_exists'] = os.path.exists(video_path)

        # Check image files
        post['image_files'] = []
        if post.get('image_urls'):
            for idx in range(1, len(post['image_urls']) + 1):
                img_path = os.path.join(session_path, 'images', f'post_{post_num}_image_{idx}.jpg')
                if os.path.exists(img_path):
                    post['image_files'].append({
                        'filename': f'post_{post_num}_image_{idx}.jpg',
                        'username': username_slug  # Use slug for URL
                    })

        # Store video info with username
        if post['video_file_exists']:
            post['video_info'] = {
                'filename': f'post_{post_num}_video.mp4',
                'username': username_slug  # Use slug for URL
            }

    return summary_data


def aggregate_feed(filter_username: str = None):
    """
    Aggregate posts from all tracked users into a single feed
    Maintains chronological order for each user while randomly interleaving between users

    Args:
        filter_username: Optional username to filter by

    Returns:
        Dict with aggregated feed data
    """
    users = user_manager.get_all_users()

    # Filter users if specified
    if filter_username:
        users = [u for u in users if u['username'] == filter_username]

    # Load posts from each user (maintaining their order)
    user_posts_map = {}
    for user in users:
        session_data = load_user_session_data(user['username'])
        if session_data and session_data.get('posts'):
            user_posts_map[user['username']] = session_data['posts']

    # Interleave posts from different users randomly
    # Like dealing cards - take one post from each user in random order
    interleaved_posts = []
    user_indices = {username: 0 for username in user_posts_map.keys()}

    # Continue until all posts are consumed
    while any(user_indices[user] < len(user_posts_map[user]) for user in user_posts_map):
        # Get list of users who still have posts
        available_users = [user for user in user_posts_map
                          if user_indices[user] < len(user_posts_map[user])]

        if not available_users:
            break

        # Randomly pick a user
        selected_user = random.choice(available_users)

        # Add their next post
        post_index = user_indices[selected_user]
        interleaved_posts.append(user_posts_map[selected_user][post_index])
        user_indices[selected_user] += 1

    return {
        'posts': interleaved_posts,
        'total_posts': len(interleaved_posts),
        'total_users': len(users),
        'filtered_by': filter_username
    }


@app.route('/')
def index():
    """Home page"""
    users = user_manager.get_all_users()
    feed_data = aggregate_feed()

    return render_template('index.html',
                         users=users,
                         feed_data=feed_data,
                         has_users=len(users) > 0)


@app.route('/api/users')
def get_users():
    """Get all tracked users"""
    users = user_manager.get_all_users()
    return jsonify({
        'users': users,
        'count': len(users)
    })


@app.route('/api/users/add', methods=['POST'])
def add_user():
    """Add a new user and start scraping immediately"""
    data = request.json
    username = data.get('username')
    target_range = data.get('range', 60)

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    # Check if scraping is already running
    try:
        status_manager.start_scraping(username, total_users=1)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Add user to tracking
    user = user_manager.add_user(username)

    # Start scraping in background
    def run_scraper():
        try:
            status_manager.update_progress(f'Scraping {username}...', username)

            # Create scraper instance
            fetcher = LinkedInActivityFetcher()

            # Run the scraper
            success, session_dir, error = fetcher.run_scrape(username, int(target_range))

            if success:
                # Update user with scrape results
                summary_path = os.path.join(session_dir, 'media_summary.json')
                post_count = 0
                if os.path.exists(summary_path):
                    with open(summary_path, 'r') as f:
                        summary = json.load(f)
                        post_count = summary.get('total_posts', 0)

                user_manager.update_user(
                    username,
                    last_scraped=datetime.now().isoformat(),
                    post_count=post_count,
                    session_dir=session_dir
                )

                status_manager.increment_completed()
                status_manager.complete_scraping(f'Successfully scraped {username}!')
            else:
                status_manager.fail_scraping(error or 'Scraping failed')

        except Exception as e:
            status_manager.fail_scraping(str(e))
        finally:
            # Guaranteed cleanup
            status_manager.ensure_cleanup()

    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'User added and scraping started',
        'user': user,
        'status': 'running'
    })


@app.route('/api/users/remove', methods=['POST'])
def remove_user():
    """Remove a user from tracking"""
    data = request.json
    username = data.get('username')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    success = user_manager.remove_user(username)

    if success:
        return jsonify({'message': 'User removed successfully'})
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/api/users/refresh-all', methods=['POST'])
def refresh_all_users():
    """Re-scrape all tracked users"""
    users = user_manager.get_all_users()
    if not users:
        return jsonify({'error': 'No users to refresh'}), 400

    data = request.json
    target_range = data.get('range', 60)

    # Check if scraping is already running
    try:
        status_manager.start_scraping(users[0]['username'], total_users=len(users))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Start scraping all users in background
    def run_scraper_all():
        try:
            for idx, user in enumerate(users, 1):
                username = user['username']
                status_manager.update_progress(
                    f'Scraping {username} ({idx}/{len(users)})...',
                    username
                )

                # Create scraper instance
                fetcher = LinkedInActivityFetcher()

                # Run the scraper
                success, session_dir, error = fetcher.run_scrape(username, int(target_range))

                if success:
                    # Update user with scrape results
                    summary_path = os.path.join(session_dir, 'media_summary.json')
                    post_count = 0
                    if os.path.exists(summary_path):
                        with open(summary_path, 'r') as f:
                            summary = json.load(f)
                            post_count = summary.get('total_posts', 0)

                    user_manager.update_user(
                        username,
                        last_scraped=datetime.now().isoformat(),
                        post_count=post_count,
                        session_dir=session_dir
                    )

                    status_manager.increment_completed()
                else:
                    print(f"Failed to scrape {username}: {error}")

            status_manager.complete_scraping(f'Successfully refreshed all {len(users)} users!')

        except Exception as e:
            status_manager.fail_scraping(str(e))
        finally:
            # Guaranteed cleanup
            status_manager.ensure_cleanup()

    thread = threading.Thread(target=run_scraper_all)
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Refresh all started',
        'total_users': len(users),
        'status': 'running'
    })


@app.route('/api/scrape-status')
def scrape_status():
    """Get current scraping status"""
    return jsonify(status_manager.get_status())


@app.route('/api/scrape-status/reset', methods=['POST'])
def reset_scrape_status():
    """Reset scraping status (in case it gets stuck)"""
    data = request.json or {}
    force = data.get('force', False)
    
    try:
        status_manager.reset(force=force)
        return jsonify({'message': 'Status reset successfully'})
    except ValueError as e:
        return jsonify({
            'error': str(e),
            'hint': 'Use {"force": true} to force reset an active scraping operation'
        }), 400


@app.route('/api/feed')
def get_feed():
    """Get aggregated feed with optional filtering"""
    filter_username = request.args.get('username')
    feed_data = aggregate_feed(filter_username)
    return jsonify(feed_data)


@app.route('/media/<username>/<path:filename>')
def serve_media(username, filename):
    """Serve media files from user's session directory"""
    # First try direct lookup (in case full URL is passed)
    user = user_manager.get_user(username)

    # If not found, try matching by username slug
    if not user:
        for u in user_manager.get_all_users():
            if extract_username_from_url(u['username']) == username:
                user = u
                break

    if not user or not user.get('session_dir'):
        return "User not found", 404

    session_path = user['session_dir']

    # Determine subdirectory based on file type
    if filename.endswith(('.jpg', '.jpeg', '.png')):
        media_dir = os.path.join(session_path, 'images')
    elif filename.endswith('.mp4'):
        media_dir = os.path.join(session_path, 'videos')
    elif filename.endswith('.txt'):
        media_dir = os.path.join(session_path, 'extracted_text')
    else:
        return "Invalid file type", 400

    return send_from_directory(media_dir, filename)


if __name__ == '__main__':
    # Create tracked_users.json if it doesn't exist
    if not os.path.exists('tracked_users.json'):
        with open('tracked_users.json', 'w') as f:
            json.dump([], f)

    app.run(debug=True, host='0.0.0.0', port=5000)
