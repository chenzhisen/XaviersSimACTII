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


class TechEvolutionGenerator:
    def __init__(self, provider: AIProvider = AIProvider.XAI):
        ai_config = Config.get_ai_config(provider)
        
        if provider == AIProvider.ANTHROPIC:
            self.client = Anthropic(api_key=ai_config.api_key)
        elif provider == AIProvider.XAI:
            self.client = Anthropic( 
                api_key=ai_config.api_key,
                base_url=ai_config.base_url
            )
        
        self.model = ai_config.model
        self.base_year = 2025
        self.end_year = 2080
        self.evolution_data = {
            "tech_trees": {},
            "last_updated": datetime.now().isoformat()
        }

    def get_tech_evolution(self):
        """Get the most recently saved tech evolution file"""
        try:
            github_ops = GithubOperations()
            # Get the tech evolution file directly
            content, _ = github_ops.get_file_content("tech_evolution.json")
            return content
            
        except Exception as e:
            print(f"Error getting tech evolution file: {e}")
            return None

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
            self._process_emerging_tech(previous_tech, prev_data)
            self._process_mainstream_tech(previous_tech, prev_data, epoch_year)
        
        self._print_tech_summary(epoch_year, previous_tech)
        return previous_tech

    def _load_tech_trees(self):
        """Load and combine saved and current tech trees"""
        recent_file = self.get_tech_evolution()
        saved_data = {}
        
        if recent_file:
            try:
                saved_data = json.loads(recent_file)
            except Exception as e:
                print(f"Error loading tech trees: {e}")
        
        return {
            **saved_data.get("tech_trees", {}),
            **self.evolution_data.get("tech_trees", {})
        }

    def _process_emerging_tech(self, previous_tech, prev_data):
        """Process emerging technologies"""
        for tech in prev_data.get("emerging_technologies", []):
            previous_tech["emerging"].append({
                "name": tech["name"],
                "estimated_year": tech["estimated_year"],
                "probability": tech.get("probability", 0.5)
            })

    def _process_mainstream_tech(self, previous_tech, prev_data, epoch_year):
        """Process mainstream technologies"""
        for tech in prev_data.get("mainstream_technologies", []):
            previous_tech["mainstream"].append({
                "name": tech["name"],
                "maturity_year": tech["maturity_year"]
            })
            if tech["maturity_year"] <= epoch_year:
                previous_tech["current_mainstream"].append({
                    "name": tech["name"],
                    "maturity_year": tech["maturity_year"]
                })

    def _print_tech_summary(self, epoch_year, previous_tech):
        """Print summary of technologies"""
        print(f"\nPrevious technologies for epoch {epoch_year}:")
        print(f"- Emerging: {len(previous_tech['emerging'])}")
        print(f"- Mainstream: {len(previous_tech['mainstream'])}")
        print(f"- Currently Mainstream: {len(previous_tech['current_mainstream'])}")

    def generate_epoch_tech_tree(self, epoch_year):
        try:
            previous_tech = self.get_previous_technologies(epoch_year)
            years_from_base = epoch_year - self.base_year
            acceleration_factor = math.exp(years_from_base / 30)

            prompt = f"""Generate technological advancements for the period {epoch_year} to {epoch_year + 5}. 

            CONTEXT:
            - Current epoch: {epoch_year}
            - Years from 2025: {years_from_base}
            - Tech acceleration (exponential growth): {acceleration_factor:.2f}x faster than in 2025
            - Previous emerging technologies: {json.dumps(previous_tech.get('emerging', []))}
            - Current mainstream technologies: {json.dumps(previous_tech.get('mainstream', []))}

            DEVELOPMENT GUIDELINES:

            1. FOCUS AREAS & INTEGRATIONS:
                - **Artificial Intelligence**: 
                    * AI Coding Assistants (like @cursor_ai, Copilot)
                    * Impact on software development practices
                    * Evolution from code completion to full development automation
                    * Integration with version control and deployment
                    * Real-time collaborative coding and debugging
                    * Encompasses advancements in machine learning, automation, and intelligent systems across various applications.
                - **Autonomous Systems**: Involves self-operating technologies across transportation, infrastructure, and daily life.
                - **Neural Technology**: Explores human-computer interactions, brain interfaces, and enhanced cognitive tools.
                - **Space Exploration**: Envisions humanity’s ventures into space, including settlement, resource management, and exploration.
                - **Sustainable Technology**: Focuses on energy efficiency, environmental resilience, and sustainability-driven innovations.
                - **Digital Infrastructure**: Centers on privacy, security, and advancements in digital infrastructure for a connected world.

            2. DEVELOPMENT PRINCIPLES:
                - **Exponential Growth**: Technologies should develop at an exponential rate, with earlier emergence and faster sophistication due to compounding advancements.
                - **Stage-Based Evolution**: Major technologies should appear as emerging stages, prototypes, or early versions before maturing into mainstream applications.
                - **Practical Applications**: Prioritize technologies that offer practical and tangible benefits, and consider real-world constraints for societal adoption.
                - **Societal Impact**: Emphasize technologies that consider ethical implications, regulatory challenges, and social adoption factors.
                - **Blockchain Integration**: Include blockchain innovations where applicable, especially in areas of security, privacy, and digital infrastructure.
                - **Balance**: Aim for a mix of breakthrough and incremental improvements to reflect the diverse pace of tech development.
                - **Developer Tools Evolution**:
                    * Track progression from basic code completion to advanced pair programming
                    * Consider impact on software development lifecycle
                    * Note changes in how developers work and learn
                    * Include social coding and knowledge sharing aspects

            3. EXCLUDE:
                - Isolated developments without clear predecessors or dependencies.
                - Overly futuristic breakthroughs without foundational technologies.
                - Technologies with no foreseeable path to real-world impact or adoption.

            RETURN FORMAT (JSON):
            {{
                "emerging_technologies": [
                    {{
                        "name": "technology name",
                        "probability": 0.0-1.0,
                        "estimated_year": YYYY,
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
                        "original_emergence_year": YYYY,
                        "maturity_year": YYYY,
                        "impact_level": 1-10,
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
            # print(prompt)
            
            print("\nSending request to API...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Process response
            if hasattr(response, 'content') and len(response.content) > 0:
                text_content = response.content[0].text
                clean_response = text_content.replace('```json\n', '').replace('```', '').strip()
                print(clean_response)
                try:
                    tree_data = json.loads(clean_response)
                    # Validate the structure
                    required_keys = ['emerging_technologies', 'mainstream_technologies', 'epoch_themes']
                    if not all(key in tree_data for key in required_keys):
                        raise ValueError(f"Missing required keys in response. Got: {list(tree_data.keys())}")
                    
                    # Add epoch identifier and store the data
                    tree_data["epoch_year"] = epoch_year
                    self.evolution_data["tech_trees"][str(epoch_year)] = tree_data
                    
                    print(f"\nGenerated for {epoch_year}:")
                    print(f"- Emerging technologies: {len(tree_data['emerging_technologies'])}")
                    print(f"- Mainstream technologies: {len(tree_data['mainstream_technologies'])}")
                    print(f"- Epoch themes: {len(tree_data['epoch_themes'])}")
                    
                    return tree_data
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print("Clean response:", clean_response[:500])  # Print first 500 chars
                    raise ValueError("Could not parse response as JSON")
            else:
                raise ValueError("No content received in response")
                
        except Exception as e:
            print(f"Failed to generate tech tree for {epoch_year}: {e}")
            return None

    def save_evolution_data(self):
        """Save the current evolution data to GitHub"""
        try:
            github_ops = GithubOperations()
            file_path = "tech_evolution.json"

            # Try to get existing file content
            try:
                print("Fetching existing file content...")
                existing_content, sha = github_ops.get_file_content(file_path)
                if existing_content:
                    # Parse existing content if it's a string
                    if isinstance(existing_content, str):
                        existing_content = json.loads(existing_content)
                    
                    # Merge tech trees
                    existing_trees = existing_content.get('tech_trees', {})
                    existing_trees.update(self.evolution_data.get('tech_trees', {}))
                    
                    # Create updated content
                    updated_content = {
                        'tech_trees': existing_trees,
                        'last_updated': datetime.now().isoformat()
                    }
                else:
                    updated_content = self.evolution_data
                
                print(f"Total tech trees after merge: {len(updated_content['tech_trees'])}")
                
            except Exception as e:
                print(f"No existing file found or error: {e}")
                updated_content = self.evolution_data
                sha = None

            # Convert to JSON string before saving
            json_content = json.dumps(updated_content, indent=2)
            
            # Save/update file
            try:
                if sha:  # Update existing file
                    response = github_ops.update_file(
                        file_path=file_path,
                        content=json_content,
                        commit_message=f"Update tech evolution data for {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        sha=sha
                    )
                else:  # Create new file
                    response = github_ops.update_file(
                        file_path=file_path,
                        content=json_content,
                        commit_message=f"Create tech evolution data for {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                
                print(f"Saved evolution data to {file_path}")
                
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error: {e.response.status_code}")
                print(f"Error response: {e.response.text}")
                raise
                
        except Exception as e:
            print(f"Failed to save evolution data: {e}")

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