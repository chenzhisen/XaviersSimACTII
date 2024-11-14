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
    def __init__(self, github_ops, client, model):
        """Initialize the tech evolution generator"""
        self.github_ops = github_ops
        self.client = client
        self.model = model
        self.base_year = 2025
        self.tech_evolution = {
            "tech_trees": {},
            "last_updated": datetime.now().isoformat()
        }
        
        # Create logs directory
        self.log_dir = "logs/tech_evolution"
        os.makedirs(self.log_dir, exist_ok=True)

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
            **self.tech_evolution.get("tech_trees", {})
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
            # Create log file with timestamp and epoch
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = f"{self.log_dir}/epoch_{epoch_year}_{timestamp}.txt"
            
            previous_tech = self.get_previous_technologies(epoch_year)
            years_from_base = epoch_year - self.base_year
            
            acceleration_factor = math.exp(years_from_base / 30)
            emerging_tech = json.dumps(previous_tech.get('emerging', []), indent=2)
            mainstream_tech = json.dumps(previous_tech.get('mainstream', []), indent=2)

            prompt = f"""Generate technological advancements from {epoch_year} to {epoch_year + 5}. 

            CONTEXT:
            - Current epoch: {epoch_year}
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


            RETURN FORMAT (JSON):
            {{
                "emerging_technologies": [
                    {{
                        "name": "technology name",
                        "probability": "0.0 to 1.0",
                        "estimated_year": "YYYY",
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
            # Log prompt before API call
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== PROMPT FOR EPOCH {epoch_year} ===\n")
                f.write(prompt)
                
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
                print("Got text content from response")
                
                # Log raw response
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write("\n\n=== RAW RESPONSE ===\n")
                    f.write(text_content)
                
                try:
                    clean_response = text_content.replace('```json\n', '').replace('```', '').strip()
                    tree_data = json.loads(clean_response)
                    
                    # Log parsed JSON
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== PARSED JSON ===\n")
                        f.write(json.dumps(tree_data, indent=2))
                    
                    # Validate the structure
                    required_keys = ['emerging_technologies', 'mainstream_technologies', 'epoch_themes']
                    if not all(key in tree_data for key in required_keys):
                        error_msg = f"Missing required keys in response. Got: {list(tree_data.keys())}"
                        print(error_msg)  # Add debug print
                        with open(log_path, 'a', encoding='utf-8') as f:
                            f.write("\n\n=== VALIDATION ERROR ===\n")
                            f.write(error_msg)
                        raise ValueError(error_msg)
                    
                    # Add epoch identifier and store the data
                    tree_data["epoch_year"] = epoch_year
                    self.tech_evolution["tech_trees"][str(epoch_year)] = tree_data
                    
                    print(f"\nGenerated for {epoch_year}:")
                    print(f"- Emerging technologies: {len(tree_data['emerging_technologies'])}")
                    print(f"- Mainstream technologies: {len(tree_data['mainstream_technologies'])}")
                    print(f"- Epoch themes: {len(tree_data['epoch_themes'])}")
                    
                    # Log summary
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== GENERATION SUMMARY ===\n")
                        f.write(f"Epoch: {epoch_year}\n")
                        f.write(f"Emerging technologies: {len(tree_data['emerging_technologies'])}\n")
                        f.write(f"Mainstream technologies: {len(tree_data['mainstream_technologies'])}\n")
                        f.write(f"Epoch themes: {len(tree_data['epoch_themes'])}\n")
                    
                    return tree_data
                    
                except json.JSONDecodeError as e:
                    error_msg = f"JSON parse error: {e}\nClean response: {clean_response[:500]}"
                    # Log parsing error
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== PARSING ERROR ===\n")
                        f.write(error_msg)
                    raise ValueError("Could not parse response as JSON")
            else:
                error_msg = "No content received in response"
                # Log empty response error
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write("\n\n=== ERROR ===\n")
                    f.write(error_msg)
                raise ValueError(error_msg)
                
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
                    existing_trees.update(self.tech_evolution.get('tech_trees', {}))
                    
                    # Create updated content
                    updated_content = {
                        'tech_trees': existing_trees,
                        'last_updated': datetime.now().isoformat()
                    }
                else:
                    updated_content = self.tech_evolution
                
                print(f"Total tech trees after merge: {len(updated_content['tech_trees'])}")
                
            except Exception as e:
                print(f"No existing file found or error: {e}")
                updated_content = self.tech_evolution
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