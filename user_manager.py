"""
User Manager - Track and manage LinkedIn profiles
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class UserManager:
    """Manage tracked LinkedIn users"""

    def __init__(self, users_file: str = "tracked_users.json"):
        self.users_file = users_file
        self.users = self.load_users()

    def load_users(self) -> List[Dict]:
        """Load tracked users from JSON file"""
        if not os.path.exists(self.users_file):
            return []

        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
            return []

    def save_users(self):
        """Save tracked users to JSON file"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving users: {e}")

    def get_all_users(self) -> List[Dict]:
        """Get all tracked users"""
        return self.users

    def get_user(self, username: str) -> Optional[Dict]:
        """Get a specific user by username"""
        for user in self.users:
            if user['username'] == username:
                return user
        return None

    def add_user(self, username: str, profile_urn: str = None) -> Dict:
        """
        Add a new user to tracking list

        Args:
            username: LinkedIn username or profile URL
            profile_urn: Optional profile URN

        Returns:
            User dictionary
        """
        # Check if user already exists
        existing = self.get_user(username)
        if existing:
            return existing

        # Extract display name from username
        display_name = self._extract_display_name(username)

        # Generate avatar initials
        initials = self._get_initials(display_name)

        # Create user object
        user = {
            'username': username,
            'display_name': display_name,
            'profile_urn': profile_urn,
            'initials': initials,
            'added_at': datetime.now().isoformat(),
            'last_scraped': None,
            'post_count': 0,
            'session_dir': None
        }

        self.users.append(user)
        self.save_users()

        return user

    def update_user(self, username: str, **kwargs):
        """
        Update user information

        Args:
            username: User to update
            **kwargs: Fields to update (profile_urn, last_scraped, post_count, session_dir)
        """
        for user in self.users:
            if user['username'] == username:
                for key, value in kwargs.items():
                    user[key] = value
                self.save_users()
                return user
        return None

    def remove_user(self, username: str) -> bool:
        """
        Remove a user from tracking list

        Args:
            username: User to remove

        Returns:
            True if removed, False if not found
        """
        for i, user in enumerate(self.users):
            if user['username'] == username:
                self.users.pop(i)
                self.save_users()
                return True
        return False

    def _extract_display_name(self, username: str) -> str:
        """Extract display name from username"""
        # Clean up the username
        name = username.replace('https://www.linkedin.com/in/', '')
        name = name.replace('https://linkedin.com/in/', '')
        name = name.replace('/', '')

        # Capitalize and format
        name = name.replace('-', ' ').replace('_', ' ')
        name = name.title()

        return name

    def _get_initials(self, name: str) -> str:
        """Get initials from name"""
        words = name.split()
        if len(words) >= 2:
            return f"{words[0][0]}{words[1][0]}".upper()
        elif len(words) == 1 and len(words[0]) >= 2:
            return words[0][:2].upper()
        elif len(words) == 1:
            return words[0][0].upper()
        return "??"

    def get_user_count(self) -> int:
        """Get total number of tracked users"""
        return len(self.users)

    def get_total_posts(self) -> int:
        """Get total posts across all users"""
        return sum(user.get('post_count', 0) for user in self.users)
