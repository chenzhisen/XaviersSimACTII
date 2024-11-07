import json
from datetime import datetime
import os
from anthropic import Anthropic
from utils.config import Config, AIProvider
from storage.github_operations import GithubOperations
import re

class DigestGenerator:
    def __init__(self):
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )
        self.XaviersSim = 'XaviersSim.json'
        self.github_ops = GithubOperations()
        self.sim_start_year = 2025  # Add this for year calculation

    def process_first_digest(self):
        """Generate initial digest from XaviersSim.json"""
        try:
            # Get existing tweets from ACTI
            actI_content, _ = self.github_ops.get_file_content(self.XaviersSim)
            prompt = self.create_first_digest(actI_content)
            digest = self.generate_digest(prompt)

            if digest:
                # Create timestamped digest entry
                timestamp = datetime.now().isoformat()
                return {
                    "generated_at": timestamp,
                    "content": str(digest),
                    "is_initial": True,
                    "year": self.sim_start_year,
                    "tweet_count": 0
                }
            return None
        except Exception as e:
            print(f"Error creating initial digest: {str(e)}")
            return None

    def create_first_digest(self, actI_content):
        """Create a prompt for initial digest generation from Act I"""
        prompt = (
            "BACKGROUND:\n"
            "Xavier's story (age 18-22) documented his early experiences, relationships, and growth "
            "through social media posts. This digest will bridge his past and future narrative.\n\n"
            
            "ORIGINAL CONTENT:\n"
        )
        
        # Add Act I content
        if isinstance(actI_content, dict):
            prompt += json.dumps(actI_content, indent=2)
        else:
            prompt += str(actI_content)
        
        prompt += self._get_digest_sections(is_first=True)
        print("digest prompt: ", prompt)
        return prompt

    def generate_digest(self, prompt):
        """Generate a digest using xAI API."""
        try:
            message = self.client.messages.create(
                model="grok-beta",
                max_tokens=2048,
                system=(
                    "You are a story curator and narrative architect maintaining Xavier's story. "
                    "Your role is to both document the story's history and guide its future development. "
                    "Create a cohesive summary that captures past events while subtly suggesting natural "
                    "story opportunities for the next 3-6 months. Balance continuity with organic growth, "
                    "ensuring technological and societal changes feel natural within Xavier's personal journey."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            return str(message.content)
        except Exception as e:
            print(f"Error generating digest: {str(e)}")
            return None

    def process_ongoing_digest(self, existing_digest, new_tweets, new_comments):
        """Generate a digest with both summary and future direction"""
        try:
            prompt = self.create_ongoing_prompt(existing_digest, new_tweets, new_comments)
            print("digest prompt: ", prompt)
            updated_digest = self.generate_digest(prompt)
            
            if updated_digest:
                # Create timestamped digest entry
                timestamp = datetime.now().isoformat()
                return {
                    "generated_at": timestamp,
                    "content": updated_digest,
                    "last_processed_tweet": new_tweets[-1]["id"] if new_tweets else None,
                    "tweet_count": len(new_tweets),
                    "year": self._get_current_year()
                }
            return None
        except Exception as e:
            print(f"Error processing ongoing digest: {e}")
            return None

    def create_ongoing_prompt(self, existing_digest, new_tweets, new_comments):
        """Create a prompt for ongoing digest updates"""
        try:
            tech_context = self._get_tech_context(new_tweets)
            
            prompt = (
                "RECENT STORY DEVELOPMENTS:\n"
                f"{json.dumps(new_tweets, indent=2)}\n\n"
                
                "PREVIOUS CONTEXT:\n"
                f"{existing_digest.get('content', 'Story begins with Xavier at age 22 in 2025.')}\n\n"
                
                "ADDITIONAL DETAILS:\n"
                f"{json.dumps(new_comments, indent=2)}\n\n"
                f"{tech_context}\n\n"
                
                "While Xavier’s journey unfolds, he occasionally notices peculiarities that make him wonder if he’s the protagonist in a larger scheme—but he quickly brushes off these thoughts.\n\n"

                "GUIDELINES:\n"
                "- Drive the story forward using recent tweets, but maintain continuity with past events\n"
                "- Evolve ongoing relationships and storylines through recent interactions\n"
                "- Use comments and tech context to enrich but not steer the main narrative\n"
                "- $XVI, a cryptocurrency token, mysteriously linked to Xavier, has special place to Xavier\n"
            )

            prompt += self._get_digest_sections(is_first=False)
            return prompt
            
        except Exception as e:
            print(f"Error creating ongoing prompt: {e}")
            return None

    def _get_tech_context(self, new_tweets):
        """Extract and format technological context including upcoming tech"""
        try:
            # Debug logging
            print("Fetching tech evolution data...")
            tech_evolution, _ = self.github_ops.get_file_content("tech_evolution.json")
            print(f"Tech evolution data: {json.dumps(tech_evolution, indent=2)[:200]}...")  # Print first 200 chars
            
            simulation_state, _ = self.github_ops.get_file_content("simulation_state.json")
            current_year = int(simulation_state.get("current_year", 2025))
            
            # Ensure tech_evolution is a dict
            if isinstance(tech_evolution, str):
                tech_evolution = json.loads(tech_evolution)
            
            # Get tech trees with better error handling
            tech_trees = tech_evolution.get('tech_trees', {}) if isinstance(tech_evolution, dict) else {}
            print(f"Found {len(tech_trees)} tech trees")
            
            if not tech_trees:
                print("No tech trees found in evolution data")
                return ""
            
            # Find current and next epochs
            current_epoch = None
            next_epoch = None
            
            # Convert years to integers for comparison
            years = sorted([int(year) for year in tech_trees.keys()])
            
            # Find current and next epochs
            for year in years:
                if year <= current_year:
                    current_epoch = tech_trees[str(year)]
                elif next_epoch is None:
                    next_epoch = tech_trees[str(year)]
                    break
            
            if not current_epoch:
                return ""
                
            context = (
                f"\nTECH CONTEXT:\n"
                f"Current Epoch ({current_year}-{current_year+5}):\n"
                f"- Mainstream: {json.dumps([tech['name'] for tech in current_epoch['mainstream_technologies']], indent=2)}\n"
                f"- Emerging: {json.dumps([tech['name'] for tech in current_epoch['emerging_technologies']], indent=2)}\n"
                f"- Themes: {json.dumps([theme['theme'] for theme in current_epoch['epoch_themes']], indent=2)}\n\n"
            )
            
            if next_epoch:
                next_year = current_year + 5
                context += (
                    f"Next Epoch ({next_year}-{next_year+5}):\n"
                    f"- Expected: {json.dumps([tech['name'] for tech in next_epoch['emerging_technologies']], indent=2)}\n"
                    f"- Emerging Themes: {json.dumps([theme['theme'] for theme in next_epoch['epoch_themes']], indent=2)}\n\n"
                )
            
            return context
            
        except Exception as e:
            print(f"Error getting tech context: {e}")
            return ""

    def _get_digest_sections(self, is_first=False):
        try:
            simulation_state, _ = self.github_ops.get_file_content("simulation_state.json")
            current_year = int(simulation_state.get("current_year", 2025))
            current_age = current_year - 2025 + 22
            
        except Exception as e:
            print(f"Error getting simulation state: {e}")
            current_age = 22
         
        context = self._get_project_guidance(current_age)

        context = "\nKEY CONTEXT:\n"
        
        if is_first:
            context += (
                "Initial Context:\n"
                "- Xavier returns from Japan with fresh tech perspectives\n"
                "- Focused on positive tech change and societal impact\n\n"
            )
        # Foundation development phase and life phase
        context += (
            f"Current Age: {current_age} (Story spans 22-72, years 2025-2075)\n"
            f"Life Phase: {self._get_life_phase(current_age)}\n"
            f"Project Development: {self._get_project_guidance(current_age)}\n"
            f"$XVI Foundation Phase: {self._get_foundation_phase(current_age)}\n\n"
        )

        # Xavier’s values
        context += (
            "Core Values & Mission:\n"
            "- Positive impact through technology\n"
            "- Curiosity about decentralized systems\n"
            "- Understanding societal challenges\n"
            "- Value of connections and community\n\n"
        )

        context += (
            "Generate a digest with these sections:\n"
            
            "1. STORY SO FAR:\n"
            "- Summarize events and character growth\n"
            "- Track relationships and major life events\n"
            "- Show how available tech shapes Xavier’s experiences\n\n"
            
            "2. STORY DIRECTION:\n"
            "- Drive story forward with opportunities aligned to core values\n"
            "- Explore societal and personal impact of new tech\n"
            "- Introduce challenges that reinforce or test values\n\n"
            
            "3. NARRATIVE GUIDANCE:\n"
            "- Depending on age phase, explore appropriate personal and professional developments\n"
            "- Focus on tech community, learning experiences, and positive growth\n\n"
        )
        
        context += "Balance character growth with Xavier’s ongoing journey in tech and personal life."
        return context

    def _get_life_phase(self, age):
        """Return the current life phase based on age and tech evolution"""
        if age < 25:
            return (
                "Early Career & Personal Growth (22-25)\n"
                "- Professional: Early career in blockchain and Web3\n"
                "- Personal: Dating and exploring city life\n"
                "- Family: Regular family conversations, sharing tech stories\n"
                "- Social: Building first professional network\n"
            )
        elif age < 30:
            return (
                "Growth & Foundation Building (25-30)\n"
                "- Professional: Growing expertise in emerging tech\n"
                "- Personal: Deeper relationships, potential relocation\n"
                "- Family: Staying connected through evolving tech\n"
                "- Social: Expanding network across tech hubs\n"
            )
        elif age < 35:
            return (
                "Stability & Partnership (30-35)\n"
                "- Professional: Growing leadership in tech\n"
                "- Personal: Partnership/marriage\n"
                "- Family: Blending traditions with modern life\n"
                "- Social: Building lasting communities\n"
            )
        elif age < 45:
            return (
                "Family & Leadership (35-45)\n"
                "- Professional: Pioneering while raising family\n"
                "- Personal: Early parenthood journey\n"
                "- Family: Creating tech-aware household\n"
                "- Social: Building family-friendly networks\n"
            )
        elif age < 60:
            return (
                "Legacy & Mentorship (45-60)\n"
                "- Professional: Shaping industry future\n"
                "- Personal: Supporting children's growth\n"
                "- Family: Multi-generational connections\n"
                "- Social: Mentoring next generation\n"
            )
        else:
            return (
                "Wisdom & Succession (60+)\n"
                "- Professional: Advisory and guidance\n"
                "- Personal: Grandparent phase\n"
                "- Family: Bridging generations\n"
                "- Social: Elder community voice\n"
            )

    def _get_project_guidance(self, age):
        """Return age-appropriate project guidance"""
        if age < 25:
            return (
                "- Focus on practical, achievable blockchain projects\n"
                "- Start with existing tech solutions\n"
                "- Show learning through implementation\n"
                "- Build credibility through small wins\n"
                "- Demonstrate growing technical expertise\n\n"
            )
        elif age < 35:
            return (
                "- Balance practical solutions with innovative concepts\n"
                "- Begin exploring novel applications\n"
                "- Combine multiple technologies creatively\n"
                "- Show increasing project scope and impact\n"
                "- Build on established reputation\n\n"
            )
        else:
            return (
                "- Push boundaries with breakthrough concepts\n"
                "- Lead technological paradigm shifts\n"
                "- Create revolutionary solutions\n"
                "- Shape future tech directions\n"
                "- Influence industry standards\n\n"
            )
        
    def _get_current_year(self):
        """Calculate current year based on simulation state"""
        try:
            state, _ = self.github_ops.get_file_content("simulation_state.json")
            if isinstance(state, dict):
                return state.get("current_year", self.sim_start_year)
            return self.sim_start_year
        except Exception as e:
            print(f"Error getting current year: {e}")
            return self.sim_start_year

    def _get_foundation_phase(self, age):
        """Track $XVI Foundation development phase"""
        if age < 23:
            return "Pre creation"
        elif age < 25:
            return "Concept Development"
        elif age < 28:
            return "Initial Implementation"
        elif age < 32:
            return "Foundation Formation"
        elif age < 40:
            return "Growth & Establishment"
        elif age < 50:
            return "Scaling Impact"
        elif age < 60:
            return "Global Expansion"
        elif age < 70:
            return "Legacy Building"
        else:
            return "Succession & Future"

def main():
    generator = DigestGenerator()
    digest = generator.process_first_digest()
    print(digest)

if __name__ == "__main__":
    main()
