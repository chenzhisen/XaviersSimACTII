from src.storage.github_operations import GithubOperations
from src.generation.tech_evolution_generator import TechEvolutionGenerator
from src.generation.digest_generator import DigestGenerator
from src.generation.tweet_generator import TweetGenerator

import json
from datetime import datetime, timedelta
import math

class SimulationWorkflow:
    def __init__(self, tweets_per_year=96):
        self.tweet_gen = TweetGenerator()
        self.github_ops = GithubOperations()
        self.tweets_per_year = tweets_per_year
        self.digest_interval = tweets_per_year // 8
        self.tech_preview_tweets = 60
        
        self.start_date = datetime(2025, 1, 1)
        self.days_per_tweet = 365 / tweets_per_year
        self.start_age = 22
        
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
            
            if ongoing_tweets:
                last_tweet = ongoing_tweets[-1]
                tweet_count = last_tweet.get('tweet_count', 0)
                current_date = datetime.strptime(
                    last_tweet.get('simulated_date', self.start_date.strftime('%Y-%m-%d')),
                    '%Y-%m-%d'
                )
                current_age = last_tweet.get('age', self.start_age)
            else:
                tweet_count = 0
                current_date = self.start_date
                current_age = self.start_age
            
            print(f"Current tweet count: {tweet_count}")
            print(f"Current simulation date: {current_date.strftime('%Y-%m-%d')}")
            print(f"Current age: {current_age:.2f}")
            
            # 1. Check/Generate tech evolution
            tech_gen = TechEvolutionGenerator()
            if not tech_gen.get_tech_evolution():
                print("Generating initial tech evolution...")
                tech_gen.generate_epoch_tech_tree(tech_gen.base_year)
                tech_gen.save_evolution_data()
            
            # 2. Check if new tech evolution needed
            current_year = current_date.year
            next_epoch = current_year + (5 - (current_year % 5))
            
            # Check if we're within 6 months of the next 5-year epoch
            months_to_next_epoch = ((next_epoch - current_year) * 12) - current_date.month
            if months_to_next_epoch <= 6:
                print(f"Generating tech evolution for epoch {next_epoch}...")
                tech_gen.generate_epoch_tech_tree(next_epoch)
                tech_gen.save_evolution_data()
            
            # 3. Check/Generate digest
            digest_gen = DigestGenerator()
            latest_digest = digest_gen.get_latest_digest()
            
            def is_digest_empty(digest):
                if not digest or 'digest' not in digest:
                    return True
                    
                for track in digest['digest'].values():
                    if track.get('historical_summary') or track.get('projected'):
                        return False
                return True
            
            if is_digest_empty(latest_digest):
                print("Generating initial digest...")
                # Get historical tweets from XaviersSim.json
                xavier_sim_content, _ = self.github_ops.get_file_content('XaviersSim.json')
                historical_tweets = []
                if xavier_sim_content and isinstance(xavier_sim_content, dict):
                    for age_range, tweets in xavier_sim_content.items():
                        historical_tweets.extend(tweets)
                
                simulation_time = current_date.strftime('%Y-%m-%d')
                latest_digest = digest_gen.generate_digest(
                    simulation_time=simulation_time,
                    simulation_age=current_age,
                    tweet_count=tweet_count,
                    latest_digest=None,
                    recent_tweets=historical_tweets  # Pass historical tweets for initial context
                )
            
            # 4. Check if new digest needed
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

            # 5. Extract values from latest digest
            simulation_time = latest_digest.get('metadata', {}).get('simulation_time')
            simulation_age = latest_digest.get('metadata', {}).get('simulation_age')
            
            # 6. Generate and store new tweet
            new_tweet = self.tweet_gen.generate_tweet( 
                latest_digest=latest_digest,
                recent_tweets=ongoing_tweets[-self.digest_interval:] if ongoing_tweets else None,
                tweet_count=tweet_count
            )
            
            if new_tweet:
                next_date = self.get_current_date(tweet_count + 1)
                next_age = self.get_current_age(tweet_count + 1)
                tweet_data = {
                    "content": new_tweet,
                    "id": f"tweet_{tweet_count + 1}",
                }
                self.tweet_gen.github_ops.add_tweet(
                    tweet_data,
                    tweet_count=tweet_count + 1,
                    simulated_date=next_date.strftime('%Y-%m-%d'),
                    age=next_age
                )
                print(f"Generated tweet for {next_date.strftime('%Y-%m-%d')} (age {next_age:.2f}): {new_tweet}")
            
        except Exception as e:
            print(f"Error in simulation workflow: {e}")
            import traceback
            traceback.print_exc()

def main():
    workflow = SimulationWorkflow()
    while True: 
        workflow.run()

if __name__ == "__main__":
    main() 