import argparse
from anthropic import Anthropic
from utils.config import Config, AIProvider
from storage.github_operations import GithubOperations
import json
from datetime import datetime
import os
import time
import requests
import math
from src.utils.ai_completion import AICompletion

class TechEvolutionGenerator:
    def __init__(self, client, model, is_production=False):
        """Initialize TechEvolutionGenerator
        
        Args:
            client: AI client for completions
            model: Model name to use
            is_production: Whether to run in production mode
        """
        self.client = client
        self.model = model
        self.github_ops = GithubOperations(is_production=is_production)
        self.ai = AICompletion(client, model)
        self.base_year = 2024
        
        # Initialize tech evolution data structure
        self.tech_evolution = {
            'tech_trees': {},
            'last_updated': datetime.now().isoformat()
        }
        
        # Update log directory based on environment
        env_dir = "prod" if is_production else "dev"
        self.log_dir = f"logs/{env_dir}/tech"
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)

    def get_tech_evolution(self):
        """Get the most recently saved tech evolution file"""
        try:
            github_ops = self.github_ops
            # Get the tech evolution file directly
            content, _ = github_ops.get_file_content("tech_evolution.json")
            return content
            
        except Exception as e:
            print(f"Failed to get tech evolution data")
            return None  # Return None instead of raising exception

    def get_previous_technologies(self, epoch_year):
        """Get technologies from previous epochs"""
        previous_tech = {
            "emerging": [],
            "mainstream": [],
            "current_mainstream": []
        }
        
        # Get tech trees from saved data
        all_tech_trees = self._load_tech_trees()
        
        # Process technologies from previous epochs
        for year in range(self.base_year, epoch_year, 5):
            year_str = str(year)
            if year_str not in all_tech_trees:
                continue
                
            prev_data = all_tech_trees[year_str]
            self._process_emerging_tech(previous_tech, prev_data, epoch_year)
            self._process_mainstream_tech(previous_tech, prev_data, epoch_year)
        
        self._print_tech_summary(epoch_year, previous_tech)
        return previous_tech

    def _load_tech_trees(self):
        """Load and combine saved and current tech trees"""
        recent_file = self.get_tech_evolution()
        saved_data = {}
        
        if recent_file:
            try:
                # Handle both string and dict inputs
                if isinstance(recent_file, str):
                    saved_data = json.loads(recent_file)
                else:
                    saved_data = recent_file
                
            except Exception as e:
                print(f"Error loading tech trees: {e}")
        
        return {
            **saved_data.get("tech_trees", {}),
            **self.tech_evolution.get("tech_trees", {})
        }

    def _process_emerging_tech(self, previous_tech, prev_data, epoch_year, cutoff_years=4):
        """Process emerging technologies with a cutoff period."""
        for tech in prev_data.get("emerging_technologies", []):
            # Convert estimated_year to int for comparison
            estimated_year = int(tech.get("estimated_year", 9999))
            # Only include technologies that are within the cutoff period
            if estimated_year <= epoch_year and (epoch_year - estimated_year) <= cutoff_years:
                previous_tech["emerging"].append({
                    "name": tech["name"],
                    "estimated_year": estimated_year,
                    "probability": tech.get("probability", 0.5)
                })

    def _process_mainstream_tech(self, previous_tech, prev_data, epoch_year):
        """Process mainstream technologies"""
        for tech in prev_data.get("mainstream_technologies", []):
            # Convert maturity_year to int for comparison
            maturity_year = int(tech.get("maturity_year", 9999))
            previous_tech["mainstream"].append({
                "name": tech["name"],
                "maturity_year": maturity_year
            })
            if maturity_year <= epoch_year:
                previous_tech["current_mainstream"].append({
                    "name": tech["name"],
                    "maturity_year": maturity_year
                })

    def _print_tech_summary(self, epoch_year, previous_tech):
        """Print summary of technologies"""
        print(f"\nPrevious technologies for epoch {epoch_year}:")
        print(f"- Emerging: {len(previous_tech['emerging'])}")
        print(f"- Mainstream: {len(previous_tech['mainstream'])}")
        print(f"- Currently Mainstream: {len(previous_tech['current_mainstream'])}")

    def generate_epoch_tech_tree(self, current_year):
        """Generate tech tree for the given epoch year."""
        try:
            # Create log file with timestamp and epoch
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = f"{self.log_dir}/epoch_{current_year}_{timestamp}.txt"
            
            previous_tech = self.get_previous_technologies(current_year)
            years_from_base = current_year - self.base_year
            
            acceleration_factor = math.exp(years_from_base / 30)
            emerging_tech = json.dumps(previous_tech.get('emerging', []), indent=2)
            mainstream_tech = json.dumps(previous_tech.get('mainstream', []), indent=2)

            system_prompt = """You are a technology evolution expert specializing in future forecasting and emerging technologies. Your expertise includes:

                1. CORE COMPETENCIES:
                - Exponential technology growth patterns
                - Cross-domain technology integration
                - Societal impact analysis
                - Market adoption trajectories
                - Technological dependencies and prerequisites

                2. ANALYTICAL FRAMEWORK:
                - Use empirical data and historical patterns
                - Consider technological dependencies
                - Account for societal and ethical implications
                - Evaluate market readiness and adoption barriers
                - Assess regulatory and infrastructure requirements

                3. OUTPUT PRINCIPLES:
                - Maintain logical progression of technology evolution
                - Ensure realistic development timelines
                - Consider both incremental and breakthrough innovations
                - Balance optimism with practical constraints
                - Provide detailed, well-reasoned analyses

                For Emerging Technologies:
                - estimated_year: When the technology first becomes viable/available for early adoption
                - probability: Likelihood of successful development by estimated_year
                - innovation_type: breakthrough (radical change) or incremental (gradual improvement)
                
                For Mainstream Technologies:
                - maturity_year: When the technology becomes widely adopted and standardized
                - from_emerging: Whether it evolved from a previous emerging technology
                - impact_level: Scale of 1-10 for societal impact
                
                Remember:
                - Emerging technologies start as experimental/early-stage
                - Some emerging tech will later become mainstream
                - estimated_year marks first appearance/viability
                - maturity_year marks widespread adoption

                Your task is to generate realistic, well-reasoned technological forecasts that build upon existing developments while maintaining narrative consistency.                
                """

            user_prompt = f"""Generate technological advancements from {current_year} to {current_year + 5}. 

            CONTEXT:
            - Current epoch: {current_year}
            - Years since 2025: {years_from_base}
            - Tech growth rate: {acceleration_factor:0.2f}x faster than in 2025
            - Prior technologies include:
                * Emerging: {emerging_tech}
                * Mainstream: {mainstream_tech}

            GUIDELINES FOR TECHNOLOGY DEVELOPMENT:

            1. **FOCUS AREAS**:
            - **Artificial Intelligence**: Envision a progression from AI assistants to fully automated development, impacting software practices and human-computer interaction. This may include life extension, cognitive enhancement, and development automation.
            - **Autonomous Systems**: Extend advancements in self-operating tech across transport, infrastructure, and resource management, reaching multi-planetary and urban-scale applications.
            - **Neural Interfaces**: Develop human-computer interface tech (e.g., brain-to-machine connections, cognitive tools). Include speculative possibilities like mind uploading, memory storage, or digital consciousness.
            - **Space Exploration**: Envision humanity's ventures beyond Earth, such as lunar and Mars bases, planetary resource management, and technology for interplanetary travel.
            - **Sustainable Technology**: Focus on developments addressing climate challenges, clean energy, and environmental resilience with impacts on long-term planetary health.
            - **Digital Infrastructure**: Prioritize privacy, security, blockchain advancements, and other foundational technologies for a connected, secure digital world.

            2. **INSPIRATION FROM INDUSTRY LEADERS**:
            Prominent companies likely influencing each area include:
                - **Tesla**: Sustainable energy, electric vehicles, and autonomous driving systems.
                - **SpaceX**: Space exploration, interplanetary travel, and Mars colonization.
                - **Neuralink**: Neural tech, brain-machine interfaces, and cognitive enhancement.
                - **Boring Company**: Infrastructure tech, urban transport tunnels, and autonomous systems.
                - **xAI**: Advanced AI, automated development, and collaborative problem-solving.

            3. **DEVELOPMENT PRINCIPLES**:
            - **Exponential Growth**: Technologies should evolve at an accelerated rate, compounding prior advancements to reach breakthroughs sooner.
            - **Stage-Based Evolution**: Major tech should first appear in early forms or experimental stages before reaching full mainstream adoption.
            - **Practical Applications**: Emphasize advancements with tangible, real-world applications; describe societal or industry-specific impacts.
            - **Societal and Ethical Considerations**: Note any societal impacts or regulatory challenges, especially around privacy, security, and human augmentation.
            - **Blockchain Integration**: Where applicable, reference blockchain innovations in security, transparency, or decentralized governance.

            4. **FORMAT AND STRUCTURE**:
            - Exclude isolated tech with no connection to prior advancements or foundations.
            - Avoid highly speculative, far-future developments without credible paths.

            Ensure each new technology builds on prior epochs to maintain continuity in the narrative.

            IMPORTANT: Return a raw JSON object without any markdown formatting or code block markers.
            Do not wrap the response in ```json``` tags.

            RETURN FORMAT (JSON):
            {{
                "emerging_technologies": [
                    {{
                        "name": "technology name",
                        "probability": "0.0 to 1.0",
                        "estimated_year": "YYYY",
                        "expected_maturity_year": "YYYY",
                        "innovation_type": "incremental|breakthrough",
                        "dependencies": ["tech1", "tech2"],
                        "impact_areas": ["area1", "area2"],
                        "description": "brief description",
                        "societal_implications": "impact analysis",
                        "adoption_factors": "adoption analysis"
                    }}
                ],
                "mainstream_technologies": [
                    {{
                        "name": "technology name",
                        "from_emerging": true,
                        "original_emergence_year": "YYYY",
                        "maturity_year": "YYYY",
                        "impact_level": "1 to 10",
                        "description": "brief description",
                        "adoption_status": "adoption analysis"
                    }}
                ],
                "epoch_themes": [
                    {{
                        "theme": "theme name",
                        "description": "brief description",
                        "related_technologies": ["tech1", "tech2"],
                        "societal_impact": "impact analysis",
                        "global_trends": "trend analysis"
                    }}
                ]
            }}
            """
            
            # Log complete context and prompts
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== CONTEXT FOR EPOCH {current_year} ===\n")
                f.write(f"Previous Emerging Tech:\n{emerging_tech}\n\n")
                f.write(f"Previous Mainstream Tech:\n{mainstream_tech}\n\n")
                f.write(f"Years from base: {years_from_base}\n")
                f.write(f"Acceleration factor: {acceleration_factor}\n\n")
                f.write(f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n")
                f.write(f"=== USER PROMPT ===\n{user_prompt}\n\n")
            
            # Make API call and get response
            response = self._get_completion(system_prompt, user_prompt)
            if not response:
                print("Failed to get valid response from AI")
                return None
            
            tech_data = json.loads(response)
            if not tech_data:
                print("Empty tech data received")
                return None
            
            # Update tech evolution with new data
            self.tech_evolution['tech_trees'][str(current_year)] = tech_data
            self.tech_evolution['last_updated'] = datetime.now().isoformat()
            
            return tech_data
            
        except Exception as e:
            print(f"Error generating tech tree: {e}")
            return None

    def save_evolution_data(self):
        """Save the current evolution data"""
        try:
            github_ops = self.github_ops
            file_path = "tech_evolution.json"
            
            print(f"Saving tech evolution data...")
            github_ops.update_file(
                file_path,
                self.tech_evolution,
                "Update tech evolution data"
            )
            return True
            
        except Exception as e:
            print(f"Failed to save evolution data: {str(e)}")
            # Continue with local data
            return False

    def check_and_generate_tech_evolution(self, current_date):
        """Check if a new tech evolution needs to be generated based on the current date."""
        current_year = current_date.year
        
        try:
            # Try to get existing tech evolution
            tech_evolution = self.get_tech_evolution()
            
            if tech_evolution is None:
                print(f"Initializing tech evolution for base year {self.base_year}")
                # Generate initial data
                self.generate_epoch_tech_tree(self.base_year)
                self.save_evolution_data()
                return self.tech_evolution  # Return local data if save failed
            
            # Get latest epoch year
            latest_epoch_year = self.get_latest_epoch_year() or self.base_year
            next_epoch_year = latest_epoch_year + 5
            
            # Only generate if approaching next epoch
            if current_year >= (next_epoch_year - 1) and next_epoch_year % 5 == 0:
                print(f"Approaching next epoch year {next_epoch_year}")
                if str(next_epoch_year) not in self.tech_evolution.get('tech_trees', {}):
                    self.generate_epoch_tech_tree(next_epoch_year)
                    self.save_evolution_data()
            
            return tech_evolution
            
        except Exception as e:
            print(f"Error in tech evolution generation: {e}")
            return self.tech_evolution  # Return local data in case of error

    def get_latest_epoch_year(self):
        """Retrieve the most up-to-date epoch year from the tech evolution data."""
        tech_evolution = self.get_tech_evolution()
        if tech_evolution:
            # If tech_evolution is already a dict, use it directly
            if isinstance(tech_evolution, dict):
                tech_trees = tech_evolution.get("tech_trees", {})
            else:
                # Otherwise parse it as JSON
                try:
                    tech_trees = json.loads(tech_evolution).get("tech_trees", {})
                except:
                    return None
            
            if tech_trees:
                # Get the latest epoch year from the keys
                latest_epoch_year = max(map(int, tech_trees.keys()))
                return latest_epoch_year
        return None  # Return None if no data found

    def _process_tech_response(self, response, epoch_year):
        """Process the API response and update tech evolution data."""
        try:
            # Parse the response JSON
            response_data = json.loads(response)
            
            # Update the tech evolution data with the new epoch data
            self.tech_evolution['tech_trees'][str(epoch_year)] = response_data
            
            # Update the last updated timestamp
            self.tech_evolution['last_updated'] = datetime.now().isoformat()
            
            print(f"Processed tech response for epoch {epoch_year}")
            return response_data
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON response: {e}")
            return None
        except Exception as e:
            print(f"Error processing tech response: {e}")
            return None

    def _get_completion(self, system_prompt, user_prompt):
        """Get completion from AI model."""
        try:
            response = self.ai.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            if not response:
                print("- Warning: Empty response received")
                return None
            
            # Clean up response - remove markdown code block markers and any extra whitespace
            cleaned_response = response
            if '```json' in response:
                cleaned_response = response.split('```json')[-1].split('```')[0].strip()
            
            # Validate JSON structure
            try:
                json.loads(cleaned_response)
                print("- Response is valid JSON")
                return cleaned_response
            except json.JSONDecodeError as e:
                print(f"- Invalid JSON response: {e}")
                print("- Full response:", response)
                return None
            
        except Exception as e:
            print(f"Error getting completion: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Generate technology evolution data')
    parser.add_argument('--provider', type=str, choices=['XAI', 'ANTHROPIC'], 
                       default='XAI', help='AI provider to use')
    
    args = parser.parse_args()
    provider = AIProvider[args.provider]
    print(f"Using provider: {provider}")
    generator = TechEvolutionGenerator(provider)
    
    try:
        # Generate tech trees for each 5-year epoch
        for year in range(generator.base_year, generator.end_year + 1, 5):
            print(f"\nGenerating tech tree for {year}")
            tree_data = generator.generate_epoch_tech_tree(year)
            
            if not tree_data:
                print(f"Failed to generate tech tree for {year}")
                continue
                
            # Add a delay between generations to avoid rate limits
            if year < generator.end_year:
                print("Waiting before next generation...")
                time.sleep(2)  # 2 second delay
        
            # Save the complete evolution data
            generator.save_evolution_data()
        print("\nTechnology evolution generation complete!")
        
    except Exception as e:
        print(f"Error during technology evolution generation: {e}")
        # Still try to save whatever data we have
        generator.save_evolution_data()

if __name__ == "__main__":
    main()