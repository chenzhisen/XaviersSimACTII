import json
from datetime import datetime, timedelta
from storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
import traceback
import os
import time
from src.utils.ai_completion import AICompletion

class DigestGenerator:
        
    def __init__(self, github_ops, client, model, tweet_generator, simulation_time=None, simulation_age=None, tweet_count=0):
        """Initialize the digest generator"""
        self.github_ops = github_ops
        self.client = client
        self.model = model
        self.tweet_generator = tweet_generator
        self.simulation_time = simulation_time or datetime.now().strftime('%Y-%m-%d')
        self.simulation_age = float(simulation_age) if simulation_age is not None else 22.0
        self.tweet_count = tweet_count
        self.ai = AICompletion(client, model)

        # Initialize logging directories
        self.log_dir = "logs"
        self.digest_log_dir = os.path.join(self.log_dir, "digest")
        self.first_digest_log_dir = os.path.join(self.log_dir, "first_digest")
        os.makedirs(self.digest_log_dir, exist_ok=True)
        os.makedirs(self.first_digest_log_dir, exist_ok=True)
        
        # Initialize life tracks
        self.life_tracks = self._initialize_life_tracks()

    def _get_tech_data(self):
        """Get technology data relevant to the current simulation time"""
        try:
            # Clean up the timestamp format - strip any time component
            if 'T' in self.simulation_time:
                self.simulation_time = self.simulation_time.split('T')[0]
            
            simulation_date = datetime.strptime(self.simulation_time, '%Y-%m-%d')
            
            tech_data, _ = self.github_ops.get_file_content('tech_evolution.json')
            if not tech_data:
                return [], [], []
            
            if isinstance(tech_data, str):
                tech_data = json.loads(tech_data)
            
            tech_trees = tech_data.get('tech_trees', {})
            if not tech_trees:
                print("No tech trees found in evolution data")
                return [], [], []

            # Parse simulation time
            simulation_date = datetime.strptime(self.simulation_time, '%Y-%m-%d')
            simulation_year = simulation_date.year
            simulation_month = simulation_date.month

            # Determine target epoch
            current_epoch = simulation_year - (simulation_year % 5)
            next_epoch = current_epoch + 5
            months_to_next_epoch = ((next_epoch - simulation_year) * 12) - simulation_month
            target_epoch = next_epoch if months_to_next_epoch <= 6 else current_epoch

            print(f"Target epoch: {target_epoch}")  # Debug
            tech_data = tech_trees.get(str(target_epoch), {})

            if not tech_data:
                print(f"No tech data found for epoch {target_epoch}")
                return [], [], []

            # Collect mature tech, soon-to-mature tech, and societal shifts
            mature_tech = [
                {'name': tech.get('name', ''), 'description': tech.get('description', ''), 'status': tech.get('adoption_status', '')}
                for tech in tech_data.get('mainstream_technologies', [])
            ]
            
            maturing_soon = [
                {'name': tech.get('name', ''), 'description': tech.get('description', ''),
                'estimated_year': tech.get('estimated_year', ''), 'probability': tech.get('probability', '')}
                for tech in tech_data.get('emerging_technologies', [])
                if int(tech.get('estimated_year', 9999)) <= simulation_year + 1
            ]
            
            # Collect epoch themes with societal and global trends
            societal_shifts = [
                {'theme': theme.get('theme', ''), 'description': theme.get('description', ''),
                'societal_impact': theme.get('societal_impact', ''), 'global_trends': theme.get('global_trends', '')}
                for theme in tech_data.get('epoch_themes', [])
            ]

            return mature_tech, maturing_soon, societal_shifts

        except Exception as e:
            print(f"Error getting tech data: {e}")
            traceback.print_exc()
            return [], [], []

    def get_latest_digest(self):
        """Get the most recent digest with metadata"""
        try:
            content, _ = self.github_ops.get_file_content('digest_history.json')
            if content and len(content) > 0:
                self.life_tracks = content[-1]
                return content[-1]  # Return the last digest with its metadata
            return None
        except Exception as e:
            print(f"Error getting latest digest: {e}")
            return None

    def _build_tech_section(self, mature_tech, emerging_tech):
        """Builds the Technology Influences section of the prompt."""
        tech_section = "AVAILABLE TECHNOLOGIES:\nCurrently Mature Technologies (to be used in Professional track):\n"
        
        # Adding mature technologies
        for tech in mature_tech:
            tech_section += f"- {tech['name']}: {tech['description']} (Status: {tech['status']})\n"
        
        # Determine emerging technologies that are maturing soon
        tech_section += "\nTechnologies Maturing Soon (to be used in Reflections track):\n"
        for tech in emerging_tech:
            if int(tech.get('estimated_year', 9999)) <= self.simulation_year + 1:  # Within the next year
                tech_section += (
                    f"- {tech['name']}: {tech['description']} "
                    f"(Emergence Year: {tech['estimated_year']}, Probability: {tech['probability']})\n"
                )

        # Outline for Technology Influences
        tech_section += (
            "\nTECHNOLOGY INFLUENCES:\n"
            "Technology-driven plot points and societal shifts include:\n"
            "- Upcoming tech trends impacting Xavier's career and personal life\n"
            "- Major shifts in society due to new tech, like neural interfaces or space exploration\n"
        )
        
        return tech_section
        
    def _build_current_tracks_section(self):
        """Build the section describing current life tracks."""
        sections = []
        if not isinstance(self.life_tracks, dict):
            return ""

        for track_name, data in self.life_tracks.get('digest', {}).items():
            # Skip metadata fields
            if track_name in ['timestamp', 'metadata']:
                continue

            # Ensure data is a dictionary
            if not isinstance(data, dict):
                continue

            # Initialize section header
            section = f"\n{track_name}:\n"

            # General handling for simplified categories
            historical = data.get('historical_summary', {"STM": [], "MTM": [], "LTM": []})
            projected_short = data.get('projected_goals', {}).get('short_term', [])
            projected_long = data.get('projected_goals', {}).get('long_term', [])
            plot_points = data.get('plot_points', [])

            # Historical summary
            if historical:
                section += "Historical Summary:\n"
                for tier, summaries in historical.items():
                    if summaries:
                        section += f"  {tier}:\n"
                        for summary in summaries:
                            section += f"    - {summary}\n"

            # Short-term goals
            if projected_short:
                section += "Short-Term Goals:\n"
                for short_goal in projected_short:
                    if isinstance(short_goal, dict):
                        goal = short_goal.get("goal", "Unnamed Goal")
                        duration = short_goal.get("duration_days", "N/A")
                        section += f"- {goal} (Duration: {duration} days)\n"
                    else:
                        section += f"- {short_goal}\n"

            # Long-term goals
            if projected_long:
                section += "Long-Term Goals:\n"
                for long_goal in projected_long:
                    section += f"- {long_goal}\n"

            # Plot points
            if plot_points:
                section += "Plot Points:\n"
                for plot_point in plot_points:
                    description = plot_point.get("description", "No description provided.")
                    section += f"- {description}\n"

            sections.append(section)

        return "\nPrevious Life Tracks:" + "".join(sections) if sections else ""
        
    def _get_empty_structure(self):
        """Return the empty structure for responses."""
        return {
            "Career & Growth": {"MTM": [], "LTM": []},
            "Personal Life & Relationships": {"MTM": [], "LTM": []},
            "Health & Well-being": {"MTM": [], "LTM": []},
            "Financial Trajectory": {"MTM": [], "LTM": []},
            "Reflections & Philosophy": {"MTM": [], "LTM": []},
            "$XVI & Technology": {"MTM": [], "LTM": []}
        }

    def _parse_response(self, response_text, step_name, current_age=None):
        """Parse response text into JSON, with focused debugging."""
        try:
            # Remove any markdown formatting
            clean_text = response_text.replace('```json\n', '').replace('\n```', '').strip()
            
            try:
                parsed = json.loads(clean_text)
                
                # Convert list to dictionary if needed (for STM)
                if isinstance(parsed, list):
                    print(f"Warning: {step_name} returned list format, converting to dictionary")
                    return self._categorize_list_response(parsed)
                
                # Validate structure based on step
                if step_name == "STM extraction":
                    return self._validate_stm_response(parsed)
                elif step_name == "historical summary":
                    return self._validate_historical_response(parsed, current_age)
                
                return parsed
                
            except json.JSONDecodeError as e:
                print(f"\nERROR: JSON parsing failed in {step_name}")
                print(f"Error location: Line {e.lineno}, Column {e.colno}")
                print(f"Context: ...{clean_text[max(0, e.pos-50):min(len(clean_text), e.pos+50)]}...")
                if step_name == "historical summary" and hasattr(self, 'life_tracks'):
                    print("Falling back to existing life tracks")
                    return self.life_tracks.get('digest', self._get_empty_structure())
                return self._get_empty_structure()
                
        except Exception as e:
            print(f"\nERROR in {step_name}: {str(e)}")
            traceback.print_exc()
            return self._get_empty_structure()

    def _validate_stm_response(self, parsed):
        """Validate and fix STM response structure."""
        expected_categories = [
            "Career & Growth",
            "Personal Life & Relationships",
            "Health & Well-being",
            "Financial Trajectory",
            "Reflections & Philosophy",
            "$XVI & Technology"
        ]
        
        result = {}
        for category in expected_categories:
            result[category] = parsed.get(category, [])
            if not isinstance(result[category], list):
                result[category] = []
        
        return result

    def _validate_historical_response(self, response, current_age):
        """Validate the historical response format and content."""
        try:
            required_categories = [
                "Career & Growth",
                "Personal Life & Relationships",
                "Health & Well-being",
                "Financial Trajectory",
                "Reflections & Philosophy",
                "$XVI & Technology"
            ]
            
            validated_response = {}
            existing_ltm = self._get_existing_ltm(self.life_tracks)  # Get existing LTM
            
            for category in required_categories:
                if category not in response:
                    print(f"Missing required category: {category}")
                    return None
                
                # Validate MTM and LTM arrays exist
                if 'MTM' not in response[category]:
                    print(f"Missing MTM array for {category}")
                    return None
                if 'LTM' not in response[category]:
                    print(f"Missing LTM array for {category}")
                    return None

                # For MTM, use new entries (overwrite)
                new_mtm = response[category]['MTM']
                
                # For LTM, merge with existing while preserving age
                merged_ltm = []
                if category in existing_ltm:
                    merged_ltm.extend(existing_ltm[category])
                
                # Add new LTM entries with age if they're not duplicates
                for new_ltm in response[category]['LTM']:
                    is_duplicate = False
                    for existing in merged_ltm:
                        if (existing.get('Milestone') == new_ltm.get('Milestone') and 
                            existing.get('Implications') == new_ltm.get('Implications')):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        if 'Age' not in new_ltm:
                            new_ltm['Age'] = current_age
                        merged_ltm.append(new_ltm)
                
                # Sort LTM entries by age
                merged_ltm.sort(key=lambda x: float(x.get('Age', 0)))
                
                validated_response[category] = {
                    'historical_summary': {
                        'MTM': new_mtm,  # Use new MTM entries
                        'LTM': merged_ltm  # Use merged LTM entries
                    }
                }
            
            print("Successfully validated historical response")
            return validated_response

        except Exception as e:
            print(f"Error validating historical response: {str(e)}")
            return None

    def _categorize_list_response(self, items):
        """Categorize a list response into the proper structure."""
        categories = self._get_empty_structure()
        
        for item in items:
            if any(word in item.lower() for word in ["career", "job", "study", "code"]):
                categories["Career & Growth"].append(item)
            elif any(word in item.lower() for word in ["friend", "relationship", "social"]):
                categories["Personal Life & Relationships"].append(item)
            elif any(word in item.lower() for word in ["health", "sleep", "stress"]):
                categories["Health & Well-being"].append(item)
            elif any(word in item.lower() for word in ["money", "finance", "cost"]):
                categories["Financial Trajectory"].append(item)
            elif any(word in item.lower() for word in ["think", "feel", "question"]):
                categories["Reflections & Philosophy"].append(item)
            elif any(word in item.lower() for word in ["tech", "crypto", "blockchain", "xvi"]):
                categories["$XVI & Technology"].append(item)
            else:
                # Default to Reflections if no clear category
                categories["Reflections & Philosophy"].append(item)
        
        return categories

    def _initialize_life_tracks(self):
        """Initialize empty life tracks structure."""
        return {
            'digest': {
                'Career & Growth': {
                    'historical_summary': {'MTM': [], 'LTM': []},
                    'projected_goals': {'short_term': [], 'long_term': []}
                },
                'Personal Life & Relationships': {
                    'historical_summary': {'MTM': [], 'LTM': []},
                    'projected_goals': {'short_term': [], 'long_term': []}
                },
                'Health & Well-being': {
                    'historical_summary': {'MTM': [], 'LTM': []},
                    'projected_goals': {'short_term': [], 'long_term': []}
                },
                'Financial Trajectory': {
                    'historical_summary': {'MTM': [], 'LTM': []},
                    'projected_goals': {'short_term': [], 'long_term': []}
                },
                'Reflections & Philosophy': {
                    'historical_summary': {'MTM': [], 'LTM': []},
                    'projected_goals': {'short_term': [], 'long_term': []}
                },
                '$XVI & Technology': {
                    'historical_summary': {'MTM': [], 'LTM': []},
                    'projected_goals': {'short_term': [], 'long_term': []}
                }
            }
        }

    def _print_life_tracks(self, life_tracks):
        """Print life tracks in a nicely formatted way."""
        print("\n=== XAVIER'S LIFE DIGEST ===\n")
        
        for area, data in life_tracks['digest'].items():
            print(f"\n=== {area.upper()} ===\n")
            
            # Print Historical Summary with Tiered Memory
            print("Historical Summary:")
            historical_summary = data.get("historical_summary", {})
            if historical_summary:
                print("\n  Short-Term Memory (Most Recent):")
                if historical_summary.get("short_term"):
                    for item in historical_summary["short_term"]:
                        print(f"   - {item}")
                else:
                    print("   No short-term historical data available.")
                
                print("\n  Medium-Term Memory (Moderately Recent):")
                if historical_summary.get("medium_term"):
                    for item in historical_summary["medium_term"]:
                        print(f"   - {item}")
                else:
                    print("   No medium-term historical data available.")
                
                print("\n  Long-Term Memory (Older History):")
                if historical_summary.get("long_term"):
                    for item in historical_summary["long_term"]:
                        print(f"   - {item}")
                else:
                    print("   No long-term historical data available.")
            else:
                print("No historical developments recorded.")
            
            # Print Short-Term Projections
            print("\nShort-Term Projections (3-6 months):")
            if data.get("projected_short"):
                for item in data["projected_short"]:
                    print(f"• {item}")
            else:
                print("No short-term developments projected.")
            
            # Print Long-Term Projections
            print("\nLong-Term Projections (1-5 years):")
            if data.get("projected_long"):
                for item in data["projected_long"]:
                    print(f"• {item}")
            else:
                print("No long-term developments projected.")
            
            # Print Plot Points - Tech-Driven and Character-Driven
            plot_points = data.get("plot_points", {})
            
            print("\nTech-Driven Plot Points:")
            if plot_points.get("tech_driven"):
                for item in plot_points["tech_driven"]:
                    print(f"• {item}")
            else:
                print("No tech-driven plot points recorded.")
            
            print("\nCharacter-Driven Plot Points:")
            if plot_points.get("character_driven"):
                for item in plot_points["character_driven"]:
                    print(f"• {item}")
            else:
                print("No character-driven plot points recorded.")
            
            print("-" * 50)  # Separator line

    def save_digest_to_history(self, digest):
        """Save the current digest to history on GitHub."""
        try:
            if digest is None:
                print("Digest is None, not saving to history.")
                return

            # Load existing history from GitHub
            history, sha = self.github_ops.get_file_content('digest_history.json')
            if history is None:
                history = []

            # Append the current digest to history
            history.append(digest)

            # Convert history to JSON string
            history_json = json.dumps(history, indent=2)

            # Commit the updated history to GitHub
            self.github_ops.update_file(
                file_path='digest_history.json',
                content=history_json,
                commit_message=f"Update digest history at {datetime.now().isoformat()}",
                sha=sha
            )

            print(f"Saved digest to history on GitHub (age: {digest.get('metadata', {}).get('simulation_age')})")

        except Exception as e:
            print(f"Error saving digest to history on GitHub: {str(e)}")
            traceback.print_exc()

    def _get_life_phase(self, age, has_major_event=False):
        """Get life phase description based on age, with optional flexibility for major life events."""

        if age < 25:
            return (
                "Early Career & Exploration (18-25)"
                + (" with resilience through recent challenges." if has_major_event else ".") + "\n"
                "- **Career & Growth**: Building foundational skills in blockchain, Web3, and tech, while navigating early career opportunities or challenges.\n"
                "- **Personal Life & Relationships**: Exploring independence, forming meaningful relationships, and discovering personal identity.\n"
                "- **Health & Well-being**: Establishing physical and mental health routines while adapting to life transitions.\n"
                "- **Financial Trajectory**: Learning financial independence, managing expenses, and exploring early investments.\n"
                "- **Reflections & Philosophy**: Developing practical perspectives on technology's role in personal and societal growth.\n"
                "- **$XVI & Technology**: Experimenting with early governance ideas and forming initial partnerships within the $XVI ecosystem.\n"
            )
        elif age < 30:
            return (
                "Growth & Foundation Building (25-30)"
                + (" while adapting to significant life changes." if has_major_event else ".") + "\n"
                "- **Career & Growth**: Advancing in career, taking on leadership roles, and building expertise in blockchain and tech.\n"
                "- **Personal Life & Relationships**: Strengthening personal connections, exploring serious relationships, and making life-changing decisions.\n"
                "- **Health & Well-being**: Focusing on stability, balancing career demands with personal health routines.\n"
                "- **Financial Trajectory**: Managing higher income, exploring investments, and preparing for long-term financial stability.\n"
                "- **Reflections & Philosophy**: Examining the social and ethical implications of emerging technologies.\n"
                "- **$XVI & Technology**: Establishing governance frameworks and integrating $XVI into professional projects.\n"
            )
        elif age < 35:
            return (
                "Stability & Partnership (30-35)"
                + (" with resilience and adaptation." if has_major_event else ".") + "\n"
                "- **Career & Growth**: Leading significant projects or ventures, possibly founding a company or driving industry innovation.\n"
                "- **Personal Life & Relationships**: Building long-term partnerships, starting a family, or deepening existing relationships.\n"
                "- **Health & Well-being**: Maintaining long-term health routines, managing stress, and balancing responsibilities.\n"
                "- **Financial Trajectory**: Growing financial security, expanding investments, and planning for family needs.\n"
                "- **Reflections & Philosophy**: Exploring broader implications of technology, including AI and decentralization.\n"
                "- **$XVI & Technology**: Scaling the ecosystem and building a resilient, sustainable foundation.\n"
            )
        elif age < 45:
            return (
                "Family & Leadership (35-45)"
                + (" while navigating major responsibilities." if has_major_event else ".") + "\n"
                "- **Career & Growth**: Balancing leadership roles with personal and family responsibilities.\n"
                "- **Personal Life & Relationships**: Supporting family dynamics, potentially raising children, and fostering connections.\n"
                "- **Health & Well-being**: Addressing mid-life challenges, focusing on well-being and resilience.\n"
                "- **Financial Trajectory**: Ensuring long-term financial security for family and managing wealth.\n"
                "- **Reflections & Philosophy**: Engaging in deeper philosophical questions about legacy and societal impact.\n"
                "- **$XVI & Technology**: Expanding governance structures, forging global partnerships, and solidifying the ecosystem.\n"
            )
        elif age < 60:
            return (
                "Legacy & Mentorship (45-60)"
                + (" while navigating personal or professional transitions." if has_major_event else ".") + "\n"
                "- **Career & Growth**: Transitioning to advisory roles, shaping industry direction, and mentoring emerging leaders.\n"
                "- **Personal Life & Relationships**: Supporting children’s growth, nurturing family bonds, and embracing life’s transitions.\n"
                "- **Health & Well-being**: Maintaining longevity, addressing health challenges, and emphasizing mental well-being.\n"
                "- **Financial Trajectory**: Managing financial legacy and preparing for generational wealth transfer.\n"
                "- **Reflections & Philosophy**: Focusing on ethical and societal impacts of technology for future generations.\n"
                "- **$XVI & Technology**: Scaling global reach, building cross-border collaborations, and ensuring sustainability.\n"
            )
        else:
            return (
                "Wisdom & Succession (60+)"
                + (" while adapting to significant transitions." if has_major_event else ".") + "\n"
                "- **Career & Growth**: Transitioning fully to mentorship and advisory roles, leaving an enduring impact.\n"
                "- **Personal Life & Relationships**: Acting as a family guide, fostering multi-generational bonds, and preparing for succession.\n"
                "- **Health & Well-being**: Prioritizing graceful aging, addressing health realities, and focusing on quality of life.\n"
                "- **Financial Trajectory**: Managing family wealth and succession planning.\n"
                "- **Reflections & Philosophy**: Reflecting on humanity’s future, the role of technology, and personal legacy.\n"
                "- **$XVI & Technology**: Securing the long-term success of the $XVI ecosystem and ensuring its continuity.\n"
            )
                
    def _get_stm_system_prompt(self):
        """Get system prompt for STM extraction."""
        return """
You are analyzing recent tweets and comments to extract Short-Term Memory (STM) summaries.
Focus only on immediate, actionable details from the most recent events.

Your response MUST be a valid JSON object with these exact categories:
{
    "Career & Growth": [
        "Summary point 1",
        "Summary point 2"
    ],
    "Personal Life & Relationships": [
        "Summary point 1",
        "Summary point 2"
    ],
    "Health & Well-being": [
        "Summary point 1",
        "Summary point 2"
    ],
    "Financial Trajectory": [
        "Summary point 1",
        "Summary point 2"
    ],
    "Reflections & Philosophy": [
        "Summary point 1",
        "Summary point 2"
    ],
    "$XVI & Technology": [
        "Summary point 1",
        "Summary point 2"
    ]
}

IMPORTANT:
1. Response must be a JSON object, not an array
2. All categories must be present
3. Each category must contain an array of strings
4. Empty categories should have empty arrays []
"""

    def _get_stm_user_prompt(self, tweets, comments):
        """Get user prompt for STM extraction."""
        base_prompt = (
            "Please analyze these recent tweets and comments to extract STM summaries:\n\n"
            f"TWEETS (ordered from oldest to newest for analysis):\n{self._format_tweets_for_prompt(tweets)}\n\n"
        )
        
        if comments:
            base_prompt += f"COMMENTS:\n{self._format_comments_for_prompt(comments)}\n\n"
        
        base_prompt += "For each category, provide only the most relevant and recent developments."
        return base_prompt

    def _get_historical_system_prompt(self):
        """Get the system prompt for historical generation."""
        return """
            You are analyzing STM summaries to update historical records. Your task is to identify patterns and significant milestones.

            IMPORTANT: Keep responses concise. Each field should be 1-2 sentences maximum.

            For each category, you MUST:
            1. Create MTM entries for recent patterns and behaviors
            2. Create LTM entries for significant milestones. Examples by category:

            Career & Growth:
            - Starting/leaving education
            - First job or internship
            - Major career changes
            - Significant promotions or setbacks

            Personal Life & Relationships:
            - Important family developments
            - Key relationship milestones
            - Significant social transitions
            - Major personal growth moments

            Health & Well-being:
            - First encounter with significant health issues
            - Major lifestyle changes
            - Important mental health realizations
            - Significant wellness achievements

            Financial Trajectory:
            - First major investment
            - Significant financial losses or gains
            - Important financial decisions
            - Major changes in financial strategy

            Reflections & Philosophy:
            - Key philosophical realizations
            - Major shifts in worldview
            - Important personal values discoveries
            - Significant life perspective changes

            $XVI & Technology:
            - First engagement with crypto/trading
            - Major trading successes or failures
            - Significant technical achievements
            - Important community involvement milestones

            Output format must be valid JSON with this structure:
            {
                "Category": {
                    "MTM": [{
                        "Summary": "One brief sentence describing the pattern.",
                        "Patterns": "3-4 key behaviors, comma-separated",
                        "Goals": "2-3 goals, comma-separated",
                        "Transition": "One brief sentence about changes."
                    }],
                    "LTM": [{
                        "Milestone": "One brief sentence about a significant event or realization.",
                        "Implications": "One brief sentence about long-term impact.",
                        "Lessons": "2-3 key lessons learned, comma-separated"
                    }]
                }
            }

            VALIDATION RULES:
            1. Every category must have at least one MTM entry
            2. Consider each category carefully for LTM-worthy events
            3. Keep entries brief and focused
            4. Use simple, complete sentences
            5. Limit MTM array to 2-3 items maximum
            """

    def _get_historical_user_prompt(self, stm_summaries, existing_tracks):
        """For historical analysis, we only care about MATURE technologies that Xavier has already interacted with"""
        mature_tech, _, _ = self._get_tech_data()
        
        tech_context = "\nRELEVANT TECHNOLOGY CONTEXT:\n"
        # Only include mature technologies that could have influenced past events
        for tech in mature_tech:
            if tech['status'] == 'mainstream' or tech['status'] == 'established':
                tech_context += f"- {tech['name']}: {tech['description']}\n"
        
        existing_mtm = self._get_existing_mtm(existing_tracks)
        existing_ltm = self._get_existing_ltm(existing_tracks)
        
        prompt = f"""Analyze recent developments and update historical summaries.

            Recent Events (STM):
            {json.dumps(stm_summaries, indent=2)}

            Existing MTM:
            {json.dumps(existing_mtm, indent=2)}

            Existing LTM:
            {json.dumps(existing_ltm, indent=2)}

            {tech_context}

            Consider how established technologies have influenced:
            1. Recent experiences and decisions
            2. Development of skills and capabilities
            3. Past milestones and achievements
            4. Previous adaptations to technological change

            Focus on actual past events and developments, not future possibilities.
            """
        return prompt

    def _get_projection_system_prompt(self, age):
        """Get system prompt for projection generation."""
        return """
            You are analyzing historical patterns to project future developments for {age} year old Xavier.
            Focus on realistic, actionable goals and developments, that are consistent across categories, with specific category focuses.

            For each category, provide:
            1. Short-term goals (3-6 months) with estimated durations, which should contribute to the long-term goals, specific to that category
            2. Long-term goals (1-5 years), which should be universal and consistent across categories

            Your response MUST be valid JSON with this structure:
            {
                "Category": {
                    "short_term": [
                        {
                            "goal": "Brief description of the goal",
                            "duration_days": number_of_days_to_achieve
                        }
                    ],
                    "long_term": [
                        "Long term goal description"
                    ]
                }
            }

            IMPORTANT:
            1. Short-term goals should have realistic durations (30-180 days)
            2. Goals should be specific and measurable
            3. Consider current life phase and circumstances
            4. Maintain narrative consistency
            5. Each category must have at least one short-term and one long-term goal
            """

    def _get_projection_user_prompt(self, historical_tracks):
        """For projections, we care about both emerging technologies and future trends"""
        mature_tech, maturing_soon, societal_shifts = self._get_tech_data()
        
        tech_context = "\nTECHNOLOGY CONTEXT:\n"
        
        # Include relevant mature tech that's still evolving
        tech_context += "\nEstablished Technologies to Build Upon:\n"
        for tech in mature_tech:
            if tech['status'] == 'evolving' or tech['status'] == 'growing':
                tech_context += f"- {tech['name']}: {tech['description']} (Status: {tech['status']})\n"
        
        # Include emerging tech for future planning
        tech_context += "\nEmerging Technologies to Watch:\n"
        for tech in maturing_soon:
            tech_context += (
                f"- {tech['name']}: {tech['description']} "
                f"(Expected: {tech['estimated_year']}, Probability: {tech['probability']})\n"
            )
        
        # Include relevant societal shifts for long-term planning
        tech_context += "\nAnticipated Societal Shifts For Reflection & Philosophy:\n"
        for shift in societal_shifts:
            tech_context += f"- {shift['theme']}: {shift['description']}\n"
            tech_context += f"  Potential Impact: {shift['societal_impact']}\n"

        prompt = f"""Based on the historical tracks and future technology context, generate realistic projections. Make sure long term goals are consistent and interconnected across categories.

            Historical Context:
            {json.dumps(historical_tracks, indent=2)}

            {tech_context}

            Consider:
            1. How to build upon current technology expertise
            2. Which emerging technologies align with goals and interests
            3. How to prepare for anticipated technological changes
            4. Realistic timeline for adopting new technologies
            5. Balance between innovation and practical implementation

            Generate projections that show progressive technology adoption while maintaining realistic personal development.
            """
        return prompt

    def generate_digest(self, latest_digest, tweets, current_age, current_date, tweet_count, comments=None, max_retries=3, retry_delay=5, log_path=None, first_digest=False):
        """Generate a new digest based on recent tweets"""
        try:
            # Create log file for this digest
            if log_path is None:
                log_path = os.path.join(
                    self.digest_log_dir, 
                    f"digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                )
            self.life_tracks = latest_digest
            
            # Step 1: Extract STM summaries
            print("\nStep 1: Extracting STM summaries...")
            stm_summaries = None
            attempt = 0
            while attempt < max_retries:
                try:
                    stm_system_prompt = self._get_stm_system_prompt()
                    stm_user_prompt = self._get_stm_user_prompt(tweets, comments)
                    
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("=== STM Generation Debug ===\n")
                            f.write(f"System Prompt:\n\n{stm_system_prompt}\n\n")
                            f.write(f"User Prompt:\n{stm_user_prompt}\n\n")

                    stm_response = self._get_completion(
                        system_prompt=stm_system_prompt,
                        user_prompt=stm_user_prompt
                    )

                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("STM Raw Response:\n")
                            f.write(f"{stm_response}\n\n")

                    # Extract and parse JSON
                    if "```json" in stm_response:
                        json_start = stm_response.find("```json") + 7
                        json_end = stm_response.find("```", json_start)
                        if json_end != -1:
                            stm_response = stm_response[json_start:json_end].strip()

                    parsed_stm = json.loads(stm_response)
                    stm_summaries = self._validate_stm_response(parsed_stm)
                    
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("Validated STM Response:\n")
                            f.write(f"{json.dumps(stm_summaries, indent=2)}\n\n")

                    if stm_summaries:
                        break

                except Exception as e:
                    attempt += 1
                    print(f"Error in STM generation (attempt {attempt}/{max_retries}): {str(e)}")
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write(f"STM Generation Error (attempt {attempt}):\n")
                            f.write(f"{str(e)}\n{traceback.format_exc()}\n\n")
                    if attempt < max_retries:
                        time.sleep(retry_delay)

            # Step 2: Update historical summaries
            print("\nStep 2: Updating historical summaries...")
            if log_path:
                with open(log_path, 'a') as f:
                    f.write("=== Historical Generation Debug ===\n")

            historical_tracks = None
            attempt = 0
            while attempt < max_retries:
                try:
                    historical_system_prompt = self._get_historical_system_prompt()
                    historical_user_prompt = self._get_historical_user_prompt(stm_summaries, self.life_tracks.get('digest', {}))
                    
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write(f"System Prompt:\n\n{historical_system_prompt}\n\n")
                            f.write(f"User Prompt:\n{historical_user_prompt}\n\n")

                    historical_response = self._get_completion(
                        system_prompt=historical_system_prompt,
                        user_prompt=historical_user_prompt
                    )

                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("Historical Raw Response:\n")
                            f.write(f"{historical_response}\n\n")

                    # Extract and parse JSON
                    if "```json" in historical_response:
                        json_start = historical_response.find("```json") + 7
                        json_end = historical_response.find("```", json_start)
                        if json_end != -1:
                            historical_response = historical_response[json_start:json_end].strip()

                    parsed_historical = json.loads(historical_response)
                    historical_tracks = self._validate_historical_response(parsed_historical, current_age)
                    
                    if historical_tracks:
                        self.life_tracks = {'digest': historical_tracks}
                        if log_path:
                            with open(log_path, 'a') as f:
                                f.write("Validated Historical Response:\n")
                                f.write(f"{json.dumps(historical_tracks, indent=2)}\n\n")
                        break

                except Exception as e:
                    attempt += 1
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write(f"Historical Generation Error (attempt {attempt}):\n")
                            f.write(f"{str(e)}\n{traceback.format_exc()}\n\n")
                    if attempt < max_retries:
                        time.sleep(retry_delay)

            # Step 3: Generate projections
            print("\nStep 3: Generating projections...")
            if log_path:
                with open(log_path, 'a') as f:
                    f.write("\n=== Projection Generation Debug ===\n")
                    f.write("System Prompt:\n\n")
                    f.write(self._get_projection_system_prompt(current_age))
                    f.write("\n\nUser Prompt:\n\n")
                    f.write(self._get_projection_user_prompt(historical_tracks))
                    f.write("\n\n")

            attempt = 0
            while attempt < max_retries:
                try:
                    # Log the raw API response
                    projection_response = self._get_completion(
                        system_prompt=self._get_projection_system_prompt(current_age),
                        user_prompt=self._get_projection_user_prompt(historical_tracks)
                    )
                    
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("\n=== Raw API Response ===\n")
                            f.write(projection_response)
                            f.write("\n")

                    # Log JSON extraction
                    if "```json" in projection_response:
                        json_start = projection_response.find("```json") + 7
                        json_end = projection_response.find("```", json_start)
                        if json_end != -1:
                            projection_response = projection_response[json_start:json_end].strip()
                            if log_path:
                                with open(log_path, 'a') as f:
                                    f.write("\n=== Extracted JSON ===\n")
                                    f.write(projection_response)
                                    f.write("\n")

                    # Log parsed JSON
                    parsed_projections = json.loads(projection_response)
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("\n=== Parsed Projections ===\n")
                            f.write(json.dumps(parsed_projections, indent=2))
                            f.write("\n")

                    # Log validated projections
                    projections = self._validate_projection_response(parsed_projections)
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("\n=== Validated Projections ===\n")
                            f.write(json.dumps(projections, indent=2))
                            f.write("\n")

                    if projections:
                        try:
                            if log_path:
                                with open(log_path, 'a') as f:
                                    f.write("\n=== Processing Categories ===")
                                    f.write(f"\nAvailable in life_tracks: {list(self.life_tracks['digest'].keys())}")
                                    f.write(f"\nAvailable in projections: {list(projections.keys())}\n")

                            for category in self.life_tracks['digest']:
                                if log_path:
                                    with open(log_path, 'a') as f:
                                        f.write(f"\nProcessing category: {category}")
                                
                                if category in projections:
                                    # Handle long_term goals - could be string or dict
                                    long_term = projections[category]['long_term']
                                    if isinstance(long_term, list):
                                        long_term = [
                                            goal['long term goal'] if isinstance(goal, dict) and 'long term goal' in goal
                                            else goal['goal'] if isinstance(goal, dict) and 'goal' in goal
                                            else goal
                                            for goal in long_term
                                        ]

                                    self.life_tracks['digest'][category]['projected_goals'] = {
                                        'short_term': projections[category]['short_term'],
                                        'long_term': long_term
                                    }
                                else:
                                    if log_path:
                                        with open(log_path, 'a') as f:
                                            f.write(f"\nCategory {category} not found in projections")

                        except Exception as e:
                            if log_path:
                                with open(log_path, 'a') as f:
                                    f.write(f"\nError processing projections: {str(e)}")
                                    f.write(f"\nTraceback: {traceback.format_exc()}")
                            raise
                    print("Successfully generated projections")
                    break

                except Exception as e:
                    attempt += 1
                    print(f"Error in projection generation (attempt {attempt}/{max_retries}): {str(e)}")
                    if log_path:
                        with open(log_path, 'a') as f:
                            f.write("\nAPI Response:\n")
                            f.write(projection_response)
                            f.write("\n\n")

                    # Rest of the code remains the same...

            # Update final state logging to show age in LTM entries
            if log_path:
                with open(log_path, 'a') as f:
                    f.write("=== FINAL DIGEST STATE ===\n")
                    f.write(f"Age: {current_age}\n")
                    f.write("Life Tracks State:\n\n")
                    for category in self.life_tracks['digest']:
                        f.write(f"{category}:\n")
                        
                        # Log MTM entries
                        f.write("  MTM Entries:\n")
                        if ('historical_summary' in self.life_tracks['digest'][category] and 
                            'MTM' in self.life_tracks['digest'][category]['historical_summary'] and 
                            self.life_tracks['digest'][category]['historical_summary']['MTM']):
                            for mtm in self.life_tracks['digest'][category]['historical_summary']['MTM']:
                                f.write(f"    - {json.dumps(mtm, indent=4)}\n")
                        else:
                            f.write("    No MTM entries\n")
                        
                        # Log LTM entries with age
                        f.write("  LTM Entries (Chronological):\n")
                        if ('historical_summary' in self.life_tracks['digest'][category] and 
                            'LTM' in self.life_tracks['digest'][category]['historical_summary'] and 
                            self.life_tracks['digest'][category]['historical_summary']['LTM']):
                            for ltm in self.life_tracks['digest'][category]['historical_summary']['LTM']:
                                # Format age in the output
                                age_str = f" (Age {ltm.get('Age', 'Unknown')})"
                                ltm_copy = ltm.copy()
                                if 'Age' in ltm_copy:
                                    del ltm_copy['Age']  # Remove age from the main JSON output
                                f.write(f"    - {json.dumps(ltm_copy, indent=4)}{age_str}\n")
                        else:
                            f.write("    No LTM entries\n")
                        
                        # Log projected goals
                        f.write("  Projected Goals:\n")
                        if 'projected_goals' in self.life_tracks['digest'][category]:
                            f.write("    Short Term:\n")
                            for goal in self.life_tracks['digest'][category]['projected_goals']['short_term']:
                                if isinstance(goal, dict):
                                    duration = goal.get('duration_days', 'N/A')
                                    f.write(f"      - {goal['goal']} (Duration: {duration} days)\n")
                                else:
                                    f.write(f"      - {goal}\n")
                            f.write("    Long Term:\n")
                            for goal in self.life_tracks['digest'][category]['projected_goals']['long_term']:
                                f.write(f"      - {goal}\n")
                        else:
                            f.write("    No projected goals\n")
                        f.write("\n")
                    f.write("\n" + "="*80 + "\n\n")

            if first_digest:
                return self.life_tracks 

            # Add metadata before saving
            self.life_tracks['metadata'] = {
                'simulation_age': current_age,
                'simulation_time': current_date if isinstance(current_date, str) else current_date.strftime('%Y-%m-%d'),
                'tweet_count': tweet_count,
                'location': tweets[-1]['location'],
                'timestamp': datetime.now().isoformat()
            }
            # Save digest to history
            self.save_digest_to_history(self.life_tracks)

            return self.life_tracks

        except Exception as e:
            print(f"Error generating digest: {str(e)}")
            if log_path:
                with open(log_path, 'a') as f:
                    f.write(f"\nFatal Error in Digest Generation:\n{str(e)}\n{traceback.format_exc()}\n")
            return None

    def generate_first_digest(self, tweets_by_age):
        """Generate first digest by processing pre-grouped age brackets"""
        try:
            print("\n=== Starting First Digest Generation ===")
            print(f"Input contains {len(tweets_by_age)} age brackets: {list(tweets_by_age.keys())}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bracket_log_path = lambda bracket: os.path.join(
                self.first_digest_log_dir, 
                f"bracket_{bracket.replace(' ', '_')}_{timestamp}.txt"
            )
            
            # Initialize location tracking
            current_location = ""
            print(f"Starting with empty location")
            
            # Process each age bracket sequentially
            sorted_brackets = sorted(tweets_by_age.keys(), 
                key=lambda x: float(x.split('-')[0].replace('age ', '')))
            print(f"Processing brackets in order: {sorted_brackets}")
            
            bracket_digest = self._initialize_life_tracks()
            for bracket in sorted_brackets:
                try:
                    # Extract age range
                    age_range = bracket.replace('age ', '').split('-')
                    start_age = float(age_range[0])
                    end_age = float(age_range[1])
                    
                    print(f"\nProcessing bracket {bracket} ({start_age} -> {end_age})")
                    print(f"Number of tweets in bracket: {len(tweets_by_age[bracket])}")
                    log_path = bracket_log_path(bracket)
                    
                    # Update simulation state
                    self.simulation_age = end_age
                    self.simulation_time = (datetime.now() + 
                        timedelta(days=(end_age - start_age) * 365)).strftime('%Y-%m-%d')
                    
                    print(f"Updated simulation state: age={self.simulation_age}, time={self.simulation_time}")
                    
                    # Pre-process tweets for location changes
                    tweets = tweets_by_age[bracket]
                    for tweet in tweets:
                        detected_location = self.tweet_generator.detect_location_change(tweet)
                        if detected_location and "No location detected" not in detected_location:
                            print(f"Location updated: {current_location} -> {detected_location}")
                            current_location = detected_location
                    
                    # Generate digest with location awareness
                    bracket_digest = self.generate_digest(
                        latest_digest=bracket_digest,
                        tweets=tweets,
                        comments=None,
                        current_age=end_age,
                        current_date=self.simulation_time,  # Pass as string
                        tweet_count=len(tweets),
                        log_path=log_path,
                        first_digest=True
                    )
                    
                    if bracket_digest:
                        # Update metadata including location
                        if 'metadata' not in bracket_digest:
                            bracket_digest['metadata'] = {}
                        bracket_digest['metadata'].update({
                            'simulation_age': end_age,
                            'simulation_time': self.simulation_time,
                            'tweet_count': self.tweet_count,
                            'age_bracket': bracket,
                            'current_location': current_location
                        })
                        print(f"Updated digest metadata for bracket {bracket}")
                        self.life_tracks = bracket_digest
                        self.save_digest_to_history(bracket_digest)
                    else:
                        print(f"Failed to generate digest for bracket {bracket}")
                
                except Exception as e:
                    print(f"Error processing bracket {bracket}: {str(e)}")
                    traceback.print_exc()
                    continue

            return self.life_tracks

        except Exception as e:
            print(f"Error in generate_first_digest: {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            return None

    def _format_tweets_for_prompt(self, tweets):
        """Format tweets for inclusion in prompts."""
        if isinstance(tweets, list):
            return "\n".join([f"- {tweet}" if isinstance(tweet, str) else f"- {tweet['age']}: {tweet['content']}" for tweet in tweets])
        elif isinstance(tweets, dict):
            # If tweets is a dictionary (e.g., for age brackets)
            formatted = []
            for age, tweet_list in tweets.items():
                formatted.extend([f"- {tweet}" for tweet in tweet_list])
            return "\n".join(formatted)
        return ""

    def _format_comments_for_prompt(self, comments):
        """Format comments for inclusion in prompts."""
        if not comments:
            return ""
        return "\n".join([f"- {comment}" for comment in comments])

    def _get_existing_mtm(self, existing_tracks):
        """Get existing MTM data from life tracks."""
        if not existing_tracks or not isinstance(existing_tracks, dict):
            return self._initialize_life_tracks()['digest']
        
        tracks_digest = existing_tracks.get('digest', {})
        return {
            category: data.get('historical_summary', {}).get('MTM', [])
            for category, data in tracks_digest.items()
        }

    def _get_existing_ltm(self, existing_tracks):
        """Get existing LTM data from life tracks."""
        if not existing_tracks or not isinstance(existing_tracks, dict):
            return self._initialize_life_tracks()['digest']
        
        tracks_digest = existing_tracks.get('digest', {})
        return {
            category: data.get('historical_summary', {}).get('LTM', [])
            for category, data in tracks_digest.items()
        }

    def _log_final_digest_state(self, log_path, current_age):
        """Log the final state of the digest with all entries."""
        try:
            with open(log_path, 'a') as f:
                f.write("\n=== FINAL DIGEST STATE ===\n")
                f.write(f"Age: {current_age}\n")
                f.write("Life Tracks State:\n\n")
                
                digest = self.life_tracks.get('digest', {})
                for category in [
                    "Career & Growth",
                    "Personal Life & Relationships",
                    "Health & Well-being",
                    "Financial Trajectory",
                    "Reflections & Philosophy",
                    "$XVI & Technology"
                ]:
                    data = digest.get(category, {})
                    f.write(f"{category}:\n")
                    
                    # Log MTM entries
                    f.write("  MTM Entries:\n")
                    for mtm in data.get('MTM', []):
                        f.write(f"    Summary: {mtm.get('Summary', '')}\n")
                        f.write(f"    Patterns: {mtm.get('Patterns', '')}\n")
                        f.write(f"    Goals: {mtm.get('Goals', '')}\n")
                        f.write(f"    Transition: {mtm.get('Transition', '')}\n\n")
                    
                    # Log LTM entries
                    f.write("  LTM Entries (Chronological):\n")
                    for ltm in sorted(data.get('LTM', []), key=lambda x: x.get('age', 0)):
                        f.write(f"    Age {ltm.get('age', '')}: {ltm.get('Milestone', '')}\n")
                        f.write(f"    Implications: {ltm.get('Implications', '')}\n")
                        f.write(f"    Lessons: {ltm.get('Lessons', '')}\n\n")
                    
                    f.write("\n")
                
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"Error logging final digest state: {str(e)}")
            traceback.print_exc()

    def _get_completion(self, system_prompt, user_prompt, max_tokens=2000, temperature=0.7):
        """Get completion from the language model."""
        try:
            response = self.ai.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response
        except Exception as e:
            print(f"Error in API call: {str(e)}")
            print(f"Model: {self.model}")
            print(f"System prompt: {system_prompt[:100]}...")
            print(f"User prompt: {user_prompt[:100]}...")
            raise

    def _validate_projection_response(self, response):
        """Validate the projection response format and content."""
        try:
            required_categories = [
                "Career & Growth",
                "Personal Life & Relationships",
                "Health & Well-being",
                "Financial Trajectory",
                "Reflections & Philosophy",
                "$XVI & Technology"
            ]
            
            # Check that all required categories are present
            for category in required_categories:
                if category not in response:
                    print(f"Missing required category: {category}")
                    return None
                
                # Check that each category has short_term and long_term arrays
                if "short_term" not in response[category]:
                    print(f"Missing short_term projections for {category}")
                    return None
                if "long_term" not in response[category]:
                    print(f"Missing long_term projections for {category}")
                    return None
                
                # Convert short-term goals to objects with duration
                if isinstance(response[category]["short_term"], list):
                    response[category]["short_term"] = [
                        {
                            "short term goal": goal,
                            "duration_days": 30 + (i * 15)  # Stagger durations: 30, 45, 60 days...
                        } if isinstance(goal, str) else goal
                        for i, goal in enumerate(response[category]["short_term"])
                    ]

                if isinstance(response[category]["long_term"], list):
                    response[category]["long_term"] = [
                        {
                            "long term goal": goal,
                            "duration_days": 30 + (i * 15)  # Stagger durations: 30, 45, 60 days...
                        } if isinstance(goal, str) else goal
                        for i, goal in enumerate(response[category]["long_term"])
                    ]

            print("Successfully validated projections")
            return response

        except Exception as e:
            print(f"Error validating projections: {str(e)}")
            return None

    def _get_base_prompt(self):
        """Get the base system prompt with age context"""
        return (
            f"You are helping analyze the life of Xavier, a {self.simulation_age:.1f} year old trader and developer. "
            "Generate a comprehensive digest of recent events and developments across different life areas. "
            "Consider age-appropriate milestones, challenges, and growth opportunities. "
            "Keep the analysis grounded in realistic expectations for someone of this age."
        )

    def _get_projection_prompt(self):
        """Get the projection prompt with age context"""
        return (
            f"As a {self.simulation_age:.1f} year old trader and developer, Xavier needs realistic goals and projections. "
            "Consider age-appropriate milestones and challenges when generating:\n"
            "1. Short-term goals (next 1-3 months)\n"
            "2. Long-term aspirations (6-12 months)\n"
            "3. Career development opportunities\n"
            "4. Personal growth targets\n\n"
            "Ensure all projections are realistic and achievable for someone of this age and experience level."
        )

    def _get_analysis_prompt(self):
        """Get the analysis prompt with age context"""
        return (
            f"Analyze recent events for Xavier (age {self.simulation_age:.1f}) considering:\n"
            "1. Career progression relative to age and experience\n"
            "2. Personal development appropriate for early 20s\n"
            "3. Financial goals aligned with age and career stage\n"
            "4. Social and relationship developments typical for this age\n"
            "5. Health and wellness priorities for a young professional"
        )

def main():
    """Test function to print digest summaries"""
    try:
        simulation_time = "2024-03-21"  # Example date
        simulation_age = 22  # Final age
        tweet_count = 42
        
        # Initialize digest generator
        digest_gen = DigestGenerator(simulation_time, simulation_age, tweet_count)
        
        # Get tweets from XaviersSim.json
        content, _ = digest_gen.github_ops.get_file_content('XaviersSim.json')
        if content:
            # Generate first digest using pre-grouped age brackets
            print("\nGenerating first digest using age brackets...")
            first_digest = digest_gen.generate_first_digest(content)
            
            if first_digest:
                print("Successfully generated first digest")
            else:
                print("Failed to generate first digest")

    except Exception as e:
        print(f"Error in main: {type(e).__name__} - {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()