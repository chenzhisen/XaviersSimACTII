import json
import os
import traceback
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from src.utils.ai_completion import AICompletion
from src.storage.github_operations import GithubOperations
from pathlib import Path


class DigestGenerator:
    def __init__(self, client, model, tweet_generator=None, digest_interval=16, is_production=False):
        """Initialize the digest generator."""
        self.client = client
        self.model = model
        self.tweet_generator = tweet_generator
        self.digest_interval = digest_interval
        self.life_tracks = None
        self.ai = AICompletion(client, model)
        self.is_production = is_production
        self.github_ops = GithubOperations(is_production=is_production)
        self.ai = AICompletion(client, model)

        # Update log directory based on environment
        env_dir = "prod" if is_production else "dev"
        self.log_dir = f"logs/{env_dir}/digest"

        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

        self.tweets_per_year = 96  # Number of tweets per year
        self.days_per_tweet = 384/ self.tweets_per_year  # Days between tweets

        self.life_phases = self._load_life_phases()

    def _load_life_phases(self) -> Dict:
        """Load life phases from JSON file."""
        json_path = Path(__file__).parent.parent.parent / \
            "data" / "dev" / "life_phases.json"
        with open(json_path, 'r') as f:
            return json.load(f)

    def _get_phase_key(self, age: float) -> Optional[str]:
        """Determine the life phase key based on age."""
        if 22 <= age < 25:
            return "22-25"
        elif 25 <= age < 30:
            return "25-30"
        elif 30 <= age < 45:
            return "30-45"
        elif 45 <= age < 60:
            return "45-60"
        elif age >= 60:
            return "60+"
        return None

    def _extract_relevant_context(self, phase_data: Dict, age: float) -> Dict:
        """Extract and organize relevant context from phase data."""
        try:
            context = {
                "phase_name": phase_data.get("phase", "unknown"),
                "professional": {
                    "role": phase_data.get("professional", {}).get("role", ""),
                    "focus": phase_data.get("professional", {}).get("focus", []),
                    "achievements": phase_data.get("professional", {}).get("achievements", []),
                    "research": {
                        "trading": phase_data.get("professional", {}).get("research", {}).get("trading", []),
                        "systems": phase_data.get("professional", {}).get("research", {}).get("systems", [])
                    }
                },
                "personal": {
                    "lifestyle": phase_data.get("personal", {}).get("lifestyle", []),
                    "relationships": phase_data.get("personal", {}).get("relationships", []),
                    "interests": phase_data.get("personal", {}).get("interests", [])
                },
                "AI_development": {
                    "Xander": {
                        "tech_stack": phase_data.get("AI_development", {}).get("Xander", {}).get("tech_stack", {}),
                        "development": phase_data.get("AI_development", {}).get("Xander", {}).get("development", {}),
                        "research": phase_data.get("AI_development", {}).get("Xander", {}).get("research", {})
                    }
                },
                "$XVI": {
                    "Xavier": {
                        "role": phase_data.get("$XVI", {}).get("Xavier", {}).get("role", ""),
                        "involvement": phase_data.get("$XVI", {}).get("Xavier", {}).get("involvement", []),
                        "foundation_development": phase_data.get("$XVI", {}).get("Xavier", {}).get("foundation_development", {}).get("focus", [])
                    },
                    "Xander": {
                        "involvement": phase_data.get("$XVI", {}).get("Xander", {}).get("involvement", []),
                        "analysis": phase_data.get("$XVI", {}).get("Xander", {}).get("analysis", []),
                        "social": {
                            "discord": phase_data.get("$XVI", {}).get("Xander", {}).get("social", {}).get("discord", ""),
                            "telegram": phase_data.get("$XVI", {}).get("Xander", {}).get("social", {}).get("telegram", ""),
                            "twitter": phase_data.get("$XVI", {}).get("Xander", {}).get("social", {}).get("twitter", "")
                        }
                    }
                },
                "community": {
                    "presence": phase_data.get("community", {}).get("presence", []),
                    "events": phase_data.get("community", {}).get("events", [])
                },
                "reflections": {
                    "themes": phase_data.get("reflections", {}).get("themes", []),
                    "questions": phase_data.get("reflections", {}).get("questions", []),
                    "growth": phase_data.get("reflections", {}).get("growth", [])
                }
            }

            # Add synthesis context for age 60+
            if age >= 60:
                context["synthesis"] = phase_data.get("synthesis", {})

            return context

        except Exception as e:
            print(f"Error extracting context: {e}")
            return {}

    def _get_completion(self, system_prompt, user_prompt):
        """Get completion from AI model."""
        return self.ai.get_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

    def _get_tech_data(self, tech_evolution, age, current_date):
        """Process tech evolution data for the digest."""
        try:
            current_year = current_date.year
            tech_data = {
                "emerging_soon": [],
                "maturing_soon": [],
                "matured": [],
                "current_themes": []
            }
            
            # Get latest tech tree
            tech_trees = tech_evolution.get("tech_trees", {})
            all_years = sorted([int(year) for year in tech_trees.keys()])
            latest_epoch = max(all_years)
            latest_tree = tech_trees.get(str(latest_epoch), {})

            # Process tech data with maturity awareness
            tech_context = "\nTECHNOLOGY LANDSCAPE:\n"
            
            # Add emerging technologies that are close to maturity
            tech_context += "\nMATURING TECHNOLOGIES (approaching mainstream):\n"
            for tech in latest_tree.get("emerging_technologies", []):
                maturity_year = int(tech.get("expected_maturity_year", 9999))
                if maturity_year - current_year <= 2:  # Within 2 years of maturity
                    tech_context += f"- {tech['name']}:\n"
                    tech_context += f"  Description: {tech['description']}\n"
                    tech_context += f"  Expected Maturity: {tech['expected_maturity_year']}\n"
                    tech_context += f"  Societal Impact: {tech.get('societal_implications', 'Unknown')}\n"
            
            # Add current mainstream technologies
            tech_context += "\nESTABLISHED TECHNOLOGIES (available for use):\n"
            for tech in latest_tree.get("mainstream_technologies", []):
                if int(tech.get("maturity_year", 9999)) <= current_year:
                    tech_context += f"- {tech['name']}:\n"
                    tech_context += f"  Description: {tech['description']}\n"
                    tech_context += f"  Current Status: {tech.get('adoption_status', 'Unknown')}\n"
            
            # Add emerging trends and possibilities
            tech_context += "\nEMERGING TRENDS (to observe and contemplate):\n"
            for theme in latest_tree.get("epoch_themes", []):
                tech_context += f"- {theme['theme']}:\n"
                tech_context += f"  Description: {theme['description']}\n"
                tech_context += f"  Societal Impact: {theme.get('societal_impact', 'Unknown')}\n"
                tech_context += f"  Global Trends: {theme.get('global_trends', 'Unknown')}\n"

            # Get Xander's development context based on life phase
            phase_key = self._get_phase_key(age)
            phase_data = self.life_phases[phase_key]
            
            xander_stage = phase_data.get("AI_development", {}).get("Xander", {})
            
            tech_context += "\nXANDER DEVELOPMENT (personal AI project):\n"
            tech_context += "Foundation:\n"
            for tech in xander_stage.get("tech_stack", {}).get("foundation", []):
                tech_context += f"  - {tech}\n"
            tech_context += "Current Development:\n"
            for feature in xander_stage.get("development", {}).get("current_stage", []):
                tech_context += f"  - {feature}\n"
            tech_context += "Technical Challenges:\n"
            for challenge in xander_stage.get("development", {}).get("challenges", []):
                tech_context += f"  - {challenge}\n"

            # Add integration guidance
            tech_context += """
            TECHNOLOGY INTEGRATION GUIDANCE:
            1. Professional Development:
               - Leverage established technologies in trading systems
               - Prepare for maturing technologies in financial markets
               - Monitor emerging trends for strategic opportunities

            2. Personal Projects (Xander):
               - Experiment with current AI capabilities
               - Anticipate and prepare for upcoming AI advances
               - Contribute to emerging agent-driven economy

            3. Balance:
               - Professional applications should be practical and proven
               - Personal projects can be more experimental and forward-looking
               - Let curiosity drive exploration of emerging technologies
            """

            tech_data['context'] = tech_context
            return tech_data
            
        except Exception as e:
            print(f"Error processing tech data: {e}")
            traceback.print_exc()
            return None

    def _get_empty_structure(self):
        """Get empty structure for narrative."""
        return {
            'digest': {
                'Age': 0.0,
                'Story': '',
                'Key_Themes': '',
                'Current_Direction': '',
                'Next_Chapter': {
                    'Immediate_Focus': '',
                    'Emerging_Threads': '',
                    'Tech_Context': ''
                }
            }
        }

    def _parse_response(self, response_text, step_name, age=None):
        """Parse response text into JSON, with focused debugging."""
        try:
            print(f"\n=== Parsing {step_name} Response ===")

            # Remove any markdown formatting
            clean_text = response_text.replace('```json\n', '').replace('\n```', '').strip()

            try:
                parsed = json.loads(clean_text)

                # Validate basic structure
                if 'digest' not in parsed:
                    print(f"ERROR: Missing digest wrapper in response")
                    return self._get_empty_structure()

                # Get the narrative section
                narrative = parsed['digest']

                # Ensure required fields exist
                required_fields = ['Age', 'Story', 'Key_Themes', 'Current_Direction', 'Next_Chapter']
                for field in required_fields:
                    if field not in narrative:
                        print(f"Missing {field} in narrative")
                        if field == 'Story':
                            narrative[field] = "Story overview not available"
                        elif field == 'Key_Themes':
                            narrative[field] = []
                        elif field == 'Current_Direction':
                            narrative[field] = "Direction not specified"
                        elif field == 'Next_Chapter':
                            narrative[field] = {
                                'Immediate_Focus': {
                                    'Professional': "Professional focus not specified",
                                    'Personal': "Personal focus not specified",
                                    'Reflections': "Reflections not specified"
                                },
                                'Emerging_Threads': '',
                                'Tech_Context': ''
                            }

                # Debug Next_Chapter structure
                next_chapter = narrative.get('Next_Chapter', {})
                if not isinstance(next_chapter, dict):
                    print("ERROR: Next_Chapter is not a dictionary")
                    narrative['Next_Chapter'] = {
                        'Immediate_Focus': {
                            'Professional': "Professional focus not specified",
                            'Personal': "Personal focus not specified",
                            'Reflections': "Reflections not specified"
                        },
                        'Emerging_Threads': '',
                        'Tech_Context': ''
                    }
                else:
                    # Validate Immediate_Focus structure
                    immediate_focus = next_chapter.get('Immediate_Focus', {})
                    if not isinstance(immediate_focus, dict):
                        next_chapter['Immediate_Focus'] = {
                            'Professional': str(immediate_focus) if immediate_focus else "Professional focus not specified",
                            'Personal': "Personal focus not specified",
                            'Reflections': "Reflections not specified"
                        }
                    else:
                        # Ensure all required sections exist
                        for section in ['Professional', 'Personal', 'Reflections']:
                            if section not in immediate_focus:
                                immediate_focus[section] = f"{section} focus not specified"

                    # Validate other Next_Chapter fields
                    if 'Emerging_Threads' not in next_chapter:
                        next_chapter['Emerging_Threads'] = ''
                    if 'Tech_Context' not in next_chapter:
                        next_chapter['Tech_Context'] = ''

                # Ensure Age is float
                if 'Age' in narrative:
                    try:
                        narrative['Age'] = float(narrative['Age'])
                    except (ValueError, TypeError):
                        print(f"Invalid Age: {narrative.get('Age')}")
                        narrative['Age'] = age or 0.0

                print(f"Successfully parsed {step_name} response")
                return parsed

            except json.JSONDecodeError as e:
                print(f"\nERROR: JSON parsing failed in {step_name}")
                print(f"Error location: Line {e.lineno}, Column {e.colno}")
                return self._get_empty_structure()

        except Exception as e:
            print(f"\nERROR in {step_name}: {str(e)}")
            traceback.print_exc()
            return self._get_empty_structure()

    def _generate_digest(self, recent_tweets, age, current_date, tweet_count, latest_digest=None, max_retries=3, retry_delay=5, log_path=None, tech_evolution=None):
        """Generate a digest based on recent tweets and previous context."""
        try:
            # Ensure log directory exists
            os.makedirs(self.log_dir, exist_ok=True)

            # Generate default log path if none provided
            if log_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                log_type = "digest"
                log_path = os.path.join(
                    self.log_dir,
                    f"{log_type}_{timestamp}.log"
                )

            # Start logging
            with open(log_path, 'a') as f:
                f.write("\n=== Digest Generation Started ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Current Age: {age}\n")
                f.write(f"Current Date: {current_date}\n")
                f.write(f"Tweet Count: {tweet_count}\n")
                f.write(f"Is First Digest: {latest_digest is None}\n\n")

            # Get life phase context
            phase_key = self._get_phase_key(age)
            if not phase_key:
                raise ValueError(f"No phase key found for age {age}")
            
            phase_data = self.life_phases[phase_key]
            context = self._extract_relevant_context(phase_data, age)

            # Use latest_digest for context if available
            self.life_tracks = latest_digest or self._get_empty_structure()

            # Process tech data
            tech_data = self._get_tech_data(tech_evolution, age, current_date)

            # Handle tweets context based on type
            tweets_context = "\nDEVELOPMENTS:\n"
            if isinstance(recent_tweets, dict):  # Historical tweets
                age_brackets = sorted(recent_tweets.keys(), key=lambda x: float(
                    x.split('-')[0].replace('age ', '')))
                for age_bracket in age_brackets:
                    tweets_context += f"\n{age_bracket}:\n"
                    for tweet in recent_tweets[age_bracket]:
                        tweets_context += f"- {tweet}\n"
            else:  # Recent tweets
                for tweet in recent_tweets[-self.digest_interval:]:
                    if isinstance(tweet, dict):
                        age = tweet.get('age', 'unknown')
                        content = tweet.get('content', '')
                        tweets_context += f"Age {age:.2f}: {content}\n"
                    elif isinstance(tweet, str):
                        tweets_context += f"- {tweet}\n"
                    else:
                        print(
                            f"Warning: Unexpected tweet format: {type(tweet)}")
                        continue

            # Add previous direction and next chapter context
            previous_context = ""
            if latest_digest and 'digest' in latest_digest:
                prev_digest = latest_digest['digest']
                previous_context = f"""
                    Previous Direction: {prev_digest.get('Current_Direction', '')}

                    Previous Goals:
                    - Professional: {prev_digest.get('Next_Chapter', {}).get('Immediate_Focus', {}).get('Professional', 'Not specified')}
                    - Personal: {prev_digest.get('Next_Chapter', {}).get('Immediate_Focus', {}).get('Personal', 'Not specified')}
                    - Reflections: {prev_digest.get('Next_Chapter', {}).get('Immediate_Focus', {}).get('Reflections', 'Not specified')}
                    - Emerging: {prev_digest.get('Next_Chapter', {}).get('Emerging_Threads', '')}
                    - Tech: {prev_digest.get('Next_Chapter', {}).get('Tech_Context', '')}
                    """

            system_prompt = f"""You are a narrative designer crafting the story of Xavier's 50-year journey rom age 22 to 72. He is currently {age:.1f} years old,
                with {72 - age:.1f} years remaining in his story. His life unfolds through 96 tweets per year,
                each capturing approximately {self.days_per_tweet:.1f} days of experiences.

                {previous_context}

                This digest will be used to generate the next {self.digest_interval} tweets, guiding the narrative and themes.

                Output format must be valid JSON with this structure:
                {{
                    "digest": {{
                        "Current_Age": float,
                        "Story": "A flowing narrative of Xavier's journey so far...",
                        "Key_Themes": "3-4 recurring themes or patterns...",
                        "Current_Direction": "Where his journey appears to be heading...",
                        "Next_Chapter": {{
                            "Immediate_Focus": {{
                                "Professional": "Key developments and goals in career and projects...",
                                "Personal": "Focus on lifestyle, relationships, and personal interests...",
                                "Reflections": "Current themes, questions, and areas of growth..."
                            }},
                            "Emerging_Threads": "Longer-term themes and possibilities beginning to take shape",
                            "Tech_Context": "How current and emerging technologies might influence these developments"
                        }}
                    }}
                }}
                """

            # Update user prompt with detailed context
            user_prompt = f"""
                Current Age: {age:.1f}
                Current Date: {current_date}

                Professional Focus:
                - Role: {context['professional']['role']}
                - Focus: {', '.join(context['professional']['focus'])}
                - Research:
                  Trading: {', '.join(context['professional']['research']['trading'])}
                  Systems: {', '.join(context['professional']['research']['systems'])}

                Personal:
                - Lifestyle: {', '.join(context['personal']['lifestyle'])}
                - Relationships: {', '.join(context['personal']['relationships'])}
                - Interests: {', '.join(context['personal']['interests'])}

                Xander Development:
                - Tech Stack: {', '.join(str(item) for item in context['AI_development']['Xander']['tech_stack'].get('foundation', []))}
                - Development: {', '.join(str(item) for item in context['AI_development']['Xander']['development'].get('current_stage', []))}
                - Research: {', '.join(str(item) for item in context['AI_development']['Xander']['research'].get('consciousness', []) + context['AI_development']['Xander']['research'].get('ethics', []))}

                $XVI Development:
                - Xavier Role: {context['$XVI']['Xavier']['role']}
                - Xavier Focus: {', '.join(context['$XVI']['Xavier']['foundation_development'])}
                - Xavier Involvement: {', '.join(context['$XVI']['Xavier']['involvement'])}
                - Xander Involvement: {', '.join(context['$XVI']['Xander']['involvement'])}
                - Xander Analysis: {', '.join(context['$XVI']['Xander']['analysis'])}
                - Xander Social:
                  - Discord: {context['$XVI']['Xander']['social']['discord']}
                  - Telegram: {context['$XVI']['Xander']['social']['telegram']}
                  - Twitter: {context['$XVI']['Xander']['social']['twitter']}

                Community:
                - Presence: {', '.join(context['community']['presence'])}
                - Events: {', '.join(context['community']['events'])}

                Reflections:
                - Themes: {', '.join(context['reflections']['themes'])}
                - Questions: {', '.join(context['reflections']['questions'])}
                - Growth: {', '.join(context['reflections']['growth'])}

                {tweets_context}
                {tech_data['context']}
                """

            # Log system prompt
            with open(log_path, 'a') as f:
                f.write("\n=== System Prompt ===\n")
                f.write(system_prompt)
                f.write("\n")

            # Log user prompt
            with open(log_path, 'a') as f:
                f.write("\n=== User Prompt ===\n")
                f.write(user_prompt)
                f.write("\n")

            # Single API call for complete digest generation
            attempt = 0
            while attempt < max_retries:
                try:
                    response = self._get_completion(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt
                    )

                    # Log response
                    with open(log_path, 'a') as f:
                        f.write("\n=== AI Response ===\n")
                        f.write(response)
                        f.write("\n")

                    # Parse and validate response
                    parsed_digest = self._parse_response(
                        response, "digest generation", age)
                    if parsed_digest:
                        self.life_tracks = parsed_digest

                        # Add metadata
                        self.life_tracks['metadata'] = {
                            'simulation_age': age,
                            'simulation_time': current_date if isinstance(current_date, str) else current_date.strftime('%Y-%m-%d'),
                            'tweet_count': tweet_count,
                            'timestamp': datetime.now().isoformat(),
                            'life_context': context
                        }

                        # Only save if we have valid content
                        if self.life_tracks.get('digest', {}).get('Story'):
                            self.save_digest_to_history(self.life_tracks)

                        return self.life_tracks

                except Exception as e:
                    attempt += 1
                    error_msg = f"Error in digest generation (attempt {attempt}/{max_retries}): {str(e)}"
                    print(error_msg)
                    with open(log_path, 'a') as f:
                        f.write(f"\n=== Error (attempt {attempt}) ===\n")
                        f.write(f"{error_msg}\n")
                        f.write(f"{traceback.format_exc()}\n")
                    if attempt < max_retries:
                        time.sleep(retry_delay)

            return None

        except Exception as e:
            error_msg = f"Fatal error in digest generation: {str(e)}"
            print(error_msg)
            if log_path:
                with open(log_path, 'a') as f:
                    f.write("\n=== Fatal Error ===\n")
                    f.write(f"{error_msg}\n")
                    f.write(f"{traceback.format_exc()}\n")
            return None

    def save_digest_to_history(self, digest_content):
        """Save the digest to history using the existing history from get_latest_digest."""
        try:
            # Get existing history
            history = []
            latest = self.get_latest_digest()
            if latest:
                if isinstance(latest, dict):
                    history = [latest]
                elif isinstance(latest, list):
                    history = latest

            # Add new digest
            history.append(digest_content)

            # Save updated history
            success = self.tweet_generator.github_ops.update_file(
                "digest_history.json",
                history,
                f"Add digest from {digest_content.get('timestamp', 'unknown date')}"
            )
            
            if success:
                print("Successfully saved digest to history")
            return success

        except Exception as e:
            print(f"Error saving digest to history: {str(e)}")
            return False

    def get_latest_digest(self):
        """Get the most recent digest."""
        try:
            history_file = "digest_history.json"
            github_content = self.tweet_generator.github_ops.get_file_content(history_file)
            
            if not github_content or not isinstance(github_content, tuple):
                return None
            
            history, _ = github_content
            if not history:
                return None
            
            # Get the most recent digest
            if isinstance(history, list):
                return history[-1] if history else None
            return history
            
        except Exception as e:
            print(f"Error retrieving digest history: {str(e)}")
            return None

    def check_and_generate_digest(self, ongoing_tweets, age, current_date, tweet_count, tech_evolution=None):
        """Check if we need a new digest and generate if needed."""
        try:
            # Get latest digest
            latest_digest = self.get_latest_digest()

            # Determine if we need to generate a new digest
            should_generate = False
            if not latest_digest:
                should_generate = True
            else:
                last_digest_tweet_count = latest_digest.get(
                    'metadata', {}).get('tweet_count', 0)
                tweets_since_last_digest = tweet_count - last_digest_tweet_count

                print(f"Last digest at tweet: {last_digest_tweet_count}")
                print(f"Current tweet: {tweet_count}")
                print(f"Tweets since last digest: {tweets_since_last_digest}")

                if tweets_since_last_digest >= self.digest_interval:
                    print(
                        f"Generating new digest after {tweets_since_last_digest} tweets...")
                    should_generate = True

            # Generate new digest if needed
            if should_generate:
                recent_tweets = ongoing_tweets[-self.digest_interval:
                                               ] if latest_digest else ongoing_tweets
                latest_digest = self._generate_digest(
                    latest_digest=latest_digest,
                    recent_tweets=recent_tweets,
                    age=age,
                    current_date=current_date,
                    tweet_count=tweet_count,
                    tech_evolution=tech_evolution
                )

            return latest_digest

        except Exception as e:
            print(f"Error in digest check and generation: {str(e)}")
            return None

    def _get_xander_context(self, age):
        """Get age-appropriate Xander development context."""
        phase_key = self._get_phase_key(age)
        if not phase_key or phase_key not in self.life_phases:
            return ""
        
        xander = self.life_phases[phase_key].get('xander_context', {})
        
        return f"""
XANDER CONTEXT:
Development Stage: {xander.get('development_stage', '')}
Reference as: {', '.join(xander.get('reference_style', []))}

Current Focus:
{chr(10).join(f'- {focus}' for focus in xander.get('focus_areas', []))}

Development Guidelines:
{chr(10).join(f'- {aspect}' for aspect in xander.get('development_aspects', []))}
"""
