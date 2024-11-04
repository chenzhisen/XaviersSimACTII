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
        xavier_age = current_year - self.sim_start_year + 22  # Xavier starts at age 22 in 2025

        # Special handling for the first tweet
        if tweet_count == 0:
            prompt = (
                "Generate Xavier's first tweet as he transitions between Japan and New York. IMPORTANT:\n"
                "- The tweet MUST be set in either:\n"
                "  a) New York City, having just returned from his transformative trip to Japan\n"
                "  b) His last moments in Japan before returning to New York\n"
                "- If in New York: Focus on his reflections about Japan and how it's influenced his perspective\n"
                "- If in Japan: Focus on his final experiences and thoughts about returning home\n"
                "- Include specific location details (e.g., specific neighborhoods, stations, or landmarks)\n"
                "- Show his emotional state about this transition period\n"
                "- Maintain Xavier's characteristic wit and observational humor\n"
                "- Reference his tech/crypto background subtly if relevant\n\n"
                "Remember: This tweet sets up his character as someone deeply impacted by his time in Japan, "
                "and hints at how this experience will influence his future decisions.\n\n"
            )
        else:
            prompt = ""

        # Calculate progress through the current year (0.0 to 1.0)
        year_progress = (tweet_count % self.tweets_per_year) / self.tweets_per_year
        month_estimate = int(year_progress * 12) + 1  # 1-12

        prompt += (
            f"Xavier's story so far:\n"
            f"Current Timeline: {current_year} (around month {month_estimate})\n"
            f"Xavier's Age: {xavier_age}\n\n"
            "IMPORTANT: Focus on Xavier's personal experiences, quirks, and emotional reflections. "
            "Xavier is a New York native with a quick wit and playful curiosity, but he is also a real person who experiences the ups and downs of life. "
            "Capture a range of emotions in his tweets, from lighthearted humor to deeper reflections, sometimes nostalgic, sometimes upbeat, and sometimes introspective. "
            "Include $XVI only occasionally and indirectly, treating it as a subtle part of his digital life, and avoid mentions of wallets or specific transaction details.\n\n"
            
            "Examples of Xavier’s humor and realism:\n"
            "1. Playfully wondering about quirky details, like celebrity trends or tech culture\n"
            "2. Using irony to point out the absurdities of futuristic or tech-dominated situations\n"
            "3. Sharing personal insights on life’s ups and downs, often with a humorous twist or wry observation\n\n"
            
            "Please consider Xavier's age and life phase:\n"
            "1. **20s** (self-discovery, career-building, social observations): Xavier is curious, open-minded, and enthusiastic about tech and crypto.\n"
            "2. **30s** (relationships, societal observations, personal growth): His interests broaden, with deeper reflections on relationships and technology's impact on society.\n"
            "3. **40s+** (legacy, social impact, nostalgia): His tweets should include more thoughtful, introspective reflections on legacy, society, and the role of technology in a changing world.\n\n"
            
            "Use humor, curiosity, or irony when natural to make the tweet feel engaging and relatable. "
            "Encourage reflections on how technology is reshaping societal norms, relationships, and daily life in subtle ways. "
            "Structure tweets to feel natural, ranging from short one-liners to longer reflections between 16-1028 characters.\n\n"
            
            "Ensure the tweets develop a coherent story arc over time, following Xavier’s personal and professional journey. "
            "Each tweet should build on past experiences or interactions to provide a sense of continuity and growth in his life story.\n\n"
        )
        
        # Provide a summary of the current technological background
        tech_evolution = context['tech_evolution']
        if tech_evolution and tech_evolution.get('tech_trees'):
            epochs = [int(epoch) for epoch in tech_evolution['tech_trees'].keys()]
            nearest_epoch = min(epochs, key=lambda x: abs(x - current_year), default=None)
            
            if nearest_epoch:
                epoch_data = tech_evolution['tech_trees'][str(nearest_epoch)]
                prompt += (
                    f"Technological Context (as of {nearest_epoch}): Technologies influencing daily life include:\n"
                    f"{json.dumps([tech['name'] for tech in epoch_data['mainstream_technologies']], indent=2)}\n\n"
                )

        # Story Digest and Recent Events
        prompt += f"Story Digest:\n{json.dumps(context['digest'], indent=2)}\n\n"
                
        if context['recent_tweets']:
            prompt += f"Recent tweets:\n{json.dumps(context['recent_tweets'], indent=2)}\n\n"
                
        if context['recent_comments']:
            prompt += f"Recent interactions:\n{json.dumps(context['recent_comments'], indent=2)}\n\n"
            
        prompt += (
            "Generate a tweet continuing Xavier's story. The tweet should:\n"
            "1. Be written in first person as Xavier, with a tone that is entertaining, personal, and relatable\n"
            "2. Vary in tone—sometimes upbeat, sometimes reflective, but always engaging\n"
            "3. Use humor, curiosity, or irony when natural, even as he reflects on life’s highs and lows\n"
            "4. Mention specific technology only if it impacts his perspective or interactions in a natural way\n"
            "5. Mention $XVI occasionally as a digital asset in his reflections on crypto, avoiding mentions of wallets or specific transactions\n"
            "6. Be between 16-1028 characters, from short one-liners to more detailed reflections\n"
            "7. Start with '[{current_year} | Age {xavier_age}]' to mark the timeline\n"
            "8. Avoid hashtags unless they add to the humor or context\n\n"
            "Tweet:"
        )
        print(prompt)
        return prompt

    def generate_tweet(self):
        """Generate a new tweet"""
        if not self.should_generate_tweet():
            print("Simulation is complete, no more tweets")
            return None
        
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
        
        # Get existing tweets and comments
        tweets, _ = self.github_ops.get_file_content("ongoing_tweets.json")
        comments, _ = self.github_ops.get_file_content("comments.json")
        existing_digest, digest_sha = self.github_ops.get_file_content("digest.json")
        
        if not existing_digest or not existing_digest.get('content'):
            # For first tweet, create initial digest from XaviersSim.json
            print("Creating initial digest from XaviersSim.json")
            initial_digest = self.digest_generator.process_digest()
            if initial_digest:
                self.github_ops.update_story_digest(
                    new_tweets=[],
                    new_comments=[],
                    initial_content=initial_digest
                )
        else:
            # For subsequent tweets, update digest with recent content
            recent_tweets = tweets[-5:] if tweets else []
            recent_comments = [
                c for c in comments 
                if any(t['id'] in c.get('tweet_id', '') for t in recent_tweets)
            ]
            
            updated_digest = self.digest_generator.process_ongoing_digest(
                existing_digest,
                recent_tweets,
                recent_comments
            )
            
            if updated_digest:
                self.github_ops.update_story_digest(
                    new_tweets=recent_tweets,
                    new_comments=recent_comments,
                    initial_content=updated_digest
                )
                print("Updated digest with recent content")
            
        # Now get context with updated digest for tweet generation
        context = self.get_context()
        if not context:
            return None
        
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
