import json
from datetime import datetime
import os
from anthropic import Anthropic
from src.utils.config import Config, AIProvider
from src.storage.github_operations import GithubOperations

class DigestGenerator:
    def __init__(self):
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )
        self.XaviersSim = 'XaviersSim.json'

    def process_digest(self):
        """Generate initial digest from XaviersSim.json"""
        try:
            # Get existing tweets from ACTI
            actI_content, _ = GithubOperations().get_file_content(self.XaviersSim)
            prompt = self.create_first_digest(actI_content)
            digest = self.generate_digest(prompt)

            if digest:
                # Format the digest properly
                digest_content = {
                    "generated_at": datetime.now().isoformat(),
                    "content": str(digest)  # Ensure content is a string
                }
                return digest_content  # Return formatted content
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
            updated_digest = self.generate_digest(prompt)
            
            if updated_digest:
                return {
                    "generated_at": datetime.now().isoformat(),
                    "content": updated_digest,
                    "last_processed_tweet": new_tweets[-1]["id"] if new_tweets else None
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
                "CURRENT STORY DIGEST:\n"
                f"{existing_digest.get('content', 'Story begins with Xavier at age 22 in 2025.')}\n\n"
                
                "RECENT UPDATES:\n"
                f"New Tweets:\n{json.dumps(new_tweets, indent=2)}\n\n"
                f"Related Comments:\n{json.dumps(new_comments, indent=2)}\n\n"
                f"{tech_context}"
            )
            
            prompt += self._get_digest_sections(is_first=False)
            return prompt
            
        except Exception as e:
            print(f"Error creating ongoing prompt: {e}")
            return None

    def _get_tech_context(self, new_tweets):
        """Extract and format technological context including upcoming tech"""
        try:
            tech_evolution, _ = GithubOperations().get_file_content("tech_evolution.json")
            if not isinstance(tech_evolution, dict):
                return ""
                
            # Calculate current year from latest tweet
            current_year = 2025
            if new_tweets:
                year_str = new_tweets[-1]['content'].split('[')[1].split('|')[0].strip()
                current_year = int(year_str)
            
            # Find current and next epoch
            epochs = [int(epoch) for epoch in tech_evolution.get('tech_trees', {}).keys()]
            current_epoch = max([e for e in epochs if e <= current_year], default=None)
            next_epoch = min([e for e in epochs if e > current_year], default=None)
            
            if not current_epoch:
                return ""
                
            current_data = tech_evolution['tech_trees'][str(current_epoch)]
            next_data = tech_evolution['tech_trees'].get(str(next_epoch)) if next_epoch else None
            
            context = (
                f"\nTECHNOLOGICAL CONTEXT:\n"
                f"Current Epoch ({current_epoch}-{current_epoch+5}):\n"
                f"- Mainstream Technologies: {json.dumps([tech['name'] for tech in current_data['mainstream_technologies']], indent=2)}\n"
                f"- Currently Emerging: {json.dumps([tech['name'] for tech in current_data['emerging_technologies']], indent=2)}\n"
                f"- Major Themes: {json.dumps([theme['theme'] for theme in current_data['epoch_themes']], indent=2)}\n\n"
            )
            
            if next_data:
                context += (
                    f"Upcoming Epoch ({next_epoch}-{next_epoch+5}):\n"
                    f"- Expected Technologies: {json.dumps([tech['name'] for tech in next_data['emerging_technologies']], indent=2)}\n"
                    f"- Emerging Themes: {json.dumps([theme['theme'] for theme in next_data['epoch_themes']], indent=2)}\n\n"
                )
            
            return context
            
        except Exception as e:
            print(f"Error getting tech context: {e}")
            return ""

    def _get_digest_sections(self, is_first=False):
        """Return standardized digest sections based on context"""
        if is_first:
            context = (
                "\nKEY CONTEXT:\n"
                "- Xavier has a deep connection to New York from his earlier years\n"
                "- He is actively planning to return to New York to pursue his next chapter\n"
                "- His future narrative will primarily take place in New York\n"
                "- The city represents both his past experiences and future opportunities\n\n"
            )
        else:
            context = "\n"

        return (
            f"{context}"
            "Please create a comprehensive digest with two sections:\n\n"
            
            "SECTION 1 - STORY SO FAR:\n"
            "1. Summarize the existing narrative and recent developments\n"
            "2. Track ongoing relationships and character growth\n"
            "3. Note significant life events and decisions\n"
            "4. Highlight emerging themes and patterns\n"
            "5. Show how available technology shapes Xavier's experiences\n\n"
            
            "SECTION 2 - STORY DIRECTION:\n"
            "1. Outline potential story arcs for the next 3-6 months that:\n"
            "   - Naturally incorporate available and emerging technologies\n"
            "   - Consider how tech trends might affect relationships and work\n"
            "   - Balance personal growth with societal changes\n"
            "2. Suggest natural developments in:\n"
            "   - Career progression in the evolving tech landscape\n"
            "   - Relationship dynamics influenced by new technologies\n"
            "   - Personal growth opportunities\n"
            "   - New York life experiences in a changing world\n"
            "3. Identify potential challenges or conflicts, including:\n"
            "   - Adapting to technological changes\n"
            "   - Balancing traditional and digital relationships\n"
            "   - Ethical considerations of new technologies\n"
            "4. Note seasonal or contextual opportunities\n\n"
            
            "Keep the story direction subtle and open-ended, providing guidance while allowing "
            "for natural tweet generation. Focus on creating situations and opportunities "
            "rather than prescribing specific outcomes. Ensure technology integration feels "
            "natural and serves the story rather than dominating it."
        )

def main():
    generator = DigestGenerator()
    digest = generator.process_digest()
    print(digest)

if __name__ == "__main__":
    main()
