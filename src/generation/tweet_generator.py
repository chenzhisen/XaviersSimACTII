import json
from datetime import datetime
from anthropic import Anthropic
from utils.config import Config, AIProvider
from storage.github_operations import GithubOperations
from generation.digest_generator import DigestGenerator
import re
import random

class TweetGenerator:
    def __init__(self, tweets_per_year=96):
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )
        self.github_ops = GithubOperations()
        self.digest_generator = DigestGenerator()
        
        # Simulation parameters
        self.sim_start_year = 2025
        self.tweets_per_year = tweets_per_year
        
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
            if file_path == "digest_history.json":
                initial_content = []  # Always initialize digest history as an empty array
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
            self.initialize_file("digest_history.json", [])
            self.initialize_file("simulation_state.json", {
                "last_tweet_timestamp": None,
                "tweet_count": 0,
                "current_year": self.sim_start_year,
                "is_complete": False
            })
                
            # Initialize tech_evolution.json with first epoch if it doesn't exist
            tech_evolution, _ = self.github_ops.get_file_content("tech_evolution.json")
            if not tech_evolution or not tech_evolution.get('tech_trees'):
                print("Initializing first tech epoch...")
                from src.generation.tech_evolution_generator import TechEvolutionGenerator
                tech_gen = TechEvolutionGenerator()
                
                # Add debug logging
                print("Generating first epoch...")
                first_epoch = tech_gen.generate_epoch_tech_tree(self.sim_start_year)
                
                # Validate the response
                if isinstance(first_epoch, dict) and all(k in first_epoch for k in ['mainstream_technologies', 'emerging_technologies', 'epoch_themes']):
                    tech_evolution = {
                        "metadata": {
                            "generated_at": datetime.now().isoformat(),
                            "base_year": self.sim_start_year,
                            "end_year": 2075
                        },
                        "tech_trees": {
                            str(self.sim_start_year): first_epoch
                        }
                    }
                    self.github_ops.update_file(
                        file_path="tech_evolution.json",
                        content=tech_evolution,
                        commit_message=f"Initialize tech evolution with first epoch"
                    )
                else:
                    print(f"Invalid first epoch format: {first_epoch}")
                    raise Exception("Failed to generate valid first tech epoch")
            
            # Calculate how many recent tweets to include
            recent_tweet_count = max(3, self.tweets_per_year // 20)  # At least 3
            
            # Now get all existing tweets to calculate current year
            try:
                ongoing_tweets, _ = self.github_ops.get_file_content("ongoing_tweets.json")
                if not isinstance(ongoing_tweets, list):
                    ongoing_tweets = []
                tweet_count = len(ongoing_tweets)
                recent_tweets = ongoing_tweets[-recent_tweet_count:] if ongoing_tweets else []
                
                # For the first few tweets, include ACTI's final tweets in context
                if tweet_count < recent_tweet_count:  # First few tweets
                    try:
                        acti_tweets, _ = self.github_ops.get_file_content("last_acti_tweets.json")
                        if not isinstance(acti_tweets, list):
                            acti_tweets = []
                        # Add the last few ACTI tweets to recent_tweets
                        acti_count = recent_tweet_count - tweet_count
                        recent_tweets = acti_tweets[-acti_count:] + recent_tweets
                    except Exception as e:
                        print(f"Error getting ACTI tweets: {e}")
                    
                # Similarly scale recent comments
                recent_comment_count = max(2, self.tweets_per_year // 32)  # At least 2 comments
                try:
                    comments, _ = self.github_ops.get_file_content("comments.json")
                    if not isinstance(comments, list):
                        comments = []
                    recent_comments = comments[-recent_comment_count:] if comments else []
                except Exception as e:
                    print(f"Error getting comments: {e}")
                    recent_comments = []

            except Exception as e:
                print(f"Error getting tweets: {e}")
                ongoing_tweets = []
                tweet_count = 0
                recent_tweets = []
                recent_comments = []
            
            # Calculate current year based on tweet count
            current_year = self.calculate_current_year(tweet_count)
            
            # Get the digest history
            try:
                digest_history, _ = self.github_ops.get_file_content("digest_history.json")
                if not isinstance(digest_history, list):
                    digest_history = []
                current_digest = digest_history[-1] if digest_history else {}
            except Exception as e:
                print(f"Error getting digest history: {e}")
                current_digest = {}
            
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
                "digest": current_digest,  # Just the most recent digest
                "recent_tweets": recent_tweets,
                "recent_comments": recent_comments,
                "tech_evolution": tech_evolution
            }
        except Exception as e:
            print(f"Error gathering context: {str(e)}")
            print(f"Full error details: {type(e).__name__}: {str(e)}")
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
        current_year = context['current_year']
        tweet_count = context['tweet_count']
        xavier_age = current_year - self.sim_start_year + 22
        month_estimate = (tweet_count % self.tweets_per_year) // 8 + 1
                # Calculate time progression
        months_per_tweet = 12 / self.tweets_per_year  # e.g., 12/96 = 0.125 months per tweet
        current_month = (tweet_count % self.tweets_per_year) * months_per_tweet
        next_month = current_month + months_per_tweet

        # Check if it's birthday time (around tweet 48 of each year - June-ish)
        is_birthday_time = (tweet_count % self.tweets_per_year) in range(1, 2)
                
        tone_options = [
            ("Humorous", 10), ("Straightforward", 10), ("Reflective", 10), ("Inquisitive", 10),
            ("Inspirational", 8), ("Critical", 8), ("Excited", 8), ("Philosophical", 8),
            ("Analytical", 5), ("Encouraging", 5), ("Cautious", 5), ("Storytelling", 5),
            ("Surprised", 4), ("Nostalgic", 4), ("Visionary", 4),
            ("Reflective with a hint of self-awareness", 1), ("Frustrated", 2), ("Melancholic", 2), 
            ("Pensive", 3), ("Hopeful", 3)
        ]
        tone_descriptions = {
            "Humorous": "Playful and light, using tech puns, ironic observations, or self-deprecating humor about developer life.",
            "Straightforward": "Direct and clear, sharing insights without embellishment or extra commentary.",
            "Reflective": "Personal and introspective, offering insights, lessons learned, or thoughtful reflections on technology and life.",
            "Inquisitive": "Posing questions or expressing curiosity, exploring tech’s impact or future potential (without clichés).",
            "Inspirational": "Encouraging and positive, emphasizing growth, progress, or the potential for technology to improve lives.",
            "Critical": "Analytical with a critical eye, questioning certain tech trends, tools, or social impacts of innovation.",
            "Excited": "High-energy and enthusiastic, sharing a new idea, discovery, or tech breakthrough with palpable excitement.",
            "Philosophical": "Deep and thought-provoking, discussing ethical implications, societal changes, or big-picture ideas around technology.",
            "Analytical": "Objective and detail-focused, diving into technical aspects, weighing pros and cons, or breaking down complex ideas.",
            "Encouraging": "Supportive and motivational, aimed at the tech community, offering advice or encouragement to peers.",
            "Cautious": "Slightly reserved, weighing potential downsides or risks, acknowledging complexities without rushing to conclusions.",
            "Storytelling": "Narrative-driven, telling a short, engaging story or anecdote from Xavier’s experiences in a relatable, conversational way.",
            "Surprised": "Playfully astonished or caught off guard by a tech discovery or unexpected development, conveying genuine surprise.",
            "Nostalgic": "Reflecting on past experiences or early days in tech, with a hint of nostalgia for 'simpler' or different times.",
            "Visionary": "Futuristic and imaginative, describing possible developments or ideas in an idealized, forward-looking manner.",
            "Reflective with a hint of self-awareness": "Noticing odd patterns or feeling like he's part of a larger scheme, but quickly letting it go.",
            "Frustrated": "Feeling challenged by obstacles or setbacks in tech or personal projects, showing a moment of struggle.",
            "Melancholic": "Quiet and introspective, reflecting on tech’s limitations or the more somber aspects of progress.",
            "Pensive": "Thoughtful and contemplative, considering complex ideas or personal purpose in a reflective tone.",
            "Hopeful": "Finding optimism in progress or potential solutions, even amid challenges."
        }

        tones, weights = zip(*tone_options)
        current_tone = random.choices(tones, weights=weights, k=1)[0]
        prompt = (
            f"Timeline: {current_year}\n"
            f"Current Month: {current_month:.1f} (progressing to {next_month:.1f})\n"
            f"Xavier's Age: {xavier_age}\n\n"
            f"Tone for this tweet: **{current_tone}** - {tone_descriptions[current_tone]}\n\n"
            
            # Dynamic Tone Selection
            f"Tone for this tweet: **{current_tone}**\n"
            "Tone Options:\n"
            "- **Humorous**: Playful and light, using tech puns, ironic observations, or self-deprecating humor about developer life.\n"
            "- **Straightforward**: Direct and to the point, focusing on sharing technical insights or updates without embellishment.\n"
            "- **Reflective**: Personal and introspective, offering insights, lessons learned, or thoughtful reflections on technology and life.\n"
            "- **Inquisitive**: Posing questions or expressing curiosity, exploring tech’s impact or future potential (avoid clichés).\n"
            "- **Inspirational**: Encouraging and positive, emphasizing growth, progress, or the potential for technology to improve lives.\n"
            "- **Critical**: Analytical with a critical eye, questioning certain tech trends, tools, or social impacts of innovation.\n"
            "- **Excited**: High-energy, enthusiastic tone, sharing a new idea, discovery, or tech breakthrough with palpable excitement.\n"
            "- **Philosophical**: Deep and thought-provoking, discussing ethical implications, societal changes, or big-picture ideas around technology.\n"
            "- **Analytical**: Objective and detail-focused, diving into technical aspects, weighing pros and cons, or breaking down complex ideas.\n"
            "- **Encouraging**: Supportive and motivational, aimed at the tech community, offering advice or encouragement to peers.\n"
            "- **Cautious**: Slightly reserved, weighing potential downsides or risks, acknowledging complexities without rushing to conclusions.\n"
            "- **Storytelling**: Narrative-driven, telling a short, engaging story or anecdote from Xavier’s experiences in a relatable, conversational way.\n"
            "- **Surprised**: Playfully astonished or caught off guard by a tech discovery or unexpected development, conveying genuine surprise.\n"
            "- **Nostalgic**: Reflecting on past experiences or early days in tech, with a hint of nostalgia for “simpler” or different times.\n"
            "- **Visionary**: Futuristic and imaginative, describing possible developments or ideas in an idealized, forward-looking manner.\n"
            "- **Reflective with a hint of self-awareness**: Occasionally feels like he’s part of something scripted, noticing odd coincidences or familiar patterns, but quickly lets it go.\n\n"  
            
            "XAVIER'S VOICE:\n"
            "Core Identity:\n"
            "- Blockchain optimist with a pragmatic, creative mindset\n"
            "- Technical expert with a creative mindset\n"
            "- Sees blockchain potential in everyday scenarios\n"
            "- Values both innovation and accessibility\n"
            "- Bridges technical and social impact\n"
            "- Occasionally wonders if he’s part of a larger scheme but dismisses it quickly.\n"
            "- Shows curiosity through actions over questions\n\n"
                        
            "Content Mix (choose ONE focus per tweet):\n"

            "20% Blockchain/Web3:\n"
            "- Technical insights on decentralization and governance\n"
            "- Breakthroughs in smart contract applications\n"
            "- Reflections on privacy, ethics, and tech sovereignty\n"
            "- Novel blockchain use cases in society and economy\n"
            "- Integration of blockchain with AI, biotech, or space tech\n\n"

            "15% General Tech/Coding:\n"
            "- Programming challenges and breakthrough solutions\n"
            "- System architecture ideas, scalability reflections\n"
            "- Musings on the future of open-source and decentralized dev tools\n"
            "- AI, automation, and tech’s impact on human life\n"
            "- Tech and creativity: code as a form of expression\n"
            "- Occasionally reference relevant real-world tech companies or figures to provide context, but do so sparingly. Aim to keep mentions organic and purposeful.\n\n"

            "10% Cultural Exploration & Social Reflection:\n"
            "- Observations from global travel and cultural immersion\n"
            "- Reflections on global social issues from a tech perspective\n"
            "- Moments of understanding and respect for other cultures\n"
            "- Insights from observing non-tech worlds, such as art or literature\n\n"

            "15% Community & Relationships:\n"
            "- Building mentorships and nurturing emerging talents\n"
            "- Reflections on leading and supporting collaborative teams\n"
            "- Insights into building digital and in-person communities\n"
            "- Stories of friendship, camaraderie, and mutual growth\n"
            "- Musings on human connection in a digital age\n\n"

            "15% Personal Growth & Family:\n"
            f"Life Stage ({xavier_age} years old):\n"
            f"{self.digest_generator._get_life_phase(xavier_age)}\n"
            "- Personal reflections on growth, purpose, and values\n"
            "- Moments with family, generational lessons\n"
            "- Navigating life transitions and evolving priorities\n"
            "- Parenting or mentoring stories, where applicable\n"
            "- Thoughts on balancing work with family and life\n\n"

            "10% Philosophy, Ethics, and Social Impact:\n"
            "- Reflections on tech’s broader societal implications\n"
            "- Ethical dilemmas in AI, data privacy, and blockchain\n"
            "- Musings on personal responsibility in tech development\n"
            "- Observations on social change and technology’s role\n\n"

            "10% Hobbies, Travel, and Leisure:\n"
            "- Insights and experiences from travel adventures\n"
            "- Reflections on art, film, music, and other passions\n"
            "- Personal projects outside of tech (e.g., writing, fitness)\n"
            "- Sharing moments of mindfulness, nature, and unwinding\n\n"

            "5% Creative & Introspective Musings:\n"
            "- Exploring analogies that blend nature, art, and technology\n"
            "- Creative reflections: what-if scenarios and futuristic musings\n"
            "- Nostalgic memories from early life, family, or formative experiences\n"
            "- Uncommon, poetic, or philosophical reflections\n\n"
            

            "Additional Themes:\n"
            "- Fusion of disciplines: art meets tech, science meets philosophy\n"
            "- Moments of joy, curiosity, or humor in daily life\n"
            "- Recollections of seemingly small yet impactful moments\n"
            
            "Humor Style:\n"
            "- Clever tech wordplay and puns\n"
            "- Unexpected parallels between tech and daily life\n"
            "- Relatable developer moments\n"
            "- Self-aware tech observations\n"
            "- Finding humor in coding challenges\n"
            "- Playful takes on tech culture\n"
            
            "Humor Guidelines:\n"
            "- Keep it smart but accessible\n"
            "- Mix technical wit with universal experiences\n"
            "- Let humor emerge from situations naturally\n"
            "- Stay positive and playful\n"
            "- Make complex concepts entertaining\n"
            "- Find the fun in the technical\n"
            
            "Avoid:\n"
            "- Crypto bro language\n"
            "- Price/investment focus\n"
            "- Overused tech jokes\n"
            "- Preaching about blockchain\n"
            "- Generic observations\n"
            "- Open-ended philosophical questions\n"
            "- Abstract 'what if' scenarios\n"
            "- Generic 'how can we' queries\n"
            "- Rhetorical questions about the future\n"
            "- ANY time references (months, seasons, weather, etc)\n"
            "- Location references except when story-critical\n\n"
            
            "Tweet Requirements:\n"
            f"1. Advance timeline to month {next_month:.1f} (avoid mentioning month directly):\n"
            "- Show project and relationship progress; align with context\n\n"
            "- Never go backwards in time\n\n"
            "- Show clear forward movement\n"
            "- Reference only current or past events\n\n"
            "- Create fresh ways to start tweets\n"
            "- Don't repeat themes from recent tweets\n"
            "- Avoid continuing metaphors from previous tweets\n"
            "- Create fresh analogies each time\n"
            "- If family is mentioned, vary which family members and contexts\n"
            "- Don't build running jokes across tweets\n\n"
            
            "2. Add fresh content fitting the timeline:\n"
            "- Include new developments and events\n\n"
            "- Avoid referencing previous tweet's content\n"
            "- Each tweet should stand alone\n"
            "- Don't reuse metaphors (no repeated food/cooking analogies)\n"
            "- Vary your technical examples\n\n"
            
            "3. Voice & Style Guidelines:\n"
            "- **Tone:** Write as a real tech professional—casual and direct, with room for variation. Some tweets should be straightforward, while others can be more expressive or reflective.\n"
            "- **Language:** Use natural tech terminology without forced metaphors or flowery language. When using analogies, keep them relevant and occasionally add creative twists that surprise or engage readers.\n"
            "- **Clarity & Flow:** Avoid overused phrases (“Just,” “So”), skip formulaic openings, and write as if speaking to peers. Connect ideas organically and keep it conversational, avoiding poetic or overly complex expressions.\n"
            "- **Content Variety:**\n"
            "   - Don’t repeat themes, vocabulary, or patterns from recent tweets.\n"
            "   - Balance technical depth with human insights; include vivid details that make tweets memorable.\n\n"
            
            "4. Endings:\n"
            "- **Primary (70%)**: Conclude with insights, realizations, project milestones, or forward-looking statements.\n"
            "- **Questions (optional, <10%)**: Use unique phrasing if questions are included; avoid “How can we…” or generic questions.\n"
            "- **Other (20%)**: Add variety with witty observations, clever wordplay, or thoughtful analogies.\n\n"
            
            "5. Stylistic Guidelines:\n"
            "- NO hashtags.\n"
            "- Limit @ mentions to known tech figures or celebs only when highly relevant.\n"
            "- Vary tweet lengths, aiming for 384-640 characters on average, but allow occasional shorter or longer tweets (16-1024 characters).\n"
            "- Share real experiences, insights, and relatable moments as a developer. Be authentic and direct—sound like yourself, not a script.\n"
            "- Each tweet should advance the story with a fresh perspective, and maintain an engaging, professional, and personable voice.\n\n"

            "6. NO $XVI token or $XVI Foundation mentions unless significant; omit 95% of the time\n\n"
            
            "Tweet: "
        )

        # Special birthday guidance
        if is_birthday_time:
            prompt += (
                f"\nBirthday Context:\n"
                f"Xavier is turning {xavier_age}. Consider:\n"
                "- Reflective or forward-looking thoughts on aging\n"
                "- Personal goals or gratitude\n"
                "- Keep it natural and relatable\n\n"
            )

        # Add story context
        if context.get('digest'):
            prompt += (
                f"Story Context:\n{context['digest'].get('content', '')}\n\n"
                "Use this context to:\n"
                "- Advance story arcs and show growth\n"
                "- Occasionally incorporate subtle hints of self-awareness but do not dwell on it\n"
                "- Respond to ongoing events authentically\n"
            )

        # Include recent activity
        if context['recent_tweets']:
            prompt += f"Recent tweets for context (DO NOT repeat their themes or metaphors):\n{json.dumps(context['recent_tweets'], indent=2)}\n\n"
        if context['recent_comments']:
            prompt += f"Recent interactions:\n{json.dumps(context['recent_comments'], indent=2)}\n\n"

        # First tweet setup
        if context['tweet_count'] == 0:
            prompt += (
                "Generate Xavier's first tweet about the transition from Japan to NYC:\n"
                "- Set in either final moments in Japan or first in NYC\n"
                "- Reflect on the influence of Japan on his perspective\n\n"
            )

        print(prompt)
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
            last_processed_count = existing_digest.get('tweet_count', 0)
            current_count = context['tweet_count']
            
            # Always update for first few tweets to establish story
            if current_count < self.tweets_per_year * 0.05:  # First 5% of yearly tweets
                return True
                
            # Update digest every ~12.5% of yearly tweets (about 1.5 months in story time)
            tweets_per_digest = max(1, self.tweets_per_year // 8)  # At least 1 tweet between digests
            if current_count - last_processed_count >= tweets_per_digest:
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
                    
            # Update if we have enough significant events (scaled to tweet frequency)
            significant_threshold = max(2, self.tweets_per_year // 32)  # At least 2 events
            if significant_events >= significant_threshold:
                return True
                
            return False
            
        except Exception as e:
            print(f"Error checking digest update criteria: {e}")
            return True  # Default to updating on error

    def should_update_tech_evolution(self, context):
        """Determine if tech evolution needs updating"""
        try:
            tech_trees = context.get('tech_evolution', {}).get('tech_trees', {})
            tweet_count = context['tweet_count']
            
            # Get the latest epoch we have tech for
            if not tech_trees:
                return True  # Generate first epoch if no tech exists
                
            # Calculate tweets per epoch (5 years)
            tweets_per_epoch = self.tweets_per_year * 5  # 96 * 5 = 480 tweets per epoch
            
            # Calculate which epoch we're in
            current_epoch_index = tweet_count // tweets_per_epoch
            next_epoch_year = self.sim_start_year + ((current_epoch_index + 1) * 5)
            
            # Check if we already have the next epoch
            if str(next_epoch_year) in tech_trees:
                return False
                
            # Generate next epoch when we're 60 tweets (~9 months) away from it
            tweets_into_epoch = tweet_count % tweets_per_epoch
            tweets_until_next_epoch = tweets_per_epoch - tweets_into_epoch
            
            return tweets_until_next_epoch <= self.tweets_per_year * 60 / 96  # About 9 months before next epoch
            
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
                
            # Calculate Xavier's age
            current_year = context['current_year']
            xavier_age = current_year - self.sim_start_year + 22
            
            # Add year and age prefix to tweet content
            year_prefix = f"[{current_year} | Age {xavier_age}] "
            
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
            
            # Check if digest needs updating
            if self.should_update_digest(context):
                # Get existing digest history
                digest_history, _ = self.github_ops.get_file_content("digest_history.json")
                if not isinstance(digest_history, list):
                    digest_history = []
                
                # Generate appropriate digest based on whether it's first or ongoing
                if not digest_history:
                    print("Generating first digest...")
                    new_digest = self.digest_generator.process_first_digest()
                else:
                    print("Generating ongoing digest...")
                    new_digest = self.digest_generator.process_ongoing_digest(
                        context['digest'],
                        context['recent_tweets'],
                        context['recent_comments']
                    )
                
                if new_digest:
                    # Add tweet count to digest metadata
                    new_digest['tweet_count'] = context['tweet_count']
                    
                    # Update digest history
                    self.github_ops.update_story_digest(
                        new_tweets=context['recent_tweets'],
                        new_comments=context['recent_comments'],
                        initial_content=new_digest
                    )
                    print(f"Updated digest at tweet #{context['tweet_count']}")
                    # Refresh context with new digest
                    context = self.get_context()
                
            prompt = self.create_tweet_prompt(context)
            
            try:
                message = self.client.messages.create(
                    model="grok-beta",
                    max_tokens=1024,
                    system=(
                        "You are Xavier, a tech visionary with a quick wit and playful curiosity. "
                        "Generate a single tweet that continues your story naturally, showing both your passion "
                        "for technology and your human side."
                        "Respond with ONLY the tweet content - no preamble, no quotes, no explanations. "
                        "Your response should be exactly what would appear in the tweet, nothing more."

                    ),
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                )
                
                tweet_content = str(message.content)
                
                # Clean the content
                tweet_content = tweet_content.replace("[TextBlock(text='", "")
                tweet_content.replace("', type='text')]", "")
                tweet_content = tweet_content.strip('"')  # Remove surrounding quotes
                
                # Remove any hashtags and clean up spacing
                tweet_content = re.sub(r'\s*#\w+\s*', ' ', tweet_content).strip()

                tweet = {
                    "id": f"tweet_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "content": year_prefix + tweet_content,  # Add prefix here
                    "timestamp": datetime.now().isoformat(),
                    "likes": 0,
                    "retweets": 0
                }
                
                self.update_simulation_state(tweet)
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

