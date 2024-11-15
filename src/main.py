from src.storage.github_operations import GithubOperations
from src.generation.tech_evolution_generator import TechEvolutionGenerator
from src.generation.digest_generator import DigestGenerator
from src.generation.tweet_generator import TweetGenerator
from src.utils.config import Config, AIProvider
from anthropic import Anthropic

import anthropic
import json
from datetime import datetime, timedelta
import math
import traceback
import os

class SimulationWorkflow:
    def __init__(self, tweets_per_year=96, provider: AIProvider = AIProvider.XAI):
        ai_config = Config.get_ai_config(provider)
        if provider == AIProvider.ANTHROPIC:
            self.client = Anthropic(api_key=ai_config.api_key)
        elif provider == AIProvider.XAI:
            self.client = Anthropic( 
                api_key=ai_config.api_key,
                base_url=ai_config.base_url
            )
        self.model = ai_config.model

        self.tweet_gen = TweetGenerator(self.client, self.model)
        self.github_ops = GithubOperations()
        
        self.tweets_per_year = tweets_per_year
        self.digest_interval = tweets_per_year // 4
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
            # 0. Read ongoing tweets
            ongoing_tweets = self.tweet_gen.get_ongoing_tweets()
            ongoing_comments = None #self.tweet_gen.get_ongoing_comments()
            trends = None #self.tweet_gen.get_trends()
            
            if ongoing_tweets:
                last_tweet = ongoing_tweets[-1]
                tweet_count = last_tweet.get('tweet_count', 0)
                if len(ongoing_tweets) < self.digest_interval:
                    ongoing_tweets = self.tweet_gen.get_acti_tweets()[-self.digest_interval+len(ongoing_tweets):] + ongoing_tweets
            else:
                ongoing_tweets = self.tweet_gen.get_acti_tweets()[-self.digest_interval:]
                tweet_count = 0
            
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
                tweet_count=tweet_count
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
                    # Get historical tweets from XaviersSim.json
                    xavier_sim_content, _ = self.github_ops.get_file_content('XaviersSim.json')
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
                        recent_tweets=recent_tweets,
                        simulation_time=simulation_time,
                        simulation_age=current_age,
                        tweet_count=tweet_count,
                        latest_digest=latest_digest
                    )

            # 6. Extract values from latest digest
            simulation_time = latest_digest.get('metadata', {}).get('simulation_time')
            
            # 7. Generate and store new tweet
            new_tweet = self.tweet_gen.generate_tweet( 
                latest_digest=latest_digest,
                recent_tweets=ongoing_tweets[-self.digest_interval:] if ongoing_tweets else None,
                recent_comments=ongoing_comments[-self.digest_interval:] if ongoing_comments else None,
                age=current_age,
                tweet_count=tweet_count,
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
    workflow = SimulationWorkflow()
    workflow.run()

if __name__ == "__main__":
    main() 