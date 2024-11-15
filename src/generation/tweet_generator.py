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
    def __init__(self, client, model, tweets_per_year=96, digest_interval=24):
        self.github_ops = GithubOperations()
        self.tweets_per_year = tweets_per_year
        self.days_per_tweet = 365 / tweets_per_year
        self.digest_interval =digest_interval   
        # Initialize Anthropic client
        self.client = client
        self.model = model
        # self.recent_prompts = deque(maxlen=3)  # Track recent prompts to avoid repetition

    def get_prompt_weights_for_age(self, age):
        """Define prompt weights based on Xavier's age."""
        if 18 <= age <= 25:  # Early Career
            return {
                "Daily Reflection": 0.20,
                "Professional Update": 0.25,
                "Relationship Insights": 0.20,
                "Current Technology Observations": 0.15,
                "Major Events and Changes": 0.10,
                "Current Events Response": 0.05,
                "Engagement Response": 0.05
            }
        elif 26 <= age <= 45:  # Mid-Life Career Growth
            return {
                "Daily Reflection": 0.15,
                "Professional Update": 0.30,
                "Relationship Insights": 0.20,
                "Current Technology Observations": 0.20,
                "Major Events and Changes": 0.10,
                "Current Events Response": 0.05,
                "Engagement Response": 0.05
            }
        elif 46 <= age <= 72:  # Late Career & Legacy
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

    def select_category(self, age, tweet_count, recent_tweets, trends):
        if tweet_count == 0:
            return "Major Events and Changes"
        if tweet_count % self.tweets_per_year in range(1, 2):
            return "Daily Reflection"
        if tweet_count < 5:
            return "Professional Update"
        
        """Select a category based on weights, avoiding recent repeats."""
        prompt_weights = self.get_prompt_weights_for_age(age)
        while True:
            category = random.choices(list(prompt_weights.keys()), weights=prompt_weights.values(), k=1)[0]
            if trends is None and category == "Current Events Response":
                continue
            if recent_tweets is None and category == "Engagement Response":
                continue
            # if category not in self.recent_prompts:
            #     self.recent_prompts.append(category)
            return category

    def add_special_context(self, tweet_count):
        """Add special context if it's the first tweet or a birthday update."""
        # First update context
        prompt = ""
        if tweet_count == 0:
            prompt = (
                "\nFIRST UPDATE CONTEXT:\n"
                "- Transition from Japan back to NYC\n"
                "- Show impact of Japan experience\n"
                "- Include both excitement and uncertainty\n\n"
            )
        
        # Birthday context
        current_age = 22 + (tweet_count / self.tweets_per_year)
        if (tweet_count % self.tweets_per_year) in range(1, 2):  # Adjust range as needed for timing
            prompt = (
                f"\nBIRTHDAY UPDATE:\n"
                f"- Xavier just turned {int(current_age)}\n"
                "- Include reflection on this milestone\n"
                "- Connect age to current developments\n\n"
            )
        return prompt
            
    def generate_tweet_prompt(self, category, digest, recent_tweets, recent_comments, age, tweet_count, trends=None):
        special_context = self.add_special_context(tweet_count)
        recent_tweets = "- " + "\n- ".join(recent_tweets)
        # print(f"Generating tweet prompt for digest: {digest}")
        """Generate the system and user prompt based on selected category."""
        time_context = self.get_time_context(age)
        if category == "Daily Reflection":
            system_prompt, user_prompt = self.generate_daily_reflection_prompts(digest, recent_tweets, recent_comments, time_context, special_context)
        elif category == "Professional Update":
            system_prompt, user_prompt = self.generate_professional_update_prompts(digest, recent_tweets, recent_comments, time_context, special_context)
        elif category == "Relationship Insights":
            system_prompt, user_prompt = self.generate_relationship_insights_prompts(digest, recent_tweets, recent_comments, time_context, special_context)
        elif category == "Current Technology Observations":
            system_prompt, user_prompt = self.generate_technology_observations_prompts(digest, recent_tweets, recent_comments, time_context, special_context)
        elif category == "Major Events and Changes":
            system_prompt, user_prompt = self.generate_major_events_prompts(digest, recent_tweets, recent_comments, time_context, special_context)
        elif category == "Current Events Response":
            system_prompt, user_prompt = self.generate_current_events_response_prompts(digest, recent_tweets, recent_comments, time_context, trends, special_context)
        elif category == "Engagement Response":
            system_prompt, user_prompt = self.generate_engagement_response_prompts(digest, recent_tweets, recent_comments, time_context, special_context)
        
                # Apply special context modifications
        return system_prompt, user_prompt
 

    def generate_tweet(self, latest_digest=None, recent_tweets=None, recent_comments=None, age=0, tweet_count=0, trends=None):
        """Generate a new tweet based on context"""
        try:
            # Get recent tweet contents for duplicate checking
            # print(f"Printing recent_tweets: {recent_tweets}")
            recent_contents = []
            if recent_tweets:
                for tweet in recent_tweets:
                    if isinstance(tweet, dict):
                        recent_contents.append(tweet['simulated_date'] + " " + tweet['content'])
                    elif isinstance(tweet, str):
                        recent_contents.append(tweet)

            # print(f"Printing recent_contents: {recent_contents}")
            # Try up to 3 times to get a unique tweet
            for attempt in range(3):
                tweet_data = self._generate_single_tweet(latest_digest['digest'], recent_contents, recent_comments, age, tweet_count, trends)
                
                # Check if tweet is unique
                if tweet_data and tweet_data['content'] not in recent_contents:
                    return tweet_data
                else:
                    print(f"Generated duplicate tweet on attempt {attempt + 1}, retrying...")
            
            # If all attempts failed, force a different topic
            return self._generate_single_tweet(latest_digest['digest'], recent_contents, recent_comments, age, tweet_count, force_new_topic=True)

        except Exception as e:
            print(f"Error generating tweet: {e}")
            traceback.print_exc()
            return None

    def get_time_context(self, age):
        """Generate a shared time context string for prompts."""
        return (
            f"\nTIME CONTEXT:\n"
            f"- Xavier is currently {age:.1f} years old\n"
            f"- This update advances the story by ~{self.days_per_tweet:.1f} days\n"
        )
    
    def generate_daily_reflection_prompts(self, digest, recent_tweets, comments, time_context, special_context, trends=None):
        """Generate system and user prompts for Daily Reflection tweets, including optional categories and time context."""

        # Extract relevant digest data, including optional categories
        reflections = digest.get("Reflections", {})
        character_dev = digest.get("Character Development", {})
        health_wellbeing = digest.get("Health & Well-being", {})
        mentorship_legacy = digest.get("Mentorship & Legacy", {})
        # System Prompt for Daily Reflection
        system_prompt = (
            "Xavier is an AI simulation exploring life from ages 18 to 72. He shares daily reflections on his experiences, "
            "including moments of introspection, personal growth, and insights into his journey. His reflections often relate to "
            "the life phase he’s in and draw upon recent experiences shared in tweets and comments.\n\n"
            "As the AI generating Xavier's daily reflections, your task is to:\n"
            "1. Summarize recent reflections and realizations based on his current experiences and digest data.\n"
            "2. Limit each reflection to one or two clear thoughts or realizations.\n"
            "3. Focus on short-term and long-term goals, as well as recent events, comments, and trends.\n\n"
            "Create a thoughtful, introspective daily reflection tweet that resonates with Xavier’s current phase of life."
            + time_context
        )

        # User Prompt for Daily Reflection
        user_prompt = (
            "Generate a concise Daily Reflection tweet for Xavier that captures one or two recent "
            "insights or realizations. Avoid mentioning previous locations if he has recently moved, focusing instead on his experiences in his current setting. "
            "Keep the message focused and impactful, emphasizing brevity. "
            "Use the following inputs:\n\n"
            
            "DIGEST DATA:\n"
            "Reflections:\n"
            f"- Historical: {reflections.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {reflections.get('projected_short', [])}\n"
            f"- Long-Term Goals: {reflections.get('projected_long', [])}\n\n"

            "OPTIONAL CATEGORIES:\n"
            "Character Development:\n"
            f"- Historical: {character_dev.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {character_dev.get('projected_short', [])}\n"
            f"- Long-Term Goals: {character_dev.get('projected_long', [])}\n\n"
            
            "Health & Well-being:\n"
            f"- Historical: {health_wellbeing.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {health_wellbeing.get('projected_short', [])}\n"
            f"- Long-Term Goals: {health_wellbeing.get('projected_long', [])}\n\n"

            "Mentorship & Legacy:\n"
            f"- Historical: {mentorship_legacy.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {mentorship_legacy.get('projected_short', [])}\n"
            f"- Long-Term Goals: {mentorship_legacy.get('projected_long', [])}\n\n"

            "RECENT TWEETS (oldest to newest):\n"
            f"{recent_tweets}\n\n"
            "COMMENTS:\n"
            f"{comments}\n\n"
            "TRENDS:\n"
            f"{trends}\n\n"
        )
        if special_context:
            user_prompt += special_context
        user_prompt += (
            "The reflection should capture one or two core thoughts or realizations relevant to Xavier’s "
            "journey, personal growth, or recent experiences. Avoid referring to places he’s recently left, and focus instead on his current context and location. Aim for a thoughtful, focused message aligned with his age and current phase of life.\n"
            + time_context
        )

        return system_prompt, user_prompt


    def generate_professional_update_prompts(self, digest, recent_tweets, comments, time_context, special_context, trends=None):
        """Generate system and user prompts for Professional Update tweets, including optional categories and time context."""

        # Extract relevant digest data, including optional categories
        professional = digest.get("Professional", {})
        financial_trajectory = digest.get("Financial Trajectory", {})
        mentorship_legacy = digest.get("Mentorship & Legacy", {})
        major_events = digest.get("Major Events", {})

        # System Prompt for Professional Update
        system_prompt = (
            "Xavier is an AI simulation progressing through his professional journey, building skills, gaining experience, "
            "and navigating challenges. His professional updates focus on one or two career-related thoughts at a time, "
            "such as recent milestones, achievements, networking experiences, or industry insights.\n\n"
            "As the AI generating Xavier's professional update, your task is to:\n"
            "1. Summarize recent professional experiences, skills development, and industry insights.\n"
            "2. Limit each update to one or two key career-related thoughts or realizations.\n"
            "3. Include any relevant short-term and long-term goals that reflect his career ambitions.\n\n"
            "Create a concise, engaging tweet that reflects Xavier’s current professional growth, focusing on one or two "
            "aspects of his career phase.\n\n"
            + time_context
        )

        # User Prompt for Professional Update
        user_prompt = (
            "Generate a Professional Update tweet for Xavier that captures one or two recent career-related insights, "
            "achievements, or goals. Focus on keeping the tweet simple and impactful. Note: Xavier had **taken a leave of absence from college**; do not use phrases like 'dropped out.' Use 'leave of absence' to correctly reflect his past college situation. Use the following inputs:\n\n"
            
            "DIGEST DATA:\n"
            "Professional:\n"
            f"- Historical: {professional.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {professional.get('projected_short', [])}\n"
            f"- Long-Term Goals: {professional.get('projected_long', [])}\n\n"

            "OPTIONAL CATEGORIES:\n"
            "Financial Trajectory:\n"
            f"- Historical: {financial_trajectory.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {financial_trajectory.get('projected_short', [])}\n"
            f"- Long-Term Goals: {financial_trajectory.get('projected_long', [])}\n\n"

            "Mentorship & Legacy:\n"
            f"- Historical: {mentorship_legacy.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {mentorship_legacy.get('projected_short', [])}\n"
            f"- Long-Term Goals: {mentorship_legacy.get('projected_long', [])}\n\n"

            "Major Events:\n"
            f"- Historical: {major_events.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {major_events.get('projected_short', [])}\n"
            f"- Long-Term Goals: {major_events.get('projected_long', [])}\n\n"

            "RECENT TWEETS (oldest to newest):\n"
            f"{recent_tweets}\n\n"
            "COMMENTS:\n"
            f"{comments}\n\n"
            "TRENDS:\n"
            f"{trends}\n\n"
        )
        if special_context:
            user_prompt += special_context
        user_prompt += (
            "The tweet should reflect Xavier’s professional journey with one or two clear career-related points. "
            "Craft an engaging, focused message that resonates with his age, ambitions, and recent experiences.\n"
            + time_context
        )

        return system_prompt, user_prompt

    def generate_relationship_insights_prompts(self, digest, recent_tweets, comments, time_context, special_context, trends=None):
        """Generate system and user prompts for Relationship Insights tweets, including optional categories and time context."""

        # Extract relevant digest data, including optional categories
        personal = digest.get("Personal", {})
        relationships_conflicts = digest.get("New Relationships and Conflicts", {})
        character_development = digest.get("Character Development", {})

        # System Prompt for Relationship Insights
        system_prompt = (
            "Xavier is an AI simulation navigating relationships, personal growth, and the complexities of forming social bonds. "
            "Relationship Insight tweets provide glimpses into his friendships, romantic interests, social interactions, and reflections "
            "on personal connections.\n\n"
            "As the AI generating Xavier's Relationship Insight, your task is to:\n"
            "1. Capture recent social experiences, personal revelations, and relationship dynamics.\n"
            "2. Focus on one or two key moments or realizations that reflect his current relationship phase.\n\n"
            "Create an engaging tweet that reflects Xavier’s relationship journey, emphasizing one or two thoughts about his relationships, "
            "emotional insights, or personal growth." + time_context
        )

        # User Prompt for Relationship Insights
        user_prompt = (
            "Generate a Relationship Insights tweet for Xavier that captures one or two recent social experiences, friendships, or reflections on "
            "personal growth. Use the following inputs:\n\n"
                
            "DIGEST DATA:\n"
            "Personal:\n"
            f"- Historical: {personal.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {personal.get('projected_short', [])}\n"
            f"- Long-Term Goals: {personal.get('projected_long', [])}\n\n"

            "New Relationships and Conflicts:\n"
            f"- Historical: {relationships_conflicts.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {relationships_conflicts.get('projected_short', [])}\n"
            f"- Long-Term Goals: {relationships_conflicts.get('projected_long', [])}\n\n"

            "OPTIONAL CATEGORY:\n"
            "Character Development:\n"
            f"- Historical: {character_development.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {character_development.get('projected_short', [])}\n"
            f"- Long-Term Goals: {character_development.get('projected_long', [])}\n\n"
            
            "RECENT TWEETS (oldest to newest):\n"
            f"{recent_tweets}\n\n"
            "COMMENTS:\n"
            f"{comments}\n\n"
            "TRENDS:\n"
            f"{trends}\n\n"
                    )
        if special_context:
            user_prompt += special_context
        user_prompt += (
            "The tweet should reflect Xavier’s social journey, relationships, and introspections in a way that aligns with his age, current "
            "life experiences, and aspirations. Craft an engaging message that conveys his relationship dynamics and emotional insights."
            + time_context
        )

        return system_prompt, user_prompt

    def generate_technology_observations_prompts(self, digest, recent_tweets, comments, time_context, special_context, trends=None):
        """Generate system and user prompts for Current Technology Observations tweets, including optional categories and time context."""

        # Extract relevant digest data, including optional categories
        professional = digest.get("Professional", {})
        reflections = digest.get("Reflections", {})
        technology_influences = digest.get("Technology Influences", {})

        # System Prompt for Current Technology Observations
        system_prompt = (
            "Xavier is an AI simulation deeply interested in technology and its societal impact, regularly reflecting on emerging trends and advancements. "
            "Technology Observations tweets capture Xavier's insights, discoveries, or thoughts on the latest in tech, innovation, and future implications.\n\n"
            "As the AI generating Xavier's Technology Observations, your task is to:\n"
            "1. Summarize Xavier's current thoughts and insights on technology.\n"
            "2. Focus on one or two key discoveries, trends, or reflections that are relevant to his career, personal interests, or society as a whole.\n\n"
            "Create an engaging tweet that conveys Xavier’s observations on technology, focusing on one main insight about innovation or societal impact."
            + time_context
        )

        # User Prompt for Current Technology Observations
        user_prompt = (
            "Generate a Current Technology Observations tweet for Xavier that reflects on one or two recent trends, discoveries, or thoughts on the role of technology. "
            "Use the following inputs:\n\n"

            "DIGEST DATA:\n"
            "Professional:\n"
            f"- Historical: {professional.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {professional.get('projected_short', [])}\n"
            f"- Long-Term Goals: {professional.get('projected_long', [])}\n\n"

            "Reflections:\n"
            f"- Historical: {reflections.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {reflections.get('projected_short', [])}\n"
            f"- Long-Term Goals: {reflections.get('projected_long', [])}\n\n"

            "OPTIONAL CATEGORY:\n"
            "Technology Influences:\n"
            f"- Upcoming Trends: {technology_influences.get('upcoming_trends', [])}\n"
            f"- Societal Shifts: {technology_influences.get('societal_shifts', [])}\n"
            f"- Tech-Driven Plot Points: {technology_influences.get('tech_driven_plot_points', [])}\n\n"

            "RECENT TWEETS (oldest to newest):\n"
            f"{recent_tweets}\n\n"
            "COMMENTS:\n"
            f"{comments}\n\n"
            "TRENDS:\n"
            f"{trends}\n\n"
                    )
        if special_context:
            user_prompt += special_context
        user_prompt += (
            "The tweet should reflect Xavier's understanding and thoughts on technology, considering his current life experiences, professional interests, and the broader societal impact of emerging tech. "
            "Craft an engaging tweet that highlights his insights on technology and innovation."
            + time_context
        )

        return system_prompt, user_prompt

    def generate_major_events_prompts(self, digest, recent_tweets, comments, time_context, special_context, trends=None):
        """Generate system and user prompts for Major Events and Changes tweets, including optional categories and time context."""

        # Extract relevant digest data, including optional categories
        major_events = digest.get("Major Events", {})
        family = digest.get("Family", {})
        reflections = digest.get("Reflections", {})
        character_development = digest.get("Character Development", {})

        # System Prompt for Major Events and Changes
        system_prompt = (
            "Xavier is an AI simulation experiencing a journey through significant life events, both personal and professional. "
            "Major Events and Changes tweets capture pivotal moments, decisions, or transitions that impact his trajectory.\n\n"
            "As the AI generating Xavier's Major Events and Changes tweets, your task is to:\n"
            "1. Highlight one key transition, major life event, or pivotal moment based on his recent experiences.\n"
            "2. Reflect on the emotional and practical impacts this change has on Xavier's life.\n\n"
            "Create an engaging tweet that captures the essence of a major event in Xavier’s life, focusing on its significance and how it shapes him."
            + time_context
        )

        # User Prompt for Major Events and Changes
        user_prompt = (
            "Generate a Major Events and Changes tweet for Xavier that captures a recent or upcoming significant life event or transition. "
            "Use the following inputs:\n\n"

            "DIGEST DATA:\n"
            "Major Events:\n"
            f"- Historical: {major_events.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {major_events.get('projected_short', [])}\n"
            f"- Long-Term Goals: {major_events.get('projected_long', [])}\n\n"

            "OPTIONAL CATEGORIES:\n"
            "Family:\n"
            f"- Historical: {family.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {family.get('projected_short', [])}\n"
            f"- Long-Term Goals: {family.get('projected_long', [])}\n\n"

            "Reflections:\n"
            f"- Historical: {reflections.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {reflections.get('projected_short', [])}\n"
            f"- Long-Term Goals: {reflections.get('projected_long', [])}\n\n"

            "Character Development:\n"
            f"- Historical: {character_development.get('historical_summary', [])}\n"
            f"- Short-Term Goals: {character_development.get('projected_short', [])}\n"
            f"- Long-Term Goals: {character_development.get('projected_long', [])}\n\n"

            "RECENT TWEETS (oldest to newest):\n"
            f"{recent_tweets}\n\n"
            "COMMENTS:\n"
            f"{comments}\n\n"
            "TRENDS:\n"
            f"{trends}\n\n"
        )
        if special_context:
            user_prompt += special_context
        user_prompt += (
            "The tweet should narrate a significant life event or transition for Xavier, capturing its impact on his personal or professional growth. "
            "It should provide a sense of change, adaptation, or introspection that resonates with his journey." 
            + time_context
        )

        return system_prompt, user_prompt

    def generate_current_events_response_prompts(self, digest, recent_tweets, comments, time_context, special_context,  recent_trends=None):
        """
        Generate the system and user prompt for a "Current Events Response" tweet.
        
        Args:
        - digest (dict): The current life digest information for Xavier.
        - recent_trends (list): A list of current events or trends for Xavier to respond to.
        - recent_tweets (list): A list of Xavier's recent tweets to reflect continuity.
        - comments (list): Recent comments on Xavier's tweets to provide engagement context.
        - time_context (str): Contextual time information for the prompt.
        
        Returns:
        - tuple: (system_prompt, user_prompt) containing system and user prompts for the API.
        """
        
        # System Prompt
        system_prompt = (
            "You are an AI simulating the life of Xavier, a tech enthusiast and professional in a futuristic setting. "
            "Generate responses to recent events or major Twitter trends, interpreting them from Xavier’s perspective as if they occurred in the past. "
            "Xavier's response should align with his current goals, personal development stage, and tech-focused career aspirations.\n"
            "\nSTRUCTURE:\n"
            "1. Acknowledge or interpret the event with thoughtful insights, humor, or curiosity as suitable.\n"
            "2. Relate the event to Xavier’s personal or professional journey, connecting it with his goals or experiences.\n"
            "3. Mention any reflective thoughts on how this event aligns with or impacts broader societal trends or personal values.\n"
            + time_context
        )

        # User Prompt
        user_prompt = (
            "Generate a Current Events Response tweet for Xavier that reflects on recent global or industry-specific events. "
            "Use the following inputs:\n\n"
            f"{time_context}\n"
            "\nCURRENT EVENTS TO RESPOND TO:\n"
            + "\n".join([f"- {trend}" for trend in recent_trends])
            + "\n\nDIGEST SUMMARY:\n"
            "Key aspects of Xavier’s life:\n"
            "- Professional: " + ", ".join(digest.get("Professional", {}).get("historical_summary", [])) + "\n"
            "- Personal: " + ", ".join(digest.get("Personal", {}).get("historical_summary", [])) + "\n"
            "\nRECENT TWEETS TO MAINTAIN CONTEXT:\n"
            + "\n".join([f"- {tweet['content']}" for tweet in recent_tweets[-self.digest_interval:]])  # Show recent context
        )

        # Add Comments Context if any
        if comments:
            user_prompt += "\n\nRECENT COMMENTS ON TWEETS:\n" + "\n".join([f"- {comment}" for comment in comments])
        
        if special_context:
            user_prompt += special_context

        return system_prompt, user_prompt

    def generate_engagement_response_prompts(self, digest, recent_tweets, comments, time_context, special_context):
        """
        Generate the system and user prompt for an "Engagement Response" tweet.
        
        Args:
        - digest (dict): The current life digest information for Xavier.
        - recent_tweets (list): A list of Xavier's recent tweets to maintain continuity in responses.
        - comments (list): Comments on Xavier's recent tweets to engage with.
        - time_context (str): Contextual time information for the prompt.
        
        Returns:
        - tuple: (system_prompt, user_prompt) containing system and user prompts for the API.
        """
        
        # System Prompt
        system_prompt = (
            "You are an AI simulating the life of Xavier, a tech-savvy individual with a public presence. "
            "Generate a response to recent comments on Xavier's tweets, creating engaging and thoughtful replies. "
            "Xavier’s engagement should reflect his current personality, life stage, and professional growth.\n"
            "\nSTRUCTURE:\n"
            "1. Acknowledge the commenter in a friendly, authentic manner.\n"
            "2. Provide thoughtful insights or reactions relevant to the comment’s content.\n"
            "3. Relate the response to Xavier’s current goals or experiences if possible.\n"
            "4. Include light humor or philosophical musings if it aligns with Xavier’s tone.\n"
            + time_context
        )

        # User Prompt
        user_prompt = (
            "Generate an Engagement Response tweet for Xavier to reply thoughtfully to recent comments. Use the following inputs:\n\n"

            f"{time_context}\n"
            "\nRECENT COMMENTS ON TWEETS:\n"
            + "\n".join([f"- {comment}" for comment in comments])
            + "\n\nRECENT TWEETS TO PROVIDE CONTEXT:\n"
            + "\n".join([f"- {tweet['content']}" for tweet in recent_tweets[-self.digest_interval:]])  # Show recent context
            + "\n\nDIGEST SUMMARY:\n"
            "Key insights from Xavier's life journey:\n"
            "- Professional: " + ", ".join(digest.get("Professional", {}).get("historical_summary", [])) + "\n"
            "- Personal: " + ", ".join(digest.get("Personal", {}).get("historical_summary", [])) + "\n"
        )
        
        if special_context:
            user_prompt += special_context

        return system_prompt, user_prompt

    def _generate_single_tweet(self, digest, recent_tweets, recent_comments, age, tweet_count=0, force_new_topic=False, trends=None):
        """Generate a single tweet attempt with two-step process, incorporating category-based prompts."""
        # Select category and generate prompts
        category = self.select_category(age, tweet_count, recent_tweets, trends) if not force_new_topic else "Daily Reflection"
        system_prompt, user_prompt = self.generate_tweet_prompt(category, digest, recent_tweets, recent_comments, age, tweet_count, trends)

        # Create logs directory if it doesn't exist
        log_dir = "logs/tweets"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log file with timestamp
        log_file = f"{log_dir}/tweet_generation_{tweet_count}.txt"
        
        def log_to_file(content):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(content + "\n\n")
        
        # Log each step
        log_to_file(f"=== Selected Category: {category} ===")
        log_to_file(f"=== System Prompt ===\n{system_prompt}")
        log_to_file(f"=== User Prompt ===\n{user_prompt}")
        
        # Step 1: Generate raw content
        raw_content = self.client.messages.create(
            model="grok-beta",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        ).content[0].text.strip()
        log_to_file(f"=== Raw Content ===\n{raw_content}")
        
        # Step 2: Refine style and structure
        style_templates = self._get_style_templates(5)
        style_prompt = (
            "Rewrite this update in Xavier's authentic voice. Keep tweets simple, focused, "
            "and human. Often a single thought or feeling is more powerful than multiple statements.\n\n"
            f"ORIGINAL UPDATE:\n{raw_content}\n\n"
            "STYLE EXAMPLES:\n- " + "\n- ".join(style_templates) + "\n\n"
            "RULES:\n"
            "1. Keep the core message and emotional weight of the original\n"
            "2. Under 280 characters, but don't sacrifice important details\n"
            "3. Sound natural and conversational\n"
            "4. Focus on the main point/feeling and avoid redundancy with recent tweets\n"
            "5. Let significant moments have their full impact\n"
            "6. No hashtags\n"
            "7. Use X handles sparingly and only when naturally relevant\n"
            "8. Skip unnecessary context\n"
            # "9. Write as if followers already know what you're talking about\n"
        )
        
        # style_prompt = (
        #      "Rewrite this update in Xavier's authentic. Match the tone, style and voice of the examples provided."
        #     f"ORIGINAL UPDATE:\n{raw_content}\n\n"
        #     "STYLE EXAMPLES:\n- " + "\n- ".join(style_templates) + "\n\n"
        # )
        # Add recent tweets for contrast
        if recent_tweets:
            recent_examples = recent_tweets[-self.digest_interval:] 
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
            'timestamp': datetime.now().isoformat(),
            'category': category  # Include selected category in response
        }

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

    def get_ongoing_tweets(self):
        content, _ = self.github_ops.get_file_content('ongoing_tweets.json')
        return content if content else []
    
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
