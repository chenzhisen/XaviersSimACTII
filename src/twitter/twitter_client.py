from requests_oauthlib import OAuth1Session
import os
import json
from src.utils.config import Config
import requests
from time import sleep
import time

class TwitterClientV2:
    def __init__(self):
        # Initialize the API client using credentials from environment variables
        self.consumer_key = Config.TWITTER_API_KEY
        self.consumer_secret = Config.TWITTER_API_SECRET
        self.access_token = Config.TWITTER_ACCESS_TOKEN
        self.access_token_secret = Config.TWITTER_ACCESS_TOKEN_SECRET
        self.bearer_token = Config.TWITTER_BEARER_TOKEN

        print(f"Consumer Key: {self.consumer_key}")
        print(f"Consumer Secret: {self.consumer_secret}")
        print(f"Access Token: {self.access_token}")
        print(f"Access Token Secret: {self.access_token_secret}")

    def post_tweet(self, text):
        """Post a tweet using Twitter API v2."""
        payload = {"text": text}

        # Create an OAuth1 session
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        # Make the request
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
        )

        if response.status_code != 201:
            print(f"Error posting tweet: {response.status_code} {response.text}")
            return None

        # Parse and print the response
        json_response = response.json()
        tweet_id = json_response.get("data", {}).get("id")
        print(f"Tweet posted: {tweet_id}")
        return tweet_id

    def reply_to_tweet(self, text, tweet_id):
        """Reply to a tweet using Twitter API v2."""
        payload = {
            "text": text,
            "reply": {
                "in_reply_to_tweet_id": tweet_id
            }
        }

        # Create an OAuth1 session
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        # Make the request
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
        )

        if response.status_code != 201:
            print(f"Error replying to tweet: {response.status_code} {response.text}: {payload} ")
            return None

        # Parse and print the response
        json_response = response.json()
        reply_id = json_response.get("data", {}).get("id")
        print(f"Reply posted: {reply_id}")
        return reply_id

    # def get_replies(self, tweet_id):
    #     """Get replies to a specific tweet."""
    #     # First, retrieve the conversation_id for the tweet
    #     conversation_id = self.get_conversation_id(tweet_id)
    #     if not conversation_id:
    #         print("Failed to retrieve conversation_id")
    #         return None

    #     # Use the conversation_id to search for replies
    #     url = f"https://api.twitter.com/2/tweets/search/recent?query=conversation_id:{conversation_id}&tweet.fields=author_id,created_at"
    #     headers = {"Authorization": f"Bearer {self.bearer_token}"}

    #     response = requests.get(url, headers=headers)

    #     if response.status_code != 200:
    #         print(f"Error fetching replies: {response.status_code} {response.text}")
    #         return None

    #     replies = response.json().get("data", [])
    #     for reply in replies:
    #         print(f"Reply ID: {reply['id']}, Text: {reply['text']}")
    #     return replies

    # def get_conversation_id(self, tweet_id):
    #     """Retrieve the conversation_id for a specific tweet."""
    #     url = f"https://api.twitter.com/2/tweets?ids={tweet_id}&tweet.fields=conversation_id"
    #     headers = {"Authorization": f"Bearer {self.bearer_token}"}
    #     print(f"URL: {url}")
    #     response = requests.get(url, headers=headers)

    #     if response.status_code != 200:
    #         print(f"Error fetching conversation_id: {response.status_code} {response.text}")
    #         return None

    #     json_response = response.json()
    #     print(f"JSON Response: {json_response}")
    #     conversation_id = json_response['data'][0]['conversation_id']
    #     print(f"Conversation ID: {conversation_id}")
    #     return conversation_id

    # Function to get replies
    def get_replies(self, tweet_id, max_results=10):
        # Define the search endpoint URL
        search_url = "https://api.twitter.com/2/tweets/search/recent"

        # Define query parameters
        query_params = {
            'query': f'conversation_id:{tweet_id}',  # Filter by conversation ID
            'tweet.fields': 'author_id,created_at,conversation_id',  # Include extra fields if needed
            'max_results': max_results  # Max number of results per request (10-100)
        }
        print(f"Query Params: {query_params}")
        # Make request
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        response = requests.get(search_url, headers=headers, params=query_params)
        
        if response.status_code != 200:
            raise Exception(f"Request returned an error: {response.status_code} {response.text}")
        
        return response.json()

    def get_user_tweets(self):
        """Get all tweets for the authenticated user."""
        # Create an OAuth1 session
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        # First get the user ID
        response = oauth.get("https://api.twitter.com/2/users/me")
        if response.status_code != 200:
            print(f"Error getting user info: {response.status_code} {response.text}")
            return None
            
        user_id = response.json()['data']['id']
        
        # Get user's tweets
        response = oauth.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets",
            params={"max_results": 100}  # Maximum allowed per request
        )

        if response.status_code != 200:
            print(f"Error getting tweets: {response.status_code} {response.text}")
            return None

        return response.json().get('data', [])

    def delete_tweet(self, tweet_id):
        """Delete a tweet using Twitter API v2."""
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        response = oauth.delete(f"https://api.twitter.com/2/tweets/{tweet_id}")

        if response.status_code != 200:
            print(f"Error deleting tweet {tweet_id}: {response.status_code} {response.text}")
            return False

        print(f"Successfully deleted tweet: {tweet_id}")
        return True

    def delete_all_tweets(self):
        """Delete all tweets for the authenticated user with Basic plan rate limits."""
        tweets = self.get_user_tweets()
        if not tweets:
            print("No tweets found or error getting tweets")
            return

        batch_size = 5  # Basic plan: 5 requests per 15 minutes
        for i in range(0, len(tweets), batch_size):
            batch = tweets[i:i + batch_size]
            print(f"\nProcessing batch {i//batch_size + 1} of {(len(tweets) + batch_size - 1)//batch_size}")
            
            for tweet in batch:
                success = self.delete_tweet(tweet['id'])
                if success:
                    print(f"Deleted tweet {tweet['id']}: {tweet.get('text', '')[:50]}...")
                else:
                    print(f"Failed to delete tweet {tweet['id']}")
                time.sleep(2)  # Small delay between deletions in same batch
            
            if i + batch_size < len(tweets):
                wait_time = 15 * 60  # 15 minutes in seconds
                print(f"\nWaiting {wait_time} seconds for rate limit reset...")
                time.sleep(wait_time)


# Example usage
def main():
    twitter_client = TwitterClientV2()

    # Step 1: Post a tweet
    tweet_id = twitter_client.post_tweet("This is a test tweet 1 from XaviersSimACTII.")
    if not tweet_id:
        print("Failed to post tweet")
        return
    sleep(2)

    # tweet_id = 1853047500241764830
    # Step 2: Reply to the tweet
    reply_id = twitter_client.reply_to_tweet("This is a reply to the test tweet 1.", tweet_id)
    if not reply_id:
        print("Failed to post reply")
        return
    sleep(2)

    # reply_id = 1852921501625839753
    first_reply_id = reply_id
    print(f"Replying to reply: {first_reply_id}")
    twitter_client.reply_to_tweet("This is a reply to a comment.", first_reply_id)

    # Step 3: Get replies to the original tweet
    replies = twitter_client.get_replies(reply_id)
    if not replies:
        print("No replies found")
        return

    sleep(2)
    # Step 4: Reply to a specific comment (if any)
    if replies:
        first_reply_id = replies[0]['id']
        print(f"Replying to reply: {first_reply_id}")
        twitter_client.reply_to_tweet("This is a reply to a comment.", first_reply_id)

if __name__ == "__main__":
    main() 