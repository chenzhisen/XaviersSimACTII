import json
from datetime import datetime
from anthropic import Anthropic
from src.utils.config import Config, AIProvider
from src.storage.github_operations import GithubOperations
from src.generation.digest_generator import DigestGenerator

class TweetGenerator:
    def __init__(self):
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )
        self.github_ops = GithubOperations()
        self.digest_generator = DigestGenerator()
        
        # Simulation parameters
        self.sim_start_year = 2025
        self.tweets_per_year = 96
        
    def calculate_current_year(self, tweet_count):
        """Calculate the current year in Xavier's timeline based on number of tweets"""
        years_elapsed = tweet_count // self.tweets_per_year
        current_year = self.sim_start_year + years_elapsed
        return current_year

    def initialize_file(self, file_path, initial_content):
        """Initialize a file if it doesn't exist"""
        try:
            _, _ = self.github_ops.get_file_content(file_path)
        except:
            print(f"Initializing {file_path} with empty content")
            # Ensure initial content is properly formatted
            if file_path == "digest.json":
                initial_content = {
                    "generated_at": datetime.now().isoformat(),
                    "content": ""
                }
            self.github_ops.update_file(
                file_path=file_path,
                content=initial_content,
                commit_message=f"Initialize {file_path}"
            )

    def get_context(self):
        """Gather all necessary context for tweet generation"""
        try:
            # Initialize files if they don't exist
            self.initialize_file("ongoing_tweets.json", [])
            self.initialize_file("comments.json", [])
            self.initialize_file("digest.json", {})
            self.initialize_file("simulation_state.json", {
                "last_tweet_timestamp": None,
                "tweet_count": 0,
                "current_year": self.sim_start_year,
                "is_complete": False
            })
            
            # Now get all existing tweets to calculate current year
            try:
                ongoing_tweets, _ = self.github_ops.get_file_content("ongoing_tweets.json")
                if not isinstance(ongoing_tweets, list):
                    ongoing_tweets = []
                tweet_count = len(ongoing_tweets)
                recent_tweets = ongoing_tweets[-5:] if ongoing_tweets else []
                
                # For the first few tweets, include ACTI's final tweets in context
                if tweet_count < 5:  # First 5 tweets
                    try:
                        acti_tweets, _ = self.github_ops.get_file_content("last_acti_tweets.json")
                        if not isinstance(acti_tweets, list):
                            acti_tweets = []
                        # Add the last few ACTI tweets to recent_tweets
                        recent_tweets = acti_tweets[-(10-tweet_count):] + recent_tweets  # Last 5-10 ACTI tweets
                    except Exception as e:
                        print(f"Error getting ACTI tweets: {e}")
                
            except Exception as e:
                print(f"Error getting tweets: {e}")
                ongoing_tweets = []
                tweet_count = 0
                recent_tweets = []
            
            # Calculate current year based on tweet count
            current_year = self.calculate_current_year(tweet_count)
            
            # Get the story digest
            try:
                digest, _ = self.github_ops.get_file_content("digest.json")
                if not isinstance(digest, dict) or not digest.get('content'):
                    digest = {}
            except Exception as e:
                print(f"Error getting digest: {e}")
                digest = {}
            
            # Get recent comments if any
            try:
                comments, _ = self.github_ops.get_file_content("comments.json")
                if not isinstance(comments, list):
                    comments = []
                recent_comments = comments[-5:] if comments else []
            except Exception as e:
                print(f"Error getting comments: {e}")
                recent_comments = []

            # Get tech evolution data
            try:
                tech_evolution, _ = self.github_ops.get_file_content("tech_evolution.json")
                if not isinstance(tech_evolution, dict):
                    tech_evolution = {"tech_trees": {}}
            except Exception as e:
                print(f"Error getting tech evolution: {e}")
                tech_evolution = {"tech_trees": {}}
                
            return {
                "current_year": current_year,
                "tweet_count": tweet_count,
                "digest": digest,
                "recent_tweets": recent_tweets,  # Now includes ACTI tweets for first few tweets
                "recent_comments": recent_comments,
                "tech_evolution": tech_evolution
            }
        except Exception as e:
            print(f"Error gathering context: {str(e)}")
            return None

    def get_simulation_state(self):
        """Get the current simulation state from GitHub"""
        try:
            state, sha = self.github_ops.get_file_content("simulation_state.json")
            return state, sha
        except:
            # Initialize with default state if file doesn't exist
            initial_state = {
                "last_tweet_timestamp": datetime.now().isoformat(),
                "tweet_count": 0,
                "current_year": self.sim_start_year,
                "is_complete": False
            }
            return initial_state, None

    def update_simulation_state(self, tweet):
        """Update the simulation state after generating a tweet"""
        try:
            current_state, sha = self.get_simulation_state()
            
            # Update state
            current_state["last_tweet_timestamp"] = datetime.now().isoformat()
            current_state["tweet_count"] = current_state.get("tweet_count", 0) + 1
            current_state["current_year"] = self.calculate_current_year(current_state["tweet_count"])
            current_state["is_complete"] = current_state["current_year"] >= 2075  # Changed from +50 years to specific end year
            
            # Save updated state
            self.github_ops.update_file(
                file_path="simulation_state.json",
                content=current_state,
                commit_message=f"Update simulation state after tweet {current_state['tweet_count']}",
                sha=sha
            )
            
            # Also update ongoing tweets
            try:
                ongoing_tweets, tweets_sha = self.github_ops.get_file_content("ongoing_tweets.json")
                if not isinstance(ongoing_tweets, list):
                    ongoing_tweets = []
                ongoing_tweets.append(tweet)
                self.github_ops.update_file(
                    file_path="ongoing_tweets.json",
                    content=ongoing_tweets,
                    commit_message=f"Add tweet {current_state['tweet_count']}",
                    sha=tweets_sha
                )
            except Exception as e:
                print(f"Error updating ongoing tweets: {e}")
            
            return current_state
        except Exception as e:
            print(f"Error updating simulation state: {e}")
            return None

    def should_generate_tweet(self):
        """Check if it's time to generate a new tweet"""
        try:
            state, _ = self.get_simulation_state()
            
            # If simulation is complete, no more tweets
            if state.get("is_complete", False):
                print("Simulation is complete")
                return False
                
            # Always generate one tweet per run
            print("Generating next tweet")
            return True
            
        except Exception as e:
            print(f"Error checking tweet generation timing: {e}")
            return False

    def create_tweet_prompt(self, context):
        """Create a prompt for tweet generation"""
        current_year = context['current_year']
        tweet_count = context['tweet_count']
        xavier_age = current_year - self.sim_start_year + 22

        # Calculate current month
        year_progress = (tweet_count % self.tweets_per_year) / self.tweets_per_year
        month_estimate = int(year_progress * 12) + 1

        # Get current tech context
        tech_context = self.get_current_tech_context(context)
        
        # Base timeline info
        prompt = (
            f"Current Timeline: {current_year} (around month {month_estimate})\n"
            f"Xavier's Age: {xavier_age}\n\n"
        )

        # Special case: First tweet
        if tweet_count == 0:
            prompt += (
                "Generate Xavier's first tweet transitioning between Japan and New York:\n"
                "- Set in either final moments in Japan or first moments back in NYC\n"
                "- Include specific location details\n"
                "- Show emotional state about this transition\n"
                "- Reference how Japan influenced his perspective\n\n"
            )

        # Add available technology context
        if tech_context:
            prompt += (
                "AVAILABLE TECHNOLOGY:\n"
                f"- Mainstream: {json.dumps([tech['name'] for tech in tech_context['mainstream']], indent=2)}\n"
                f"- Recently Emerged: {json.dumps([tech['name'] for tech in tech_context['emerging']], indent=2)}\n"
                f"- Current Themes: {json.dumps([theme['theme'] for theme in tech_context['themes']], indent=2)}\n\n"
                "Only reference technologies and themes listed above.\n\n"
            )

        # Story Context
        if context.get('digest'):
            prompt += (
                f"Story Context:\n{context['digest'].get('content', '')}\n\n"
                "Use this context to:\n"
                "- Advance story arcs naturally\n"
                "- Show character growth\n"
                "- React to ongoing situations\n"
                "While maintaining an authentic social media voice\n\n"
            )
                
        # Recent Activity
        if context['recent_tweets']:
            prompt += f"Recent tweets:\n{json.dumps(context['recent_tweets'], indent=2)}\n\n"
                
        if context['recent_comments']:
            prompt += f"Recent interactions:\n{json.dumps(context['recent_comments'], indent=2)}\n\n"

        # Tweet Guidelines
        prompt += (
            "Tweet Requirements:\n"
            "1. First-person perspective, entertaining and relatable\n"
            "2. Use natural humor, curiosity, or irony when fitting\n"
            "3. Length: Usually 384-640 chars, occasionally 16-1028 based on content weight\n"
            "4. Format: Start with '[{current_year} | Age {xavier_age}]'\n"
            "5. Style: Authentic social media voice, hashtags only if meaningful\n\n"
            "Tweet:"
        )
        return prompt

    def should_update_digest(self, context):
        """Determine if digest needs updating based on tweet counts and content"""
        try:
            existing_digest = context['digest']
            recent_tweets = context['recent_tweets']
            
            # Check if we have an existing digest
            if not existing_digest or not existing_digest.get('content'):
                return True
                
            # Get last processed tweet count
            last_processed_count = existing_digest.get('last_tweet_count', 0)
            current_count = context['tweet_count']
            
            # Always update for first few tweets to establish story
            if current_count < 5:
                return True
                
            # Update digest every ~12 tweets (about 1.5 months in story time)
            if current_count - last_processed_count >= 12:
                return True
                
            # Check for significant events since last digest
            significant_events = 0
            for tweet in recent_tweets:
                content = tweet['content'].lower()
                if any(marker in content for marker in [
                    'decided to', 'realized', 'started', 'finished',
                    'met with', 'moving to', 'leaving', 'joined',
                    'launched', 'created', 'ended', 'beginning'
                ]):
                    significant_events += 1
                    
            # Update if we have enough significant events
            if significant_events >= 3:
                return True
                
            return False
            
        except Exception as e:
            print(f"Error checking digest update criteria: {e}")
            return True  # Default to updating on error

    def should_update_tech_evolution(self, context):
        """Determine if tech evolution needs updating"""
        try:
            tech_evolution = context.get('tech_evolution', {}).get('tech_trees', {})
            tweet_count = context['tweet_count']
            
            # Get the latest epoch we have tech for
            if not tech_evolution:
                return True  # Generate first epoch if no tech exists
                
            # Calculate tweets per epoch (5 years)
            tweets_per_epoch = self.tweets_per_year * 5  # 96 * 5 = 480 tweets per epoch
            
            # Calculate which epoch we're in
            current_epoch_index = tweet_count // tweets_per_epoch
            tweets_into_epoch = tweet_count % tweets_per_epoch
            
            # Generate next epoch when we're 60 tweets (~9 months) away from it
            tweets_until_next_epoch = tweets_per_epoch - tweets_into_epoch
            
            if tweets_until_next_epoch <= 60:  # About 9 months before next epoch
                next_epoch = self.sim_start_year + ((current_epoch_index + 1) * 5)
                print(f"Approaching new tech epoch: {next_epoch}")
                print(f"Tweets until next epoch: {tweets_until_next_epoch}")
                return True
                
            return False
            
        except Exception as e:
            print(f"Error checking tech evolution criteria: {e}")
            return True

    def generate_tweet(self):
        """Generate a new tweet"""
        try:
            # Get current context
            context = self.get_context()
            if not context:
                return None
                
            # Check if tech evolution needs updating
            if self.should_update_tech_evolution(context):
                from src.generation.tech_evolution_generator import TechEvolutionGenerator
                tech_gen = TechEvolutionGenerator()
                next_epoch = max([int(year) for year in context['tech_evolution']['tech_trees'].keys()]) + 5
                
                print(f"Generating tech evolution for epoch {next_epoch}")
                tree_data = tech_gen.generate_epoch_tech_tree(next_epoch)
                
                if tree_data:
                    tech_gen.evolution_data['tech_trees'][str(next_epoch)] = tree_data
                    tech_gen.save_evolution_data()
                    # Refresh context with new tech data
                    context = self.get_context()
                
            # Continue with digest and tweet generation
            if self.should_update_digest(context):
                updated_digest = self.digest_generator.process_ongoing_digest(
                    context['digest'],
                    context['recent_tweets'],
                    context['recent_comments']
                )
                
                if updated_digest:
                    # Add tweet count to digest metadata
                    updated_digest['last_tweet_count'] = context['tweet_count']
                    
                    self.github_ops.update_story_digest(
                        new_tweets=context['recent_tweets'],
                        new_comments=context['recent_comments'],
                        initial_content=updated_digest
                    )
                    print(f"Updated digest at tweet #{context['tweet_count']}")
                    # Refresh context with new digest
                    context = self.get_context()
                
            prompt = self.create_tweet_prompt(context)
            
            try:
                message = self.client.messages.create(
                    model="grok-beta",
                    max_tokens=512,
                    system="You are Xavier, a young adult navigating life. Generate a single tweet that continues your story naturally.",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                )
                
                tweet_content = str(message.content)
                
                tweet = {
                    "id": f"tweet_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "content": tweet_content,
                    "timestamp": datetime.now().isoformat(),
                    "likes": 0,
                    "retweets": 0
                }
                
                # Store tweet and update state
                self.update_simulation_state(tweet)
                print(f"Generated tweet #{context['tweet_count'] + 1}")
                return tweet
                    
            except Exception as e:
                print(f"Error generating tweet: {str(e)}")
                return None
        except Exception as e:
            print(f"Error generating tweet: {str(e)}")
            return None

def main():
    generator = TweetGenerator()
    
    while True:
        # Check simulation state
        state, _ = generator.get_simulation_state()
        current_year = state.get("current_year", 2025)
        
        if current_year >= 2075:  # Xavier would be 72 years old (started at 22 in 2025)
            print("Xavier has reached 72 years old. His story is complete!")
            return
            
        # Generate tweet if under age limit
        tweet = generator.generate_tweet()
        if tweet:
            print("Generated tweet:")
            print(json.dumps(tweet, indent=2))
        else:
            print("No tweet generated this time")
            break  # Exit if tweet generation fails

if __name__ == "__main__":
    main()
