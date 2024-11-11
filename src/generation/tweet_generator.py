import random
import json
import traceback
from datetime import datetime
from src.storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
import re
import os

class TweetGenerator:
    def __init__(self):
        self.github_ops = GithubOperations()
        self.tweets_per_year = 96
        self.digest_interval = self.tweets_per_year // 8  # ~12 tweets, about 1.5 months
        # Initialize Anthropic client
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )

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

    def _analyze_patterns(self, tweets):
        """Analyze patterns while allowing natural story progression"""
        patterns = []
        contents = [t['content'] if isinstance(t, dict) else t for t in tweets]
        
        # Get tweet count to determine story phase
        tweet_count = len(contents)
        
        # Basic readability patterns (always check)
        self._check_position_patterns(contents, patterns)
        self._check_structure_patterns(contents, patterns)
        
        # Story-sensitive pattern checks
        if tweet_count < 50:  # Early story
            # More flexible in early stages
            self._check_basic_variety(contents, patterns)
        else:  # Later story
            # Allow focused themes but check for extreme repetition
            topic_balance = self._check_topic_balance(contents, patterns)
            
            # If story is naturally focusing on $XVI, don't fight it
            if topic_balance.get('$XVI', 0) > 50:
                patterns = [p for p in patterns if not p.startswith("High focus on $XVI")]
                patterns.append("NOTE: Natural story focus on $XVI detected - allowing concentration")
        
        # Meta analysis
        if len(patterns) > 3:
            patterns.append("Multiple pattern types detected - need more variation")
            
        # Add overall style recommendation
        if patterns:
            patterns.append("\nRECOMMENDATION: Try a completely different approach in:")
            patterns.append("- Sentence structure (simple/compound)")
            patterns.append("- Subject focus (self/others/tech)")
            patterns.append("- Emotional tone (neutral/excited/reflective)")
            patterns.append("- Time perspective (past/present/future)")
        
        return patterns

    def _check_semantic_patterns(self, contents, patterns):
        """Check for repeated themes and concepts"""
        semantic_categories = {
            'Tech concepts': ['AI', 'blockchain', 'crypto', 'smart contract', 'decentralized', '$XVI'],
            'Emotions': ['excited', 'nervous', 'curious', 'wondering', 'thinking'],
            'Activities': ['coding', 'meeting', 'working', 'building', 'developing'],
            'Time references': ['tomorrow', 'next week', 'soon', 'later', 'tonight'],
            'Progress markers': ['milestone', 'breakthrough', 'progress', 'achievement', 'level up']
        }
        
        for category, terms in semantic_categories.items():
            repeated_terms = []
            for term in terms:
                count = sum(1 for c in contents if term.lower() in c.lower())
                if count > 1:
                    repeated_terms.append(f"'{term}' ({count}x)")
            if repeated_terms:
                patterns.append(f"Repeated {category}: {', '.join(repeated_terms)}")

    def _check_contextual_patterns(self, contents, patterns):
        """Check for repeated context or situation types"""
        context_types = {
            'Meeting patterns': ['coffee with', 'met with', 'catching up', 'chatting with'],
            'Work patterns': ['project', 'deadline', 'working on', 'building'],
            'Learning patterns': ['learned', 'discovered', 'figured out', 'realized'],
            'Future plans': ['planning to', 'going to', 'about to', 'will be']
        }
        
        for context, phrases in context_types.items():
            repeated = []
            for phrase in phrases:
                count = sum(1 for c in contents if phrase.lower() in c.lower())
                if count > 1:
                    repeated.append(f"'{phrase}' ({count}x)")
            if repeated:
                patterns.append(f"Repeated {context}: {', '.join(repeated)}")

    def _check_narrative_patterns(self, contents, patterns):
        """Check for repeated storytelling patterns"""
        arcs = {
            'Problem-solution': ['challenge...solved', 'issue...fixed', 'bug...resolved'],
            'Discovery': ['just found', 'discovered', 'realized'],
            'Progress update': ['update on', 'progress with', 'moving forward with'],
            'Reflection-action': ['thinking about...time to', 'wondering if...lets', 'considering...maybe']
        }
        
        for arc_type, patterns_list in arcs.items():
            for pattern in patterns_list:
                parts = pattern.split('...')
                if len(parts) == 2:
                    start, end = parts
                    count = sum(1 for c in contents 
                              if start.lower() in c.lower() and end.lower() in c.lower())
                    if count > 1:
                        patterns.append(f"Repeated {arc_type} pattern: '{pattern}' ({count}x)")

    def _check_interaction_patterns(self, contents, patterns):
        """Check for repeated interaction types"""
        interaction_types = {
            'Social': ['met with', 'talked to', 'connected with'],
            'Professional': ['meeting with', 'interviewed', 'presented to'],
            'Community': ['community', 'group', 'team', 'network'],
            'Learning': ['learned from', 'taught by', 'mentored by']
        }
        
        for int_type, phrases in interaction_types.items():
            repeated = []
            for phrase in phrases:
                count = sum(1 for c in contents if phrase.lower() in c.lower())
                if count > 1:
                    repeated.append(f"'{phrase}' ({count}x)")
            if repeated:
                patterns.append(f"Repeated {int_type} interactions: {', '.join(repeated)}")

    def _check_temporal_patterns(self, contents, patterns):
        """Check for patterns in time progression"""
        temporal_markers = {
            'Future references': ['soon', 'next', 'upcoming', 'planning'],
            'Past references': ['just', 'earlier', 'yesterday', 'last week'],
            'Continuous': ['still', 'keeping', 'continuing', 'ongoing'],
            'Transitions': ['now', 'finally', 'at last', 'beginning']
        }
        
        for marker_type, phrases in temporal_markers.items():
            repeated = []
            for phrase in phrases:
                count = sum(1 for c in contents if phrase.lower() in c.lower())
                if count > 1:
                    repeated.append(f"'{phrase}' ({count}x)")
            if repeated:
                patterns.append(f"Repeated {marker_type}: {', '.join(repeated)}")

    def _check_position_patterns(self, contents, patterns):
        """Check patterns at specific positions in tweets"""
        # Start patterns
        starts = [c.split()[0].lower() for c in contents]
        if len(set(starts)) < len(starts):
            patterns.append(f"Repeated starting words: {', '.join(set(w for w in starts if starts.count(w) > 1))}")
        
        # End patterns
        endings = [c.split('.')[-1].strip().lower() for c in contents]
        if len(set(endings)) < len(endings):
            patterns.append(f"Repeated ending phrases: {', '.join(set(e for e in endings if endings.count(e) > 1))}")

    def _check_phrase_patterns(self, contents, patterns):
        """Check for repeated phrases and expressions"""
        # Common phrases to watch for
        phrase_categories = {
            'Time markers': ['today', 'just', 'finally', 'now'],
            'Action starters': ['time to', 'going to', 'about to', 'trying to'],
            'Transitions': ['turns out', 'looks like', 'seems like'],
            'Reflective': ['thinking about', 'wondering if', 'realizing that'],
            'Conclusive': ['in the end', 'after all', 'at last'],
        }
        
        # Check each category
        for category, phrases in phrase_categories.items():
            repeated_phrases = []
            for phrase in phrases:
                count = sum(1 for c in contents if phrase in c.lower())
                if count > 1:
                    repeated_phrases.append(f"'{phrase}' ({count}x)")
            if repeated_phrases:
                patterns.append(f"Repeated {category}: {', '.join(repeated_phrases)}")

    def _check_structure_patterns(self, contents, patterns):
        """Check for structural patterns in tweets"""
        # Sentence types
        structures = [self._get_sentence_structure(c) for c in contents]
        struct_counts = {s: structures.count(s) for s in set(structures)}
        if any(count > 1 for count in struct_counts.values()):
            patterns.append(f"Repeated sentence structures: {', '.join(f'{k} ({v}x)' for k, v in struct_counts.items() if v > 1)}")
        
        # Question patterns
        questions = [c for c in contents if c.endswith('?')]
        if len(questions) > 1:
            question_starts = [q.split()[0].lower() for q in questions]
            if len(set(question_starts)) < len(question_starts):
                patterns.append("Similar question structures")
        
        # Emotional markers
        exclamations = sum(1 for c in contents if c.endswith('!'))
        if exclamations > 1:
            patterns.append(f"Multiple exclamation endings ({exclamations}x)")

    def _get_sentence_structure(self, text):
        """Analyze sentence structure more comprehensively"""
        text_lower = text.lower()
        
        # Basic structure
        if text.endswith('?'):
            if text_lower.startswith(('what if', 'could ', 'what ', 'why ')):
                return 'rhetorical_question'
            return 'question'
        elif text.endswith('!'):
            return 'exclamation'
            
        # Common patterns
        if any(text_lower.startswith(p) for p in ['today', 'just', 'finally']):
            return 'time_marker_start'
        if any(p in text_lower for p in ['time to', 'going to']):
            return 'action_intention'
        if text_lower.startswith(('thinking', 'wondering', 'realizing')):
            return 'reflection'
            
        return 'statement'

    def _check_emotional_patterns(self, contents, patterns):
        """Check for repeated emotional expressions"""
        emotion_types = {
            'Excitement': ['excited', 'thrilled', 'can\'t wait', 'amazing', 'incredible'],
            'Uncertainty': ['maybe', 'perhaps', 'wondering', 'not sure', 'might'],
            'Determination': ['will', 'must', 'need to', 'going to', 'have to'],
            'Reflection': ['thinking about', 'reflecting on', 'realizing', 'understanding'],
            'Gratitude': ['thankful', 'grateful', 'appreciate', 'blessed', 'lucky']
        }
        
        for emotion, phrases in emotion_types.items():
            count = sum(1 for c in contents for p in phrases if p.lower() in c.lower())
            if count > 1:
                patterns.append(f"Repeated {emotion.lower()} expressions ({count}x)")

    def _check_subject_patterns(self, contents, patterns):
        """Check for repeated subject focus"""
        subjects = {
            'Self-focused': ['I ', 'my ', 'me ', 'myself'],
            'Project-focused': ['$XVI', 'project', 'code', 'system'],
            'People-focused': ['team', 'community', 'people', 'everyone'],
            'Tech-focused': ['AI', 'blockchain', 'algorithm', 'data']
        }
        
        for focus, terms in subjects.items():
            count = sum(1 for c in contents for t in terms if t.lower() in c.lower())
            if count > len(contents)/2:  # If more than half the tweets focus on same subject
                patterns.append(f"Over-emphasis on {focus.lower()} subjects")

    def _check_complexity_patterns(self, contents, patterns):
        """Check for repeated sentence complexity patterns"""
        for content in contents:
            # Check for compound sentences
            compounds = content.count(' and ') + content.count(' but ') + content.count(' or ')
            if compounds > 1:
                patterns.append("Multiple compound sentences - vary complexity")
            
            # Check sentence length
            words = len(content.split())
            if all(len(c.split()) == words for c in contents):
                patterns.append("Similar sentence lengths - vary more")

    def _check_topic_balance(self, contents, patterns):
        """Ensure healthy topic diversity while allowing story progression"""
        topics = {
            '$XVI': ['$XVI', 'XVI', 'token', 'cryptocurrency'],
            'Tech/Dev': ['coding', 'algorithm', 'development', 'AI', 'system'],
            'Personal': ['learning', 'thinking', 'feeling', 'life', 'growth'],
            'Social': ['team', 'community', 'people', 'friends', 'network'],
            'NYC Life': ['city', 'NYC', 'Manhattan', 'neighborhood'],
            'Innovation': ['idea', 'innovation', 'solution', 'concept'],
            'Market': ['market', 'trading', 'analysis', 'strategy']
        }
        
        # Count mentions of each topic
        topic_counts = {topic: 0 for topic in topics}
        for content in contents:
            content_lower = content.lower()
            for topic, keywords in topics.items():
                if any(keyword.lower() in content_lower for keyword in keywords):
                    topic_counts[topic] += 1
        
        # Calculate percentages
        total_tweets = len(contents)
        topic_percentages = {topic: (count / total_tweets) * 100 
                           for topic, count in topic_counts.items()}
        
        # Only warn about extreme imbalances (70%+ focus on one topic)
        for topic, percentage in topic_percentages.items():
            if percentage > 70:
                patterns.append(f"SUGGESTION: Consider adding secondary themes alongside {topic}")
                patterns.append("But don't force it if the story naturally focuses here")
        
        return topic_percentages

    def _check_basic_variety(self, contents, patterns):
        """Check for basic variety in tweet structure"""
        if not contents:
            return
            
        # Check recent tweet starts
        recent_starts = [c.split()[0].lower() for c in contents[-3:]]
        if len(set(recent_starts)) == 1:
            patterns.append("Vary your opening words")
            
        # Check sentence endings
        recent_ends = [c.split('.')[-1].strip().lower() for c in contents[-3:]]
        if len(set(recent_ends)) == 1:
            patterns.append("Vary your sentence endings")
            
        # Check for repeated phrases
        common_phrases = ['time to', 'just', 'finally', 'here we go']
        for phrase in common_phrases:
            if sum(1 for c in contents if phrase in c.lower()) > 1:
                patterns.append(f"Avoid repeating '{phrase}'")

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
