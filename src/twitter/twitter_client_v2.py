import tweepy
from time import sleep
from src.utils.config import Config

class TwitterClientV2:
    def __init__(self):
        # Authenticate to Twitter using OAuth 2.0 Bearer Token
        self.client = tweepy.Client(bearer_token=Config.TWITTER_BEARER_TOKEN)

    def post_tweet(self, text):
        """Post a tweet using Twitter API v2."""
        try:
            response = self.client.create_tweet(text=text)
            tweet_id = response.data['id']
            print(f"Tweet posted: {tweet_id}")
            return tweet_id
        except tweepy.TweepyException as e:
            print(f"Error posting tweet: {e}")
            return None

    def read_comments(self, tweet_id):
        """Read comments (replies) under a specific tweet using Twitter API v2."""
        try:
            replies = []
            query = f'conversation_id:{tweet_id} to:{Config.TWITTER_USERNAME}'
            response = self.client.search_recent_tweets(query=query, tweet_fields=['conversation_id'])
            for tweet in response.data:
                if tweet.conversation_id == tweet_id:
                    replies.append(tweet)
            return replies
        except tweepy.TweepyException as e:
            print(f"Error reading comments: {e}")
            return []

    def reply_to_comment(self, tweet_id, comment_text):
        """Reply to a specific comment using Twitter API v2."""
        try:
            response = self.client.create_tweet(text=comment_text, in_reply_to_tweet_id=tweet_id)
            reply_id = response.data['id']
            print(f"Replied to comment: {reply_id}")
            return reply_id
        except tweepy.TweepyException as e:
            print(f"Error replying to comment: {e}")
            return None

    def comment_on_tweet(self, tweet_id, comment_text):
        """Post a comment on the initial tweet using Twitter API v2."""
        return self.reply_to_comment(tweet_id, comment_text)

# Example usage
def main():
    twitter_client = TwitterClientV2()

    # Step 1: Post a tweet
    tweet_id = twitter_client.post_tweet("This is a test tweet from XaviersSimACTII.")
    if not tweet_id:
        print("Failed to post tweet")
        return
    sleep(2)

    # Step 2: Comment on the tweet
    comment_id = twitter_client.comment_on_tweet(tweet_id, "This is a comment on the initial tweet.")
    if not comment_id:
        print("Failed to comment on tweet")
        return
    sleep(2)

    # Step 3: Read the comment
    comments = twitter_client.read_comments(tweet_id)
    if comments:
        print("Comments:")
        for comment in comments:
            print(f"- {comment.text} (ID: {comment.id})")
        sleep(2)
        
        # Step 4: Reply to the first comment
        first_comment = comments[0]
        reply_id = twitter_client.reply_to_comment(first_comment.id, "Thank you for your comment!")
        if reply_id:
            print(f"Replied to comment: {reply_id}")

if __name__ == "__main__":
    main() 