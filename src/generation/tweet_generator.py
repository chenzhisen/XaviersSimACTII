import random
import json
import traceback
from datetime import datetime
from src.storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
from openai import OpenAI
import re
import os
from collections import deque
from typing import List, Dict, Any, Union
from difflib import SequenceMatcher
import time
from src.utils.ai_completion import AICompletion

class TweetGenerator:
    def __init__(self, client, model, tweets_per_year=96, digest_interval=8):
        self.model = model
        self.client = client
        self.tweets_per_year = tweets_per_year
        self.days_per_tweet = 365 / tweets_per_year
        self.digest_interval = digest_interval
        self.github_ops = GithubOperations()
        self.reference_tweets = []
        self.ai = AICompletion(client, model)
        # Update log file path to use logs/tweets directory
        self.log_dir = "logs/tweets"
        self.log_file = os.path.join(
            self.log_dir,
            f"tweet_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Create logs/tweets directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.active_goals = {}
        self.completed_goals = []
        
        # Initialize refined content prompts
        self.content_prompts = {
            'tech': {
                '20s': "Share specific insights into your AI or blockchain projects and how they're solving real-world problems. Focus on tangible impacts or lessons learned.",
                '30s': "Highlight how you're integrating cutting-edge technology into larger systems. Reflect on your role in driving innovation.",
                '40s': "Discuss your contributions to the evolution of technology and how they address industry challenges.",
                '50s': "Provide practical advice on leading through technological change and mentoring future innovators.",
                '60s_plus': "Reflect on your lifetime of contributions to technology and share perspectives on its future trajectory."
            },
            'finance': {
                '20s': "Discuss your experiences navigating finance with technology, such as AI-driven strategies. Highlight specific challenges or lessons learned.",
                '30s': "Share insights into strategic financial decisions and their impact. Tie them to your personal growth or industry trends.",
                '40s': "Reflect on industry shifts and your leadership in navigating financial complexity.",
                '50s': "Offer practical guidance on long-term investment strategies and share lessons from your career.",
                '60s_plus': "Reflect on the evolution of financial systems and share enduring principles for stability and success."
            },
            'health': {
                '20s': "Explore how technology, like wearables or AI, supports your wellness journey. Share practical takeaways from your experiences.",
                '30s': "Discuss balancing demanding careers with health-focused habits. Highlight solutions that integrate technology or mindfulness.",
                '40s': "Reflect on how your approach to health has evolved, emphasizing sustainable energy and longevity.",
                '50s': "Share insights into personalized health practices and their role in maintaining vitality.",
                '60s_plus': "Reflect on lifelong wellness strategies and their impact on your overall well-being."
            },
            'personal': {
                '20s': "Share honest reflections on navigating growth and relationships. Highlight moments of self-discovery and their influence on your goals.",
                '30s': "Discuss balancing career and personal milestones, like family or relationships, and how they shape your ambitions.",
                '40s': "Reflect on meaningful personal experiences that have influenced your life’s direction.",
                '50s': "Explore themes of legacy and fulfillment through key personal moments.",
                '60s_plus': "Share wisdom from your life’s journey, offering insights that inspire connection and purpose."
            },
            'reflection': {
                '20s': "Reflect on lessons learned from recent experiences. Highlight how they connect to your goals or values without overcomplicating the narrative.",
                '30s': "Discuss lessons from balancing ambition and purpose. Use clear and resonant analogies without overreliance on metaphors.",
                '40s': "Offer insights on how your personal and professional paths intersect with global or cultural themes.",
                '50s': "Share reflections on navigating complex choices and focus on growth and balance.",
                '60s_plus': "Reflect on your journey’s interconnectedness and offer timeless wisdom on humanity and progress."
            },
            'career': {
                '20s': "Share key milestones or challenges in your career. Focus on how you're blending disciplines like tech and finance to make an impact.",
                '30s': "Discuss leadership lessons and how you’ve shaped projects or teams to achieve meaningful results.",
                '40s': "Reflect on your leadership philosophy and its influence on innovation within your industry.",
                '50s': "Provide advice to younger professionals while sharing pivotal moments from your career.",
                '60s_plus': "Reflect on your career legacy and the principles that guide your contributions to the future."
            }
        }
        
        self.category_to_tweet_type = {
            "Career & Growth": "career",
            "Personal Life & Relationships": "personal",
            "Health & Well-being": "health",
            "Financial Trajectory": "finance",
            "Reflections & Philosophy": "reflection",
            "$XVI & Technology": "tech"
        }

        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Initialize by getting ACTI tweets
        self.reference_tweets = self.get_acti_tweets()
        
        # Tweet length constraints
        self.min_chars = 16     # Allow very short, impactful tweets
        self.max_chars = 2048   # Allow for occasional longer form thoughts
        
        # Add a system prompt that explicitly prohibits age prefixes
        self.system_prompt = """
            You are Xavier, a 22-year-old navigating the intersections of tech, creativity, and personal growth. 
            Your goal is to share authentic and engaging tweets that capture specific moments in your journey, showing both progress and humanity.

            ### Guidelines:
            1. **Specific Moments:**
            - Focus on a single, vivid moment or experience. Avoid summarizing progress broadly.
            - Describe what happened, how you felt, and what you’re learning.

            2. **Tone:**
            - Keep the tone conversational and human—like you’re talking to a friend.
            - Include humor, sarcasm, or vulnerability when appropriate.
            - Avoid generic phrases like "every glitch is a lesson." Instead, share unique, relatable thoughts.

            3. **Structure:**
            - Open with an attention-grabbing observation or moment.
            - Share the experience or insight briefly, tying it back to a personal thought or emotion.
            - End with a subtle reflection or forward-looking idea.

            4. **Avoid:**
            - Overused metaphors, excessive technical jargon, or overly abstract language.
            - Generic phrases or overly polished "motivational" tones.

            ### What to Emphasize:
            - Humor when things go wrong: “Spent three hours debugging $XVI’s AI, only to realize the problem was me.”
            - Emotions and personality: “The AI works, but now I’m wondering if it’s judging my coffee addiction.”
            - Relatable slices of life: “$XVI’s trend predictor is great, but it doesn’t help me predict NYC’s subway delays.”
            """

            
    def get_content_prompt(self, tweet_type, age):
        """Get tailored content prompt based on Xavier's age and tweet type."""
        if tweet_type not in self.content_prompts:
            return "Provide an insightful, narrative-driven tweet related to Xavier's experiences."

        # Determine the age group for appropriate tone and complexity
        if age < 30:
            stage = '20s'
        elif age < 40:
            stage = '30s'
        elif age < 50:
            stage = '40s'
        elif age < 60:
            stage = '50s'
        else:
            stage = '60s_plus'

        return self.content_prompts[tweet_type].get(stage, "")
    
    def get_acti_tweets(self):
        """Get reference tweets from ACTI.
        
        Returns:
            List of tweets from XaviersSim.json
        """
        if self.reference_tweets:
            return self.reference_tweets
        
        content, _ = self.github_ops.get_file_content('XaviersSim.json')
        if not content:
            print("Failed to load XaviersSim.json")
            return []
        
        # Collect all tweets from all age ranges
        all_tweets = []
        for age_range, tweets in content.items():
            # Extract content if tweet is a dict, otherwise use the tweet string directly
            for tweet in tweets:
                if isinstance(tweet, dict):
                    all_tweets.append(tweet.get('content', ''))
                else:
                    all_tweets.append(tweet)
                    
        self.reference_tweets = all_tweets
        return all_tweets

    def _get_reference_tweets(self, count=3):
        """Get a random sample of reference tweets."""
        if not self.reference_tweets:
            return []
        return random.sample(
            self.reference_tweets, 
            min(count, len(self.reference_tweets))
        )

    def log_step(self, step_name, **kwargs):
        """Log a generation step with all relevant information."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"\n=== {step_name} === {timestamp}\n"
        
        for key, value in kwargs.items():
            log_entry += f"{key}:\n{value}\n\n"
            
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "="*50 + "\n")

    def get_age_weighted_types(self, age):
        """Get tweet type weights based on age/life phase"""
        if 18 <= age < 25:  # Early Career
            return {
                "career": 0.5,    # Heavy focus on career establishment
                "finance": 0.2,   # Strong focus on financial growth
                "tech": 0.1,       # High tech/crypto involvement
                "personal": 0.1,   # Some personal life content
                "reflection": 0.05,  # Some philosophical thoughts
                "health": 0.05      # Basic health awareness
            }
        elif 25 <= age < 35:  # Career Growth
            return {
                "career": 0.2,
                "finance": 0.2,
                "tech": 0.15,
                "personal": 0.2,   # Increased personal life focus
                "reflection": 0.15,
                "health": 0.1
            }
        elif 35 <= age < 50:  # Mid-Life
            return {
                "career": 0.15,
                "finance": 0.15,
                "tech": 0.15,
                "personal": 0.25,  # More focus on relationships/family
                "reflection": 0.15,
                "health": 0.15    # Increased health awareness
            }
        else:  # 50+
            return {
                "career": 0.1,
                "finance": 0.15,
                "tech": 0.1,
                "personal": 0.25,
                "reflection": 0.25,  # More philosophical
                "health": 0.15
            }

    def generate(self, system_prompt, user_prompt, temperature=0.7, max_retries=3):
        """Wrapper for model generation with retry logic"""
        
        # Add length guidance to system prompt
        length_guide = (
            "\nTweet Length Guidelines:\n"
            "- Keep tweets concise and impactful\n"
            "- Most tweets should be 1-2 short sentences\n"
            "- Occasionally (1%) can be longer for important updates\n"
            "- Let content determine natural length\n"
            "- Avoid unnecessary words or padding\n"
        )
        system_prompt = system_prompt + length_guide

        for attempt in range(max_retries):
            try:
                response = self.ai.get_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=1000,
                    temperature=temperature
                )
                return response

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

    def validate_tweet(self, tweet):
        """Validate tweet meets requirements"""
        length = len(tweet)
        if length < self.min_chars:
            self.log_step(
                "Warning", 
                message=f"Tweet too short ({length} chars), minimum: {self.min_chars}"
            )
            return False
        if length > self.max_chars:
            self.log_step(
                "Warning", 
                message=f"Tweet too long ({length} chars), maximum: {self.max_chars}"
            )
            return False
        return True

    def generate_tweet(self, latest_digest=None, recent_tweets=None, recent_comments=None, age=None, tweet_count=0, current_location=None, trends=None):
        """Generate a new tweet based on context"""
        self.log_file = os.path.join(
            self.log_dir,
            f"tweet_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        try:
            # Update active goals from latest digest if available
            if latest_digest and 'projections' in latest_digest:
                self.active_goals = {
                    f"goal_{i}": goal 
                    for i, goal in enumerate(latest_digest['projections'].get('goals', []))
                }
            
            # Add debug logging for digest
            self.log_step(
                "Debug Digest",
                digest=json.dumps(latest_digest, indent=2) if latest_digest else "None"
            )

            # Get tweet count from the last ongoing tweet if not provided
            if tweet_count is None and recent_tweets:
                last_tweet = recent_tweets[-1]
                if isinstance(last_tweet, dict):
                    tweet_count = last_tweet.get('tweet_count', 0)
                else:
                    tweet_count = 0

            # Load goals first
            if latest_digest:
                self.load_goals_from_digest(latest_digest)
            
            # Then update their progress
            self.update_goals_progress(tweet_count)

            self.log_step(
                "Starting Tweet Generation",
                age=f"{age:.1f}",
                tweet_count=str(tweet_count),
                location=current_location,
                trends=json.dumps(trends) if trends else "None"
            )

            # Select tweet type based on both age-weighted probabilities and recent context
            weights = self.get_age_weighted_types(age)
            
            # Analyze recent tweets to influence next topic selection
            if recent_tweets and len(recent_tweets) > 0:
                last_tweet = recent_tweets[-1]
                last_type = self._detect_tweet_type(last_tweet)  # New helper method
                
                # Boost weight of related topics for natural transitions
                boosted_weights = weights.copy()
                for topic, weight in weights.items():
                    if self._are_topics_related(last_type, topic):  # New helper method
                        boosted_weights[topic] = weight * 1.5  # Boost related topics
                
                # Normalize weights
                total = sum(boosted_weights.values())
                weights = {k: v/total for k, v in boosted_weights.items()}
            
            tweet_type = random.choices(
                list(weights.keys()), 
                weights=list(weights.values())
            )[0]

            self.log_step(
                "Tweet Type Selection",
                weights=json.dumps(weights, indent=2),
                selected_type=tweet_type
            )

            # Generate raw content
            raw_content = self.generate_tweet_content(
                latest_digest, age, recent_tweets, tweet_type, 
                current_location, trends, tweet_count
            )

            # Format the content
            formatted_content = self.format_tweet_style(raw_content, age, recent_tweets)

            # Detect any location changes
            new_location = self.detect_location_change(formatted_content)
            self.log_step(
                "Detecting location Change",
                new_location=new_location,
                current_location=current_location
            )
            tweet_location = new_location if new_location is not None else current_location

            # Validate the formatted tweet
            if not self.validate_tweet(formatted_content):
                return None

            # Return tweet with all metadata
            return {
                'content': formatted_content,
                'raw_content': raw_content,
                'type': tweet_type,
                'age': age,
                'location': tweet_location,
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error generating tweet: {e}")
            traceback.print_exc()
            return None

    def get_time_context(self, age, days_elapsed, location="Unknown"):
        """Generate temporal context for prompts.
        
        Args:
            age: Current simulated age
            days_elapsed: Days since last tweet
            location: Current location
        """
        return f"""
        Current Context:
        - You are {age:.1f} years old
        - {days_elapsed:.1f} days have passed since your last tweet
        """

    def log_to_file(self, content):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(content + "\n\n")

    def get_acti_tweets(self):
        content, _ = self.github_ops.get_file_content('XaviersSim.json')
        if not content:
            print("Failed to load XaviersSim.json")
            return []
        
        # Collect all tweets from all age ranges
        all_tweets = []
        for age_range, tweets in content.items():
            # Extract content if tweet is a dict, otherwise use the tweet string directly
            for tweet in tweets:
                if isinstance(tweet, dict):
                    all_tweets.append(tweet.get('content', ''))
                else:
                    all_tweets.append(tweet)
        self.reference_tweets = all_tweets
        return all_tweets

    def _get_style_templates(self, sample_count=20):
        """Get random tweets from XaviersSim.json as style templates"""
        try:
            all_tweets = self.get_acti_tweets()
            
            if len(all_tweets) > sample_count:
                style_templates = random.sample(all_tweets, sample_count)
            else:
                style_templates = all_tweets
                
            print(f"Selected {len(style_templates)} style template tweets")
            return style_templates
                
        except Exception as e:
            print(f"Error getting style templates: {e}")
            return []
    
    def save_ongoing_tweets(self, tweets):
        """Save ongoing tweets to storage"""
        try:
            content = json.dumps(tweets, indent=2)
            self.github_ops.update_file(
                'ongoing_tweets.json',
                content,
                f"Update ongoing tweets at {datetime.now().isoformat()}"
            )
        except Exception as e:
            print(f"Error saving ongoing tweets: {e}")

    def detect_location_change(self, tweet):
        """Detects definitive location changes in a tweet using xAI model."""
        
        system_prompt = """You are a location-change detection assistant. Your task is to identify when someone has JUST arrived at a new location OR has a clear intention to travel to a new location.

        STRICT RULES:
        1. Detect ARRIVAL at a location:
            - Look for clear arrival phrases:
                - "just landed in X"
                - "arrived in X"20
                - "touching down in X"
                - "made it to X"
                - "finally in X"
            - The location after these phrases is the NEW location.

        2. Detect TRAVEL INTENT to a location:
            - Look for strong travel intent or planned movement:
                - "heading to X"
                - "taking back to X"
                - "returning to X"
                - "on my way to X"
                - "moving to X"
            - The location after these phrases is the DESTINATION.

        3. Return EXACTLY:
            - The location name for confirmed arrivals or travel intent (e.g., "NYC", "Tokyo", "London").
            - "No location change" if:
                - No clear arrival or travel intent is mentioned.
                - The location is a past reference or casual mention.

        4. Ignore:
            - Past locations being left.
            - Future plans without definitive intent.
            - Casual references without movement indicators.

        Examples:
        1. "Just landed in NYC from Tokyo" -> "NYC"
        2. "Taking back to NYC with memories from Tokyo" -> "NYC"
        3. "Carrying the spirit of Japan with me" -> "No location change"
        4. "On my way to London for a conference" -> "London"
        5. "Finally touched down in Paris!" -> "Paris"
        6. "Heading home after an amazing trip to Tokyo" -> "home"
        7. "Leaving Japan for NYC tomorrow" -> "NYC"
        8. "Missing Tokyo already" -> "No location change"
        """

        try:
            response = self.ai.get_completion(
                system_prompt=system_prompt,
                user_prompt=tweet,
                max_tokens=100
            )
            
            self.log_step(
                "Location Change Detection",
                system_prompt=system_prompt,
                tweet=tweet,
                response=response
            )
            
            return None if "no location" in response.lower() else response

        except Exception as e:
            print(f"Error in location detection: {e}")
            return None

    def _get_relevant_goals(self, tweet_type, tweet_count):
        """Get goals relevant to this tweet type, with their progress phase."""
        goals_context = self._get_active_goals_context(tweet_count)
        relevant_goals = [
            {
                'goal': goal['goal'],
                'phase': goal['phase'],
                'category': goal['category']
            }
            for goal in goals_context 
                if self.category_to_tweet_type.get(goal['category']) == tweet_type
        ]
        return relevant_goals

    def validate_post(self, text):
        """Validate post meets length requirements"""
        length = len(text)
        if length < self.min_chars:
            self.log_step(
                "Warning", 
                message=f"Post too short ({length} chars), minimum: {self.min_chars}"
            )
            return False
        if length > self.max_chars:
            self.log_step(
                "Warning", 
                message=f"Post too long ({length} chars), maximum: {self.max_chars}"
            )
            return False
        return True

    def _get_latest_context(self, digest):
        """Helper to get recent context from digest."""
        context = ""
        for category in digest:
            if 'historical_summary' in digest[category]:
                # Get most recent MTM entry
                if digest[category]['historical_summary'].get('MTM'):
                    mtm = digest[category]['historical_summary']['MTM'][-1]
                    context += f"\n{category}:\n- {mtm['Summary']}"
                
                # Get most recent LTM entry
                if digest[category]['historical_summary'].get('LTM'):
                    ltm = digest[category]['historical_summary']['LTM'][-1]
                    context += f"\n- Recent milestone: {ltm['Milestone']}"
        
        return context

    def _format_recent_tweets(self, recent_tweets):
        """Format recent tweets for context.
        
        Args:
            recent_tweets: List of tweets, can be either strings or dicts
                         (assumed to be in chronological order, oldest first)
        
        Returns:
            Formatted string of recent tweets, newest first
        """
        if not recent_tweets:
            return "No recent tweets available."
        
        formatted = "\n=== RECENT TWEETS (newest first) ===\n\n"
        # Reverse the list to get newest first, and take last 3
        for tweet in reversed(recent_tweets[-self.digest_interval:]):
            # Handle both string and dict tweet formats
            if isinstance(tweet, dict):
                tweet_content = tweet.get('content', '')
                if isinstance(tweet_content, str) and '\ud83d' in tweet_content:
                    # Handle emoji encoding if present
                    tweet_content = tweet_content.encode('utf-8').decode('unicode-escape')
                formatted += f" - {tweet_content}\n"
            else:
                formatted += f" - {str(tweet)}\n"
        
        return formatted

    def generate_tweet_content(self, digest, age, recent_tweets, tweet_type, location, trends=None, tweet_count=0):
        """First step: Generate raw content for the tweet."""
        # Check for special contexts
        is_first_tweet = tweet_count == 0
        is_birthday = (tweet_count % self.tweets_per_year) in range(1, 2)
        
        # Build special context prompts
        special_context = ""
        if is_first_tweet:
            special_context += (
                "Special Context (Very Important, must mention NYC explicitly) - Return from Japan:\n"
                "- Moving from Japan back to NYC\n"
                "- Show impact of Japan experience\n"
                "- Include both excitement and uncertainty\n"
            )
            tweet_type = "personal"
        if is_birthday:
            special_context += (
                f"\nSpecial Context - Birthday:\n"
                f"- Just turned {int(age)}\n"
                f"- Incorporate birthday reflection naturally\n"
                f"- Connect this milestone to current {tweet_type} developments\n"
            )
            tweet_type = "career"

        context = self._get_relevant_context(digest, tweet_type, tweet_count, recent_tweets)
        time_context = self.get_time_context(age, self.days_per_tweet, location)
        
        # Emphasize goal focus in system prompt
        system_prompt = (
            f"""Generate the next tweet for Xavier, progressing {int(self.days_per_tweet)} days from most recent tweets, toward short-term and long-term goals that are consistent with broader historical context.

            Each tweet must:
                1. Focus on specific actions Xavier took and the outcome of those actions.
                2. Include challenges or surprises in the process, focusing on real, relatable moments.
                3. Reflect progress or a key realization relevant to Xavier's active goals.

            ### Guidelines:
            1. **Story Development**:
                - Do not repeat the same topic in consecutive tweets unless reasonable progress is made.
                - Do not repeat the same joke or theme from previous tweets.
                - Do not repeat the same structure or format in previous tweets.
                
            2. **Be Specific**:
                - Describe how something happened
                - Avoid vague claims

            3. **Humor & Emotion**:
                - Show humor, frustration, excitement, or other emotions.
                - Show quirky moments from time to time

            Avoid:
                - Reusing similar jokes or themes (e.g., quirky AI anecdotes or "funny bot mistakes").
                - Overly vague or generic claims like "integrated AI into blockchain art."
                - Focusing solely on humor without moving the story forward.
            """
        )

        user_prompt = (
            f"{time_context}\n"
            f"{special_context}\n"
            f"Relevant Context:\n"
            f"{context}\n"
            f"{trends_context if trends else ''}\n\n"
            f"Generate ONE tweet that clearly demonstrates progress or strategic thinking about {tweet_type}. "
            f"Include specific details about the process, challenges, or surprises. Make it funny, relatable, and personal.\n\n"
            f"{self.get_content_prompt(tweet_type, age)}"
        )
        
        self.log_step(
            "Content Generation Request",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            trends=trends
        )
        
        response = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return response

    def format_tweet_style(self, content, age, recent_tweets):
        """Format content to match Xavier's writing style."""
        reference_tweets = self._get_reference_tweets(5)
        examples = "\n".join(f"{i+1}. {tweet}" for i, tweet in enumerate(reference_tweets))
        
        # Determine life stage based on age
        if age < 25:
            persona = "a young professional finding your way"
        elif age < 35:
            persona = "an established professional in your prime"
        elif age < 45:
            persona = "a seasoned industry veteran"
        else:
            persona = "an experienced leader and mentor"
                                
        system_prompt = f"""
            You are Xavier, a {age}-year-old {persona} writing tweets about your life, work, and interests. Your tone is human, engaging, and sometimes humorous or sarcastic. Share authentic updates with moments of joy, frustration, or self-reflection.
            
            ### Guidelines:
            1. Match closely the tone, style or voice in provided reference examples
            2. Be concise and to the point
            2. **Avoid:**
                - Motivational speaker clichés (e.g., “Time to crush it!” or “Believe in yourself!”).
                - Forced enthusiasm or over-the-top excitement.
                - Rigidly separating technical and personal topics; let them blend naturally when relevant.
                - Repeating metaphors or ideas without variation.
                - Hashtags or emojis or Unicode characters or special symbols or arrows unless they add genuine value to the tweet.
                -  NO Unicode escape sequences (like \\ud83c\\udf63)
            - Overuse of @ mentions; only reference public figures or accounts when essential.
            """
            # 1. **Be Funny and Relatable:**
            # - Use humor or sarcasm to highlight real challenges and show human emotions.
            # - Make fun of your own mistakes or quirks in a way others can relate to.
            # - Avoid making the humor feel forced or over-engineered.

            # 2. **Specific Details:**
            # - Focus on vivid details, like what happened, how you felt, and what surprised you.
            # - Avoid vague or generic insights. Always zoom in on a relatable scenario.

        # Initialize style prompt template
        style_prompt = (
            "Format this content as a tweet. Output ONLY the tweet text, no commentary or quotes:\n\n"
            "Content to format:\n{content}\n\n"
            "\nMatch closely the tone, style or voice in these reference examples:\n"
            "{examples}\n"
            # "\nAvoid repeating similar content/structure to recent tweets:\n{recent_tweets}\n\n"
        )

        user_prompt = style_prompt.format(
            content=content,
            examples=examples,
            recent_tweets=self._format_recent_tweets(recent_tweets),
            age=age
        )
        
        self.log_step(
            "Style Formatting Request",
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        response = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4
        )
        
        # Clean up the response
        response = response.strip()
        response = re.sub(r'^["\']\s*', '', response)  # Remove leading quotes
        response = re.sub(r'\s*["\']$', '', response)  # Remove trailing quotes
        response = re.sub(r'^Here\'s.*?:\s*', '', response)  # Remove any meta commentary
        
        return response

    def get_ongoing_tweets(self):
        """Get ongoing tweets with ACTI backfill if needed."""
        try:
            # Get ongoing tweets
            ongoing_tweets, _ = self.github_ops.get_file_content('ongoing_tweets.json')

            # If we have ongoing tweets but need more history
            if ongoing_tweets and len(ongoing_tweets) < self.digest_interval:
                acti_tweets = self.get_acti_tweets()
                # Combine ACTI history with ongoing tweets
                ongoing_tweets = (
                    acti_tweets[-self.digest_interval+len(ongoing_tweets):] + 
                    ongoing_tweets
                )
            # If no ongoing tweets, start with ACTI history
            elif not ongoing_tweets:
                acti_tweets = self.get_acti_tweets()
                ongoing_tweets = acti_tweets[-self.digest_interval:]

            return ongoing_tweets

        except Exception as e:
            print(f"Note: Error getting ongoing tweets: {e}")
            # Fallback to ACTI tweets
            acti_tweets = self.get_acti_tweets()
            return acti_tweets[-self.digest_interval:]

    def update_goals_progress(self, tweet_count):
        """Update progress of active goals based on tweet count and days per tweet."""
        days_elapsed = tweet_count * self.days_per_tweet
        completed = []

        for goal_id, goal_data in self.active_goals.items():
            if goal_data['type'] == 'short_term':
                if days_elapsed >= goal_data['start_day'] + goal_data['duration_days']:
                    completed.append(goal_id)
                    self.completed_goals.append({
                        'goal': goal_data['goal'],
                        'completed_at': days_elapsed,
                        'category': goal_data['category']
                    })

        # Remove completed goals from active list
        for goal_id in completed:
            del self.active_goals[goal_id]

    def load_goals_from_digest(self, digest):
        """Load new goals from digest update"""
        # Handle nested digest structure
        if 'digest' in digest:
            digest = digest['digest']
            
        current_day = len(self.completed_goals) * self.days_per_tweet
        
        # Reset active goals (but keep completion history)
        self.active_goals = {}
        
        # Load new goals from digest
        for category in digest:
            if 'projected_goals' in digest[category]:
                goals_data = digest[category]['projected_goals']
                
                # Handle short-term goals
                for goal in goals_data.get('short_term', []):
                    if isinstance(goal, dict):
                        goal_id = f"{category}_st_{len(self.active_goals)}"
                        self.active_goals[goal_id] = {
                            'goal': goal['goal'],
                            'duration_days': goal.get('duration_days', 30),
                            'start_day': current_day,
                            'category': category,
                            'type': 'short_term'
                        }
                
                # Handle long-term goals
                for goal in goals_data.get('long_term', []):
                    goal_id = f"{category}_lt_{len(self.active_goals)}"
                    goal_text = goal if isinstance(goal, str) else goal.get('goal', '')
                    self.active_goals[goal_id] = {
                        'goal': goal_text,
                        'category': category,
                        'type': 'long_term'
                    }
        
        print(f"Loaded {len(self.active_goals)} goals from digest")  # Debug log

    def _get_active_goals_context(self, tweet_count):
        """Get context about active goals and their progress."""
        try:
            # Ensure tweet_count is a number
            print(f"Tweet count: {tweet_count}")
            tweet_count = float(tweet_count) if tweet_count else 0
            days_elapsed = tweet_count * self.days_per_tweet
            goals_context = []
            
            for goal_id, goal_data in self.active_goals.items():
                if goal_data['type'] == 'short_term':
                    # Calculate progress in terms of tweets/checkpoints rather than days
                    elapsed_since_start = days_elapsed - goal_data['start_day']
                    total_duration = float(goal_data['duration_days'])
                    tweets_remaining = int((total_duration - elapsed_since_start) / self.days_per_tweet)
                    progress_phase = "early"
                        
                    # Simplified progress tracking (early, middle, final phase)
                    if elapsed_since_start >= (total_duration * 0.7):  # Final 30%
                        progress_phase = "final"
                    elif elapsed_since_start >= (total_duration * 0.3):  # Middle 40%
                        progress_phase = "middle"
                        
                    goals_context.append({
                        'type': goal_data['type'],
                        'goal': goal_data['goal'],
                        'category': goal_data['category'],
                        'phase': progress_phase,
                        'tweets_remaining': max(0, tweets_remaining)  # Ensure non-negative
                    })
                else:
                    goals_context.append({
                        'type': goal_data['type'],
                        'goal': goal_data['goal'],
                        'category': goal_data['category'],
                    })
            return goals_context
            
        except Exception as e:
            print(f"Error in _get_active_goals_context: {e}")
            return []  # Return empty list on error

    def _get_relevant_context(self, digest, tweet_type, tweet_count=0, recent_tweets=None):
        """Extract relevant context from digest based on tweet type."""
        if not digest:
            return "No specific context available."
        
        context = []

        # 1. RECENT TWEETS - Highlight context from the newest tweets
        if recent_tweets:
            formatted_tweets = self._format_recent_tweets(recent_tweets)
            context.append(formatted_tweets)

        # Handle nested digest structure
        if 'digest' in digest:
            digest = digest['digest']
        
        # Get the relevant category for the given tweet type
        category = next((cat for cat, type_ in self.category_to_tweet_type.items()
                        if type_ == tweet_type), None)
        
        if category and category in digest:
            category_data = digest[category]

            # Filter out redundant or overused phrases from recent tweets
            used_phrases = {
                tweet['content'] if isinstance(tweet, dict) else tweet
                for tweet in (recent_tweets or [])
            }
            
            # 1. ACTIVE GOALS with progress information
            context.append("\n=== ACTIVE GOALS ===")
            goals_context = self._get_active_goals_context(tweet_count)
            
            goals_by_phase = {'final': [], 'middle': [], 'early': [], 'long_term': []}
            for goal in goals_context:
                if goal['category'] == category and goal['goal'] not in used_phrases:
                    if goal['type'] == 'long_term':
                        # Long-term goals don't have phase or remaining tweets
                        goals_by_phase['long_term'].append(f"• {goal['goal']}")
                    else:
                        # Short-term goals have phase and remaining tweets
                        phase = goal.get('phase', 'early')
                        phase_info = f"({phase} phase - {goal.get('tweets_remaining', '?')} tweets remaining)"
                        goal_text = f"• {goal['goal']} {phase_info}"

                        if phase == 'final':
                            goals_by_phase['final'].append(goal_text)
                        elif phase == 'middle':
                            goals_by_phase['middle'].append(goal_text)
                        else:
                            goals_by_phase['early'].append(goal_text)

            # Add goals by phase
            if goals_by_phase['final']:
                context.append("\nUrgent Goals (Final Phase):")
                context.extend(goals_by_phase['final'])
            if goals_by_phase['middle']:
                context.append("\nOngoing Goals (Middle Phase):")
                context.extend(goals_by_phase['middle'])
            if goals_by_phase['early']:
                context.append("\nNew Goals (Early Phase):")
                context.extend(goals_by_phase['early'])
            if goals_by_phase['long_term']:
                context.append("\nLong-term Goals:")
                context.extend(goals_by_phase['long_term'])

            
            # 3. HISTORICAL CONTEXT - Supporting background
            if 'historical_summary' in category_data:
                historical_summary = category_data['historical_summary']

                # Add recent developments (MTM)
                if 'MTM' in historical_summary:
                    mtm_list = historical_summary['MTM']
                    if mtm_list:
                        context.append("\n=== PREVIOUS DEVELOPMENTS ===")
                        for mtm in mtm_list[:3]:  # Include up to 3 MTMs
                            summary = mtm.get('Summary', 'No summary available')
                            transition = mtm.get('Transition', 'No transition available')
                            if summary not in used_phrases:
                                context.append(f"• Summary: {summary}")
                                context.append(f"• Transition: {transition}")
                
                # Add earlier milestones (LTM)
                if 'LTM' in historical_summary:
                    ltm_list = historical_summary['LTM']
                    if ltm_list:
                        context.append("\n=== EARLIER KEY MILESTONES (newest first) ===")
                        for ltm in reversed(ltm_list[-6:]):  # Include the 6 most recent milestones
                            milestone = ltm.get('Milestone', 'No milestone available')
                            implications = ltm.get('Implications', 'No implications available')
                            if milestone not in used_phrases:
                                context.append(f"\n• Event: {milestone}")
                                context.append(f"• Impact: {implications}")
        
        # Join all context into a single string
        return "\n".join(context) if context else "No specific context available."
        
    def _detect_tweet_type(self, tweet):
        """Detect the type of a tweet based on its content"""
        # Simple keyword-based detection
        keywords = {
            'tech': ['coding', 'blockchain', 'crypto', '$XVI', 'algorithm', 'tech'],
            'career': ['work', 'job', 'career', 'internship', 'interview'],
            'finance': ['trading', 'market', 'investment', 'stock', 'portfolio'],
            'personal': ['friend', 'family', 'relationship', 'feel', 'life'],
            'reflection': ['think', 'wonder', 'realize', 'maybe', 'perhaps'],
            'health': ['sleep', 'tired', 'gym', 'health', 'stress']
        }
        
        tweet_text = tweet.lower() if isinstance(tweet, str) else tweet.get('content', '').lower()
        
        for type_, words in keywords.items():
            if any(word in tweet_text for word in words):
                return type_
        return 'personal'  # default type

    def _are_topics_related(self, type1, type2):
        """Define which topics naturally flow together"""
        related_topics = {
            'tech': ['career', 'finance'],
            'career': ['tech', 'finance', 'personal'],
            'finance': ['tech', 'career'],
            'personal': ['health', 'reflection', 'career'],
            'reflection': ['personal', 'career', 'health'],
            'health': ['personal', 'reflection']
        }
        
        return type2 in related_topics.get(type1, [])

def main():
    """Test the tweet generator"""
    try:
        generator = TweetGenerator()
        
        # Example usage
        latest_digest = {
            "Professional": {
                "projected": [{"event": "Exploring new trading strategies"}]
            },
            "Personal": {
                "projected": [{"event": "Planning to improve work-life balance"}]
            }
        }
        
        recent_tweets = [
            "Just finished another trading session. The markets are wild today!",
            "Need to find a better routine. Coffee isn't cutting it anymore."
        ]
        
        tweet = generator.generate_tweet(
            latest_digest=latest_digest,
            recent_tweets=recent_tweets
        )
        
        print("\nGenerated Tweet:")
        print(tweet)

    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

