from src.storage.github_operations import GithubOperations
from src.generation.tech_evolution_generator import TechEvolutionGenerator
from src.generation.digest_generator import DigestGenerator
from src.generation.tweet_generator import TweetGenerator
from src.utils.config import Config, AIProvider
from anthropic import Anthropic
from openai import OpenAI

import anthropic
import json
from datetime import datetime, timedelta
import math
import traceback
import os
import argparse

class SimulationWorkflow:
    def __init__(self, tweets_per_year=96, digest_interval=16, provider: AIProvider = AIProvider.XAI, is_production=False):
        ai_config = Config.get_ai_config(provider)
        
        if provider == AIProvider.ANTHROPIC:
            self.client = Anthropic(api_key=ai_config.api_key)
        elif provider == AIProvider.OPENAI:
            self.client = OpenAI(
                api_key=ai_config.api_key,
            )
        elif provider == AIProvider.XAI:
            self.client = Anthropic( 
                api_key=ai_config.api_key,
                base_url=ai_config.base_url
            )
        self.model = ai_config.model
        self.digest_interval = digest_interval
        self.is_production = is_production
        
        # Set post_to_twitter based on is_production
        self.post_to_twitter = is_production

        # Initialize GitHub operations with production flag
        self.github_ops = GithubOperations(is_production=is_production)

        # Initialize tweet generator with production flag
        self.tweet_gen = TweetGenerator(
            client=self.client, 
            model=self.model,
            tweets_per_year=tweets_per_year,
            digest_interval=self.digest_interval,
            is_production=is_production
        )
        
        self.tweets_per_year = tweets_per_year
        self.tech_preview_months = 6
        self.start_date = datetime(2025, 1, 1)
        self.days_per_tweet = 365 / tweets_per_year
        self.start_age = 22.0
        
    def get_current_date(self, tweet_count):
        """Calculate current simulation date based on tweet count"""
        days_elapsed = tweet_count * self.days_per_tweet
        current_date = self.start_date + timedelta(days=days_elapsed)
        return current_date
    
    def get_current_age(self, tweet_count):
        """Calculate Xavier's current age based on tweet count"""
        years_elapsed = tweet_count / self.tweets_per_year
        return self.start_age + years_elapsed
        
    def run(self):
        try:
            # 0. Read ongoing tweets with proper history
            ongoing_tweets = self.tweet_gen.get_ongoing_tweets()
            xavier_sim_content, _ = self.github_ops.get_file_content('XaviersSim.json')
            ongoing_comments = None
            trends = None

            # Initialize counters
            tweet_count = 0
            current_age = 22.0
            
            # Extract latest state from ongoing tweets
            if ongoing_tweets:
                last_tweet = ongoing_tweets[-1]
                if isinstance(last_tweet, dict):
                    tweet_count = last_tweet.get('tweet_count', 0)
                    current_age = last_tweet.get('age', 22.0)

            current_date = self.get_current_date(tweet_count + 1)
            current_age = self.get_current_age(tweet_count + 1)
            print(f"Current tweet count: {tweet_count}")
            print(f"Current simulation date: {current_date.strftime('%Y-%m-%d')}")
            print(f"Current age: {current_age:.2f}")
            
            # 1. Initialize components with current state and post_to_twitter flag
            tech_gen = TechEvolutionGenerator(
                client=self.client, 
                model=self.model,
                is_production=self.is_production
            )
            
            digest_gen = DigestGenerator(
                client=self.client,
                model=self.model,
                tweet_generator=self.tweet_gen,
                is_production=self.is_production
            )
            
            # Check and get latest tech evolution
            latest_tech = tech_gen.check_and_generate_tech_evolution(current_date)
            if not latest_tech:
                print("Failed to get tech evolution data")
                return

            print(f"Using tech evolution for epoch: {latest_tech.get('epoch_year')}")
            
            # 4. Check/Generate digest
            latest_digest = digest_gen.get_latest_digest()
            
            def is_digest_empty(digest):
                """Check if digest is empty or invalid."""
                if not digest:
                    return True
                    
                # Check if we have the main digest content
                if not digest.get('digest'):
                    return True
                    
                # Check if we have the core narrative elements
                narrative = digest.get('digest', {})
                if not narrative.get('Story'):
                    return True
                    
                return False
            
            if is_digest_empty(latest_digest):
                # Fetch the digest history from GitHub
                digest_history, _ = self.github_ops.get_file_content("digest_history_acti.json")
                
                if digest_history:
                    latest_digest = digest_history[-1]
                    print("Loaded latest digest from GitHub.")
                else:
                    print("Generating initial digest from historical tweets...")
                    if xavier_sim_content and isinstance(xavier_sim_content, dict):
                        print("Processing historical tweets by age brackets...")
                        latest_digest = digest_gen.generate_digest(
                            tweets=xavier_sim_content,
                            current_age=current_age,
                            current_date=current_date,
                            tweet_count=tweet_count
                        )
                    else:
                        # Generate first digest with no tweets
                        print("Generating very first digest...")
                        latest_digest = digest_gen.generate_digest(
                            tweets=[],
                            current_age=current_age,
                            current_date=current_date,
                            tweet_count=tweet_count
                        )
            
            # 5. Check if new digest needed
            if latest_digest:
                # Get the tweet count from the last digest's metadata
                last_digest_tweet_count = latest_digest.get('metadata', {}).get('tweet_count', 0)
                tweets_since_last_digest = tweet_count - last_digest_tweet_count
                
                print(f"Last digest at tweet: {last_digest_tweet_count}")
                print(f"Current tweet: {tweet_count}")
                print(f"Tweets since last digest: {tweets_since_last_digest}")
                
                # Only generate new digest if we've passed the interval
                if tweets_since_last_digest >= self.digest_interval:
                    print(f"Generating new digest after {tweets_since_last_digest} tweets...")
                    recent_tweets = ongoing_tweets[-self.digest_interval:]
                    simulation_time = current_date.strftime('%Y-%m-%d')
                    latest_digest = digest_gen.generate_digest(
                        latest_digest=latest_digest,
                        tweets=recent_tweets,
                        current_age=current_age,
                        current_date=current_date,
                        tweet_count=tweet_count
                    )

            # Handle case where digest generation fails
            if latest_digest is None:
                print("Failed to generate digest")
                return
            
            # Extract metadata from digest
            simulation_time = latest_digest.get('metadata', {}).get('simulation_time')
            
            # 7. Generate and store new tweet
            new_tweet = self.tweet_gen.generate_tweet( 
                latest_digest=latest_digest,
                recent_tweets=ongoing_tweets[-self.digest_interval:] if ongoing_tweets else None,
                recent_comments=ongoing_comments[-self.digest_interval:] if ongoing_comments else None,
                age=current_age,
                tweet_count=tweet_count,
                trends=trends,
                sequence_length=self.digest_interval
            )
            # print(f"New tweet: {new_tweet}")
            if new_tweet:
                # Post to Twitter if flag is True
                if self.post_to_twitter:
                    from src.twitter.twitter_client import TwitterClientV2
                    twitter_client = TwitterClientV2()
                    
                    # Add TEST prefix and ensure total length is under 280
                    test_prefix = "TEST: "
                    max_content_length = 280 - len(test_prefix)
                    tweet_content = test_prefix + new_tweet['content'][:max_content_length]
                    
                    tweet_id = twitter_client.post_tweet(tweet_content)
                    
                    if tweet_id:
                        print(f"Successfully posted to Twitter with ID: {tweet_id}")
                        print(f"Tweet content: {tweet_content}")
                        # Store the tweet using Twitter ID
                        self.tweet_gen.github_ops.add_tweet(
                            new_tweet,
                            id=tweet_id,  # Use actual Twitter ID
                            tweet_count=tweet_count + 1,
                            simulated_date=current_date.strftime('%Y-%m-%d'),
                            age=current_age
                        )
                    else:
                        print("Failed to post tweet to Twitter")
                        # Fallback to sequential ID if Twitter post fails
                        self.tweet_gen.github_ops.add_tweet(
                            new_tweet,
                            id=f"tweet_{tweet_count + 1}",
                            tweet_count=tweet_count + 1,
                            simulated_date=current_date.strftime('%Y-%m-%d'),
                            age=current_age
                        )
                else:
                    # Use sequential ID when not posting to Twitter
                    self.tweet_gen.github_ops.add_tweet(
                        new_tweet,
                        id=f"tweet_{tweet_count + 1}",
                        tweet_count=tweet_count + 1,
                        simulated_date=current_date.strftime('%Y-%m-%d'),
                        age=current_age
                    )
                    print("Tweet generated but not posted to Twitter (post_to_twitter=False)")
                
                # print(f"Generated tweet for {current_date.strftime('%Y-%m-%d')} (age {current_age:.2f}): {new_tweet}")
            
        except Exception as e:
            print(f"Error in simulation workflow: {str(e)}")
            traceback.print_exc()

def main():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Run Xavier simulation')
    parser.add_argument('--tweets-per-year', type=int, default=96,
                      help='Number of tweets to generate per year')
    parser.add_argument('--digest-interval', type=int, default=16,
                      help='Number of tweets between digests')
    parser.add_argument('--provider', type=str, choices=['anthropic', 'openai', 'xai'],
                      default='xai', help='AI provider to use')
    parser.add_argument('--is-production', action='store_true',
                      help='Run in production mode (default: False)')
    
    args = parser.parse_args()
    
    provider_map = {
        'anthropic': AIProvider.ANTHROPIC,
        'openai': AIProvider.OPENAI,
        'xai': AIProvider.XAI
    }
    
    workflow = SimulationWorkflow(
        tweets_per_year=args.tweets_per_year,
        digest_interval=args.digest_interval,
        provider=provider_map[args.provider],
        is_production=args.is_production
    )
    
    while True:
        workflow.run()

if __name__ == "__main__":
    main() 