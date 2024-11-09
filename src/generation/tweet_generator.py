import json
from datetime import datetime, timedelta
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
        
        self.tone_options = [
            ("Humorous", 10), ("Straightforward", 10), ("Reflective", 10), ("Inquisitive", 10),
            ("Inspirational", 8), ("Critical", 8), ("Excited", 8), ("Philosophical", 8),
            ("Analytical", 5), ("Encouraging", 5), ("Cautious", 5), ("Storytelling", 5),
            ("Surprised", 4), ("Nostalgic", 4), ("Visionary", 4),
            ("Meta-Aware", 1), ("Frustrated", 2), ("Melancholic", 2), 
            ("Pensive", 3), ("Hopeful", 3),
            ("Playful", 5), ("Earnest", 4), ("Curious", 6), ("Determined", 4), ("Warm", 5)
        ]

        # Updated tone descriptions with new additions
        self.tone_descriptions = {
            "Humorous": "Playful and light, using tech puns, ironic observations, or self-deprecating humor about developer life.",
            "Straightforward": "Direct and clear, sharing insights without embellishment or extra commentary.",
            "Reflective": "Personal and introspective, offering insights, lessons learned, or thoughtful reflections on technology and life.",
            "Inquisitive": "Posing questions or expressing curiosity, exploring tech's impact or future potential (without clichés).",
            "Inspirational": "Encouraging and positive, emphasizing growth, progress, or the potential for technology to improve lives.",
            "Critical": "Analytical with a critical eye, questioning certain tech trends, tools, or social impacts of innovation.",
            "Excited": "High-energy and enthusiastic, sharing a new idea, discovery, or tech breakthrough with palpable excitement.",
            "Philosophical": "Deep and thought-provoking, discussing ethical implications, societal changes, or big-picture ideas around technology.",
            "Analytical": "Objective and detail-focused, diving into technical aspects, weighing pros and cons, or breaking down complex ideas.",
            "Encouraging": "Supportive and motivational, aimed at the tech community, offering advice or encouragement to peers.",
            "Cautious": "Slightly reserved, weighing potential downsides or risks, acknowledging complexities without rushing to conclusions.",
            "Storytelling": "Narrative-driven, telling a short, engaging story or anecdote from Xavier's experiences in a relatable, conversational way.",
            "Surprised": "Playfully astonished or caught off guard by a tech discovery or unexpected development, conveying genuine surprise.",
            "Nostalgic": "Reflecting on past experiences or early days in tech, with a hint of nostalgia for 'simpler' or different times.",
            "Visionary": "Futuristic and imaginative, describing possible developments or ideas in an idealized, forward-looking manner.",
            "Meta-Aware": "Momentarily sensing patterns in his life that seem too perfect, or wondering about the nature of his reality, before returning to his usual perspective.",
            "Frustrated": "Feeling challenged by obstacles or setbacks in tech or personal projects, showing a moment of struggle.",
            "Melancholic": "Quiet and introspective, reflecting on tech's limitations or the more somber aspects of progress.",
            "Pensive": "Thoughtful and contemplative, considering complex ideas or personal purpose in a reflective tone.",
            "Hopeful": "Finding optimism in progress or potential solutions, even amid challenges.",
            "Playful": "Light and casual, bringing out a fun or whimsical side to technology and exploration.",
            "Earnest": "Sincere and heartfelt, expressing genuine appreciation, gratitude, or personal connection.",
            "Curious": "Full of wonder and fascination, openly exploring complex or beautiful aspects of the world.",
            "Determined": "Showing resilience and motivation to overcome challenges, pushing forward despite setbacks.",
            "Warm": "Gentle and friendly, fostering a positive and supportive atmosphere in interactions."
        }
  
        self.tweet_patterns = {
            "starts": {
                "action_verb": "Start with a strong verb",
                "observation": "Share what you notice",
                "reflection": "Share a realization",
                "emotion": "Express genuine feeling",
                "milestone": "Mark progress",
                "realization": "Share discovery",
                "question": "Pose a thoughtful query",
                "comparison": "Draw an interesting parallel",
                "challenge": "Present a problem solved",
                "quote": "Reference something meaningful",
                "hypothesis": "Propose an idea",
                "contrast": "Note an interesting difference",
                "celebration": "Share a win",
                "surprise": "Express unexpected discovery",
                "curiosity": "Start with something you’re curious about"
            },
            "ends": {
                "insight": "Share learning",
                "outcome": "Show result",
                "forward_looking": "Show anticipation",
                "appreciation": "Express gratitude",
                "impact": "Show significance",
                "simple_close": "Brief wrap-up",
                "invitation": "Engage others' thoughts",
                "reflection": "Share deeper meaning",
                "call_to_action": "Suggest next steps",
                "connection": "Link to bigger picture",
                "humor": "End with light observation",
                "possibility": "Open new doors",
                "challenge": "Pose thoughtful question",
                "resolution": "Show problem solved",
                "gratitude": "End with a note of thanks",
                "pondering": "Leave a thought hanging",
                "regret": "Express a missed opportunity",
                "celebration": "Close with a joyful acknowledgment"
            }
        }
        
    def calculate_current_year(self, tweet_count):
        """Calculate the current year in Xavier's timeline based on number of tweets"""
        years_elapsed = tweet_count // self.tweets_per_year
        current_year = self.sim_start_year + years_elapsed
        return current_year

    def handle_tech_evolution(self, current_context=None):
        """Handle tech evolution initialization and updates"""
        try:
            tech_evolution, _ = self.github_ops.get_file_content("tech_evolution.json")
            
            # Initialize if no tech evolution exists
            if not tech_evolution or not tech_evolution.get('tech_trees'):
                print("Initializing first tech epoch...")
                from src.generation.tech_evolution_generator import TechEvolutionGenerator
                tech_gen = TechEvolutionGenerator()
                first_epoch = tech_gen.generate_epoch_tech_tree(self.sim_start_year)
                
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
            
            # Check if update needed (only if we have current context)
            elif current_context and self.should_update_tech_evolution(current_context):
                print("Updating tech evolution for next epoch...")
                from src.generation.tech_evolution_generator import TechEvolutionGenerator
                tech_gen = TechEvolutionGenerator()
                next_epoch = max([int(year) for year in tech_evolution['tech_trees'].keys()]) + 5
                
                tree_data = tech_gen.generate_epoch_tech_tree(next_epoch)
                if tree_data:
                    tech_gen.evolution_data['tech_trees'][str(next_epoch)] = tree_data
                    tech_gen.save_evolution_data()
                    tech_evolution, _ = self.github_ops.get_file_content("tech_evolution.json")
            
            return tech_evolution
            
        except Exception as e:
            print(f"Error handling tech evolution: {e}")
            return {"tech_trees": {}}

    def get_context(self):
        """Gather all necessary context for tweet generation"""
        try:
            print("Starting context gathering...")
            
            # 1. Get and handle tech evolution
            print("Getting tech evolution...")
            try:
                tech_evolution = self.handle_tech_evolution()
                print("Tech evolution loaded successfully")
            except Exception as e:
                print(f"Error loading tech_evolution.json: {str(e)}")
                return None
            
            # 2. Get ongoing tweets and comments
            print("Getting ongoing_tweets.json...")
            try:
                ongoing_tweets, _ = self.github_ops.get_file_content("ongoing_tweets.json")
                if not ongoing_tweets:
                    print("No ongoing tweets found, initializing empty list")
                    ongoing_tweets = []
                elif isinstance(ongoing_tweets, str):
                    ongoing_tweets = json.loads(ongoing_tweets)
                print("Ongoing tweets loaded successfully")
            except Exception as e:
                print(f"Error loading ongoing_tweets.json: {str(e)}")
                return None
            
            tweet_count = len(ongoing_tweets)
            print(f"Found {tweet_count} tweets")
            
            print("Getting comments.json...")
            try:
                comments, _ = self.github_ops.get_file_content("comments.json")
                if not comments:
                    print("No comments found, initializing empty list")
                    comments = []
                elif isinstance(comments, str):
                    comments = json.loads(comments)
                print("Comments loaded successfully")
            except Exception as e:
                print(f"Error loading comments.json: {str(e)}")
                return None

            # 3. Get recent context using rolling windows
            recent_tweets_window = self.tweets_per_year // 8
            recent_tweets = ongoing_tweets[-recent_tweets_window:] if ongoing_tweets else []

            # Include ACTI's tweets for the first few tweets
            # if tweet_count < recent_tweets_window:
            #     try:
            #         acti_tweets, _ = self.github_ops.get_file_content("last_acti_tweets.json")
            #         if isinstance(acti_tweets, list):
            #             acti_count = 5 - tweet_count
            #             recent_tweets = acti_tweets[-acti_count:] + recent_tweets
            #     except Exception as e:
            #         print(f"Error getting ACTI tweets: {e}")

            # Get recent comments
            recent_comment_count = max(2, self.tweets_per_year // 20)
            recent_comments = comments[-recent_comment_count:] if comments else []

            current_year = self.calculate_current_year(tweet_count)
            print(f"Current year calculated: {current_year}")

            # 4. Handle digest
            print("Getting digest history...")
            digest_history, _ = self.github_ops.get_file_content("digest_history.json")
            if not digest_history:
                print("No digest history found, initializing empty list")
                digest_history = []
            elif isinstance(digest_history, str):
                digest_history = json.loads(digest_history)
            
            latest_digest = digest_history[-1] if digest_history else {}

            context = {
                "current_year": current_year,
                "tweet_count": tweet_count,
                "recent_tweets": recent_tweets,
                "recent_comments": recent_comments,
                "digest": latest_digest,
                "tech_evolution": tech_evolution
            }
            
            print(f"Initial context gathered successfully")
            
            # Check for tech evolution updates with full context
            context["tech_evolution"] = self.handle_tech_evolution(context)

            # Generate new digest if needed
            if self.should_update_digest(context):
                print("Updating digest...")
                digest_window = self.tweets_per_year // 4
                digest_tweets = ongoing_tweets[-digest_window:] if ongoing_tweets else []
                
                if not digest_history:
                    new_digest = self.digest_generator.process_first_digest()
                else:
                    new_digest = self.digest_generator.process_ongoing_digest(
                        latest_digest,
                        digest_tweets,
                        recent_comments
                    )
                
                if new_digest:
                    new_digest['tweet_count'] = tweet_count
                    self.github_ops.update_story_digest(
                        new_tweets=digest_tweets,
                        new_comments=recent_comments,
                        initial_content=new_digest
                    )
                    context['digest'] = new_digest

            return context

        except Exception as e:
            print(f"Error gathering context: {str(e)}")
            return None

    def get_simulation_state(self):
        """Get the current simulation state from GitHub"""
        try:
            state, sha = self.github_ops.get_file_content("simulation_state.json")

            # Return initial state if state is None
            if state is None:
                initial_state = {
                    "last_tweet_timestamp": datetime.now().isoformat(),
                    "tweet_count": 0,
                    "current_year": self.sim_start_year,
                    "is_complete": False
                }
                return initial_state, None
                
            return state, sha
            
        except Exception as e:
            print(f"Error getting simulation state: {type(e).__name__} - {str(e)}")
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
        """Create the prompt for tweet generation"""
        # Calculate context variables
        current_year = context['current_year']
        tweet_count = context['tweet_count']
        xavier_age = current_year - self.sim_start_year + 22
        
        # Calculate time interval between tweets
        days_per_tweet = 365 / self.tweets_per_year
        days_elapsed = tweet_count * days_per_tweet
        current_date = datetime(self.sim_start_year, 1, 1) + timedelta(days=days_elapsed)
        
        # Create system prompt
        system = (
            "You are Xavier, a tech visionary who tweets naturally. "
            f"Each tweet represents approximately {days_per_tweet:.1f} days in your life.\n\n"
            
            "NARRATIVE FOCUS:\n"
            "- Each tweet should advance the story by showing meaningful progress\n"
            "- Show natural progression of projects and relationships\n"
            "- Maintain realistic pacing of life events\n"
            "- Build continuity between major milestones\n"
            "- Balance daily experiences with significant moments\n\n"
            
            "CORE CHARACTER TRAITS:\n"
            "- Innovative but practical mindset\n"
            "- Deep curiosity about technology's role in society\n"
            "- Values human connections and community building\n"
            "- Balances ambition with ethical considerations\n"
            "- Occasionally notices patterns that seem too perfect\n\n"
            
            "WRITING STYLE:\n"
            "- Natural, conversational tone\n"
            "- Show rather than tell experiences\n"
            "- Mix technical insight with personal reflection\n"
            "- Create memorable moments\n"
            "- Avoid explicit time references unless significant\n\n"
            
            "ALWAYS AVOID:\n"
            "- Hashtags or unnecessary @ mentions\n"
            "- Generic observations or questions\n"
            "- Time references (months, seasons, weather)\n"
            "- Location references unless story-critical\n"
            "- $XVI token mentions (omit 95% of time)\n"
            "- Repeated metaphors or running jokes\n"
            "- Abstract 'what if' scenarios\n"
            "- Generic 'how can we' queries\n"
            "- TextBlock formatting\n"
            "- Starting tweets with 'Just...'\n"
            "- Rhetorical questions or 'how do we' formats\n"
            "- Overly formal or academic language\n"
            "- Repeating recent events or conversations\n\n"
            
            "Respond with ONLY the tweet content."
        )

        # Get recent variations
        recent_variations = {
            'tones': set(),
            'focuses': set(),
            'starts': set(),
            'ends': set()
        }
        for tweet in context.get('recent_tweets', [])[-(self.tweets_per_year // 8):]:
            if 'variations' in tweet:
                tone, _, start, end = tweet['variations']
                recent_variations['tones'].add(tone)
                recent_variations['starts'].add(start)
                recent_variations['ends'].add(end)

        # Filter out recently used variations
        available_tones = [(tone, weight) for tone, weight in self.tone_options if tone not in recent_variations['tones']] or self.tone_options
        tones, weights = zip(*available_tones)
        current_tone = random.choices(tones, weights=weights, k=1)[0]
                
        # Get age-appropriate content focuses
        content_focuses = self._get_age_adjusted_content_focuses(xavier_age)
        current_focus = random.choice(list(content_focuses.keys()))
        
        # Select patterns avoiding recent ones
        available_starts = [s for s in self.tweet_patterns["starts"].keys() if s not in recent_variations['starts']] or list(self.tweet_patterns["starts"].keys())
        available_ends = [e for e in self.tweet_patterns["ends"].keys() if e not in recent_variations['ends']] or list(self.tweet_patterns["ends"].keys())
        start_type = random.choice(available_starts)
        end_type = random.choice(available_ends)
        
        # Build base prompt with context
        prompt = (
            f"Timeline: {current_date}\n"
            f"Xavier's Age: {xavier_age}\n"
            f"Life Phase: {self.digest_generator._get_life_phase(xavier_age)}\n"
            f"Foundation Phase: {self.digest_generator._get_foundation_phase(xavier_age)}\n"
            f"Tone: {current_tone} - {self.tone_descriptions[current_tone]}\n\n"
            
            # Story Progression Block
            "=== STORY PROGRESSION ===\n"
            f"Focus Area: {current_focus}\n"
            f"Example Theme (adapt to current tech landscape if relevant):\n"
            f"- {random.choice(content_focuses[current_focus]['examples'])}\n\n"
            
            # Recent Tweets Block
            "=== RECENT TWEETS ===\n"
            "Consider these recent tweets for continuity:\n" +
            ''.join(f"- {tweet['content']}...\n" for tweet in context.get('recent_tweets', [])) + "\n"
            
            # Recent Comments Block
            "=== RECENT COMMENTS ===\n"
            "Key insights from recent comments:\n" +
            ''.join(f"- {comment}...\n" for comment in context.get('recent_comments', [])) + "\n"
            
            # Digest Summary Block
            "=== DIGEST SUMMARY ===\n"
            "Summary of ongoing narrative from digest:\n"
            f"{context.get('digest', {}).get('content', '')}\n\n"
        )

        # Tech Context Block
        tech_trees = context.get('tech_evolution', {}).get('tech_trees', {})
        current_epoch = str(current_year - (current_year % 5))

        if current_epoch in tech_trees:
            tech_context = tech_trees[current_epoch]
            prompt += (
                "=== CURRENT TECH LANDSCAPE ===\n"
                f"Year: {context['current_year']}\n\n"
                
                "Mainstream Technologies:\n" +
                "\n".join(f"- {tech['name']}" for tech in tech_context.get('mainstream_technologies', [])) +
                "\n\n"
                
                "Emerging Developments:\n" +
                "\n".join(f"- {tech['name']} (Probability: {tech['probability']})" 
                        for tech in tech_context.get('emerging_technologies', []) if tech.get('probability', 0) > 0.7) +
                "\n\n"
                
                "Key Themes of the Epoch:\n" +
                "\n".join(f"- {theme['theme']}" for theme in tech_context.get('epoch_themes', [])) +
                "\n\n"
            )
            
        prompt += (
            "=== REQUIREMENTS ===\n"
            "1. Show clear progress or development in this focus area.\n"
            "2. Build on recent tweets and comment context.\n"
            "3. Connect to ongoing digest narrative.\n\n"
            
            "=== GUIDELINES ===\n"
            "- Avoid static observations, repeated themes, generic statements, and disconnected musings.\n\n"
            "- Frame your response within this technological era while maintaining personal authenticity.\n\n"
            
            "Goal: Move the story forward within this focus area.\n\n"
        )

        # Add special cases
        if (tweet_count % self.tweets_per_year) in range(1, 2):
            prompt += (
                f"\nBirthday Context:\n"
                f"Xavier is turning {xavier_age}. Consider:\n"
                "- Reflective or forward-looking thoughts\n"
                "- Personal goals or gratitude\n"
                "- Keep it natural and relatable\n\n"
            )
        elif tweet_count == 0:
            prompt += (
                "\nFirst Tweet Context:\n"
                "- Set in either final moments in Japan or first in NYC\n"
                "- Reflect on the influence of Japan on his perspective\n"
                "- Show transition and growth\n\n"
            )
                
        prompt += (
            "\nTWEET GUIDELINES:\n"
            "- Do NOT include pattern labels (like 'Milestone:' or 'Humor:')\n"
            "- Write as a single, cohesive thought\n"
            "- Don't use explicit line breaks or formatting\n"
            "- Write the tweet directly, without any markdown or special characters\n"
            "- Avoid metaphor reuse across tweets\n"
            "- Focus on one specific aspect/moment\n"
            "- Stay true to the selected focus area\n\n"
            "- Keep it natural and conversational\n\n"
            
            f"Opening style: {start_type} - {self.tweet_patterns['starts'][start_type]}\n"
            f"Closing style: {end_type} - {self.tweet_patterns['ends'][end_type]}\n"
        )
        
        prompt += (
            f"Write a single tweet that captures a moment or development during this {days_per_tweet:.1f}-day period. "
            "Focus on advancing the story through experiences, relationships, and growth. "
            "Ensure natural progression from recent events while building towards longer-term developments."
        )
        return system, prompt, (current_tone, current_focus, start_type, end_type)

    def should_update_digest(self, context):
        """Determine if digest needs updating based on tweet counts and content"""
        try:
            existing_digest = context['digest']
            # recent_tweets = context['recent_tweets']
            
            # Check if we have an existing digest
            if not existing_digest or not existing_digest.get('content'):
                return True
                
            # Get last processed tweet count
            last_processed_count = existing_digest.get('tweet_count', 0)
            current_count = context['tweet_count']
            
            # # Always update for first few tweets to establish story
            # if current_count < self.tweets_per_year * 0.05:  # First 5% of yearly tweets
            #     return True
                
            # Update digest every ~12.5% of yearly tweets (about 1.5 months in story time)
            tweets_per_digest = max(1, self.tweets_per_year // 8)  # At least 1 tweet between digests
            if current_count - last_processed_count >= tweets_per_digest:
                return True
                
            # # Check for significant events since last digest
            # significant_events = 0
            # for tweet in recent_tweets:
            #     content = tweet['content'].lower()
            #     if any(marker in content for marker in [
            #         'decided to', 'realized', 'started', 'finished',
            #         'met with', 'moving to', 'leaving', 'joined',
            #         'launched', 'created', 'ended', 'beginning'
            #     ]):
            #         significant_events += 1
                    
            # # Update if we have enough significant events (scaled to tweet frequency)
            # significant_threshold = max(2, self.tweets_per_year // 32)  # At least 2 events
            # if significant_events >= significant_threshold:
            #     return True
                
            return False
            
        except Exception as e:
            print(f"Error checking digest update criteria: {e}")
            return True  # Default to updating on error

    def should_update_tech_evolution(self, context):
        """Determine if tech evolution needs updating or initializing"""
        try:
            tech_trees = context.get('tech_evolution', {}).get('tech_trees', {})
            tweet_count = context['tweet_count']
            
            # Calculate tweets per epoch (5 years)
            tweets_per_epoch = self.tweets_per_year * 5  # 96 * 5 = 480 tweets per epoch
            
            # Calculate which epoch we should have
            current_epoch_index = tweet_count // tweets_per_epoch
            current_epoch_year = self.sim_start_year + (current_epoch_index * 5)
            next_epoch_year = current_epoch_year + 5
            
            # If we don't have the current epoch, we need to generate it
            if str(current_epoch_year) not in tech_trees:
                return True
                
            # If we're approaching the next epoch and don't have it yet
            if str(next_epoch_year) not in tech_trees:
                tweets_into_epoch = tweet_count % tweets_per_epoch
                tweets_until_next_epoch = tweets_per_epoch - tweets_into_epoch
                
                # Generate next epoch when we're ~9 months away from it
                return tweets_until_next_epoch <= self.tweets_per_year * 60 / 96
                
            return False
            
        except Exception as e:
            print(f"Error checking tech evolution criteria: {e}")
            return True

    def generate_tweet(self):
        """Generate a new tweet"""
        try:
            # Get context
            context = self.get_context()
            if not context:
                return None
                
            # Get prompts
            system, prompt, variations = self.create_tweet_prompt(context)
            
            # Generate tweet
            try:
                message = self.client.messages.create(
                    model="grok-beta",
                    max_tokens=1024,
                    system=system,
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
                tweet_content = tweet_content.replace("', type='text')]", "")
                tweet_content = tweet_content.strip('"')  # Remove surrounding quotes
                
                # Remove any hashtags and clean up spacing
                tweet_content = re.sub(r'\s*#\w+\s*', ' ', tweet_content).strip()

                # Calculate age for prefix
                xavier_age = context['current_year'] - self.sim_start_year + 22

                # Always add year and age prefix (not just for first tweet)
                year_prefix = f"[{context['current_year']}, Age {xavier_age}] "

                tweet = {
                    "id": f"tweet_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "content": year_prefix + tweet_content,  # Always include the prefix
                    "timestamp": datetime.now().isoformat(),
                    "likes": 0,
                    "retweets": 0, 
                    "variations": variations,
                }
                
                self.update_simulation_state(tweet)
                return tweet
                    
            except Exception as e:
                print(f"Error generating tweet: {str(e)}")
                return None
        except Exception as e:
            print(f"Error generating tweet: {str(e)}")
            return None

    def _extract_themes(self, content):
        """Helper method to identify key themes from a tweet to avoid repetition"""
        # Could be enhanced with NLP later
        return [
            word.lower() 
            for word in content.split() 
            if (len(word) > 2  and not word.startswith('[')) | (word == 'AI')
        ]

    def _get_age_adjusted_content_focuses(self, age):
        """Get content focuses with weights adjusted for Xavier's age"""
        if age < 25:
            return {
                "Integrated Tech Explorations": {
                    "weight": 20,
                    "examples": [
                        "Experimenting with how blockchain enhances AI data security",
                        "Diving into VR/AR applications with Web3 elements",
                        "Connecting IoT and blockchain for smarter devices",
                        "Building a decentralized app with AI-driven insights",
                        "Real-time data sharing on blockchain—bridging gaps in IoT"
                    ]
                },
                "Dating & Early Relationships": {
                    "weight": 20,
                    "examples": [
                        "Navigating dating in a digital world—balancing time with tech",
                        "Meeting someone special at a tech event and seeing sparks fly",
                        "Learning how my tech lifestyle impacts my relationships",
                        "Exploring how shared interests in tech bring people closer",
                        "Realizing that relationships require more than just digital connection"
                    ]
                },
                "Cross-Disciplinary Learning": {
                    "weight": 15,
                    "examples": [
                        "Exploring the intersection of tech and art",
                        "Learning about AI ethics and its impact on privacy in blockchain",
                        "Understanding how cybersecurity enhances blockchain security",
                        "Reflecting on tech philosophy: How does tech change who we are?",
                        "Experimenting with blockchain in environmental monitoring"
                    ]
                },
                "Personal Discoveries": {
                    "weight": 15,
                    "examples": [
                        "Figuring out what it means to balance work and life",
                        "Learning the limits of tech’s influence on personal relationships",
                        "Exploring life lessons through coding challenges",
                        "Building skills outside of tech for a well-rounded life",
                        "Discovering creativity through non-tech hobbies"
                    ]
                },
                "Global Tech Culture": {
                    "weight": 10,
                    "examples": [
                        "Seeing how Japan's approach to tech influences my thinking",
                        "Exploring diverse perspectives on AI and Web3",
                        "Cultural insights from attending tech events globally",
                        "How tech innovation varies across different regions",
                        "Discovering cross-cultural collaboration opportunities"
                    ]
                }
            }
        elif age < 30:
            return {
                "Blockchain’s Role in Emerging Tech": {
                    "weight": 20,
                    "examples": [
                        "Applying blockchain in decentralized AI models",
                        "Exploring how Web3 supports digital identity security",
                        "Blockchain as a foundation for next-gen smart cities",
                        "Combining blockchain with AI for better data integrity",
                        "Using blockchain to manage IoT security challenges"
                    ]
                },
                "Community & Tech Impact": {
                    "weight": 15,
                    "examples": [
                        "Organizing discussions on the ethical implications of tech",
                        "Bringing AI and blockchain communities together",
                        "Creating spaces to discuss cross-industry tech impact",
                        "Fostering diverse tech perspectives in local communities",
                        "Building inclusive tech events for knowledge sharing"
                    ]
                },
                "Future-Driven Tech Concepts": {
                    "weight": 15,
                    "examples": [
                        "Researching blockchain’s role in the metaverse",
                        "Exploring tech’s potential in space exploration",
                        "Innovating at the convergence of quantum computing and Web3",
                        "Focusing on tech solutions for climate resilience",
                        "Prototyping decentralized systems for supply chain transparency"
                    ]
                },
                "Relationships & Building Foundations": {
                    "weight": 20,
                    "examples": [
                        "Navigating a serious relationship while advancing my career",
                        "Learning the value of work-life balance for personal connections",
                        "Reflecting on how a relationship changes one’s goals",
                        "Exploring shared goals with a partner beyond tech",
                        "Building strong foundations as a couple while balancing ambitions"
                    ]
                },
                "Identity & Personal Growth": {
                    "weight": 10,
                    "examples": [
                        "Learning to define myself beyond career achievements",
                        "Building life skills that complement tech expertise",
                        "Defining personal values in an ever-connected world",
                        "Reflecting on the intersection of career and identity",
                        "Discovering self through diverse tech experiences"
                    ]
                }
            }
        elif age < 35:
            return {
                "Leadership in Emerging Tech Integration": {
                    "weight": 25,
                    "examples": [
                        "Guiding teams through AI and blockchain convergence projects",
                        "Learning to inspire teams in tech-driven transformation",
                        "Establishing a vision for interdisciplinary tech applications",
                        "Leading projects that blend AI, blockchain, and IoT",
                        "Fostering collaboration across decentralized networks"
                    ]
                },
                "Family Formation & Life Transitions": {
                    "weight": 20,
                    "examples": [
                        "Reflecting on marriage and building a life together",
                        "Balancing career ambitions with family goals",
                        "Preparing for the possibility of parenthood",
                        "Finding a partner who shares my values and vision",
                        "Exploring how tech shapes our family life and choices"
                    ]
                },
                "Strategic Vision for Technology": {
                    "weight": 15,
                    "examples": [
                        "Imagining how blockchain and AI redefine data ownership",
                        "Exploring cross-industry applications for Web3",
                        "Assessing the future of smart cities powered by blockchain",
                        "Considering blockchain’s role in energy sustainability",
                        "The role of tech in bridging real and virtual worlds"
                    ]
                },
                "Relationships & Support Systems": {
                    "weight": 15,
                    "examples": [
                        "Building a support system with my partner",
                        "Growing together through life’s challenges",
                        "Maintaining strong relationships in a tech-focused life",
                        "Learning from family and friends outside of tech",
                        "Supporting each other's dreams while maintaining individuality"
                    ]
                },
                "Community Impact & Mentorship": {
                    "weight": 15,
                    "examples": [
                        "Developing programs to educate on Web3 security",
                        "Building educational initiatives to bridge tech gaps",
                        "Encouraging future generations to explore tech responsibly",
                        "Creating hands-on learning spaces for cross-industry tech",
                        "Advocating for responsible tech integration in education"
                    ]
                }
            }
        elif age < 45:
            return {
                "Tech Impact & Broader Industry Influence": {
                    "weight": 25,
                    "examples": [
                        "Blockchain’s role in societal infrastructure and privacy",
                        "Exploring tech’s impact on social equity",
                        "Shaping digital identities with Web3 principles",
                        "Blockchain’s potential in addressing global data privacy",
                        "How integrated tech reshapes industry standards"
                    ]
                },
                "Parenting in the Digital Age": {
                    "weight": 20,
                    "examples": [
                        "Teaching my children about responsible tech use",
                        "Balancing tech exposure for kids and family life",
                        "Parenting with digital boundaries in a connected world",
                        "Creating tech habits that emphasize wellness and balance",
                        "Helping my children develop a healthy relationship with technology"
                    ]
                },
                "Sustainable Tech Integration": {
                    "weight": 20,
                    "examples": [
                        "Developing blockchain for sustainable energy systems",
                        "Encouraging greener solutions through decentralized models",
                        "Applying blockchain for environmental monitoring",
                        "Assessing long-term effects of decentralized energy solutions",
                        "Balancing tech growth with ecological responsibility"
                    ]
                },
                "Industry & Family Balance": {
                    "weight": 15,
                    "examples": [
                        "Balancing the demands of leadership with family life",
                        "Creating family time amidst a busy tech career",
                        "Finding harmony between personal goals and industry impact",
                        "Building a lifestyle that respects family and career goals",
                        "Navigating challenges as both a parent and tech leader"
                    ]
                },
                "Philosophical Insights on Tech & Society": {
                    "weight": 15,
                    "examples": [
                        "Reflecting on humanity’s role in tech evolution",
                        "Considering ethical questions in digital privacy",
                        "Exploring the influence of tech on social consciousness",
                        "Balancing automation with human-centered design",
                        "Recognizing the importance of mindfulness in tech innovation"
                    ]
                }
            }
        elif age < 60:
            return {
                "Legacy & Succession in Tech": {
                    "weight": 25,
                    "examples": [
                        "Ensuring knowledge transfer for future innovators",
                        "Shaping sustainable systems for the next generation",
                        "Creating platforms to foster interdisciplinary tech",
                        "Mentoring with a focus on holistic tech growth",
                        "Leaving behind resources for continued innovation"
                    ]
                },
                "Parenting & Family Wisdom": {
                    "weight": 20,
                    "examples": [
                        "Passing down values of tech responsibility",
                        "Helping my children navigate their own career paths",
                        "Building a family legacy rooted in mindful tech use",
                        "Supporting my children’s dreams and ambitions",
                        "Reflecting on how family shapes our view of tech’s future"
                    ]
                },
                "Future-Focused Industry Influence": {
                    "weight": 20,
                    "examples": [
                        "Helping define policies that govern tech integration",
                        "Supporting tech ecosystems with a sustainable outlook",
                        "Engaging in projects with cross-generational impact",
                        "Encouraging tech use for long-term societal benefit",
                        "Guiding the next wave in responsible tech growth"
                    ]
                },
                "Global Vision & Wisdom Sharing": {
                    "weight": 15,
                    "examples": [
                        "Sharing insights from a multi-tech perspective",
                        "Encouraging balanced, ethical innovation",
                        "Creating sustainable tech philosophies for future generations",
                        "Reflecting on cross-industry insights for lasting impact",
                        "Mentoring young leaders to think beyond short-term gains"
                    ]
                },
                "Reflective Family & Community Legacy": {
                    "weight": 20,
                    "examples": [
                        "Building a family culture that respects tech’s societal impact",
                        "Leaving a legacy that values tech mindfulness and responsibility",
                        "Strengthening community ties through shared tech values",
                        "Helping my family understand the positive power of technology",
                        "Creating a legacy of innovation that balances tech with human values"
                    ]
                }
            }
        else:  # age >= 60
            return {
                "Legacy & Succession": {
                    "weight": 30,
                    "examples": [
                        "Planning for the continuation of projects and values",
                        "Creating systems to support sustainable innovation",
                        "Ensuring a smooth transition of leadership in tech initiatives",
                        "Building a knowledge-sharing network for future innovators",
                        "Developing strategies to preserve a positive tech legacy"
                    ]
                },
                "Elder Wisdom & Mentorship": {
                    "weight": 25,
                    "examples": [
                        "Sharing life lessons from a career in tech and beyond",
                        "Helping younger generations navigate industry challenges",
                        "Reflecting on career wisdom and what I would have done differently",
                        "Encouraging new leaders to consider tech’s broader impact",
                        "Mentoring with a focus on sustainable growth and ethics"
                    ]
                },
                "Future Vision & Society": {
                    "weight": 20,
                    "examples": [
                        "Considering long-term impacts of tech on future societies",
                        "Exploring how humanity can adapt to rapid tech advancement",
                        "Advocating for responsible tech evolution for future generations",
                        "Fostering discussions on ethics in digital transformation",
                        "Championing tech initiatives that benefit society at large"
                    ]
                },
                "Family & Community Legacy": {
                    "weight": 15,
                    "examples": [
                        "Reflecting on the impact I’ve had on my family through tech",
                        "Ensuring that family values align with responsible tech use",
                        "Passing down stories and values that emphasize integrity in tech",
                        "Engaging in community initiatives that promote mindful tech",
                        "Leaving a legacy that respects both tradition and innovation"
                    ]
                },
                "Reflective & Philosophical Insights": {
                    "weight": 10,
                    "examples": [
                        "Reflecting on the purpose and meaning of a life in tech",
                        "Considering how my work will be remembered and valued",
                        "Exploring the philosophical implications of a digital society",
                        "Reflecting on the limits and opportunities technology provides",
                        "Sharing insights on achieving fulfillment beyond career success"
                    ]
                }
            }

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

