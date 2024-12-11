import random
import json
import traceback
from datetime import datetime, timedelta
from src.storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
from openai import OpenAI
import re
import os
from collections import deque
from typing import List, Dict, Any, Union, Optional
from difflib import SequenceMatcher
import time
from src.utils.ai_completion import AICompletion

class TweetGenerator:
    def __init__(self, model, client, tweets_per_year=96, digest_interval=24, is_production=False, start_date=datetime(2025, 1, 1)):
        """Initialize the tweet generator."""
        self.model = model
        self.client = client
        self.tweets_per_year = tweets_per_year
        self.days_per_tweet = 384 / tweets_per_year # use 384 to align with tweet count
        self.digest_interval = digest_interval
        self.start_date = start_date
        self.github_ops = GithubOperations(is_production=is_production)
        self.acti_tweets = []
        self.ai = AICompletion(client, model)
        
        # Load life phases data with debug prints
        try:
            life_phases_content, _ = self.github_ops.get_file_content('life_phases.json')
            
            if life_phases_content is None:
                print("Warning: life_phases_content is None")
                self.life_phases = {}
            else:
                if isinstance(life_phases_content, str):
                    self.life_phases = json.loads(life_phases_content)
                else:
                    self.life_phases = life_phases_content
                
            print(f"Parsed life phases type: {type(self.life_phases)}")
            print(f"Life phases keys: {self.life_phases.keys() if self.life_phases else 'No keys'}")
            
        except Exception as e:
            print(f"Error loading life phases: {e}")
            traceback.print_exc()
            self.life_phases = {}
        
        # Update log directory based on environment
        env_dir = "prod" if is_production else "dev"
        self.log_dir = f"logs/{env_dir}/tweets"
        self.log_file = os.path.join(
            self.log_dir,
            f"tweet_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Create log directories if they don't exist
        os.makedirs(self.log_dir, exist_ok=True)
                
        # Tweet length constraints
        self.min_chars = 16     # Allow very short, impactful tweets
        self.max_chars = 2048   # Allow for occasional longer form thoughts
        
        self.tmp_tweets_file = 'tmp/upcoming_tweets.json'  # Path in the repo
        
        self.tweet_history = set()  # For duplicate detection
        self.current_day = 0  # Track days since start
    
    def _get_acti_tweets_examples(self, count=5):
        """Get reference tweets from curated examples."""
        curated_examples = [
            "Can’t decide where to stay—East Side or West Side? East has the hustle, West has the charm.",
            "I ran into Barron Trump while walking around campus and tried to act casual, but all I could think about was how to ask him if his father's hair tips truly hold any merit!",
            "Trying to figure out how to make my dating life more interesting. Any suggestions? Dinner and a movie feels too cliché.",
            "Random question: if I was just a character, would I even be aware of it?",
            "Feeling tempted to jump on before it blows up. What wallet should I use?",
            "Trying to decide if I should invite that girl I’ve been lowkey crushing on. Imagine her seeing my dance moves… or maybe not."    
        ]
        
        # Get additional real reference tweets if available
        if self.acti_tweets:
            real_tweets = random.sample(
                self.acti_tweets, 
                min(count, len(self.acti_tweets))
            )
            curated_examples = curated_examples + real_tweets
        
        formatted_examples = "\n".join(f"{i+1}. {tweet}" for i, tweet in enumerate(curated_examples))
        return formatted_examples

    def log_step(self, step_name, **kwargs):
        """Log a generation step with all relevant information."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"\n=== {step_name} === {timestamp}\n"
        
        for key, value in kwargs.items():
            log_entry += f"{key}:\n{value}\n\n"
            
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "="*50 + "\n")

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

    def _get_acti_tweets(self):
        content, _ = self.github_ops.get_file_content('XaviersSim.json')
        self.acti_tweets_by_age = content

        # Collect all tweets from all age ranges
        acti_tweets = []
        for age_range, tweets in content.items():
            # Extract content if tweet is a dict, otherwise use the tweet string directly
            for tweet in tweets:
                if isinstance(tweet, dict):
                    acti_tweets.append(tweet.get('content', ''))
                else:
                    acti_tweets.append(tweet)
        self.acti_tweets = acti_tweets

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
        
        formatted = f"\n=== RECENT TWEETS (newest first, {int(self.days_per_tweet):.1f} days has passed since last tweet) ===\n\n"
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




    def get_ongoing_tweets(self):
        """Get ongoing tweets with ACTI backfill if needed."""
        try:
            # Single call to get ongoing tweets
            ongoing_tweets, _ = self.github_ops.get_file_content('ongoing_tweets.json')

            # If we have ongoing tweets but need more history
            if ongoing_tweets:
                if len(ongoing_tweets) < self.digest_interval:
                    self._get_acti_tweets()
                    # Combine ACTI history with ongoing tweets
                    ongoing_tweets = (
                        self.acti_tweets[-self.digest_interval+len(ongoing_tweets):] + 
                        ongoing_tweets
                    )
                return ongoing_tweets, None
            
            # If no ongoing tweets, use ACTI tweets
            self._get_acti_tweets()
            ongoing_tweets = self.acti_tweets[-self.digest_interval:]
            return ongoing_tweets, self.acti_tweets_by_age

        except Exception as e:
            print(f"Note: Error getting ongoing tweets: {e}")
            # Fallback to ACTI tweets if not already loaded
            if not hasattr(self, 'acti_tweets'):
                self._get_acti_tweets()
            return self.acti_tweets[-self.digest_interval:], None

    def _get_relevant_context(self, digest, tweet_count=0, recent_tweets=None):
        """Extract relevant context from digest based on tweet type."""
        if not digest:
            return "No specific context available."
        
        context = []
        
        # 1. RECENT TWEETS
        if recent_tweets:
            formatted_tweets = "\n***MOST IMPORTANT: EACH TWEET SHOULD SHOW CLEAR PROGRESS ON THE IMMEDIATE FOCUS GOALS***\n\n"
            formatted_tweets += self._format_recent_tweets(recent_tweets)
            context.append(formatted_tweets)

        # 2. NARRATIVE DIRECTION AND GOALS
        narrative = digest.get('digest', {})
        
        # Add synthesis context if present
        synthesis = narrative.get('synthesis')
        if synthesis:
            context.append("\n=== SYNTHESIS STATUS ===")
            if synthesis.get('preparation'):
                context.append("Current Preparation:")
                for prep in synthesis['preparation']:
                    context.append(f"• {prep}")
            
            if synthesis.get('process'):
                context.append("\nOngoing Process:")
                for proc in synthesis['process']:
                    context.append(f"• {proc}")
            
            if synthesis.get('outcomes'):
                context.append("\nTargeted Outcomes:")
                for outcome in synthesis['outcomes']:
                    context.append(f"• {outcome}")
            
            # Add synthesis proximity awareness
            proximity = narrative.get('synthesis_proximity', {})
            if proximity:
                context.append(f"\nSynthesis Timeline:")
                context.append(f"• Years remaining: {proximity.get('years_remaining', 'unknown')}")
                context.append(f"• Status: {proximity.get('preparation_status', 'ongoing')}")
                context.append(f"• Priority: {proximity.get('priority_level', 'normal')}")
        
        # Add current story context
        current_story = narrative.get('Current_Story')
        if current_story:
            context.append("\n=== CURRENT STORY ===")
            context.append(current_story)
        
        # Add current direction
        current_direction = narrative.get('Current_Direction')
        if current_direction:
            context.append("\n=== CURRENT TRAJECTORY ===")
            context.append(current_direction)
        
        # Add community engagement context
        community = digest.get('community', {})
        if community:
            context.append("\n=== COMMUNITY ENGAGEMENT ===")
            context.append("Social Media Focus:")
            for focus in community.get('social_media', []):
                context.append(f"• {focus}")
            
            context.append("\nCommunity Building:")
            for activity in community.get('community_building', []):
                context.append(f"• {activity}")
            
            context.append("\nConference/Event Participation:")
            for event in community.get('conferences', []):
                context.append(f"• {event}")
        
        # Add immediate focus goals
        next_chapter = narrative.get('Next_Chapter', {})
        if next_chapter:
            context.append("\n=== CURRENT GOALS ===")
            immediate_focus = next_chapter.get('Immediate_Focus', {})
            if isinstance(immediate_focus, dict):
                # Professional goals
                context.append("Professional Focus:")
                professional = immediate_focus.get('Professional', '')
                context.append(f"• {professional}")
                
                # Personal goals
                context.append("\nPersonal Focus:")
                personal = immediate_focus.get('Personal', '')
                context.append(f"• {personal}")
                
                # Reflections
                context.append("\nCurrent Reflections:")
                reflections = immediate_focus.get('Reflections', '')
                context.append(f"• {reflections}")
        
            # Add emerging threads for context
            emerging_threads = next_chapter.get('Emerging_Threads', '')
            if emerging_threads:
                context.append("\n=== EMERGING OPPORTUNITIES ===")
                context.append(f"• {emerging_threads}")
        
            # Add tech context
            tech_context = next_chapter.get('Tech_Context', [])
            if tech_context:
                context.append("\n=== TECH DEVELOPMENTS ===")
                context.append(f"• {tech_context}")
        
        return "\n".join([c for c in context if c]) if context else "No specific context available."

    def _clean_unicode_emojis(self, text):
        """Clean up Unicode emoji codes from text."""        
        if not text:
            self.log_step("Clean Emojis - Empty Input")
            return text

        # Method 1: Remove Unicode escape sequences
        cleaned = re.sub(r'\\u[0-9a-fA-F]{4,8}', '', text)
        
        # Method 2: Remove actual emoji characters (including all emoji ranges)
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"  # dingbats
            u"\U000024C2-\U0001F251" 
            u"\U0001f926-\U0001f937"
            u"\U00010000-\U0010ffff"
            u"\u2640-\u2642" 
            u"\u2600-\u2B55"
            u"\u200d"
            u"\u23cf"
            u"\u23e9"
            u"\u231a"
            u"\u3030"
            u"\ufe0f"
            "]+", flags=re.UNICODE)
        
        cleaned = emoji_pattern.sub(r'', cleaned)
        
        # Method 3: Remove any remaining special characters that might be emoji-related
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f\u200d\ufe0f\u2640-\u27bf]', '', cleaned)
        
        final_result = cleaned.strip()
        return final_result

    def _style_tweet(self, tweet_data):
        """Apply casual Twitter styling to make tweets more natural."""
        try:
            # Clean up any raw Unicode emoji codes from the content
            content = self._clean_unicode_emojis(tweet_data['content'])
            tweet_data['content'] = content
            
            age = tweet_data.get('age', 22)  # Default to 22 if not specified
            
            system_prompt = f"""You are a social media expert helping {int(age)} year old Xavier style his tweets.

                Convert the input into a casual tweet that:
                - Uses natural language and tone appropriate for age {int(age)}
                - Sometimes uses lowercase
                - Includes 0-2 relevant emojis
                - Never use hashtags, emojis, unnecessary symbols or raw Unicode emoji codes. Keep tweets natural and text-only
                - Mention public figures sparingly and only when it enhances humor or ties into the topic meaningfully.
                - May use common abbreviations (rn, tbh, ngl)
                - Keeps the same meaning but sounds like a real person tweeting
                - Shows personality and emotion matching the persona
                
                Reference examples for style and tone:
                {self._get_acti_tweets_examples()}
                """
            
            user_prompt = f"""Make this tweet sound more natural and casual while keeping the core message:
            {tweet_data['content']}"""
            
            self.log_step(
                "Tweet Styling Prompts",
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            styled_content = self.ai.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8
            )
            
            # Clean up again after styling
            styled_content = self._clean_unicode_emojis(styled_content)
            tweet_data['raw_content'] = tweet_data['content']
            tweet_data['content'] = styled_content.strip()
            
            self.log_step(
                "Tweet Styling Result",
                styled_content=tweet_data['content']
            )
            
            return tweet_data
            
        except Exception as e:
            self.log_step(
                "Tweet Styling Error",
                error=str(e),
                original_tweet=tweet_data.get('content', 'N/A')
            )
            return tweet_data  # Return original if styling fails

    def generate_tweet(self, latest_digest, age, recent_tweets, recent_comments=None, tweet_count=0, trends=None, sequence_length=1):
        """Main entry point for tweet generation."""
        try:
            # First try to get a stored tweet
            next_tweet = self._get_next_stored_tweet()
            if next_tweet:
                next_tweet['content'] = self._clean_unicode_emojis(next_tweet['content'])
                return self._style_tweet(next_tweet)
            
            # Generate new sequences until we get unique tweets
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                # Generate a sequence of tweets
                sequence = self._generate_tweet_sequence(
                    latest_digest, age, recent_tweets, 
                    trends, tweet_count, sequence_length
                )
                
                # Check all tweets in sequence for duplicates
                has_duplicate = False
                recent_contents = [t.get('content', t) if isinstance(t, dict) else t for t in recent_tweets]
                tweet_content = {}

                if len(sequence) != sequence_length:
                    retry_count += 1
                    print(f"Generated sequence length {len(sequence)} does not match expected length {sequence_length}, retrying ({retry_count}/{max_retries})...")
                    self.log_step(
                        "Generated Sequence Length Mismatch",
                        sequence_length=len(sequence),
                        expected_length=sequence_length
                    )
                    continue
                
                for tweet_data in sequence:
                    tweet_content = tweet_data.get('content') if isinstance(tweet_data, dict) else tweet_data
                    if tweet_content in recent_contents:
                        has_duplicate = True
                        break
                
                if not has_duplicate:
                    # Store extra tweets for later if we generated a sequence
                    if len(sequence) > 1:
                        self._store_upcoming_tweets(sequence[1:])
                    return self._style_tweet(sequence[0])
                
                
                retry_count += 1
                self.log_step(
                    "Duplicate Tweet Found",
                    tweet_content=tweet_content
                )
                print(f"Found duplicate tweets, retrying ({retry_count}/{max_retries})...")
            
            print("Warning: Could not generate unique tweets after max retries")
            if len(sequence) > 1:
                self._store_upcoming_tweets(sequence[1:])
            return self._style_tweet(sequence[0])  # Return first tweet even if duplicate
            
        except Exception as e:
            print(f"Error generating tweet: {e}")
            traceback.print_exc()
            return None

    def _get_experiment_context(self, age, life_phases):
        """Get experiment context from the current life phase."""
        phase_key = self._get_phase_key(age)
        if not phase_key or phase_key not in life_phases:
            return ""
        
        # Get the appropriate Xander version based on age
        phase_data = life_phases[phase_key]
        xander_data = phase_data["side_projects"]["AI_experiments"].get(f"Xander_{self._get_xander_version(age)}")
        
        if not xander_data or "experiments" not in xander_data:
            return ""
        
        experiments = xander_data["experiments"]
        guidelines = experiments.get("narrative_guidelines", {})
        
        # Format the experiment context
        context = "AI EXPERIMENTATION CONTEXT:\n"
        
        # Add current experiments
        for category, items in experiments.items():
            if category != "narrative_guidelines":
                context += f"\n{category.replace('_', ' ').title()}:\n"
                for item in items:
                    context += f"- {item}\n"
        
        # Add narrative guidelines
        context += "\nNARRATIVE GUIDELINES:\n"
        for phase, steps in guidelines.items():
            context += f"\n{phase.title()}:\n"
            for step in steps:
                context += f"- {step}\n"
        
        return context

    def _generate_tweet_sequence(self, digest, age, recent_tweets, trends=None, tweet_count=0, sequence_length=16):
        """Generate a sequence of related tweets that tell a coherent story."""
        try:
            # Calculate exact day number and sequence timing
            self.current_day = self._calculate_day(tweet_count)
            days_per_sequence = int(self.days_per_tweet * (sequence_length-1))
            sequence_start_day = self.current_day
            sequence_end_day = sequence_start_day + days_per_sequence
            
            # Calculate simulated date (assuming start date is January 1, 2024)
            current_date = self.start_date + timedelta(days=self.current_day)
            end_date = self.start_date + timedelta(days=sequence_end_day)

            # Add date context to special_context
            date_context = f"""
                Temporal Context:
                - Current Date: {current_date.strftime('%B %d, %Y')}
                - Sequence End Date: {end_date.strftime('%B %d, %Y')}
                - Each tweet spans approximately {int(self.days_per_tweet):.1f} days
                
                Note: Ground all references to time, events, and technology in this specific time period.
                """

            # Birthday context
            tweets_per_year = self.tweets_per_year
            current_tweet_in_year = tweet_count % tweets_per_year
            
            birthday_positions = []
            for i in range(sequence_length):
                tweet_position = (current_tweet_in_year + i) % tweets_per_year
                if tweet_position in range(1, 2):
                    birthday_positions.append(i + 1)
            
            # Check if we're approaching the end (age 72)
            is_final_sequence = age >= 71.9
            
            special_context = ""
            if is_final_sequence:
                special_context = """
                Special Context - Story Conclusion:
                - Approaching a transformative moment at age 72
                - Reference breakthrough longevity technologies of 2074
                - Hint at evolution beyond traditional human limitations
                - Maintain ambiguity about transcendence vs ending
                - Include subtle references to consciousness transfer or digital preservation
                - End with wonder and possibility rather than conclusion
                """
                sequence_length = 1  # Final tweet should stand alone
            elif tweet_count == 0:
                special_context = (
                    "\nSpecial Context - NYC Return:\n"
                    "- Just returned to NYC\n"
                    "- First tweet should naturally establish being in NYC\n"
                    "- Show excitement about the city's energy\n"
                    "- Include a specific detail about being back\n"
                    "- He has lost his job and is looking to restart his career\n"
                    "- Keep it casual and observational\n"
                )
                special_context += """After a few tweets, 
                    - Xavier starts thinking about creating an AI agent
                    - He decides to start coding it
                    - Around tweet 6-7, he names it Xander
                    - Show the natural progression of:
                        1. Getting the idea
                        2. Starting to research/plan
                        3. Beginning development
                        4. Naming it Xander
                    - Keep it organic, showing his thought process
                    - No mentions of Xander before he creates it
                """
            
            if birthday_positions:
                birthday_days = [sequence_start_day + (pos-1) * int(self.days_per_tweet) for pos in birthday_positions]
                special_context += (
                    f"\nSpecial Context - Birthday:\n"
                    f"- Just turned {int(age)}\n"
                    f"- Incorporate birthday reflection naturally on [Day {birthday_days[0]}]\n"
                    f"- Connect this milestone to current developments\n"
                )

            # Set up logging
            self.log_file = os.path.join(
                self.log_dir,
                f"tweet_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            
            self.log_step(
                "Debug Digest",
                digest=json.dumps(digest, indent=2) if digest else "None"
            )

            # Handle tweet count
            if tweet_count is None and recent_tweets:
                last_tweet = recent_tweets[-1]
                if isinstance(last_tweet, dict):
                    tweet_count = last_tweet.get('tweet_count', 0)
                else:
                    tweet_count = 0

            xander_context = self._get_xander_context(age, self.life_phases)
            
            # Format Xander development context for the prompt - with error handling
            try:
                tech_focus = xander_context.get('tech_stack', {}).get('foundation', [])
                recent_progress = xander_context.get('evolution', [])
                challenges = xander_context.get('development_challenges', [])
                
                xander_prompt = f"""
                Current Xander Development:
                - Tech Focus: {', '.join(tech_focus[:2]) if tech_focus else 'Basic AI development'}
                - Recent Progress: {', '.join(recent_progress[:2]) if recent_progress else 'Initial development'}
                - Current Challenges: {', '.join(challenges[:2]) if challenges else 'Learning fundamentals'}
                
                Social Integration:
                {self._format_social_presence(xander_context.get('social_presence', {}))}
                """
            except Exception as e:
                print(f"Error formatting Xander prompt: {e}")
                xander_prompt = """
                Current Xander Development:
                - Tech Focus: Basic AI development
                - Recent Progress: Initial development
                - Current Challenges: Learning fundamentals
                
                Social Integration:
                Early
                """
            
            system_prompt = f"""You are Xavier, currently {age} years old, on a 50-year journey from age 22 to 72.
                Your life unfolds through {self.tweets_per_year} tweets per year, each representing approximately {self.days_per_tweet} days of experiences.

                {date_context}

                {xander_prompt}

                {"CONTENT MIX (per " + str(self.digest_interval) + " tweets):"}
                {'''
                - 4-5 tweets about synthesis journey and consciousness integration
                - 3-4 tweets about personal/professional wisdom sharing
                - 3-4 tweets about Xander's evolution
                - 2-3 tweets about XVI foundation development
                - 2 tweets with philosophical reflections on unity/duality
                ''' if age >= 60 else '''
                - 4-5 tweets about personal life and experiences
                - 4-5 tweets about professional development
                - 2-3 tweets about tech projects and Xander's evolution
                - 2-3 tweets with observations and reflections
                - 1-2 tweets about XVI development and community
                '''}

                WRITING GUIDELINES:
                1. Show progress on Immediate Focus goals
                2. Weave in emerging narrative threads naturally
                3. Ground content in current tech landscape
                4. Balance achievements with struggles
                5. Use natural, conversational tone
                6. Avoid meta-commentary

                {self._get_experiment_guidelines(age)}

                REQUIRED FORMAT:
                [Day {sequence_start_day}]
                <tweet content showing progress from day {sequence_start_day-int(self.days_per_tweet)} to {sequence_start_day}>

                [Day {sequence_start_day + int(self.days_per_tweet)}]
                <tweet content showing progress from day {sequence_start_day} to {sequence_start_day + int(self.days_per_tweet)}>

                ...

                [Day {sequence_start_day + int(self.days_per_tweet*(sequence_length-1))}]
                <tweet content showing progress from day {sequence_start_day + int(self.days_per_tweet*(sequence_length-2))} to {sequence_start_day + int(self.days_per_tweet*(sequence_length-1))}>
                """
            
            context = self._get_relevant_context(digest, tweet_count, recent_tweets)
            trends_context = f"\nCurrent Trends:\n{json.dumps(trends, indent=2)}" if trends else ""
            
            user_prompt = f"""
                {special_context if 'special_context' in locals() else ''}
                
                Relevant Context:
                
                {context}

                {trends_context}

                Create a sequence of {sequence_length} tweets that:
                1. Show tangible progress on Immediate Focus goals
                2. Demonstrate steps taken toward stated objectives
                3. Include specific achievements or setbacks
                4. Reference concrete actions and decisions
                5. Build naturally toward Next Developments
                
                Remember to:
                - Each tweet should reflect {int(self.days_per_tweet):.1f} days of development
                - Include multi-day projects and their progress
                - Show how relationships and situations evolve over days
                - Reference ongoing work and its progression
                - Ensure natural time progression between tweets
                """
                
            self.log_step(
                "Generating Sequence",
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            response = self.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            self.log_step(
                "Raw Sequence Response",
                response=response
            )
            
            print("Starting to format tweets from response")
            def clean_tweet_content(content):
                """Remove hashtags and clean up tweet content."""
                # Remove hashtags (both the symbol and word)
                content = re.sub(r'#\w+', '', content)  # Remove #word
                content = re.sub(r'\s+', ' ', content)  # Clean up extra spaces
                return content.strip()
            
            formatted_tweets = []
            for i, tweet_text in enumerate(response.split('[Day')):
                print(f"Processing tweet {i} from response")
                if not tweet_text.strip():
                    continue
                
                try:
                    # Clean up the raw content first
                    raw_content = tweet_text.split(']')[-1].strip()
                    print(f"Raw content for tweet {i}: {raw_content[:50]}...")  # Show first 50 chars
                    
                    # Clean up formatting and remove hashtags
                    raw_content = re.sub(r'\*\*Day \d+\.?\d*\*\*', '', raw_content)
                    raw_content = re.sub(r'---+', '', raw_content)
                    raw_content = re.sub(r'\*\*\s*', '', raw_content)
                    raw_content = raw_content.strip('- \n')
                    
                    # Format and clean the display content
                    formatted_content = raw_content
                    formatted_content = re.sub(r'\*\*\n*', '', formatted_content)
                    formatted_content = re.sub(r'\n+', ' ', formatted_content)
                    formatted_content = clean_tweet_content(formatted_content)
                    
                    if formatted_content:                    
                        tweet_data = {
                            'content': formatted_content,
                            'age': age,
                            'timestamp': datetime.now().isoformat(),
                        }
                        
                        formatted_tweets.append(tweet_data)
                        print(f"Successfully added tweet {i}")
                        
                except Exception as e:
                    print(f"Error processing tweet {i}: {str(e)}")
                    raise
            
            self.log_step(
                "Sequence Generation Complete",
                tweet_count=str(len(formatted_tweets)),
                tweets=json.dumps(formatted_tweets, indent=2)
            )
            return formatted_tweets

        except Exception as e:
            print(f"Error generating tweet sequence: {e}")
            traceback.print_exc()
            return []

    def _store_upcoming_tweets(self, tweets, overwrite=True):
        """Store tweets for future use in the repository.
        
        Args:
            tweets: List of tweets to store
            overwrite: If True, replace existing tweets. If False, append to existing.
        """
        try:
            # Retrieve existing tweets from the repo
            existing_tweets, sha = self.github_ops.get_file_content(self.tmp_tweets_file)
            if not existing_tweets:
                existing_tweets = []

            if overwrite:
                # Simply save new tweets
                stored_tweets = tweets
                print(f"Overwriting stored tweets with {len(tweets)} new tweets")
            else:
                # Append to existing tweets
                stored_tweets = existing_tweets + tweets
                print(f"Added {len(tweets)} tweets to existing {len(existing_tweets)} tweets")
            
            # Convert to JSON and update the file in the repo
            content = json.dumps(stored_tweets, indent=2)
            self.github_ops.update_file(
                self.tmp_tweets_file,
                content,
                f"Update upcoming tweets at {datetime.now().isoformat()}",
                sha
            )
            
        except Exception as e:
            print(f"Error storing tweets: {e}")
            raise

    def _get_next_stored_tweet(self):
        """Get next stored tweet from the repository if available."""
        try:
            # Retrieve tweets from the repo
            stored_tweets, sha = self.github_ops.get_file_content(self.tmp_tweets_file)
            
            if not stored_tweets:
                print("No stored tweets available")
                return None
            
            # Get next tweet
            next_tweet = stored_tweets.pop(0)
            
            # Update the file with remaining tweets
            content = json.dumps(stored_tweets, indent=2)
            self.github_ops.update_file(
                self.tmp_tweets_file,
                content,
                f"Remove used tweet at {datetime.now().isoformat()}",
                sha
            )
            
            print(f"Retrieved next tweet, {len(stored_tweets)} remaining")
            return next_tweet
            
        except Exception as e:
            print(f"Error getting stored tweet: {e}")
            return None

    def _calculate_day(self, tweet_count):
        """Calculate the exact day number based on tweet count."""
        # Each tweet represents days_per_tweet days (approximately 3.8 days)
        # Start counting from the first tweet (tweet_count = 0)
        return int(tweet_count * self.days_per_tweet)

    def _get_xander_context(self, age, life_phases):
        """Get Xander context from the current life phase."""        
        # Default context when data is missing
        default_context = {
            "tech_stack": {"foundation": ["Basic AI development", "Learning fundamentals"]},
            "development": {"current": ["Initial development"], "challenges": ["Learning curve"]},
            "research": {"focus": ["Basic functionality"]},
        }
        
        if not life_phases:
            print("Warning: No life phases data available, using default context")
            return default_context
        
        phase_key = self._get_phase_key(age)
        print(f"Phase key: {phase_key}")
        
        if not phase_key or phase_key not in life_phases:
            print(f"Warning: Phase key {phase_key} not found in life phases")
            return default_context
        
        try:
            # Get Xander data directly from AI_development section
            phase_data = life_phases[phase_key]
            xander_data = phase_data.get("AI_development", {}).get("Xander", {})
            
            if not xander_data:
                print(f"Warning: No Xander data found for age {age}")
                return default_context
            
            result = {
                "tech_stack": xander_data.get("tech_stack", {"foundation": []}),
                "development": xander_data.get("development", {}),
                "research": xander_data.get("research", {})
            }
            return result
        
        except Exception as e:
            print(f"Error getting Xander context: {e}")
            return default_context

    def _get_xander_version(self, age):
        """Get Xander version based on age."""
        if 22 <= age < 25:
            return "1.0"
        elif 25 <= age < 30:
            return "3.0"  # As per existing data
        elif 30 <= age < 45:
            return "Evolution"
        elif 45 <= age < 60:
            return "Transcendence"
        else:
            return "Infinity"

    def _get_experiment_guidelines(self, age):
        """Get experiment guidelines based on age."""
        try:
            phase_key = self._get_phase_key(age)
            if not phase_key or phase_key not in self.life_phases:
                return ""
            
            phase_data = self.life_phases[phase_key]
            
            # Get Xander data from AI_development section
            xander_data = phase_data.get("AI_development", {}).get("Xander", {})
            if not xander_data:
                print(f"Warning: No Xander data found for age {age}")
                return ""

            # Format the experiment guidelines
            guidelines = "### AI EXPERIMENTATION CONTEXT:\n\n"
            
            # Add tech stack info
            tech_stack = xander_data.get("tech_stack", {})
            if tech_stack:
                guidelines += "\nTech Stack:\n"
                for category, items in tech_stack.items():
                    guidelines += f"\n{category.title()}:\n"
                    for item in items:
                        guidelines += f"- {item}\n"
            
            # Add development info
            development = xander_data.get("development", {})
            if development:
                guidelines += "\nDevelopment:\n"
                for category, items in development.items():
                    guidelines += f"\n{category.title()}:\n"
                    for item in items:
                        guidelines += f"- {item}\n"
            
            # Add research info if available
            research = xander_data.get("research", {})
            if research:
                guidelines += "\nResearch:\n"
                for category, items in research.items():
                    guidelines += f"\n{category.title()}:\n"
                    for item in items:
                        guidelines += f"- {item}\n"
            
            return guidelines

        except Exception as e:
            print(f"Error getting experiment guidelines: {e}")
            return ""

    def _get_phase_key(self, age):
        """Get the appropriate life phase key based on age."""
        if age < 25:
            return "22-25"
        elif age < 30:
            return "25-30"
        elif age < 45:
            return "30-45"
        elif age < 60:
            return "45-60"
        else:
            return "60+"

    def _format_social_presence(self, social_presence):
        """Format social presence data into a readable string."""
        if not social_presence:
            return "Early stages of development"
        
        formatted_text = ""
        for platform, details in social_presence.items():
            if isinstance(details, dict):
                formatted_text += f"- {platform.title()}: {details.get('status', 'In development')}\n"
            else:
                formatted_text += f"- {platform.title()}: {details}\n"
        
        return formatted_text if formatted_text else "Early stages of development"

    def _format_reflection_context(self, context):
        """Format reflection themes for prompt context."""
        reflections = context.get("reflections", {})
        return f"""
        Current Themes:
        - {' '.join(reflections.get('themes', []))}
        
        Key Questions:
        - {' '.join(reflections.get('questions', []))}
        
        Personal Growth:
        - {' '.join(reflections.get('growth', []))}
        """



