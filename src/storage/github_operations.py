import json
import base64
import requests
from datetime import datetime
from utils.config import Config
from github import Github

class GithubOperations:
    def __init__(self, is_production=False):
        self.headers = {
            'Authorization': f'token {Config.GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = "https://api.github.com"
        self.repo_owner = Config.GITHUB_OWNER
        self.repo_name = Config.GITHUB_REPO
        
        # Define base directory based on environment - just prod or dev
        self.base_dir = "prod" if is_production else "dev"
        
        # Define file paths
        self.ongoing_tweets_path = "ongoing_tweets.json"
        self.comments_path = "comments.json"
        self.story_digest_path = "digest_history.json"
        self.tech_advances_path = "tech_evolution.json"

    def get_file_content(self, file_path):
        """Get file content from GitHub"""
        try:
            # Add base directory to path if it's not already included
            full_path = f"data/{self.base_dir}/{file_path}"
            
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{full_path}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            content_data = response.json()
            content = base64.b64decode(content_data['content']).decode('utf-8')
            
            try:
                parsed_content = json.loads(content)
                print(f"Successfully parsed {file_path}")
                return parsed_content, content_data['sha']
            except json.JSONDecodeError as e:
                print(f"JSON decode error in {file_path}: {str(e)}")
                return None, None
                
        except requests.exceptions.HTTPError as e:
            print(f"File {file_path} not found")
            return None, None
        except Exception as e:
            print(f"Error reading {file_path}: {type(e)} - {str(e)}")
            return None, None

    def update_file(self, file_path, content, commit_message, sha=None):
        """Update file in GitHub repository"""
        try:
            # Add base directory to path if it's not already included
            full_path = f"data/{self.base_dir}/{file_path}"
            # Get current file info (including SHA) if not provided
            if sha is None:
                url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/data/{full_path}"
                response = requests.get(url, headers=self.headers)
                
                # If file exists, get its SHA
                if response.status_code == 200:
                    current_file = response.json()
                    sha = current_file['sha']
            
            # Convert content to string if it's not already
            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=2)
            elif not isinstance(content, str):
                content = str(content)
            
            # Prepare the update data
            data = {
                'message': commit_message,
                'content': base64.b64encode(content.encode()).decode(),
            }
            
            # Include SHA if available
            if sha:
                data['sha'] = sha
                
            # Make the update request
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{full_path}"
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Error storing {file_path}: {str(e)}")
            raise

    def _update_file_with_retry(self, file_path, content, message, sha=None, max_retries=3):
        """Helper method to update a file with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.update_file(file_path, content, message, sha)
                return response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Attempt {attempt + 1} failed, retrying...")
        return None

    def add_tweet(self, tweet, id=None, tweet_count=None, simulated_date=None, age=None):
        """Add a tweet to ongoing_tweets.json"""
        print(f"Adding tweet: {tweet}")
        try:
            # Handle ongoing tweets
            tweets, sha = self.get_file_content(self.ongoing_tweets_path)
            tweets = tweets or []
            
            # Add metadata to tweet
            tweet_with_metadata = {
                **tweet,
                "id": id,
                "tweet_count": tweet_count,
                "simulated_date": simulated_date,
                "age": age
            }
            if not any(existing.get('id') == tweet.get('id') for existing in tweets):
                tweets.append(tweet_with_metadata)
                self._update_file_with_retry(
                    self.ongoing_tweets_path,
                    tweets,
                    f"Add tweet: {tweet.get('id', 'new')}",
                    sha
                )
            print(f"Successfully added tweet: {len(tweets)}")
        except Exception as e:
            print(f"Error saving ongoing tweets: {str(e)}")
            raise

    def add_comments(self, tweet_id, comments):
        all_comments, sha = self.get_file_content(self.comments_path)
        tweet_comments = next((item for item in all_comments if item["tweet_id"] == tweet_id), None)
        if tweet_comments:
            tweet_comments['comments'].extend(comments)
        else:
            all_comments.append({"tweet_id": tweet_id, "comments": comments})
        self.update_file(self.comments_path, all_comments, f"Add comments for tweet: {tweet_id}", sha)

        # Also update the story digest
        story_digest, digest_sha = self.get_file_content(self.story_digest_path)
        for comment in comments:
            story_digest.append({"tweet_id": tweet_id, "comment": comment})
        self.update_file(self.story_digest_path, story_digest, f"Update story digest with comments for tweet: {tweet_id}", digest_sha)

    def update_story_digest(self, new_tweets, new_comments, initial_content=None):
        """Update the story digest with new content"""
        try:
            # Fetch the existing digest history
            history, digest_sha = self.get_file_content(self.story_digest_path)
            if not isinstance(history, list):
                history = []
            
            if initial_content:
                # Add the new digest to history
                history.append(initial_content)
            
            # Store the updated history
            self.update_file(
                file_path=self.story_digest_path,
                content=history,
                commit_message=f"Update digest history with {len(new_tweets)} tweets and {len(new_comments)} comments",
                sha=digest_sha
            )
            print(f"Successfully updated digest history with {len(new_tweets)} tweets and {len(new_comments)} comments")
                
        except Exception as e:
            print(f"Error updating story digest: {str(e)}")
            raise

    def delete_file(self, file_path, commit_message, sha):
        """
        Delete a file from the GitHub repository
        """
        # Add base directory to path if it's not already included
        full_path = f"data/{self.base_dir}/{file_path}"
        
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{full_path}"
        print(f"Deleting file: {url}")
        data = {
            "message": commit_message,
            "sha": sha
        }
        response = requests.delete(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
