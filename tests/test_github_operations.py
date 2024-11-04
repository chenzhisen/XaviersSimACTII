import unittest
from unittest.mock import patch, MagicMock
from src.storage.github_operations import GitHubStorage
import json
import base64
from datetime import datetime

class TestGitHubStorage(unittest.TestCase):

    def setUp(self):
        self.storage = GitHubStorage()

    @patch('src.storage.github_operations.requests.get')
    def test_load_existing_compilation(self, mock_get):
        """Test loading existing compilation of tweets"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": base64.b64encode(json.dumps({
                "age 22-22.5": ["Test tweet 1", "Test tweet 2"]
            }).encode()).decode()
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        tweets = self.storage.load_existing_compilation()
        self.assertEqual(len(tweets), 2)
        self.assertEqual(tweets[0]['text'], "Test tweet 1")

    @patch('src.storage.github_operations.requests.get')
    def test_load_ongoing_tweets(self, mock_get):
        """Test loading ongoing tweets"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": base64.b64encode(json.dumps([
                {"text": "Ongoing tweet 1"},
                {"text": "Ongoing tweet 2"}
            ]).encode()).decode()
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        tweets = self.storage.load_ongoing_tweets()
        self.assertEqual(len(tweets), 2)
        self.assertEqual(tweets[0]['text'], "Ongoing tweet 1")

    @patch('src.storage.github_operations.requests.put')
    @patch('src.storage.github_operations.requests.get')
    def test_save_tweet(self, mock_get, mock_put):
        """Test saving a new tweet"""
        # Mock the GET request to return existing tweets
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "content": base64.b64encode(json.dumps([]).encode()).decode()
        }
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response

        # Mock the PUT request to simulate saving the tweet
        mock_put_response = MagicMock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response

        tweet = {"text": "New tweet", "id": "new_tweet_id"}
        result = self.storage.save_tweet(tweet)
        self.assertTrue(result)

    # Add more tests for other methods as needed

def main():
    # Initialize the GitHubStorage
    storage = GitHubStorage()

    # Load existing compilation of tweets
    existing_tweets = storage.load_existing_compilation()
    print("Existing Tweets:", existing_tweets)

    # Load ongoing tweets
    ongoing_tweets = storage.load_ongoing_tweets()
    print("Ongoing Tweets:", ongoing_tweets)

    # Save a new tweet
    new_tweet = {
        "text": "This is a test tweet",
        "id": "test_tweet_id",
        "created_at": datetime.now().isoformat()
    }
    success = storage.save_tweet(new_tweet)
    if success:
        print("New tweet saved successfully.")
    else:
        print("Failed to save new tweet.")

    # Load recent comments for a specific tweet
    comments = storage.load_recent_comments("test_tweet_id")
    print("Comments for test_tweet_id:", comments)

    # Save comments for a tweet
    new_comments = ["Great tweet!", "Very informative."]
    success = storage.save_comments("test_tweet_id", new_comments)
    if success:
        print("Comments saved successfully.")
    else:
        print("Failed to save comments.")

if __name__ == '__main__':
    # unittest.main()
    main()
