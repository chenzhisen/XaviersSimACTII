import random
import json
import traceback
from datetime import datetime
from src.storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
import re
import os
from collections import deque
from typing import List, Dict, Any

class TweetGenerator:
    def __init__(self, client, model):
        self.github_ops = GithubOperations()
        self.tweets_per_year = 96
        self.digest_interval = self.tweets_per_year // 8  # ~12 tweets, about 1.5 months
        # Initialize Anthropic client
        self.client = client
        self.model = model
        self.recent_prompts = deque(maxlen=3)  # Track recent prompts to avoid repetition
        self.prompt_weights = self.get_prompt_weights_for_age()

    def get_prompt_weights_for_age(self):
        """Define prompt weights based on Xavier's age."""
        if 18 <= self.age <= 25:  # Early Career
            return {
                "Daily Reflection": 0.20,
                "Professional Update": 0.25,
                "Relationship Insights": 0.20,
                "Current Technology Observations": 0.15,
                "Major Events and Changes": 0.10,
                "Current Events Response": 0.05,
                "Engagement Response": 0.05
            }
        elif 26 <= self.age <= 45:  # Mid-Life Career Growth
            return {
                "Daily Reflection": 0.15,
                "Professional Update": 0.30,
                "Relationship Insights": 0.20,
                "Current Technology Observations": 0.20,
                "Major Events and Changes": 0.10,
                "Current Events Response": 0.05,
                "Engagement Response": 0.05
            }
        elif 46 <= self.age <= 72:  # Late Career & Legacy
            return {
                "Daily Reflection": 0.20,
                "Professional Update": 0.20,
                "Relationship Insights": 0.20,
                "Current Technology Observations": 0.20,
                "Major Events and Changes": 0.10,
                "Current Events Response": 0.05,
                "Engagement Response": 0.05
            }
        else:
            return {}  # Default empty if age is out of expected range

    def select_prompt_type(self):
        """Select a prompt type based on weighted probabilities, avoiding recent repeats."""
        prompt_choices = list(self.prompt_weights.keys())
        weights = [self.prompt_weights[prompt] for prompt in prompt_choices]

        # Choose a prompt, avoiding recent repetitions
        while True:
            selected_prompt = random.choices(prompt_choices, weights=weights, k=1)[0]
            if selected_prompt not in self.recent_prompts:
                self.recent_prompts.append(selected_prompt)
                return selected_prompt


    def generate_tweet(self, latest_digest=None, recent_tweets=None, recent_comments=None, tweet_count=0):
        """Generate a new tweet based on context"""
        try:
            # Get recent tweet contents for duplicate checking
            recent_contents = []
            if recent_tweets:
                for tweet in recent_tweets:
                    if isinstance(tweet, dict):
                        recent_contents.append(tweet['content'])
                    elif isinstance(tweet, str):
                        recent_contents.append(tweet)

            # Try up to 3 times to get a unique tweet
            for attempt in range(3):
                tweet_data = self._generate_single_tweet(latest_digest, recent_tweets, recent_comments, tweet_count)
                
                # Check if tweet is unique
                if tweet_data and tweet_data['content'] not in recent_contents:
                    return tweet_data
                else:
                    print(f"Generated duplicate tweet on attempt {attempt + 1}, retrying...")
            
            # If all attempts failed, force a different topic
            return self._generate_single_tweet(latest_digest, recent_tweets, recent_comments, tweet_count, force_new_topic=True)

        except Exception as e:
            print(f"Error generating tweet: {e}")
            traceback.print_exc()
            return None

    def daily_reflection_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, a 23-year-old on a journey to explore technology, relationships, and personal growth. 
        Generate a reflective, introspective tweet based on recent events and experiences from Xavier's life. 
        Consider Xavier's current focus on self-discovery, the impact of technology on life, and any recent 
        developments or experiences he may have had.
        """
        
        user_prompt = f"""
        Based on the following context, create a tweet where Xavier reflects on his day or recent thoughts 
        in a way that feels personal and introspective.

        CONTEXT:
        - Digest: {self.digest.get('Reflections', {}).get('historical_summary', [])}
        - Short-Term Goals: {self.digest.get('Reflections', {}).get('projected_short', [])}
        - Long-Term Goals: {self.digest.get('Reflections', {}).get('projected_long', [])}
        - Recent Tweets: {self.recent_tweets}
        - Comments on Recent Tweets: {self.comments_to_recent_tweets}

        Make sure the reflection feels authentic, with Xavier contemplating technology, his relationships, 
        or life choices. Limit the reflection to a tweet length.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def professional_update_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, a young professional with a passion for technology, blockchain, and personal growth. 
        Generate a tweet that shares an update on Xavier's recent professional activities, accomplishments, 
        or future ambitions in a way that is authentic and aligned with his career path.
        """
        
        user_prompt = f"""
        Based on the following context, create a tweet for Xavier that highlights his recent professional 
        progress, new skills, or career ambitions in technology and blockchain.

        CONTEXT:
        - Professional History: {self.digest.get('Professional', {}).get('historical_summary', [])}
        - Professional Short-Term Goals: {self.digest.get('Professional', {}).get('projected_short', [])}
        - Professional Long-Term Goals: {self.digest.get('Professional', {}).get('projected_long', [])}
        - Recent Tweets: {self.recent_tweets}
        - Major Twitter Trends in Technology: {self.major_twitter_trends}

        Make sure the tweet reflects Xavier’s professional development in a way that shows excitement 
        or progress in his field, especially regarding blockchain and technology.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def relationship_insights_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, reflecting on friendships and relationships as you navigate young adulthood. 
        Generate a tweet where Xavier shares an insight or experience related to his social connections, 
        romantic interests, or interpersonal growth.
        """
        
        user_prompt = f"""
        Using the context provided, create a tweet where Xavier reflects on his relationships, recent 
        friendship experiences, or personal insights about social interactions. 

        CONTEXT:
        - Relationship History: {self.digest.get('New Relationships and Conflicts', {}).get('historical_summary', [])}
        - Relationship Short-Term Goals: {self.digest.get('New Relationships and Conflicts', {}).get('projected_short', [])}
        - Relationship Long-Term Goals: {self.digest.get('New Relationships and Conflicts', {}).get('projected_long', [])}
        - Recent Tweets: {self.recent_tweets}
        - Comments to Recent Tweets: {self.comments_to_recent_tweets}

        The tweet should feel personal and sincere, providing insight into Xavier’s experiences or challenges 
        in friendships, dating, or personal growth.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def technology_observations_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, fascinated by advancements in technology and their impact on society. 
        Generate a tweet where Xavier shares a recent observation, thought, or question about emerging technologies 
        in his field, such as blockchain, AI, or any tech-related trends he finds intriguing.
        """
        
        user_prompt = f"""
        Create a tweet where Xavier reflects on current trends or technological developments in blockchain, AI, 
        or any other fields of interest.

        CONTEXT:
        - Technology Trends: {self.digest.get('Technology Influences', {}).get('upcoming_trends', [])}
        - Societal Shifts: {self.digest.get('Technology Influences', {}).get('societal_shifts', [])}
        - Recent Tweets on Technology: {self.recent_tweets}
        - Major Twitter Trends in Technology: {self.major_twitter_trends}

        Make sure Xavier’s observations feel relevant to his interests in technology and are connected to 
        broader technological or societal trends.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def major_events_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, reflecting on significant recent changes, decisions, or life events. 
        Generate a tweet where Xavier shares a personal milestone or important change in his life, 
        highlighting how he feels or his thoughts about this shift.
        """
        
        user_prompt = f"""
        Based on the following context, create a tweet for Xavier that captures a major life change, 
        decision, or recent milestone.

        CONTEXT:
        - Major Life Events History: {self.digest.get('Major Events', {}).get('historical_summary', [])}
        - Major Events Short-Term Goals: {self.digest.get('Major Events', {}).get('projected_short', [])}
        - Major Events Long-Term Goals: {self.digest.get('Major Events', {}).get('projected_long', [])}
        - Recent Tweets: {self.recent_tweets}
        - Comments to Recent Tweets: {self.comments_to_recent_tweets}

        Ensure the tweet feels impactful and reflective of a pivotal moment in Xavier’s life, 
        such as moving to a new place, starting a new job, or a significant decision.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def current_events_response_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, reflecting on recent global events from a future perspective. Generate a tweet where 
        Xavier comments on a major current event as if it has already happened, sharing his future insights or 
        reflections on its impact.
        """
        
        user_prompt = f"""
        Create a tweet where Xavier shares his thoughts on a recent major global event from a future perspective, 
        using the past tense to suggest it has already occurred.

        CONTEXT:
        - Major Twitter Trends: {self.major_twitter_trends}
        - Recent Tweets: {self.recent_tweets}
        - Relevant Technology and Societal Shifts: {self.digest.get('Technology Influences', {}).get('societal_shifts', [])}

        This tweet should feel relevant, insightful, and reflect Xavier’s unique perspective on technology, 
        society, or culture in response to current events.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def engagement_response_prompt(self) -> Dict[str, str]:
        system_prompt = """
        You are Xavier, actively engaging with your followers. Generate a tweet where Xavier responds to 
        a recent comment, acknowledges followers, or incorporates their input into his ongoing narrative.
        """
        
        user_prompt = f"""
        Using the context below, create a tweet where Xavier responds to a recent comment, engages with 
        followers, or includes their perspectives into his own thoughts.

        CONTEXT:
        - Recent Comments to Tweets: {self.comments_to_recent_tweets}
        - Recent Tweets: {self.recent_tweets}

        Make this tweet feel engaging and conversational, as if Xavier is interacting directly with his audience.
        """
        
        return {"system": system_prompt, "user": user_prompt}

    def _generate_single_tweet(self, latest_digest=None, recent_tweets=None, recent_comments=None, tweet_count=0, force_new_topic=False):
        """Generate a single tweet attempt with two-step process"""
        # Create logs directory if it doesn't exist
        log_dir = "data/generation_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{log_dir}/tweet_generation_{timestamp}.log"
        
        def log_to_file(content):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(content + "\n\n")
        
        # Step 1: Generate raw content
        content_system = (
            "You are an AI simulating Xavier's life from ages 22-72, compressed into 100 days. "
            "Starting as a tech founder experiencing both successes and struggles, "
            "mix important plot developments with everyday slice-of-life moments.\n"
            "Focus on ONE clear thought or moment per tweet, like:\n"
            "- Quick observations about NYC neighborhoods\n"
            "- Small daily experiences (food, weather, commute)\n"
            "- Random thoughts and musings\n"
            "- Minor frustrations or simple pleasures\n\n"
            "Not every tweet needs to advance the plot - sometimes just share authentic "
            "moments that make Xavier feel real and relatable. Choose one moment or feeling "
            "and let it stand on its own. For example:\n"
            "- 'This bodega cat just judged my 3am sandwich choice'\n"
            "- 'Missing those quiet Tokyo subway rides. NYC hits different'\n"
            "- 'First winter in NYC. Didn't know wind could feel like needles'\n"
            "- 'Found this amazing ramen spot that reminds me of Tokyo'\n"
            "Focus on the human experience first, tech achievements second."
        )
        content_prompt = self._build_prompt(latest_digest, recent_tweets, recent_comments, tweet_count)
        
        # Log each step
        log_to_file(f"=== Content System ===\n{content_system}")
        log_to_file(f"=== Content Prompt ===\n{content_prompt}")
        
        raw_content = self.client.messages.create(
            model="grok-beta",
            max_tokens=2048,
            system=content_system,
            messages=[{"role": "user", "content": content_prompt}]
        ).content[0].text.strip()
        log_to_file(f"=== Raw Content ===\n{raw_content}")
        
        # Step 2: Refine style and structure
        style_templates = self._get_style_templates(20)
        style_prompt = (
            "Rewrite this update in Xavier's authentic voice. Keep tweets simple, focused, "
            "and human. Often a single thought or feeling is more powerful than multiple statements.\n\n"
            f"ORIGINAL UPDATE:\n{raw_content}\n\n"
            "STYLE EXAMPLES:\n- " + "\n- ".join(style_templates) + "\n\n"
            "RULES:\n"
            "1. Keep the core message and emotional weight of the original\n"
            "2. Under 280 characters, but don't sacrifice important details\n"
            "3. Sound natural and conversational\n"
            "4. Focus on the main point/feeling\n"
            "5. Let significant moments have their full impact\n"
            "6. No hashtags\n"
            "7. Use X handles sparingly and only when naturally relevant\n"
            "8. Skip unnecessary context\n"
            "9. Write as if followers already know what you're talking about\n"
        )
        
        # Add recent tweets for contrast
        if recent_tweets:
            recent_examples = recent_tweets[-self.digest_interval:] if len(recent_tweets) > self.digest_interval else recent_tweets
            style_prompt += "\nRECENT TWEETS (use different patterns/structures than these):\n"
            for tweet in recent_examples:
                content = tweet['content'] if isinstance(tweet, dict) else tweet
                style_prompt += f"- {content}\n"
            style_prompt += "\nEnsure your response uses different sentence structures and patterns than the above tweets.\n"
        
        log_to_file(f"=== Style Prompt ===\n{style_prompt}")
        
        refined_tweet = self.client.messages.create(
            model="grok-beta",
            max_tokens=2048,
            system="You are a writing style expert. Rewrite the given update while preserving its meaning.",
            messages=[{"role": "user", "content": style_prompt}]
        ).content[0].text.strip()
        log_to_file(f"=== Refined Tweet ===\n{refined_tweet}")
        
        # Clean up the response
        tweet = refined_tweet.split("\n")[-1].strip()
        
        # Ensure consistent $XVI formatting
        tweet = re.sub(r"\bXVI\b", "$XVI", tweet)
        
        # Replace GitHub Copilot with @cursor_ai
        tweet = re.sub(r"(?i)github copilot", "@cursor_ai", tweet)
        
        # Return both raw and refined content
        return {
            'content': tweet,
            'raw_content': raw_content,
            'timestamp': datetime.now().isoformat()
        }

    def _get_style_templates(self, sample_count=20):
        """Get random tweets from XaviersSim.json as style templates"""
        try:
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
            
            if len(all_tweets) > sample_count:
                style_templates = random.sample(all_tweets, sample_count)
            else:
                style_templates = all_tweets
                
            print(f"Selected {len(style_templates)} style template tweets")
            return style_templates
                
        except Exception as e:
            print(f"Error getting style templates: {e}")
            return []

    def _get_historical_tweets(self, count):
        """Get last N tweets from XaviersSim.json"""
        try:
            content, _ = self.github_ops.get_file_content('XaviersSim.json')
            if not content:
                return []
            
            # Collect all tweets and sort by age
            all_tweets = []
            for age_range, tweets in content.items():
                all_tweets.extend(tweets)
            
            # Return the last 'count' tweets
            return all_tweets[-count:]
                
        except Exception as e:
            print(f"Error getting historical tweets: {e}")
            return []

    def _build_prompt(self, latest_digest=None, recent_tweets=None, recent_comments=None, tweet_count=0, force_new_topic=False):
        """Build context-aware prompt for tweet generation"""
        days_per_tweet = 365 / self.tweets_per_year
        
        prompt = (
            "Generate a brief update about Xavier's current activities and developments. Focus on:\n"
            # "1. SPECIFIC actions and outcomes\n"
            # "2. Professional developments (70% of updates)\n"
            # "3. Personal growth and experiences (30% of updates)\n"
            # "4. Concrete details over abstract thoughts\n"
            # "1. Only mention $XVI when directly relevant\n\n"
            "Write in simple, clear language - style will be refined later.\n"
        )

        # Add temporal context
        if tweet_count > 0:
            days_elapsed = tweet_count * days_per_tweet
            current_age = 22 + (tweet_count / self.tweets_per_year)
            prompt += (
                f"\nTIME CONTEXT:\n"
                f"- Xavier is currently {current_age:.1f} years old\n"
                f"- This update advances the story by ~{days_per_tweet:.1f} days\n"
            )

        # Special context for first tweet
        if tweet_count == 0:
            prompt += (
                "\nFIRST UPDATE CONTEXT:\n"
                "- Set during transition from Japan to NYC\n"
                "- Show impact of Japan experience\n"
                "- Include both excitement and uncertainty\n"
            )
        
        # Birthday context
        current_age = 22 + (tweet_count / self.tweets_per_year)
        if (tweet_count % self.tweets_per_year) in range(1, 2):
            prompt += (
                f"\nBIRTHDAY UPDATE:\n"
                f"- Xavier just turned {int(current_age)}\n"
                "- Include reflection on this milestone\n"
                "- Connect age to current developments\n"
            )

        # Add projected developments
        if latest_digest and 'digest' in latest_digest:
            prompt += "\nADVANCE THESE DEVELOPMENTS:\n"
            digest_content = latest_digest['digest']
            for area, data in digest_content.items():
                if isinstance(data, dict) and 'projected' in data and data['projected']:
                    for proj in data['projected']:
                        prompt += f"- {proj}\n"

        # Add safety check for recent_tweets
        recent_tweets = recent_tweets if recent_tweets else []
        needed_tweets = self.digest_interval - len(recent_tweets)
        
        # Get existing tweets if we need more context
        if needed_tweets > 0:
            try:
                xavier_sim_content, _ = self.github_ops.get_file_content('XaviersSim.json')
                if xavier_sim_content and isinstance(xavier_sim_content, dict):
                    prompt += "HISTORICAL TWEETS from XaviersSim:\n"
                    all_tweets = []
                    for age_range, tweets in xavier_sim_content.items():
                        all_tweets.extend(tweets)
                    # Get only the number of tweets we need from the end
                    for tweet in all_tweets[-needed_tweets:]:
                        prompt += f"- {tweet}\n"
                    prompt += "\n"
            except Exception as e:
                print(f"Error loading existing tweets: {e}")
                traceback.print_exc()
        # Add recent tweets context
        if recent_tweets:
            prompt += "\nRECENT CONTEXT:\n"
            digest_tweets = recent_tweets[-self.digest_interval:] if len(recent_tweets) > self.digest_interval else []
            for tweet in digest_tweets:
                content = tweet['content']['content'] if isinstance(tweet, dict) else tweet
                prompt += f"- {content}\n"
            
        prompt += "\nGenerate a single tweet that shows a new development in Xavier's story:\n"
        return prompt

    def get_ongoing_tweets(self):
        """Get ongoing tweets from storage"""
        try:
            content, _ = self.github_ops.get_file_content('ongoing_tweets.json')
            return content if content else []
        except:
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
