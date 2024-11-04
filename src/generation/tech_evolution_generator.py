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
            "tech_trees": {},
            "last_updated": datetime.now().isoformat()
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
        try:
            previous_tech = self.get_previous_technologies(epoch_year)
            years_from_base = epoch_year - self.base_year
            acceleration_factor = 1 + (years_from_base / 20)
            
            prompt = f"""Generate technological advancements for {epoch_year} to {epoch_year + 5}. 

            CONTEXT:
            - Current epoch: {epoch_year}
            - Years from 2025: {years_from_base}
            - Tech acceleration: {acceleration_factor:.2f}x faster than 2025
            - Previous emerging tech: {json.dumps(previous_tech.get('emerging', []))}
            - Current mainstream tech: {json.dumps(previous_tech.get('mainstream', []))}
            
            DEVELOPMENT GUIDELINES:

            1. FOCUS AREAS & INTEGRATIONS:
               - AI & Robotics
                 * AI-driven smart contracts
                 * Decentralized AI governance
                 * Tokenized AI models
               
               - Autonomous Systems
                 * Blockchain-verified autonomous decisions
                 * Decentralized transport networks
                 * Token-incentivized infrastructure
               
               - Neural Interfaces
                 * Blockchain identity and memory markets
                 * Tokenized cognitive enhancements
                 * DAO-governed neural networks
               
               - Space Technology
                 * Decentralized space operations
                 * Interplanetary settlement DAOs
                 * Space resource tokenization
               
               - Sustainable Energy
                 * Tokenized energy markets
                 * Decentralized grid management
                 * Green energy certificates
               
               - Digital Infrastructure
                 * Zero-knowledge applications
                 * Cross-chain innovations
                 * Decentralized physical infrastructure

            2. DEVELOPMENT PRINCIPLES:
               - Focus on practical implementations
               - Consider real-world constraints
               - Balance innovation with reliability
               - Account for societal adoption
               - Emphasize blockchain integration

            3. AVOID:
               - Isolated technological developments
               - Unrealistic breakthroughs
               - Technologies without clear predecessors

            Return JSON:
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
            }}"""
            
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
            
            # Get the response content
            if hasattr(response, 'content') and len(response.content) > 0:
                # Extract text from the first content block
                text_content = response.content[0].text
                
                # Clean up the response
                clean_response = text_content.replace('```json\n', '').replace('```', '').strip()
                
                print("\nComplete response length:", len(clean_response))
                print("First 200 chars:", clean_response[:200])
                
                try:
                    tree_data = json.loads(clean_response)
                    # Validate the structure
                    required_keys = ['emerging_technologies', 'mainstream_technologies', 'epoch_themes']
                    if not all(key in tree_data for key in required_keys):
                        raise ValueError(f"Missing required keys in response. Got: {list(tree_data.keys())}")
                    
                    # Add epoch identifier and store the data
                    tree_data["epoch_year"] = epoch_year
                    self.evolution_data["tech_trees"][str(epoch_year)] = tree_data
                    
                    # Print summary
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
            if 'complete_response' in locals():
                print("Full response:", complete_response)
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