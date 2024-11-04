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
        """Create a prompt for initial digest generation"""
        prompt = (
            "You are tasked with creating a digest of 'Xavier's Sim', a narrative Twitter project that "
            "chronicled Xavier's life from age 18 to 22 (though it was originally planned to continue until age 72). "
            "This digest will serve as a foundation for continuing Xavier's story. "
            "The original tweets covered approximately 4 years of Xavier's life, documenting his experiences, "
            "relationships, and development. Here are all the existing tweets:\n\n"
        )
        
        # Convert dictionary to formatted string if needed
        if isinstance(actI_content, dict):
            prompt += json.dumps(actI_content, indent=2)
        else:
            prompt += str(actI_content)
        
        prompt += "\nPlease create a comprehensive digest that:\n"
        prompt += "1. Summarizes Xavier's journey from age 18 to 22, highlighting key life events and character development\n"
        prompt += "2. Details important relationships and social connections he has formed\n"
        prompt += "3. Describes his current situation at age 22 (where the original story left off)\n"
        prompt += "4. Notes any ongoing plot threads or unresolved situations that could be relevant for continuing the story\n"
        prompt += "5. Emphasizes Xavier's strong connection to New York and his plans to return there soon\n"
        prompt += "6. Maintains a tone that allows for natural story continuation\n"
        prompt += "\nImportant Context for Continuation:\n"
        prompt += "- Xavier has a deep connection to New York from his earlier years\n"
        prompt += "- He is actively planning to return to New York to pursue his next chapter\n"
        prompt += "- His future narrative will primarily take place in New York\n"
        prompt += "- The city represents both his past experiences and future opportunities\n"
        
        return prompt

    def generate_digest(self, prompt):
        """Generate a digest using xAI API."""
        try:
            message = self.client.messages.create(
                model="grok-beta",
                max_tokens=1024,  # Adjust based on your needs
                system="You are an AI assistant helping to create a story digest. Your goal is to summarize the key events and maintain narrative continuity.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
            return message.content
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
        """Create a prompt that uses existing digest as context and plans future developments"""
        prompt = (
            "You are maintaining an ongoing digest of Xavier's story. Your role is both to summarize "
            "past events and to outline potential near-future story developments.\n\n"
            
            "CURRENT STORY DIGEST:\n"
            f"{existing_digest.get('content', 'Story begins with Xavier at age 22 in 2025.')}\n\n"
            
            "RECENT UPDATES:\n"
            "New Tweets:\n"
            f"{json.dumps(new_tweets, indent=2)}\n\n"
            
            "Related Comments:\n"
            f"{json.dumps(new_comments, indent=2)}\n\n"
            
            "Please create a comprehensive digest with two sections:\n\n"
            
            "SECTION 1 - STORY SO FAR:\n"
            "1. Summarize the existing narrative and recent developments\n"
            "2. Track ongoing relationships and character growth\n"
            "3. Note significant life events and decisions\n"
            "4. Highlight emerging themes and patterns\n\n"
            
            "SECTION 2 - STORY DIRECTION:\n"
            "1. Outline potential story arcs for the next 3-6 months\n"
            "2. Suggest natural developments in:\n"
            "   - Career progression\n"
            "   - Relationship dynamics\n"
            "   - Personal growth opportunities\n"
            "   - New York life experiences\n"
            "3. Identify potential challenges or conflicts\n"
            "4. Note seasonal or contextual opportunities (holidays, events, etc.)\n\n"
            
            "Keep the story direction subtle and open-ended, providing guidance while allowing "
            "for natural tweet generation. Focus on creating situations and opportunities "
            "rather than prescribing specific outcomes."
        )
        return prompt

    def generate_digest(self, prompt):
        """Generate a digest using xAI API."""
        try:
            message = self.client.messages.create(
                model="grok-beta",
                max_tokens=2048,  # Increased for comprehensive digest
                system="You are a story curator maintaining a comprehensive narrative digest. "
                       "Create a cohesive summary that captures the entire story while "
                       "maintaining proper continuity and character development.",
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

def main():
    generator = DigestGenerator()
    digest = generator.process_digest()
    print(digest)

if __name__ == "__main__":
    main()
