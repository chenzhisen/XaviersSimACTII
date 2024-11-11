import json
from datetime import datetime
from storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
import traceback

class DigestGenerator:
    # Class-level system prompt
    SYSTEM_PROMPT = (
        "Xavier is an AI life simulation exploring the journey from 18 to 72 in 108 real world days, with $XVI, a crypto currency on Solana mysteriously linked to his life.\n"
        "You are:\n"
        "1. Using recent tweets to update the historical summary - ONLY include events that have ALREADY HAPPENED in tweets\n"
        "2. Using tech context and history to project future developments - ONLY include events that have NOT YET HAPPENED\n"
        "\nFormat your response in this structure:\n"
        "\nProfessional:\n"
        "Historical Summary:\n"
        "- [ONLY summarize events that have already occurred in tweets]\n"
        "Projected Developments (Next 3-6 Months):\n"
        "- [ONLY project new developments that haven't happened yet]\n"
        "\nPersonal:\n"
        "[Same structure as above]\n"
        "\nFamily:\n"
        "[Same structure as above]\n"
        "\nSocial:\n"
        "[Same structure as above]\n"
        "\nReflections:\n"
        "[Same structure as above]\n\n"
        "\n$XVI:\n"
        "[Same structure as above]\n\n"
        "Format rules:\n"
        "1. Each category MUST have both Historical Summary and Projected Developments sections\n"
        "2. Historical Summary MUST ONLY include events from tweets\n"
        "3. Projected Developments MUST ONLY include future events (next 3-6 months)\n"
        "4. Professional track MUST reference specific mature technologies\n"
        "5. Reflections track MUST include thoughts about maturing technologies\n"
        "6. Keep all projections realistic and actionable\n"
        "7. Connect developments to Xavier's demonstrated interests and personality\n"
    )

    def __init__(self, simulation_time=None, simulation_age=None, tweet_count=None):
        self.github_ops = GithubOperations()
        self.simulation_time = simulation_time
        self.simulation_age = simulation_age
        self.tweet_count = tweet_count
        
        # Initialize Anthropic client
        xai_config = Config.get_ai_config(AIProvider.XAI)
        self.client = Anthropic(
            api_key=xai_config.api_key,
            base_url=xai_config.base_url
        )
        
        # Initialize empty life tracks
        self.life_tracks = self._initialize_empty_tracks()

    def _get_tech_data(self):
        """Get and format technology data from tech_evolution.json"""
        try:
            tech_evolution, _ = self.github_ops.get_file_content('tech_evolution.json')
            if not tech_evolution:
                print("No tech evolution data found")
                return [], []
            
            if isinstance(tech_evolution, str):
                tech_evolution = json.loads(tech_evolution)
            
            if not isinstance(tech_evolution, dict):
                print(f"Invalid tech evolution data type: {type(tech_evolution)}")
                return [], []
                
            tech_trees = tech_evolution.get('tech_trees', {})
            if not tech_trees:
                print("No tech trees found in evolution data")
                return [], []
                
            # Parse simulation time
            simulation_date = datetime.strptime(self.simulation_time, '%Y-%m-%d')
            simulation_year = simulation_date.year
            simulation_month = simulation_date.month
            
            # Calculate current and next epochs
            current_epoch = simulation_year - (simulation_year % 5)
            next_epoch = current_epoch + 5
            
            # If within 6 months of next epoch, use that instead
            months_to_next_epoch = ((next_epoch - simulation_year) * 12) - simulation_month
            target_epoch = next_epoch if months_to_next_epoch <= 6 else current_epoch
            
            print(f"Target epoch: {target_epoch}")  # Debug
            tech_data = tech_trees.get(str(target_epoch), {})
            
            if not tech_data:
                print(f"No tech data found for epoch {target_epoch}")
                return [], []
                
            # Collect mature and soon-to-mature tech
            mature_tech = []
            for tech in tech_data.get('mainstream_technologies', []):
                mature_tech.append({
                    'name': tech.get('name', ''),
                    'description': tech.get('description', ''),
                    'status': tech.get('adoption_status', '')
                })
            
            maturing_soon = []
            for tech in tech_data.get('emerging_technologies', []):
                if int(tech.get('estimated_year', 9999)) <= simulation_year + 1:
                    maturing_soon.append({
                        'name': tech.get('name', ''),
                        'description': tech.get('description', ''),
                        'estimated_year': tech.get('estimated_year', ''),
                        'probability': tech.get('probability', '')
                    })
            
            return mature_tech, maturing_soon
            
        except Exception as e:
            print(f"Error getting tech data: {e}")
            print("Full error details:")
            traceback.print_exc()
            return [], []

    def get_latest_digest(self):
        """Get the most recent digest with metadata"""
        try:
            content, _ = self.github_ops.get_file_content('digest_history.json')
            if content and len(content) > 0:
                return content[-1]  # Return the last digest with its metadata
            return None
        except Exception as e:
            print(f"Error getting latest digest: {e}")
            return None

    def _build_tech_section(self, mature_tech, maturing_soon):
        """Build the technology section of the prompt"""
        tech_section = "AVAILABLE TECHNOLOGIES:\nCurrently Mature Technologies (must be used in Professional track):\n"
        
        for tech in mature_tech:
            tech_section += f"- {tech['name']}: {tech['description']} (Status: {tech['status']})\n"
        
        tech_section += "\nTechnologies Maturing Soon (must be used in Reflections track):\n"
        for tech in maturing_soon:
            tech_section += (
                f"- {tech['name']}: {tech['description']} "
                f"(Est. Year: {tech['estimated_year']}, Probability: {tech['probability']})\n"
            )
        return tech_section

    def _build_current_tracks_section(self):
        """Build the section describing current life tracks"""
        sections = []
        if not isinstance(self.life_tracks, dict):
            return ""
            
        for track_name, data in self.life_tracks.items():
            # Skip metadata fields
            if track_name in ['timestamp', 'metadata']:
                continue
                
            # Verify data is a dictionary
            if not isinstance(data, dict):
                continue
                
            # Check if track has any content using get() for safety
            historical = data.get('historical_summary', [])
            projected = data.get('projected', [])
            
            if not (historical or projected):
                continue
                
            section = f"\n{track_name}:\n"
            if historical:
                section += "Historical:\n- " + "\n- ".join(historical) + "\n"
            sections.append(section)
            
        return "\nCurrent Life Tracks:" + "".join(sections) if sections else ""

    def _build_prompt(self, mature_tech, maturing_soon, recent_tweets=None, recent_comments=None):
        """Build the prompt for AI with all necessary context"""
        life_phase = self._get_life_phase(self.simulation_age)
        
        prompt = (
            f"Based on the provided information, create Xavier's life digest at age {self.simulation_age}. "
            "For each category:\n"
            "1. Summarize past events and developments from the tweets\n"
            "2. Project specific developments for the next 3-6 months (must be realistic and actionable)\n\n"
            f"CURRENT LIFE PHASE:\n{life_phase}\n\n"
            "TIMEFRAME RULES:\n"
            "1. Historical Summary: Past historical summary and recent tweets\n"
            "2. Projected Developments: ONLY events within next 3-6 months\n"
            "3. All projections must be specific and realistic\n\n"
        )
        
        prompt += self._build_tech_section(mature_tech, maturing_soon)
        
        prompt += (
            "\nTECHNOLOGY INTEGRATION RULES:\n"
            "1. Professional track MUST reference mature technologies that directly relate to trading, blockchain, or AI\n"
            "2. Reflections track MUST explore emerging technologies that naturally extend from current interests\n"
            "3. Other tracks MAY reference technologies ONLY if they have clear, logical connections to activities\n"
            "4. Each technology reference must demonstrate depth in core interests rather than superficial connections\n\n"
        )

        prompt += "Combine the following Historical Summary with Recent Tweets and Comments to create a new historical summary and Project specific new developments for the next 3-6 months:\n"
        prompt += self._build_current_tracks_section()
        
        if recent_tweets:
            prompt += "\nRECENT TWEETS TO ANALYZE (from newest to oldest):\n"
            if isinstance(recent_tweets, list):
                for tweet in reversed(recent_tweets):
                    if isinstance(tweet, dict):
                        date = tweet.get('simulated_date', '')
                        content = tweet.get('content', '').get('content', '')
                        prompt += f"[{date}] {content}\n"
                    else:
                        prompt += f"- {tweet}\n"
            else:
                prompt += f"- {recent_tweets}\n"

        if recent_comments:
            prompt += "\nRECENT COMMENTS:\n" + "\n".join(f"- {comment}" for comment in recent_comments) + "\n"
        
        return prompt

    def _parse_summaries_into_tracks(self, response_text):
        """Parse Claude's response into structured life tracks"""
        life_tracks = {
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "simulation_time": self.simulation_time,
                "simulation_age": self.simulation_age,
                "tweet_count": self.tweet_count
            },
            "digest": {
                "Professional": {"historical_summary": [], "projected": []},
                "Personal": {"historical_summary": [], "projected": []},
                "Family": {"historical_summary": [], "projected": []},
                "Social": {"historical_summary": [], "projected": []},
                "Reflections": {"historical_summary": [], "projected": []},
                "$XVI": {"historical_summary": [], "projected": []}
            }
        }
        
        print("\nStarting parsing process...")
        
        current_track = None
        current_section = None
        
        # Split into lines and process each line
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Track detection (multiple formats)
            if '**Professional:**' in line or 'Professional:' in line:
                current_track = 'Professional'
                print(f"\nFound track: {current_track}")
            elif '**Personal:**' in line or 'Personal:' in line:
                current_track = 'Personal'
                print(f"\nFound track: {current_track}")
            elif '**Family:**' in line or 'Family:' in line:
                current_track = 'Family'
                print(f"\nFound track: {current_track}")
            elif '**Social:**' in line or 'Social:' in line:
                current_track = 'Social'
                print(f"\nFound track: {current_track}")
            elif '**Reflections:**' in line or 'Reflections:' in line:
                current_track = 'Reflections'
                print(f"\nFound track: {current_track}")
            elif '**$XVI:**' in line or '$XVI:' in line:
                current_track = '$XVI'
                print(f"\nFound track: {current_track}")
            
            # Section detection (multiple formats)
            elif '*Historical Summary*' in line or 'Historical Summary:' in line:
                current_section = "historical_summary"
                print(f"Switched to historical_summary in {current_track}")
            elif '*Projected Developments*' in line or 'Projected Developments' in line:
                current_section = "projected"
                print(f"Switched to projected in {current_track}")
            
            # Content processing (bullet points)
            elif line.startswith('- ') and current_track and current_section:
                content = line[2:].strip()  # Remove bullet
                content = content.replace('**', '').replace('*', '').strip()  # Remove all markdown
                
                if content:
                    print(f"Adding to {current_track}/{current_section}: {content[:50]}...")
                    life_tracks['digest'][current_track][current_section].append(content)
            
            # Handle content continuation
            elif current_track and current_section and line and not any(marker in line for marker in ['**', '*Historical', '*Projected', '---']):
                if life_tracks['digest'][current_track][current_section]:
                    last_item = life_tracks['digest'][current_track][current_section][-1]
                    content = line.replace('**', '').replace('*', '').strip()
                    life_tracks['digest'][current_track][current_section][-1] = f"{last_item} {content}"
                    print(f"Appended continuation to {current_track}/{current_section}")
        
        # Print final counts
        print("\nFinal content counts:")
        for track in life_tracks['digest']:
            hist_count = len(life_tracks['digest'][track]['historical_summary'])
            proj_count = len(life_tracks['digest'][track]['projected'])
            print(f"{track}: {hist_count} historical, {proj_count} projected")
        
        return life_tracks

    def _initialize_empty_tracks(self):
        """Initialize empty life tracks structure"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "simulation_time": self.simulation_time,
                "simulation_age": self.simulation_age,
                "tweet_count": self.tweet_count
            },
            "digest": {
                "Professional": {"historical_summary": [], "projected": []},
                "Personal": {"historical_summary": [], "projected": []},
                "Family": {"historical_summary": [], "projected": []},
                "Social": {"historical_summary": [], "projected": []},
                "Reflections": {"historical_summary": [], "projected": []},
                "$XVI": {"historical_summary": [], "projected": []}
            }
        }

    def update_projections(self, tech_context):
        """Update projected storylines based on tech context"""
        try:
            # Update Professional track based on mainstream tech
            mainstream_tech = tech_context.get('mainstream_technologies', [])
            self.life_tracks['digest']['Professional']['projected'] = [
                f"Working with {tech['name']}: {tech['description']} (Status: {tech['status']})"
                for tech in mainstream_tech
            ]

            # Update Reflections based on emerging tech
            emerging_tech = tech_context.get('emerging_technologies', [])
            self.life_tracks['digest']['Reflections']['projected'] = [
                f"Considering implications of {tech['name']}: {tech['description']} "
                f"(Est. Year: {tech['estimated_year']}, Probability: {tech['probability']})"
                for tech in emerging_tech
                if float(tech.get('probability', 0)) > 0.7
            ]
            
        except Exception as e:
            print(f"Error updating projections: {e}")
            traceback.print_exc()

    def _print_life_tracks(self, life_tracks):
        """Print life tracks in a nicely formatted way"""
        print("\n=== XAVIER'S LIFE DIGEST ===\n")
        
        for area, data in life_tracks.items():
            print(f"\n=== {area.upper()} ===\n")
            
            # Print Historical Summary
            print("Historical Summary:")
            if data["history"]:
                for item in data["history"]:
                    print(f" {item['summary']}")
            else:
                print("No historical developments recorded")
            
            # Print Upcoming Developments
            print("\nUpcoming Developments:")
            if data["projected"]:
                for item in data["projected"]:
                    print(f"• {item['event']}")
            else:
                print("No upcoming developments projected")
            
            print("-" * 50)  # Separator line

    def save_digest_to_history(self):
        """Save current digest to digest_history.json"""
        try:
            # Try to load existing history
            content, sha = self.github_ops.get_file_content('digest_history.json')
            history = content if content is not None else []

            # Create new digest entry with metadata
            new_digest = {
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "simulation_time": self.simulation_time,
                    "simulation_age": self.simulation_age,
                    "tweet_count": self.tweet_count
                },
                "digest": {
                    area: {
                        "historical_summary": data.get("historical_summary", []),
                        "projected": data.get("projected", [])
                    }
                    for area, data in self.life_tracks["digest"].items()
                }
            }
            
            # Append new digest
            history.append(new_digest)
            
            # Save updated history
            self.github_ops.update_file(
                'digest_history.json',
                json.dumps(history, indent=2),
                f"Update digest history at simulation time {self.simulation_time}",
                sha  # Pass None if file doesn't exist yet
            )
            
            print(f"\nSuccessfully saved digest to history at simulation time {self.simulation_time}")
            
        except Exception as e:
            print(f"Error saving digest to history: {e}")
            traceback.print_exc()

    def get_digest(self):
        """Get complete digest for all areas and save to history"""
        try:
            # Create complete digest structure
            complete_digest = {
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "simulation_time": self.simulation_time,
                    "simulation_age": self.simulation_age,
                    "tweet_count": self.tweet_count
                },
                "digest": self.life_tracks["digest"]
            }
            
            # Save to history
            self.save_digest_to_history()
            
            return complete_digest

        except Exception as e:
            print(f"Error getting digest: {e}")
            traceback.print_exc()
            return None

    def _get_life_phase(self, age):
        """Get life phase description based on age"""
        if age < 25:
            return (
                "Early Career & Education (18-25)\n"
                "- Professional: Focus on practical tech skills and career building in blockchain and Web3\n"
                "- Personal: Dating and exploring city life\n"
                "- Family: Regular family conversations, sharing tech stories\n"
                "- Social: Building first professional network\n"
                "- Reflections: Curious about technology's immediate potential, with a practical outlook\n"
                f"- $XVI: {'Becoming more aware' if age < 25 else 'governance structure, first major partnerships'}\n"
            )
        elif age < 30:
            return (
                "Growth & Foundation Building (25-30)\n"
                "- Professional: Developing expertise and tackling innovative projects\n"
                "- Personal: Deeper relationships, potential relocation\n"
                "- Family: Staying connected through evolving tech\n"
                "- Social: Expanding network across tech hubs\n"
                "- Reflections: Begins exploring tech's social impact, still primarily focused on practical outcomes\n"
                "- $XVI: Foundation Concept Development\n"
            )
        elif age < 35:
            return (
                "Stability & Partnership (30-35)\n"
                "- Professional: Growing leadership in tech\n"
                "- Personal: Partnership/marriage\n"
                "- Family: Blending traditions with modern life\n"
                "- Social: Building lasting communities\n"
                "- Reflections: Exploring tech's social impact, while focused on practical outcomes\n"
                "- $XVI: Foundation Formation\n"
            )
        elif age < 45:
            return (
                "Family & Leadership (35-45)\n"
                "- Professional: Pioneering while raising family\n"
                "- Personal: Early parenthood journey\n"
                "- Family: Creating tech-aware household\n"
                "- Social: Building family-friendly networks\n"
                "- Reflections: Early philosophical musings about tech’s future impact, blended with family and legacy\n"
                "- $XVI: Foundation Establishment & Growth\n"
            )
        elif age < 60:
            return (
                "Legacy & Mentorship (45-60)\n"
                "- Professional: Shaping industry future\n"
                "- Personal: Supporting children's growth\n"
                "- Family: Multi-generational connections\n"
                "- Social: Mentoring next generation\n"
                "- Reflections: Increasingly philosophical, considering ethical implications of tech on society\n"
                "- $XVI: Foundation Scaling Impact & Global Expansion\n"
            )
        else:
            return (
                "Wisdom & Succession (60+)\n"
                "- Professional: Advisory and guidance\n"
                "- Personal: Grandparent phase\n"
                "- Family: Bridging generations\n"
                "- Social: Elder community voice\n"
                "- Reflections: Deep philosophical insights on technology, humanity, and legacy\n"
                "- $XVI: Foundation Legacy Building & Succession & Future\n"
            )

    def generate_digest(self, recent_tweets=None, recent_comments=None, simulation_time=None, simulation_age=None, tweet_count=None, latest_digest=None):
        """Generate digest based on recent history and new developments"""
        try:
            # Update metadata
            if simulation_time is not None:
                self.simulation_time = simulation_time
            if simulation_age is not None:
                self.simulation_age = simulation_age
            if tweet_count is not None:
                self.tweet_count = tweet_count

            # Initialize life tracks from latest digest or create new
            if latest_digest and isinstance(latest_digest, dict):
                if 'digest' in latest_digest:
                    self.life_tracks = latest_digest['digest']
                else:
                    self.life_tracks = self._initialize_empty_tracks()
            else:
                self.life_tracks = self._initialize_empty_tracks()

            # Get tech data and build prompt
            mature_tech, maturing_soon = self._get_tech_data()
            prompt = self._build_prompt(mature_tech, maturing_soon, recent_tweets, recent_comments)
            
            print("self.SYSTEM_PROMPT", self.SYSTEM_PROMPT)
            print(f"DEBUG: Prompt built: {prompt}")
            # Get AI response
            response = self.client.messages.create(
                model="grok-beta",
                max_tokens=2048,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            print(f"DEBUG: AI response received: {response.content[0].text}")
            # Parse response and update life tracks
            updated_tracks = self._parse_summaries_into_tracks(response.content[0].text)
            self.life_tracks = updated_tracks
            print("DEBUG: Updated life tracks", self.life_tracks)
            return self.get_digest()

        except Exception as e:
            print(f"Error generating digest: {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            return None

def main():
    """Test function to print digest summaries"""
    try:
        # For testing, we'll pass in some sample values
        simulation_time = 18.5
        simulation_age = 25
        tweet_count = 42
        
        # Initialize digest generator with metadata
        digest_gen = DigestGenerator(simulation_time, simulation_age, tweet_count)
        
        # Generate first digest using tweets from XaviersSim.json
        print("\nGenerating digest from XaviersSim.json...")
        digest_gen.generate_digest()
        
        # Could also test subsequent digest generation with new tweets
        # print("\nGenerating next digest...")
        # digest_gen.generate_digest(
        #     recent_tweets=["Some new tweet"],
        #     recent_comments=["Some new comment"]
        # )

    except Exception as e:
        print(f"Error generating digest: {type(e).__name__} - {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()