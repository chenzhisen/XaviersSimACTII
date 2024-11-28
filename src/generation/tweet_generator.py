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
    def __init__(self, client, model, tweets_per_year=96, digest_interval=8, is_production=False):
        self.model = model
        self.client = client
        self.tweets_per_year = tweets_per_year
        self.days_per_tweet = 365 / tweets_per_year
        self.digest_interval = digest_interval
        self.github_ops = GithubOperations(is_production=is_production)
        self.reference_tweets = []
        self.ai = AICompletion(client, model)
        
        # Update log directory based on environment
        env_dir = "prod" if is_production else "dev"
        self.log_dir = f"logs/{env_dir}/tweets"
        self.log_file = os.path.join(
            self.log_dir,
            f"tweet_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Create log directories if they don't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize by getting ACTI tweets
        self.reference_tweets = self.get_acti_tweets()
        
        # Tweet length constraints
        self.min_chars = 16     # Allow very short, impactful tweets
        self.max_chars = 2048   # Allow for occasional longer form thoughts
        
        self.tmp_tweets_file = 'tmp/upcoming_tweets.json'  # Path in the repo
    
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

    def get_time_context(self, age, days_elapsed):
        """Generate temporal context for prompts.
        
        Args:
            age: Current simulated age
            days_elapsed: Days since last tweet
        """
        persona = self.get_persona(age)     
        return f"""
        Current Context:
        - Xavier is {age:.1f} years old {persona}
        - {days_elapsed:.1f} days have passed since your last tweet
        """

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

    def get_persona(self, age):
        """Get Xavier's persona based on age."""
                # Determine life stage based on age
        if age < 25:
            persona = "a young professional finding your way"
        elif age < 35:
            persona = "an established professional in your prime"
        elif age < 45:
            persona = "a seasoned industry veteran"
        else:
            persona = "an experienced leader and mentor"
        return persona

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

    def _get_relevant_context(self, digest, tweet_count=0, recent_tweets=None):
        """Extract relevant context from digest based on tweet type."""
        if not digest:
            return "No specific context available."
        
        context = []
        
        # 1. RECENT TWEETS
        if recent_tweets:
            formatted_tweets = "\n***MOST IMPORTANT: GENERATE NEW TWEETS TO PROGRESS FROM THESE TWEETS***\n\n"
            formatted_tweets += self._format_recent_tweets(recent_tweets)
            context.append(formatted_tweets)

        # 2. CURRENT NARRATIVE AND DIRECTION
        narrative = digest.get('digest', {})  # Get the digest content directly
        if narrative:  # If we have narrative content
            context.append("\n=== CURRENT NARRATIVE ===")
            context.append(f"Story: {narrative.get('Story', '')}")
            context.append(f"\nKey Themes: {narrative.get('Key_Themes', '')}")
            context.append(f"\nCurrent Direction: {narrative.get('Current_Direction', '')}")
            
            # 3. NEXT CHAPTER DETAILS
            next_chapter = narrative.get('Next_Chapter', {})
            if next_chapter:
                context.append("\n=== NEXT DEVELOPMENTS ===")
                context.append(f"Immediate Focus: {next_chapter.get('Immediate_Focus', '')}")
                context.append(f"\nEmerging Threads: {next_chapter.get('Emerging_Threads', '')}")
                context.append(f"\nTech Context: {next_chapter.get('Tech_Context', '')}")
        
        # Join all context into a single string
        return "\n".join([c for c in context if c]) if context else "No specific context available."

    def generate_tweet(self, latest_digest, age, recent_tweets, recent_comments=None, tweet_count=0, trends=None, sequence_length=1):
        """Main entry point for tweet generation."""
        try:
            # First try to get a stored tweet
            next_tweet = self._get_next_stored_tweet()
            if next_tweet:
                return next_tweet
            
            # If no stored tweets, generate new sequence
            sequence = self._generate_tweet_sequence(
                latest_digest, age, recent_tweets, 
                trends, tweet_count, sequence_length=sequence_length
            )
            if sequence:
                print(f"Generated sequence of {len(sequence)} tweets")
                if len(sequence) > 1:
                    self._store_upcoming_tweets(sequence[1:])  # Store all but first tweet
                return sequence[0]  # Return first tweet
                        
        except Exception as e:
            print(f"Error in tweet generation: {e}")
            return None

    def _generate_tweet_sequence(self, digest, age, recent_tweets, trends=None, tweet_count=0, sequence_length=3):
        """Generate a sequence of related tweets that tell a coherent story."""
        self.log_file = os.path.join(
            self.log_dir,
            f"tweet_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        self.log_step(
            "Debug Digest",
            digest=json.dumps(digest, indent=2) if digest else "None"
        )

        # Get tweet count from the last ongoing tweet if not provided
        print(f"Getting tweet count. Current: {tweet_count}")
        if tweet_count is None and recent_tweets:
            last_tweet = recent_tweets[-1]
            if isinstance(last_tweet, dict):
                tweet_count = last_tweet.get('tweet_count', 0)
            else:
                tweet_count = 0
            print(f"Updated tweet count to: {tweet_count}")

        # Add NYC return context for first tweet
        special_context = ""
        if tweet_count == 0:
            special_context += (
                "\nSpecial Context - NYC Return:\n"
                "- Just returned to NYC\n"
                "- First tweet should naturally establish being in NYC\n"
                "- Show excitement about the city's energy\n"
                "- Include a specific detail about being back\n"
                "- Keep it casual and observational\n"
            )

        # Add birthday context if applicable
        tweets_per_year = self.tweets_per_year
        current_tweet_in_year = tweet_count % tweets_per_year
        
        birthday_positions = []
        for i in range(sequence_length):
            tweet_position = (current_tweet_in_year + i) % tweets_per_year
            if tweet_position in range(1, 2):
                birthday_positions.append(i + 1)
        
        if birthday_positions:
            special_context += (
                f"\nSpecial Context - Birthday:\n"
                f"- Just turned {int(age)}\n"
                f"- Incorporate birthday reflection naturally in tweet(s) {birthday_positions}\n"
                f"- Connect this milestone to current developments\n"
            )

        self.log_step(
            "Starting Sequence Generation",
            age=f"{age:.1f}",
            tweet_count=str(tweet_count),
            sequence_length=str(sequence_length),
            trends=json.dumps(trends, indent=2) if trends else "None",
            special_context=special_context
        )

        # Get reference tweets for style guidance
        reference_tweets = self._get_reference_tweets(5)
        examples = "\n".join(f"{i+1}. {tweet}" for i, tweet in enumerate(reference_tweets))
        
        system_prompt = f"""You are Xavier, currently {age:.1f} years old, on a 50-year journey from age 22 to 72.
        Your life unfolds through {self.tweets_per_year} tweets per year, each representing approximately {self.days_per_tweet:.1f} days of experiences.

        You are {self.get_persona(age)}, passionate about markets, AI, and philosophy.
        Your tweets should feel authentic and natural, mixing:
        - Technical insights from your work
        - Personal experiences
        - Philosophical observations about tech and society
        - Family moments
        - Humor and wit when natural
        - Playful thoughts about simulation/reality (<1% of tweets)
        - Inner monologue and reflections (<1% of tweets)
        
        Key guidelines:
        - Vary sentence structures and beginnings naturally
        - Share specific experiences and insights
        - Make observations rather than asking questions
        - Let your personality show through details
        - Keep it conversational and genuine
        - Never use hashtags, emojis, or Unicode symbols
        - Mention well-known figures (<1% of tweets) only when highly relevant
        - Vary tweet length naturally - occasionally longer for in-depth thoughts
        - Break the fourth wall occasionally with playful simulation references
        - Tone should be:
        • Casual and Witty: Capture the small absurdities and frustrations of life with humor.
        • Observational and Relatable: Make mundane moments feel engaging (e.g., subway rides, coffee runs).
        • Reflective with Personality: Share personal growth and professional ambitions in a way that feels authentic.
        • Imperfect and Unfiltered: Avoid over-polishing thoughts—let them feel raw when appropriate.


        Reference examples for style and tone:
        {examples}

        Generate a sequence of {sequence_length} tweets that progress naturally over {int(1+self.days_per_tweet):.1f} days between each tweet.

        REQUIRED FORMAT:
        [Day X]
        <tweet content>

        [Day Y]
        <tweet content>
        """
        context = self._get_relevant_context(digest, tweet_count, recent_tweets)
        time_context = self.get_time_context(age, self.days_per_tweet)
        trends_context = f"\nCurrent Trends:\n{json.dumps(trends, indent=2)}" if trends else ""
        
        user_prompt = f"""
        {time_context}
        {special_context if 'special_context' in locals() else ''}
        
        Relevant Context:
        
        ***MOST IMPORTANT: GENERATE NEW TWEETS TO PROGRESS FROM THESE RECENT TWEETS WITH IMMEDIATE FOCUS***

=== RECENT TWEETS (newest first) ===
{recent_tweets}

        {context}

        {trends_context}

        Create a sequence of {sequence_length} tweets that:
        1. Primarily advance the Immediate Focus goals
        2. Show progress on current projects and thoughts
        3. Mix in personal experiences and observations
        4. Include philosophical reflections that relate to current work
        5. Maintain natural variety in topics and structure
        
        Remember to:
        - Keep each tweet authentic and unforced
        - Vary between light and deep topics
        - Occasionally break the fourth wall
        - Let personality show through specific details
        - Ensure tweets build toward stated goals
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
        formatted_tweets = []
        for i, tweet_text in enumerate(response.split('[Day')):
            print(f"Processing tweet {i} from response")
            if not tweet_text.strip():
                continue
            
            try:
                # Clean up the raw content first
                raw_content = tweet_text.split(']')[-1].strip()
                print(f"Raw content for tweet {i}: {raw_content[:50]}...")  # Show first 50 chars
                
                raw_content = re.sub(r'\*\*Day \d+\.?\d*\*\*', '', raw_content)
                raw_content = re.sub(r'---+', '', raw_content)
                raw_content = re.sub(r'\*\*\s*', '', raw_content)
                raw_content = raw_content.strip('- \n')
                
                # Format the display content
                formatted_content = raw_content
                formatted_content = re.sub(r'\*\*\n*', '', formatted_content)
                formatted_content = re.sub(r'\n+', ' ', formatted_content)
                formatted_content = formatted_content.strip()
                
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
        # print(f"Generated sequence: {formatted_tweets}")
        
        # # Return first unique tweet
        # for tweet in formatted_tweets:
        #     if not self._is_duplicate_tweet(tweet['content'], recent_tweets):
        #         self.log_step(
        #             "Selected Unique Tweet",
        #             tweet=json.dumps(tweet, indent=2)
        #         )
        #         return tweet
                
        # # Fallback to first tweet if all are similar
        # self.log_step(
        #     "No unique tweets found, using first tweet",
        #     tweet=json.dumps(formatted_tweets[0], indent=2)
        # )
        return formatted_tweets

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


