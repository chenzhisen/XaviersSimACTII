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
    def __init__(self, tweets_per_year=96, digest_interval=8, provider: AIProvider = AIProvider.XAI):
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

        # Initialize GitHub operations
        self.github_ops = GithubOperations()

        # Initialize tweet generator first
        self.tweet_gen = TweetGenerator(
            client=self.client, 
            model=self.model,
            tweets_per_year=tweets_per_year,
            digest_interval=self.digest_interval
        )
        
        self.tweets_per_year = tweets_per_year
        self.digest_interval = tweets_per_year // 12
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

            # Initialize counters and location
            tweet_count = 0
            current_age = 22.0
            current_location = "Japan"  # Default starting location
            
            # Extract latest state from ongoing tweets
            if ongoing_tweets:
                last_tweet = ongoing_tweets[-1]
                if isinstance(last_tweet, dict):
                    tweet_count = last_tweet.get('tweet_count', 0)
                    # Get location from last tweet, fallback to Japan if not found
                    current_location = last_tweet.get('location', current_location)
                    current_age = last_tweet.get('age', 22.0)
            print(f"tweet_count: {tweet_count}")

            current_date = self.get_current_date(tweet_count + 1)
            current_age = self.get_current_age(tweet_count + 1)
            print(f"Current tweet count: {tweet_count}")
            print(f"Current simulation date: {current_date.strftime('%Y-%m-%d')}")
            print(f"Current age: {current_age:.2f}")
            
            # 1. Initialize components with current state
            tech_gen = TechEvolutionGenerator(self.github_ops, self.client, self.model)
            digest_gen = DigestGenerator(
                github_ops=self.github_ops,
                client=self.client,
                model=self.model,
                simulation_time=current_date.strftime('%Y-%m-%d'),
                simulation_age=current_age,
                tweet_count=tweet_count,
                tweet_generator=self.tweet_gen
            )
            
            # 2. Check/Generate tech evolution
            if not tech_gen.get_tech_evolution():
                print("Generating initial tech evolution...")
                tech_gen.generate_epoch_tech_tree(tech_gen.base_year)
                tech_gen.save_evolution_data()
            
            # 3. Check if new tech evolution needed
            current_year = current_date.year
            next_epoch = current_year + (5 - (current_year % 5))
            
            # Check if we're within 6 months of the next 5-year epoch
            months_to_next_epoch = ((next_epoch - current_year) * 12) - current_date.month
            if months_to_next_epoch <= self.tech_preview_months:
                print(f"Generating tech evolution for epoch {next_epoch}...")
                tech_gen.generate_epoch_tech_tree(next_epoch)
                tech_gen.save_evolution_data()
            
            # 4. Check/Generate digest
            latest_digest = digest_gen.get_latest_digest()
            
            def is_digest_empty(digest):
                if not digest or 'digest' not in digest:
                    return True
                    
                for track in digest['digest'].values():
                    if track.get('historical_summary') or track.get('projected'):
                        return False
                return True
            
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
                        latest_digest = digest_gen.generate_first_digest(xavier_sim_content)
                        if latest_digest:
                            print("Successfully generated first digest")
                        else:
                            print("Failed to generate first digest")
            
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
                current_location=current_location,
                trends=trends
            )
            if new_tweet:
                self.tweet_gen.github_ops.add_tweet(
                    new_tweet,
                    id=f"tweet_{tweet_count + 1}",
                    tweet_count=tweet_count + 1,
                    simulated_date=current_date.strftime('%Y-%m-%d'),
                    age=current_age
                )
                print(f"Generated tweet for {current_date.strftime('%Y-%m-%d')} (age {current_age:.2f}): {new_tweet}")
            
        except Exception as e:
            print(f"Error in simulation workflow: {str(e)}")
            traceback.print_exc()

def main():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Run Xavier Simulation')
    parser.add_argument(
        '--provider', 
        type=str, 
        choices=['XAI', 'ANTHROPIC', 'OPENAI'],
        default='XAI',
        help='AI provider to use (XAI, ANTHROPIC, or OPENAI)'
    )
    parser.add_argument(
        '--tweets-per-year',
        type=int,
        default=96,
        help='Number of tweets to generate per year'
    )
    parser.add_argument(
        '--digest-interval',
        type=int,
        default=8,
        help='Number of tweets between digest generations'
    )
    
    args = parser.parse_args()
    
    # Convert string to enum
    provider = AIProvider[args.provider]
    
    print(f"Starting simulation with {provider.value} provider")
    workflow = SimulationWorkflow(
        tweets_per_year=args.tweets_per_year,
        digest_interval=args.digest_interval,
        provider=provider
    )
    
    while True:
        workflow.run()

if __name__ == "__main__":
    main() 