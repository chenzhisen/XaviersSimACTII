import json
import os
import traceback
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from src.utils.ai_completion import AICompletion
from src.storage.github_operations import GithubOperations

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

    def _get_completion(self, system_prompt, user_prompt):
        """Get completion from AI model."""
        return self.ai.get_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

    def _get_tech_data(self, tech_evolution, current_date):
        """Process tech evolution data for the digest.
        
        Args:
            tech_evolution: Tech evolution data
            current_date: Current simulation date
            
        Returns:
            dict: Processed tech data containing:
                - emerging_soon: Technologies expected to emerge in next few years
                - maturing_soon: Technologies expected to become mainstream soon
                - recently_matured: Technologies that recently became mainstream
                - current_themes: Themes relevant to current epoch
        """
        try:
            current_year = current_date.year
            tech_data = {
                "emerging_soon": [],
                "maturing_soon": [],
                "recently_matured": [],
                "current_themes": []
            }
            
            # Get latest tech tree
            tech_trees = tech_evolution.get("tech_trees", {})
            latest_epoch = max([int(year) for year in tech_trees.keys()]) if tech_trees else current_year
            latest_tree = tech_trees.get(str(latest_epoch), {})
            
            # Process epoch themes
            for theme in latest_tree.get("epoch_themes", []):
                tech_data["current_themes"].append({
                    "theme": theme["theme"],
                    "description": theme.get("description", ""),
                    "societal_impact": theme.get("societal_impact", ""),
                    "global_trends": theme.get("global_trends", ""),
                    "related_technologies": theme.get("related_technologies", [])
                })
            
            # Process emerging technologies
            for tech in latest_tree.get("emerging_technologies", []):
                estimated_year = int(tech.get("estimated_year", 9999))
                expected_maturity = int(tech.get("expected_maturity_year", 9999))
                
                # Technologies emerging in next 2 years
                if current_year <= estimated_year <= current_year + 2:
                    tech_data["emerging_soon"].append({
                        "name": tech["name"],
                        "year": estimated_year,
                        "description": tech.get("description", ""),
                        "probability": tech.get("probability", 0.5)
                    })
                
                # Technologies expected to mature in next 2 years
                if current_year <= expected_maturity <= current_year + 2:
                    tech_data["maturing_soon"].append({
                        "name": tech["name"],
                        "maturity_year": expected_maturity,
                        "description": tech.get("description", ""),
                        "implications": tech.get("societal_implications", "")
                    })
            
            # Process mainstream technologies
            for tech in latest_tree.get("mainstream_technologies", []):
                maturity_year = int(tech.get("maturity_year", 9999))
                # Technologies that became mainstream in last year
                if current_year - 1 <= maturity_year <= current_year:
                    tech_data["recently_matured"].append({
                        "name": tech["name"],
                        "year": maturity_year,
                        "description": tech.get("description", ""),
                        "impact_level": tech.get("impact_level", 5)
                    })
            
            return tech_data
            
        except Exception as e:
            print(f"Error processing tech data: {e}")
            return None

    def _get_life_phase(self, age):
        """Get life phase description to guide narrative direction."""
        if age < 25:
            return """Early Career & Self-Discovery (18-25):
                - Finding voice in tech: experimenting with blockchain, Web3, and emerging technologies
                - Personal identity: exploring values, beliefs, and what matters most
                - Relationships: building friendships in tech community, possibly dating
                - Health & Lifestyle: establishing routines, managing work-life balance
                - Emotional growth: handling successes, failures, and uncertainties
                - Living space: creating first independent home environment
                - Financial learning: managing income, investments, and responsibilities
                - Creative outlets: coding side projects, writing, possibly music
                - $XVI involvement: connecting technology with personal values
                """
        elif age < 30:
            return """Growth & Deepening Roots (25-30):
                - Career evolution: leading projects, mentoring others
                - Personal growth: developing stronger sense of self and purpose
                - Relationships: deeper connections, possibly serious partnership
                - Living situation: creating a more permanent home base
                - Health focus: developing sustainable wellness practices
                - Financial planning: balancing growth with security
                - Community building: fostering meaningful tech communities
                - Personal interests: integrating hobbies with professional life
                - $XVI vision: aligning personal values with community impact
                """
        elif age < 35:
            return """Stability & Life Integration (30-35):
                - Professional impact: founding or scaling meaningful ventures
                - Personal life: possibly marriage, family planning
                - Home life: establishing longer-term living situation
                - Health & wellness: maintaining balance with increased responsibilities
                - Financial strategy: planning for family or future ventures
                - Relationship dynamics: balancing partnership with ambitions
                - Community leadership: guiding and inspiring others
                - Personal development: deeper philosophical exploration
                - $XVI ecosystem: building lasting positive impact
                """
        elif age < 45:
            return """Leadership & Life Mastery (35-45):
                - Career pinnacle: driving industry change while maintaining authenticity
                - Family life: possibly raising children, supporting partner
                - Home environment: creating nurturing family/personal space
                - Health consciousness: adapting to changing needs
                - Wealth management: planning for family future
                - Mentorship: guiding next generation while still growing
                - Personal fulfillment: finding deeper meaning in work and life
                - Legacy building: considering long-term impact
                - $XVI maturity: ensuring sustainable community growth
                """
        else:
            return """Wisdom & Legacy Creation (45+):
                - Professional evolution: strategic guidance and vision
                - Family focus: nurturing relationships across generations
                - Life reflection: finding deeper meaning and purpose
                - Health priority: focusing on longevity and vitality
                - Wealth legacy: planning for generational impact
                - Personal growth: continued learning and adaptation
                - Community impact: fostering lasting positive change
                - Knowledge sharing: passing on wisdom and experience
                - $XVI future: ensuring lasting beneficial impact
                """
        
    def _get_empty_structure(self):
        """Get empty structure for narrative."""
        return {
            'digest': {
                'Current_Age': 0.0,
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

    def _parse_response(self, response_text, step_name, current_age=None):
        """Parse response text into JSON, with focused debugging."""
        try:
            # Remove any markdown formatting
            clean_text = response_text.replace('```json\n', '').replace('\n```', '').strip()
            
            try:
                parsed = json.loads(clean_text)
                
                # Validate basic structure
                if 'digest' not in parsed:
                    print(f"Missing digest in {step_name}")
                    return self._get_empty_structure()
                    
                if 'Current_Age' not in parsed['digest']:
                    print(f"Missing Current_Age in {step_name}")
                    return self._get_empty_structure()
                
                # Validate required narrative fields
                narrative = parsed['digest']
                required_fields = [
                    'Current_Age', 
                    'Story', 
                    'Key_Themes', 
                    'Current_Direction',
                    'Next_Chapter'
                ]
                
                for field in required_fields:
                    if field not in narrative:
                        print(f"Missing {field} in narrative")
                        narrative[field] = ''
                
                # Validate Next_Chapter structure
                if isinstance(narrative['Next_Chapter'], dict):
                    required_next = [
                        'Immediate_Focus',
                        'Emerging_Threads',
                        'Tech_Context'
                    ]
                    for field in required_next:
                        if field not in narrative['Next_Chapter']:
                            print(f"Missing {field} in Next_Chapter")
                            narrative['Next_Chapter'][field] = ''
                else:
                    print("Next_Chapter is not a dictionary")
                    narrative['Next_Chapter'] = {
                        'Immediate_Focus': '',
                        'Emerging_Threads': '',
                        'Tech_Context': ''
                    }
                
                # Ensure Current_Age is float
                try:
                    narrative['Current_Age'] = float(narrative['Current_Age'])
                except (ValueError, TypeError):
                    print(f"Invalid Current_Age: {narrative['Current_Age']}")
                    narrative['Current_Age'] = current_age or 0.0
                
                return parsed
                    
            except json.JSONDecodeError as e:
                print(f"\nERROR: JSON parsing failed in {step_name}")
                print(f"Error location: Line {e.lineno}, Column {e.colno}")
                print(f"Context: ...{clean_text[max(0, e.pos-50):min(len(clean_text), e.pos+50)]}...")
                return self._get_empty_structure()
                    
        except Exception as e:
            print(f"\nERROR in {step_name}: {str(e)}")
            traceback.print_exc()
            return self._get_empty_structure()

    def generate_digest(self, tweets, current_age, current_date, tweet_count, latest_digest=None, max_retries=3, retry_delay=5, log_path=None):
        """Generate a digest based on tweets and previous context."""
        try:
            persona = self.tweet_generator.get_persona(current_age)
            
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
                f.write(f"Current Age: {current_age}\n")
                f.write(f"Current Date: {current_date}\n")
                f.write(f"Tweet Count: {tweet_count}\n")
                f.write(f"Is First Digest: {latest_digest is None}\n\n")
            
            # Use latest_digest for context if available
            self.life_tracks = latest_digest or self._get_empty_structure()
            
            # Get technology context from GitHub
            tech_evolution = self.github_ops.get_file_content('tech_evolution.json')
            if tech_evolution:
                if isinstance(tech_evolution, tuple):
                    tech_evolution = tech_evolution[0]
                if isinstance(tech_evolution, str):
                    tech_evolution = json.loads(tech_evolution)
            else:
                tech_evolution = {"tech_trees": {}}
            
            # Process tech data
            tech_data = self._get_tech_data(tech_evolution, current_date)
            if not tech_data:
                tech_data = {
                    "emerging_soon": [],
                    "maturing_soon": [],
                    "recently_matured": []
                }
            
            # Get life phase context
            life_phase = self._get_life_phase(current_age)
            
            # Handle tweets context based on type
            tweets_context = "\nDEVELOPMENTS:\n"
            if isinstance(tweets, dict):  # Historical tweets
                age_brackets = sorted(tweets.keys(), key=lambda x: float(x.split('-')[0].replace('age ', '')))
                for age_bracket in age_brackets:
                    tweets_context += f"\n{age_bracket}:\n"
                    for tweet in tweets[age_bracket]:
                        tweets_context += f"- {tweet}\n"
            else:  # Recent tweets
                for tweet in tweets[-self.digest_interval:]:
                    if isinstance(tweet, dict):
                        age = tweet.get('age', 'unknown')
                        content = tweet.get('content', '')
                        tweets_context += f"Age {age:.2f}: {content}\n"
                    elif isinstance(tweet, str):
                        tweets_context += f"- {tweet}\n"
                    else:
                        print(f"Warning: Unexpected tweet format: {type(tweet)}")
                        continue
            
            system_prompt = f"""
                You are synthesizing Xavier's life journey from age 22 to 72. He is currently {current_age:.1f} years old,
                with {72 - current_age:.1f} years remaining in his story. His life unfolds through 96 tweets per year,
                each capturing approximately 3.8 days of experiences.

                Consider both his current phase and the broader arc of his 50-year journey when crafting this digest.
                As he approaches 72, the narrative should evolve toward reflection, wisdom, and legacy.

                This digest will be used to generate the next {self.digest_interval} tweets, guiding the narrative and themes.

                Output format must be valid JSON with this structure:
                {{
                    "digest": {{
                        "Current_Age": float,
                        "Story": "A flowing narrative of Xavier's journey so far...",
                        "Key_Themes": "3-4 recurring themes or patterns...",
                        "Current_Direction": "Where his journey appears to be heading...",
                        "Next_Chapter": {{
                            "Immediate_Focus": "Key developments and goals likely in the next few months",
                            "Emerging_Threads": "Longer-term themes and possibilities beginning to take shape",
                            "Tech_Context": "How current and emerging technologies might influence these developments"
                        }}
                    }}
                }}
                """
            
            # Log system prompt
            with open(log_path, 'a') as f:
                f.write("\n=== System Prompt ===\n")
                f.write(system_prompt)
                f.write("\n")
            
            # Build technology context
            tech_context = "\nTECHNOLOGY CONTEXT:\n"
            
            tech_context += "\nCurrent Technological Themes:\n"
            for theme in tech_data['current_themes']:
                tech_context += f"- {theme['theme']}:\n"
                tech_context += f"  Description: {theme['description']}\n"
                tech_context += f"  Societal Impact: {theme['societal_impact']}\n"
                tech_context += f"  Global Trends: {theme['global_trends']}\n"
                if theme['related_technologies']:
                    tech_context += f"  Related Technologies: {', '.join(theme['related_technologies'])}\n"
            
            tech_context += "\nMature Technologies (actively using or directly impacting daily life):\n"
            for tech in tech_data['recently_matured']:
                tech_context += f"- {tech['name']}: {tech['description']}\n"
                tech_context += f"  Current Impact: {tech.get('adoption_status', '')}\n"
            
            tech_context += "\nTechnologies Approaching Mainstream (preparing for widespread adoption):\n"
            for tech in tech_data['maturing_soon']:
                tech_context += f"- {tech['name']}: {tech['description']}\n"
                tech_context += f"  Expected Impact: {tech.get('implications', '')}\n"
                tech_context += f"  Expected Maturity: {tech.get('maturity_year', 'unknown')}\n"
            
            tech_context += "\nEmerging Technologies (contemplating, theorizing, or dreaming about):\n"
            for tech in tech_data['emerging_soon']:
                tech_context += f"- {tech['name']}: {tech['description']}\n"
                tech_context += f"  Societal Implications: {tech.get('societal_implications', '')}\n"
            
            # Get existing narrative
            existing_narrative = self.life_tracks.get('digest', {})
            narrative_context = "\nEXISTING NARRATIVE:\n"
            if existing_narrative:
                narrative_context += json.dumps(existing_narrative, indent=2)
            else:
                narrative_context += "No existing narrative."
            
            user_prompt = f"""
                Current Age: {current_age:.1f}
                Current Date: {current_date}
                
                LIFE PHASE CONTEXT:
                {life_phase}
                
                {narrative_context}
                
                {tweets_context}
                
                {tech_context}
                
                Synthesize these elements into an updated narrative that:
                1. Reflects Xavier's current life phase and its typical developments
                2. Shows him actively using and being impacted by mature technologies
                3. Shows him preparing for and anticipating soon-to-mature technologies
                4. Demonstrates his intellectual engagement with emerging technologies
                5. Shows growth appropriate for his age and circumstances
                6. Aligns with current technological themes and their societal implications
                7. Projects future directions aligned with global technological trends
                
                Create an authentic narrative that captures Xavier as a complete person,
                balancing his practical use of current tech, preparation for maturing tech,
                and philosophical exploration of emerging technologies and broader themes.
                """
            
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
                    parsed_digest = self._parse_response(response, "digest generation", current_age)
                    if parsed_digest:
                        self.life_tracks = parsed_digest
                        
                        # Add metadata
                        self.life_tracks['metadata'] = {
                            'simulation_age': current_age,
                            'simulation_time': current_date if isinstance(current_date, str) else current_date.strftime('%Y-%m-%d'),
                            'tweet_count': tweet_count,
                            'timestamp': datetime.now().isoformat(),
                            'persona': persona
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
        """Save the digest to history"""
        try:
            # Ensure digest content is in the correct format
            if isinstance(digest_content, str):
                try:
                    digest_content = json.loads(digest_content)
                except json.JSONDecodeError:
                    print("Warning: Digest content is not valid JSON, wrapping in object")
                    digest_content = {
                        "content": digest_content,
                        "timestamp": datetime.now().isoformat(),
                        "type": "digest"
                    }
            elif isinstance(digest_content, dict):
                # Ensure minimum required fields
                if "timestamp" not in digest_content:
                    digest_content["timestamp"] = datetime.now().isoformat()
                if "type" not in digest_content:
                    digest_content["type"] = "digest"
            else:
                raise ValueError("Digest content must be string or dict")

            # Get existing history
            history, sha = self.tweet_generator.github_ops.get_file_content(
                "digest_history.json"
            )
            
            if not history:
                history = []
            elif isinstance(history, dict):
                history = [history]  # Convert single dict to list
            
            # Add new digest
            history.append(digest_content)
            
            # Save updated history
            return self.tweet_generator.github_ops.update_file(
                "digest_history.json",
                history,
                f"Add digest from {digest_content.get('timestamp', 'unknown date')}",
                sha
            )
                
        except Exception as e:
            print(f"Error saving digest to history: {str(e)}")
            raise

    def get_latest_digest(self):
        """Get the latest digest from GitHub repository."""
        try:
            history_file = 'digest_history.json'
            
            if not hasattr(self.tweet_generator, 'github_ops'):
                print("GitHub operations not available")
                return None
            
            try:
                # Get from GitHub
                github_content = self.tweet_generator.github_ops.get_file_content(history_file)
                
                # If file doesn't exist yet, that's okay for first run
                if github_content is None:
                    print(f"No digest history found (first run) - {history_file}")
                    return None
                    
                # Handle different content types
                if isinstance(github_content, tuple) and len(github_content) > 0:
                    content = github_content[0]
                else:
                    content = github_content
                
                # Parse content if it's a string
                if isinstance(content, str):
                    history = json.loads(content)
                elif isinstance(content, list):
                    history = content
                else:
                    print(f"Unexpected content type: {type(content)}")
                    return None
                
                print("Retrieved digest history from GitHub")
                return history[-1] if history else None
                
            except FileNotFoundError:
                print(f"Starting fresh - no digest history yet")
                return None
                
            except json.JSONDecodeError:
                print("Invalid digest history format in GitHub repository")
                return None
                
        except Exception as e:
            print(f"Error getting latest digest from GitHub: {e}")
            traceback.print_exc()
            return None
