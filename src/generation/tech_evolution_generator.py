import argparse
from anthropic import Anthropic
from src.utils.config import Config, AIProvider
from src.storage.github_operations import GithubOperations
import json
from datetime import datetime
import os
import time
import requests

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
        
        print(f"Using model: {ai_config.model}")
        print(ai_config.api_key, ai_config.base_url)
        self.model = ai_config.model
        self.base_year = 2025
        self.end_year = 2080
        self.evolution_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "base_year": self.base_year,
                "end_year": self.end_year
            },
            "tech_trees": {}
        }

    def get_data_directory(self):
        """Ensure data directory exists and return its path"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir

    def get_most_recent_evolution_file(self):
        """Get the most recently saved tech evolution file"""
        try:
            github_ops = GithubOperations()
            # List files in the data directory
            url = f"{github_ops.base_url}/repos/{github_ops.repo_owner}/{github_ops.repo_name}/contents/data"
            response = requests.get(url, headers=github_ops.headers)
            response.raise_for_status()
            
            # Filter for tech evolution files
            tech_files = [f for f in response.json() if f['name'].startswith('tech_evolution_')]
            if not tech_files:
                return None
                
            # Sort by name (which includes timestamp) to get the most recent
            tech_files.sort(key=lambda x: x['name'], reverse=True)
            latest_file = tech_files[0]['name']
            
            # Get the content of the latest file
            content, _ = github_ops.get_file_content(latest_file)
            return content
            
        except Exception as e:
            print(f"Error getting most recent evolution file: {e}")
            return None

    def get_previous_technologies(self, epoch_year):
        """Get technologies from previous epochs"""
        previous_tech = {
            "emerging": [],  # Technologies that were emerging in previous epochs
            "mainstream": [], # Technologies that became mainstream in previous epochs
            "current_mainstream": []  # Technologies that are currently mainstream
        }
        
        # Try to load from most recent file first
        recent_file = self.get_most_recent_evolution_file()
        if recent_file:
            try:
                with open(recent_file, 'r') as f:
                    saved_data = json.load(f)
                    print(f"Loaded previous technology data from {recent_file}")
            except Exception as e:
                print(f"Error loading {recent_file}: {e}")
                saved_data = {"tech_trees": {}}
        else:
            saved_data = {"tech_trees": {}}
        
        # Combine saved data with current data
        all_tech_trees = {
            **saved_data.get("tech_trees", {}),
            **self.evolution_data.get("tech_trees", {})
        }
        
        # Process technologies from previous epochs
        for year in range(self.base_year, epoch_year, 5):
            year_str = str(year)
            if year_str in all_tech_trees:
                prev_data = all_tech_trees[year_str]
                
                # Add emerging technologies with their predicted years
                for tech in prev_data.get("emerging_technologies", []):
                    previous_tech["emerging"].append({
                        "name": tech["name"],
                        "estimated_year": tech["estimated_year"],
                        "probability": tech.get("probability", 0.5)
                    })
                
                # Add mainstream technologies
                for tech in prev_data.get("mainstream_technologies", []):
                    previous_tech["mainstream"].append({
                        "name": tech["name"],
                        "maturity_year": tech["maturity_year"]
                    })
                    # If this technology is mature by current epoch, add to current_mainstream
                    if tech["maturity_year"] <= epoch_year:
                        previous_tech["current_mainstream"].append({
                            "name": tech["name"],
                            "maturity_year": tech["maturity_year"]
                        })
        
        # Print summary
        print(f"\nPrevious technologies for epoch {epoch_year}:")
        print(f"- Emerging: {len(previous_tech['emerging'])}")
        print(f"- Mainstream: {len(previous_tech['mainstream'])}")
        print(f"- Currently Mainstream: {len(previous_tech['current_mainstream'])}")
        
        return previous_tech
    
    def generate_epoch_tech_tree(self, epoch_year):
        previous_tech = self.get_previous_technologies(epoch_year)
        years_from_base = epoch_year - self.base_year
        acceleration_factor = 1 + (years_from_base / 20)
        
        prompt = f"""Generate realistic technological advancements and developments expected for the period {epoch_year} to {epoch_year + 5}. 

        Context:
        - Current year being analyzed: {epoch_year}
        - Years from base year (2025): {years_from_base}
        - Technology acceleration factor: {acceleration_factor:.2f}x, indicating that advancements during this period are progressing {acceleration_factor:.2f} times faster than in 2025
        - Previous emerging technologies include: {previous_tech['emerging']}
        - Currently mainstream technologies include: {previous_tech['mainstream']}
        
        Important Guidelines for Plausible Technological Development:
        
        1. **Advancement Level by Epoch**:
           - In the period {epoch_year}-{epoch_year + 5}, we expect:
             - **2025-2035**: Moderate, incremental developments and initial integrations of advanced technology in society.
             - **2035-2050**: Significant breakthroughs with notable societal impact, emphasizing combined systems and smarter integrations.
             - **2050+**: Revolutionary, transformative technologies with fundamental changes to human life, such as full automation and large-scale AI-human integration.
        
        2. **Practical Technology Implementation**:
           - For earlier periods (e.g., 2025-2035), prioritize practical applications that enhance daily life, infrastructure, healthcare, and energy, focusing on:
             - Enhancements to current devices (like wearables, medical devices, and home assistants)
             - Early steps toward AI and robotics in household and urban settings
             - Basic applications of brain-computer interfaces, digital identity management, and blockchain for secure transactions
        
        3. **Example Technology Areas**:
           - **Digital Trust & Robotics**:
             - Improved blockchain for secure digital identity verification
             - Household assistant robots with limited autonomy and safety protocols
             - Decentralized control systems and tokenized resources for households
           - **Neural Integration**:
             - Brain-computer interface applications for specialized tasks (e.g., medical support, accessibility)
             - Simple neural-feedback devices for focused functions like cognitive enhancement and stress management
           - **Infrastructure & Personal Transportation**:
             - Limited personal autonomous vehicles for urban settings
             - Robotic assistance in smart home management and minor repair work
           - **Space Exploration** (as long-term planning, with limited advances for near-term epochs):
             - Minimal applications like AI-driven remote monitoring and basic autonomous maintenance
             - Robots adapted for simple habitat support (e.g., cleaning, resource allocation)
           - **Healthcare Innovations**:
             - Health-monitoring wearables integrated with AI analytics
             - Basic medical robots for diagnostic support and preventive care
             - AI-based genetic health screenings and personalized wellness tracking
           - **Sustainability & Energy**:
             - Household robots with energy-saving functionalities
             - Smart home energy management integrated with urban infrastructure
             - Basic autonomous recycling and waste management robots

        4. **Technology Integration Level by Epoch**:
           - **2025-2035**: Focused on individual improvements and practical integration into daily life.
           - **2035-2050**: Greater convergence of tech systems; more seamless AI-robot-human collaboration.
           - **2050+**: Fundamental transformations in human life, full adoption of highly integrated AI, robotics, and sustainable systems.

        Return your response in the following JSON structure:
        {{
            "emerging_technologies": [
                {{
                    "name": "new technology emerging in {epoch_year}-{epoch_year + 5}",
                    "probability": 0.0-1.0,
                    "estimated_year": YYYY,
                    "innovation_type": "incremental|breakthrough",
                    "dependencies": ["tech1", "tech2"],
                    "impact_areas": ["area1", "area2"],
                    "description": "brief description",
                    "societal_implications": "analysis of social impact and ethical considerations",
                    "adoption_factors": "analysis of societal readiness and adoption barriers"
                }}
            ],
            "mainstream_technologies": [
                {{
                    "name": "technology maturing in {epoch_year}-{epoch_year + 5}",
                    "from_emerging": true,
                    "original_emergence_year": YYYY,
                    "maturity_year": YYYY,
                    "impact_level": 1-10,
                    "description": "brief description",
                    "adoption_status": "description of societal adoption and integration"
                }}
            ],
            "epoch_themes": [
                {{
                    "theme": "major theme for {epoch_year}-{epoch_year + 5}",
                    "description": "brief description",
                    "related_technologies": ["tech1", "tech2"],
                    "societal_impact": "analysis of broader societal implications",
                    "global_trends": "relationship to global technological trends"
                }}
            ]
        }}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system="You are a technology futurist helping to generate realistic technology evolution scenarios.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
             # Handle TextBlock response format
            if isinstance(response.content, list):
                # Combine all text blocks into a single string
                full_text = ''.join(block.text for block in response.content)
                
                # Extract JSON from the combined text
                import re
                json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
                if json_match:
                    tree_data = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            else:
                tree_data = json.loads(response.content)
            
            # Validate the data is unique for this epoch
            if str(epoch_year) in self.evolution_data["tech_trees"]:
                existing_data = self.evolution_data["tech_trees"][str(epoch_year)]
                if existing_data == tree_data:
                    raise ValueError(f"Generated data for {epoch_year} is identical to existing data")
            
            # Add epoch identifier to the data
            tree_data["epoch_year"] = epoch_year
            
            # Store the data
            self.evolution_data["tech_trees"][str(epoch_year)] = tree_data
            
            # Print summary of generated data
            print(f"Generated for {epoch_year}:")
            print(f"- Emerging technologies: {len(tree_data['emerging_technologies'])}")
            print(f"- Mainstream technologies: {len(tree_data['mainstream_technologies'])}")
            print(f"- Epoch themes: {len(tree_data['epoch_themes'])}")
            
            return tree_data
            
        except Exception as e:
            print(f"Failed to generate tech tree for {epoch_year}: {e}")
            if 'response' in locals():
                print("Full response type:", type(response.content))
                if isinstance(response.content, list):
                    print("First few blocks:", response.content[:3])
            return None

    def save_evolution_data(self):
        """Save the current evolution data to GitHub"""
        try:
            github_ops = GithubOperations()
            file_path = "tech_evolution.json"  # Remove the extra data/ prefix

            # Try to get existing file's SHA
            try:
                print("Fetching existing file content...")
                existing_content, sha = github_ops.get_file_content(file_path)
                print(f"Found existing file with SHA: {sha}")
            except Exception as e:
                print(f"No existing file found or error: {e}")
                sha = None

            # Prepare content
            content_json = json.dumps(self.evolution_data, indent=2)
            print(f"Content size: {len(content_json)} bytes")
            
            # Save/update file
            try:
                if sha:  # If file exists, we need the SHA
                    response = github_ops.update_file(
                        file_path=file_path,
                        content=self.evolution_data,
                        commit_message=f"Update tech evolution data for {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        sha=sha
                    )
                else:  # First time creation
                    response = github_ops.update_file(
                        file_path=file_path,
                        content=self.evolution_data,
                        commit_message=f"Create tech evolution data for {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                print(f"Update response: {response}")
            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error: {e.response.status_code}")
                print(f"Error response: {e.response.text}")
                raise
                
            print(f"Saved evolution data to {file_path}")
                
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