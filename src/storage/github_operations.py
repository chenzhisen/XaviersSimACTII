import json
import base64
import requests
from datetime import datetime
from src.utils.config import Config

class GithubOperations:
    def __init__(self):
        self.headers = {
            'Authorization': f'token {Config.GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = "https://api.github.com"
        self.repo_owner = Config.GITHUB_OWNER
        self.repo_name = Config.GITHUB_REPO
        self.ongoing_tweets_path = "ongoing_tweets.json"
        self.comments_path = "comments.json"
        self.story_digest_path = "digest.json"
        self.tech_advances_path = "tech_evolution.json"

    def get_file_content(self, file_path):
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/data/{file_path}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            content = response.json()
            decoded_content = base64.b64decode(content['content']).decode('utf-8')
            data = json.loads(decoded_content)
            # If the file is empty or contains an empty list, return an empty dict
            if isinstance(data, list) and len(data) == 0:
                return {}, content.get('sha', None)
            return data, content.get('sha', None)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # File doesn't exist yet, return empty dict and None for sha
                return {}, None
            raise  # Re-raise other HTTP errors

    def update_file(self, file_path, content, commit_message, sha=None):
        """Update or create a file in the repository"""
        try:
            # Convert content to JSON string if it's a dict or list
            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=2)
            
            # Ensure content is a string
            content = str(content)
            
            # Create the full path including data directory
            full_path = f"data/{file_path}"
            
            # Remove the .gitkeep creation attempt - it's not necessary
            # The directory will be created automatically when we create files
            
            # Encode content to base64
            content_bytes = content.encode('utf-8')
            base64_content = base64.b64encode(content_bytes).decode('utf-8')
            
            data = {
                "message": commit_message,
                "content": base64_content,
                "branch": "main"
            }
            
            if sha:
                data["sha"] = sha
                
            response = requests.put(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{full_path}",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error storing {file_path}: {str(e)}")
            raise

    def add_tweet(self, tweet):
        tweets, sha = self.get_file_content(self.ongoing_tweets_path)
        tweets.append(tweet)
        self.update_file(self.ongoing_tweets_path, tweets, f"Add tweet: {tweet['id']}", sha)

        # Also update the story digest
        story_digest, digest_sha = self.get_file_content(self.story_digest_path)
        story_digest.append(tweet)
        self.update_file(self.story_digest_path, story_digest, f"Update story digest with tweet: {tweet['id']}", digest_sha)

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
            # Fetch the existing digest
            existing_digest, digest_sha = self.get_file_content(self.story_digest_path)
            
            if initial_content:
                # Use the provided initial content
                digest_content = initial_content
            else:
                # Initialize digest if it doesn't exist
                digest_content = existing_digest if existing_digest else {
                    "generated_at": datetime.now().isoformat(),
                    "content": "",
                    "tweets": [],
                    "comments": []
                }
            
            # Update timestamp
            digest_content["generated_at"] = datetime.now().isoformat()
            
            # Store the updated digest
            self.update_file(
                file_path=self.story_digest_path,
                content=digest_content,
                commit_message=f"Update digest with {len(new_tweets)} tweets and {len(new_comments)} comments",
                sha=digest_sha
            )
            print(f"Successfully updated digest with {len(new_tweets)} tweets and {len(new_comments)} comments")
                
        except Exception as e:
            print(f"Error updating story digest: {str(e)}")
            raise

    def delete_file(self, file_path, commit_message, sha):
        """
        Delete a file from the GitHub repository
        """
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/data/{file_path}"
        data = {
            "message": commit_message,
            "sha": sha
        }
        response = requests.delete(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

# Example usage
def main():
    storage = GithubOperations()

    try:
        # Test reading XaviersSim.json
        xaviers_sim_path = "data/XaviersSim.json"
        
        # Get the raw content first
        url = f"{storage.base_url}/repos/{storage.repo_owner}/{storage.repo_name}/contents/{xaviers_sim_path}"
        response = requests.get(url, headers=storage.headers)
        response.raise_for_status()
        content = response.json()
        
        # Print the raw content for debugging
        raw_content = base64.b64decode(content['content']).decode('utf-8')
        print("Raw content:")
        print(raw_content[:500])  # Print first 500 characters
        print("...")
        print(raw_content[-500:])  # Print last 500 characters
        
        try:
            # Try to parse the JSON
            xaviers_data = json.loads(raw_content)
            
            # Print some basic information about the data
            print("\nSuccessfully parsed JSON")
            print(f"Number of age groups: {len(xaviers_data)}")
            
            # Print a sample from each age group
            for age_group, tweets in xaviers_data.items():
                print(f"\nAge group: {age_group}")
                print(f"Number of tweets: {len(tweets)}")
                print("Sample tweet:", tweets[0] if tweets else "No tweets")
                print("-" * 50)

        except json.JSONDecodeError as je:
            print(f"\nJSON Decode Error: {str(je)}")
            print(f"Error at line {je.lineno}, column {je.colno}")
            # Print the problematic section
            lines = raw_content.split('\n')
            if je.lineno <= len(lines):
                print("\nProblematic line and surrounding context:")
                start_line = max(0, je.lineno - 2)
                end_line = min(len(lines), je.lineno + 2)
                for i in range(start_line, end_line):
                    print(f"Line {i+1}: {lines[i]}")

    except Exception as e:
        print(f"Error reading XaviersSim.json: {str(e)}")

if __name__ == "__main__":
    main()
