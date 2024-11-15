import json
from datetime import datetime
from storage.github_operations import GithubOperations
from utils.config import Config, AIProvider
from anthropic import Anthropic
import traceback
import os
import time

class DigestGenerator:
        
    def __init__(self, github_ops, client, model, simulation_time=None, simulation_age=None, tweet_count=0):
        """Initialize the digest generator"""
        self.github_ops = github_ops
        self.client = client
        self.model = model
        self.simulation_time = simulation_time or datetime.now().strftime('%Y-%m-%d')
        self.simulation_age = float(simulation_age) if simulation_age is not None else 22.0  # Default age
        self.tweet_count = tweet_count
        print(f"DigestGenerator initialized with age: {self.simulation_age}")
        
        # Initialize empty life tracks
        self.life_tracks = self._initialize_empty_tracks()

    def _get_tech_data(self):
        """Get and format technology data from tech_evolution.json"""
        try:
            tech_evolution, _ = self.github_ops.get_file_content('tech_evolution.json')
            if not tech_evolution:
                print("No tech evolution data found")
                return [], [], []

            if isinstance(tech_evolution, str):
                tech_evolution = json.loads(tech_evolution)
            
            tech_trees = tech_evolution.get('tech_trees', {})
            if not tech_trees:
                print("No tech trees found in evolution data")
                return [], [], []

            # Parse simulation time
            simulation_date = datetime.strptime(self.simulation_time, '%Y-%m-%d')
            simulation_year = simulation_date.year
            simulation_month = simulation_date.month

            # Determine target epoch
            current_epoch = simulation_year - (simulation_year % 5)
            next_epoch = current_epoch + 5
            months_to_next_epoch = ((next_epoch - simulation_year) * 12) - simulation_month
            target_epoch = next_epoch if months_to_next_epoch <= 6 else current_epoch

            print(f"Target epoch: {target_epoch}")  # Debug
            tech_data = tech_trees.get(str(target_epoch), {})

            if not tech_data:
                print(f"No tech data found for epoch {target_epoch}")
                return [], [], []

            # Collect mature tech, soon-to-mature tech, and societal shifts
            mature_tech = [
                {'name': tech.get('name', ''), 'description': tech.get('description', ''), 'status': tech.get('adoption_status', '')}
                for tech in tech_data.get('mainstream_technologies', [])
            ]
            
            maturing_soon = [
                {'name': tech.get('name', ''), 'description': tech.get('description', ''),
                'estimated_year': tech.get('estimated_year', ''), 'probability': tech.get('probability', '')}
                for tech in tech_data.get('emerging_technologies', [])
                if int(tech.get('estimated_year', 9999)) <= simulation_year + 1
            ]
            
            # Collect epoch themes with societal and global trends
            societal_shifts = [
                {'theme': theme.get('theme', ''), 'description': theme.get('description', ''),
                'societal_impact': theme.get('societal_impact', ''), 'global_trends': theme.get('global_trends', '')}
                for theme in tech_data.get('epoch_themes', [])
            ]

            return mature_tech, maturing_soon, societal_shifts

        except Exception as e:
            print(f"Error getting tech data: {e}")
            traceback.print_exc()
            return [], [], []
            
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
                self.life_tracks = content[-1]
                return content[-1]  # Return the last digest with its metadata
            return None
        except Exception as e:
            print(f"Error getting latest digest: {e}")
            return None

    def _build_tech_section(self, mature_tech, emerging_tech):
        """Builds the Technology Influences section of the prompt."""
        tech_section = "AVAILABLE TECHNOLOGIES:\nCurrently Mature Technologies (to be used in Professional track):\n"
        
        # Adding mature technologies
        for tech in mature_tech:
            tech_section += f"- {tech['name']}: {tech['description']} (Status: {tech['status']})\n"
        
        # Determine emerging technologies that are maturing soon
        tech_section += "\nTechnologies Maturing Soon (to be used in Reflections track):\n"
        for tech in emerging_tech:
            if int(tech.get('estimated_year', 9999)) <= self.simulation_year + 1:  # Within the next year
                tech_section += (
                    f"- {tech['name']}: {tech['description']} "
                    f"(Emergence Year: {tech['estimated_year']}, Probability: {tech['probability']})\n"
                )

        # Outline for Technology Influences
        tech_section += (
            "\nTECHNOLOGY INFLUENCES:\n"
            "Technology-driven plot points and societal shifts include:\n"
            "- Upcoming tech trends impacting Xavier's career and personal life\n"
            "- Major shifts in society due to new tech, like neural interfaces or space exploration\n"
        )
        
        return tech_section
        
    def _build_current_tracks_section(self):
        """Build the section describing current life tracks"""
        sections = []
        if not isinstance(self.life_tracks, dict):
            return ""
        
        for track_name, data in self.life_tracks['digest'].items():
            # Skip metadata fields
            if track_name in ['timestamp', 'metadata']:
                continue
            
            # Verify data is a dictionary
            if not isinstance(data, dict):
                continue
            
            # Handle Plot Points separately
            if track_name == "Plot Points":
                tech_plot_points = data.get("tech_driven", [])
                char_plot_points = data.get("character_driven", [])
                
                section = f"\n{track_name}:\n"

                # Tech-driven plot points
                if tech_plot_points:
                    section += "Tech-Driven Plot Points:\n- " + "\n- ".join(tech_plot_points) + "\n"

                # Character-driven plot points
                if char_plot_points:
                    section += "Character-Driven Plot Points:\n- " + "\n- ".join(char_plot_points) + "\n"

                sections.append(section)
                continue  # Skip to the next track after handling Plot Points
            
            # Handle Technology Influences separately
            if track_name == "Technology Influences":
                upcoming_trends = data.get("upcoming_trends", [])
                societal_shifts = data.get("societal_shifts", [])
                tech_plot_points = data.get("tech_driven_plot_points", [])
                
                section = f"\n{track_name}:\n"

                # Upcoming Trends
                if upcoming_trends:
                    section += "Upcoming Trends:\n- " + "\n- ".join(upcoming_trends) + "\n"

                # Societal Shifts
                if societal_shifts:
                    section += "Societal Shifts:\n- " + "\n- ".join(societal_shifts) + "\n"

                # Tech-Driven Plot Points
                if tech_plot_points:
                    section += "Tech-Driven Plot Points:\n- " + "\n- ".join(tech_plot_points) + "\n"

                sections.append(section)
                continue  # Skip to the next track after handling Technology Influences
            
            # General handling for other sections
            section = f"\n{track_name}:\n"
            historical = data.get('historical_summary', [])
            projected_short = data.get('projected_short', [])
            projected_long = data.get('projected_long', [])
            tech_plot_points = data.get("plot_points", {}).get("tech_driven", [])
            char_plot_points = data.get("plot_points", {}).get("character_driven", [])

            # Historical summary
            if historical:
                section += "Historical:\n- " + "\n- ".join(historical) + "\n"

            # Short-term projections
            if projected_short:
                section += "Short-Term Goals:\n- " + "\n- ".join(projected_short) + "\n"
            
            # Long-term projections
            if projected_long:
                section += "Long-Term Goals:\n- " + "\n- ".join(projected_long) + "\n"

            # Tech-driven plot points
            if tech_plot_points:
                section += "Tech-Driven Plot Points:\n- " + "\n- ".join(tech_plot_points) + "\n"

            # Character-driven plot points
            if char_plot_points:
                section += "Character-Driven Plot Points:\n- " + "\n- ".join(char_plot_points) + "\n"

            sections.append(section)

        return "\nCurrent Life Tracks:" + "".join(sections) if sections else ""

    def _parse_summaries_into_tracks(self, response_text):
        """Parse AI's response into structured life tracks with historical summaries and projections."""
        
        life_tracks = self._initialize_empty_tracks()
        print("Initialized empty life tracks.")  # Debug

        try:
            # Clean the response text
            cleaned_response = response_text.strip()
            
            # Check if the response starts with a markdown code block
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove the initial ```json
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove the trailing ```
            
            # Parse the JSON response
            response_data = json.loads(cleaned_response)
            print("Successfully parsed JSON response.")  # Debug
            
            for track_name, track_data in response_data.items():
                print(f"Processing track: {track_name}")  # Debug
                if track_name not in life_tracks['digest']:
                    life_tracks['digest'][track_name] = {}  # Initialize if not present
                    print(f"Initialized track: {track_name}")  # Debug
                
                for section, items in track_data.items():
                    print(f"Processing section: {section} with {len(items)} items")  # Debug
                    if section not in life_tracks['digest'][track_name]:
                        life_tracks['digest'][track_name][section] = {} if isinstance(items, dict) else []  # Initialize if not present
                        print(f"Initialized section: {section}")  # Debug
                    
                    if isinstance(items, list):
                        life_tracks['digest'][track_name][section].extend(items)
                        print(f"Added {len(items)} items to section: {section}")  # Debug
                    elif isinstance(items, dict):
                        for sub_section, sub_items in items.items():
                            if sub_section not in life_tracks['digest'][track_name][section]:
                                life_tracks['digest'][track_name][section][sub_section] = []
                            life_tracks['digest'][track_name][section][sub_section].extend(sub_items)
                            print(f"Added {len(sub_items)} items to sub-section: {sub_section}")  # Debug
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            traceback.print_exc()
        
        return life_tracks

    def _initialize_empty_tracks(self):
        """Initialize and return the empty structure for life tracks."""
        return {
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "simulation_time": self.simulation_time,
                "simulation_age": self.simulation_age,
                "tweet_count": self.tweet_count
            },
            "digest": {
                "Professional": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Personal": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Family": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Social": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Reflections": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "$XVI": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Major Events": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Financial Trajectory": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Health & Well-being": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Mentorship & Legacy": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Character Development": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "New Relationships and Conflicts": {"historical_summary": [], "projected_short": [], "projected_long": [], "plot_points": {"tech_driven": [], "character_driven": []}},
                "Plot Points": {"tech_driven": [], "character_driven": []},
                "Technology Influences": {"upcoming_trends": [], "societal_shifts": [], "tech_driven_plot_points": []}
            }
        }

    def _print_life_tracks(self, life_tracks):
        """Print life tracks in a nicely formatted way"""
        print("\n=== XAVIER'S LIFE DIGEST ===\n")
        
        for area, data in life_tracks['digest'].items():
            print(f"\n=== {area.upper()} ===\n")
            
            # Print Historical Summary
            print("Historical Summary:")
            if data.get("historical_summary"):
                for item in data["historical_summary"]:
                    print(f" - {item}")
            else:
                print("No historical developments recorded")
            
            # Print Short-Term Projections
            print("\nShort-Term Projections (3-6 months):")
            if data.get("projected_short"):
                for item in data["projected_short"]:
                    print(f"• {item}")
            else:
                print("No short-term developments projected")
            
            # Print Long-Term Projections
            print("\nLong-Term Projections (1-5 years):")
            if data.get("projected_long"):
                for item in data["projected_long"]:
                    print(f"• {item}")
            else:
                print("No long-term developments projected")
            
            # Print Plot Points - Tech-Driven and Character-Driven
            plot_points = data.get("plot_points", {})
            
            print("\nTech-Driven Plot Points:")
            if plot_points.get("tech_driven"):
                for item in plot_points["tech_driven"]:
                    print(f"• {item}")
            else:
                print("No tech-driven plot points recorded")
            
            print("\nCharacter-Driven Plot Points:")
            if plot_points.get("character_driven"):
                for item in plot_points["character_driven"]:
                    print(f"• {item}")
            else:
                print("No character-driven plot points recorded")
            
            print("-" * 50)  # Separator line

    def save_digest_to_history(self, digest):
        """Save the current digest to history on GitHub"""
        try:
            if digest is None:
                print("Digest is None, not saving to history.")
                return
            
            # Load existing history from GitHub
            history, sha = self.github_ops.get_file_content('digest_history.json')

            if history is None:
                history = []

            # Add new digest with timestamp
            history.append(digest)

            # Convert history to JSON string
            history_json = json.dumps(history, indent=2)
            # Commit the updated history to GitHub
            self.github_ops.update_file(
                file_path='digest_history.json',
                content=history_json,
                commit_message=f"Update digest history at {datetime.now().isoformat()}",
                sha=sha
            )
            
            print(f"Saved digest to history on GitHub (age: {digest.get('metadata', {}).get('simulation_age')})")
            
        except Exception as e:
            print(f"Error saving digest to history on GitHub: {str(e)}")
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
            
            print("Complete Digest:", complete_digest)  # Debugging line
            
            # Save to history
            self.save_digest_to_history(complete_digest)
            
            return complete_digest

        except Exception as e:
            print(f"Error getting digest: {e}")
            traceback.print_exc()
            return None
            

    def _get_life_phase(self, age, has_major_event=False):
        """Get life phase description based on age, with optional flexibility for major life events"""

        if age < 25:
            if has_major_event:
                return (
                    "Early Career & Exploration (18-25) with resilience through recent challenges.\n"
                    "- Professional: Building foundational tech skills in blockchain and Web3, while adapting to challenges.\n"
                    "- Personal: Navigating relationships, independence, and unexpected life shifts.\n"
                    "- Family: Relying on family support and strengthening connections.\n"
                    "- Social: Building a network, often leaning on friendships through changes.\n"
                    "- Reflections: Practical, adaptive outlook due to recent events.\n"
                    "- $XVI: Governance ideas and early partnerships; navigating potential obstacles.\n"
                    "- Major Events: College life, early career challenges, initial exploration in blockchain.\n"
                    "- Financial Trajectory: Learning financial independence, adapting to new priorities.\n"
                    "- Health & Well-being: Establishing routines amidst changes.\n"
                    "- Mentorship & Legacy: Seeking guidance, reflecting on early experiences.\n"
                    "- Character Development: Strengthening resilience, exploring self-identity.\n"
                    "- New Relationships & Conflicts: Building connections, resolving early-life conflicts.\n"
                )
            else:
                return (
                    "Early Career & Exploration (18-25)\n"
                    "- Professional: Focus on foundational tech skills and career building in blockchain and Web3.\n"
                    "- Personal: Formative relationships, dating, and exploring independence in a big city.\n"
                    "- Family: Regular family conversations, sharing tech stories, and maintaining close connections.\n"
                    "- Social: Building a professional network, especially among tech peers.\n"
                    "- Reflections: Exploring technology's immediate potential with a pragmatic outlook.\n"
                    "- $XVI: Initial awareness, considering governance and early partnerships.\n"
                    "- Major Events: Transitioning to college life, first job or internship, initial explorations in blockchain.\n"
                    "- Financial Trajectory: Minimal savings or early investments, possibly learning financial independence.\n"
                    "- Health & Well-being: Adjusting to college life and city living, establishing a health routine.\n"
                    "- Mentorship & Legacy: Receiving mentorship from college professors or early career mentors.\n"
                    "- Character Development: Developing independence, managing responsibilities, and exploring identity.\n"
                    "- New Relationships & Conflicts: Meeting diverse personalities, navigating friendships, and minor conflicts.\n"
                )
        elif age < 30:
            if has_major_event:
                return (
                    "Growth & Foundation Building (25-30) while adapting to significant life changes.\n"
                    "- Professional: Advancing in career, handling larger projects, adapting to new challenges.\n"
                    "- Personal: Strengthening serious relationships, possibly relocating or making big life choices.\n"
                    "- Family: Staying connected with family as a support system.\n"
                    "- Social: Deepening networks; building support through challenges.\n"
                    "- Reflections: Pragmatic look at tech’s impact; balancing values with career growth.\n"
                    "- $XVI: Concept development, possibly facing obstacles or new insights.\n"
                    "- Major Events: Relocation, major relationship shift, or career pivot.\n"
                    "- Financial Trajectory: Managing finances, building assets; possible major expenses.\n"
                    "- Health & Well-being: Emphasis on stability, adapting to increased demands.\n"
                    "- Mentorship & Legacy: Mentoring others, finding meaning in contributions.\n"
                    "- Character Development: Resilience, re-evaluating goals, strengthening relationships.\n"
                    "- New Relationships & Conflicts: Forming alliances, managing conflicts in personal/professional life.\n"
                )
            else:
                return (
                    "Growth & Foundation Building (25-30)\n"
                    "- Professional: Advancing in career, taking on larger projects or first leadership roles.\n"
                    "- Personal: Building serious relationships, possibly relocating for career growth.\n"
                    "- Family: Staying connected through evolving tech, occasionally involving family in projects.\n"
                    "- Social: Expanding network across tech hubs, frequenting industry events, and building deeper connections.\n"
                    "- Reflections: Starting to examine tech’s social impact and ethical questions.\n"
                    "- $XVI: Foundation Concept Development; exploring governance structures and first significant partnerships.\n"
                    "- Major Events: Potential relocation, entering a committed relationship, considering major career changes.\n"
                    "- Financial Trajectory: Higher income, considering substantial investments or crypto holdings.\n"
                    "- Health & Well-being: Increased focus on work-life balance as career responsibilities grow.\n"
                    "- Mentorship & Legacy: Beginning to mentor younger professionals, giving back to the community.\n"
                    "- Character Development: Evolving self-awareness, embracing career goals, and forming long-term connections.\n"
                    "- New Relationships & Conflicts: Forming key alliances and managing emerging conflicts or rivalries.\n"
                )
        elif age < 35:
            if has_major_event:
                return (
                    "Stability & Partnership (30-35) with focus on resilience and adaptation.\n"
                    "- Professional: Leading significant projects or ventures while adapting to recent changes.\n"
                    "- Personal: Deepening personal relationships, potentially facing challenges together.\n"
                    "- Family: Relying on family for support and stability.\n"
                    "- Social: Close-knit community focus, finding support through relationships.\n"
                    "- Reflections: Revisiting values, adapting beliefs in light of recent events.\n"
                    "- $XVI: Expanding ecosystem, adapting governance in challenging conditions.\n"
                    "- Major Events: Family changes, significant career pivot, major achievements.\n"
                    "- Financial Trajectory: Securing finances, preparing for future or unexpected events.\n"
                    "- Health & Well-being: Stress management, long-term health goals.\n"
                    "- Mentorship & Legacy: Focus on resilience; becoming a source of wisdom for others.\n"
                    "- Character Development: Fostering patience, resilience, and empathy.\n"
                    "- New Relationships & Conflicts: Strengthening bonds, resolving higher-stakes conflicts.\n"
                )
            else:
                return (
                    "Stability & Partnership (30-35)\n"
                    "- Professional: Growing leadership in tech, possibly founding a company or leading a significant project.\n"
                    "- Personal: Partnership/marriage, beginning to contemplate long-term family planning.\n"
                    "- Family: Integrating tech into family life; introducing new family members to technology.\n"
                    "- Social: Strong community connections; focused on building lasting friendships and professional relationships.\n"
                    "- Reflections: Considering the ethical and social dimensions of decentralization and AI.\n"
                    "- $XVI: Foundation Formation; expanding the ecosystem, establishing resilient infrastructure.\n"
                    "- Major Events: Potential marriage or major relationship commitment, key career milestones.\n"
                    "- Financial Trajectory: Stable finances with growing investments in tech and real estate.\n"
                    "- Health & Well-being: Health and fitness become priority, establishing long-term habits.\n"
                    "- Mentorship & Legacy: Taking on mentor roles, considering contributions to industry and society.\n"
                    "- Character Development: Embracing leadership, refining values, and strengthening core relationships.\n"
                    "- New Relationships & Conflicts: Dealing with high-stakes relationships, new partnerships, and professional rivalries.\n"
                )
        elif age < 45:
            if has_major_event:
                return (
                    "Family & Leadership (35-45) while navigating major responsibilities and changes.\n"
                    "- Professional: Leading projects with a focus on balancing family and professional responsibilities.\n"
                    "- Personal: Parenthood or deepening family roles, handling recent life changes.\n"
                    "- Family: Building a tech-aware household, emphasizing family unity.\n"
                    "- Social: Strong community focus, managing relationships through life adjustments.\n"
                    "- Reflections: Deep philosophical introspection on legacy and ethics.\n"
                    "- $XVI: Expanding governance structure, adapting to new challenges within the ecosystem.\n"
                    "- Major Events: Parenthood, career peaks, or other transformative events.\n"
                    "- Financial Trajectory: Financial planning for family’s long-term security.\n"
                    "- Health & Well-being: Focus on maintaining resilience, possibly facing health challenges.\n"
                    "- Mentorship & Legacy: Embracing leadership, guiding others through similar life stages.\n"
                    "- Character Development: Adapting with empathy, fostering stability for others.\n"
                    "- New Relationships & Conflicts: Resolving conflicts, supporting allies.\n"
                )
            else:
                return (
                    "Family & Leadership (35-45)\n"
                    "- Professional: Leading pioneering projects, balancing career with family responsibilities.\n"
                    "- Personal: Parenthood or family-building phase, focusing on stability and work-life balance.\n"
                    "- Family: Creating a tech-aware household, balancing tech with traditional values.\n"
                    "- Social: Strong support network centered around family and community involvement.\n"
                    "- Reflections: Deeper philosophical considerations on legacy, ethical responsibilities, and societal impact.\n"
                    "- $XVI: Foundation Growth; expanding community, building sustainable governance structures.\n"
                    "- Major Events: Parenthood, career peaks, major project launches.\n"
                    "- Financial Trajectory: Financial security, planning for family wealth and legacy.\n"
                    "- Health & Well-being: Maintaining health routines; increasing focus on mental well-being.\n"
                    "- Mentorship & Legacy: Influencing industry direction, shaping future talent.\n"
                    "- Character Development: Embracing responsibility, considering legacy, and focusing on family and community.\n"
                    "- New Relationships & Conflicts: New mentors, mentees, and potential high-stakes business conflicts.\n"
                ) 
        elif age < 60:
            if has_major_event:
                return (
                    "Legacy & Mentorship (45-60) while adapting to significant personal or professional transitions.\n"
                    "- Professional: Serving as an industry advisor, handling shifts in responsibilities.\n"
                    "- Personal: Supporting family growth, facing and adapting to new dynamics.\n"
                    "- Family: Multi-generational connections, adjusting to family changes.\n"
                    "- Social: Acting as a mentor, navigating broader relationships.\n"
                    "- Reflections: Exploring tech’s societal impact with a deeper philosophical lens.\n"
                    "- $XVI: Scaling foundation and governance; navigating global partnerships.\n"
                    "- Major Events: Family changes, possible career transition to advisory roles.\n"
                    "- Financial Trajectory: Managing financial legacy, supporting broader family needs.\n"
                    "- Health & Well-being: Focus on maintaining health, adapting to life’s transitions.\n"
                    "- Mentorship & Legacy: Emphasizing mentorship, contemplating enduring contributions.\n"
                    "- Character Development: Fostering wisdom, patience, and broader influence.\n"
                    "- New Relationships & Conflicts: Balancing professional legacies and resolving conflicts peacefully.\n"
                )
            else:
                return (
                    "Legacy & Mentorship (45-60)\n"
                    "- Professional: Advisory role, shaping industry trends and policies.\n"
                    "- Personal: Supporting children’s development, guiding them in career and personal decisions.\n"
                    "- Family: Multi-generational bonds; focusing on family values and legacy.\n"
                    "- Social: Acting as a mentor in professional and personal networks.\n"
                    "- Reflections: Ethical and philosophical insights on technology's impact on future generations.\n"
                    "- $XVI: Global Expansion; scaling impact, increasing partnerships, building cross-border networks.\n"
                    "- Major Events: Career shift towards advisory roles, family achievements.\n"
                    "- Financial Trajectory: Well-established financial legacy, family wealth management.\n"
                    "- Health & Well-being: Emphasis on longevity and quality of life, potential health setbacks.\n"
                    "- Mentorship & Legacy: Focused on guiding the next generation of innovators.\n"
                    "- Character Development: Emphasizing mentorship, reflecting on legacy, and deepening family bonds.\n"
                    "- New Relationships & Conflicts: Building global partnerships, possibly managing large-scale disputes.\n"
                )      
        else:
            if has_major_event:
                return (
                    "Wisdom & Succession (60+) while adapting to key transitions in personal and professional spheres.\n"
                    "- Professional: Transitioning from active roles to advisory; handing down responsibilities.\n"
                    "- Personal: Strengthening family bonds, preparing for succession.\n"
                    "- Family: Becoming a family guide, reinforcing traditions and values.\n"
                    "- Social: Respected elder, guiding others with historical insights.\n"
                    "- Reflections: Focus on long-term impact and existential thoughts.\n"
                    "- $XVI: Succession planning to ensure the Foundation’s longevity.\n"
                    "- Major Events: Family milestones, legacy building, preparing for a full transition.\n"
                    "- Financial Trajectory: Succession planning and managing family legacy.\n"
                    "- Health & Well-being: Emphasis on graceful aging, facing health realities.\n"
                    "- Mentorship & Legacy: Finalizing legacy contributions, preparing for succession.\n"
                    "- Character Development: Acceptance, wisdom, and reflection.\n"
                    "- New Relationships & Conflicts: Guiding younger generations, resolving legacy-related issues.\n"
                )
            else:
                return (
                    "Wisdom & Succession (60+)\n"
                    "- Professional: Advisory and mentorship, guiding younger industry leaders.\n"
                    "- Personal: Grandparent role, strengthening family bonds.\n"
                    "- Family: Acting as the family’s guiding figure, promoting continuity and tradition.\n"
                    "- Social: Respected community elder, contributing historical insights.\n"
                    "- Reflections: Deep, existential thoughts on humanity, technology, and purpose.\n"
                    "- $XVI: Succession Planning; ensuring the Foundation’s future and stability.\n"
                    "- Major Events: Family milestones, public recognition, possibly retirement.\n"
                    "- Financial Trajectory: Managing family wealth and succession planning.\n"
                    "- Health & Well-being: Focus on graceful aging, may face age-related challenges.\n"
                    "- Mentorship & Legacy: Establishing an enduring legacy, passing on knowledge to family and mentees.\n"
                    "- Character Development: Wisdom, patience, and acceptance, focusing on long-term impact.\n"
                    "- New Relationships & Conflicts: Fostering relationships with younger generations, resolving conflicts peacefully.\n"
                )
                
    def generate_digest(self, recent_tweets=None, simulation_time=None, simulation_age=None, tweet_count=None, latest_digest=None):
        """Generate digest based on recent history and new developments"""
        try:
            self.life_tracks = latest_digest
            # Create logs directory
            log_dir = "logs/digests"
            os.makedirs(log_dir, exist_ok=True)
            
            # Create log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = f"{log_dir}/digest_{timestamp}.txt"
            
            return self._generate_digest_with_logging(
                recent_tweets=recent_tweets,
                simulation_age=simulation_age,
                simulation_time=simulation_time,
                log_path=log_path
            )
            
        except Exception as e:
            print(f"Error generating digest: {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            return None

    def generate_first_digest(self, tweets_by_age):
        """Generate first digest by processing pre-grouped age brackets"""
        try:
            # Create logs directory if it doesn't exist
            log_dir = "logs/first_digest"
            os.makedirs(log_dir, exist_ok=True)
            
            # Process each age bracket sequentially
            sorted_brackets = sorted(tweets_by_age.keys(), 
                key=lambda x: float(x.split('-')[0].replace('age ', '')))
            
            for bracket in sorted_brackets:
                try:
                    # Extract age range
                    age_range = bracket.replace('age ', '').split('-')
                    end_age = float(age_range[1])
                    
                    print(f"\nProcessing age bracket {bracket} (end age: {end_age})")
                    
                    # Create log file for this bracket
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    log_path = f"{log_dir}/bracket_{bracket.replace(' ', '_')}_{timestamp}.txt"
                    
                    print(f"Generating digest for age bracket {bracket} (end age: {end_age})")
                    # Generate digest for this bracket
                    bracket_digest = self._generate_digest_with_logging(
                        recent_tweets=tweets_by_age[bracket],
                        simulation_age=end_age,  # Pass the end age of the bracket
                        simulation_time=self.simulation_time,
                        log_path=log_path
                    )
                    
                    if bracket_digest:
                        # Update metadata for this bracket
                        if 'metadata' not in bracket_digest:
                            bracket_digest['metadata'] = {}
                        bracket_digest['metadata'].update({
                            'simulation_age': end_age,
                            'simulation_time': self.simulation_time,
                            'tweet_count': self.tweet_count,
                            'age_bracket': bracket
                        })
                        
                        self.life_tracks = bracket_digest
                        
                        # Log successful processing
                        print(f"Successfully processed bracket {bracket}")
                        
                        # Save intermediate digest
                        self.save_digest_to_history(bracket_digest)
                    else:
                        print(f"Failed to generate digest for bracket {bracket}")
                
                except (ValueError, TypeError) as e:
                    print(f"Error processing bracket {bracket}: {str(e)}")
                    continue

            return self.life_tracks

        except Exception as e:
            print(f"Error in generate_first_digest: {type(e).__name__} - {str(e)}")
            traceback.print_exc()
            return None


    def _generate_digest_with_logging(self, recent_tweets, simulation_age, simulation_time, log_path=None):
        """Generate digest with logging of prompts and responses"""
        max_retries = 3000
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                # Build the prompts
                system_prompt = self._build_system_prompt()
                user_prompt = self._build_prompt(
                    mature_tech=[],  # We'll need to pass these from tech evolution
                    maturing_soon=[],
                    recent_tweets=recent_tweets,
                    recent_comments=None
                )
                
                # Log prompts before API call
                if log_path:
                    with open(log_path, 'w', encoding='utf-8') as f:
                        f.write("=== METADATA ===\n")
                        f.write(f"Simulation Age: {simulation_age}\n")
                        f.write(f"Simulation Time: {simulation_time}\n\n")
                        f.write("=== SYSTEM PROMPT ===\n")
                        f.write(system_prompt)
                        f.write("\n\n=== USER PROMPT ===\n")
                        f.write(user_prompt)
                
                # Get AI response
                print("Sending request to AI client...")  # Debug
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                print("Received response from AI client.")  # Debug
                
                # Log raw response
                raw_response = response.content[0].text if response.content else "No content received"
                print(f"Raw AI Response: {raw_response}")  # Debug
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== RAW AI RESPONSE ===\n")
                        f.write(raw_response)
                
                # Check if response content is empty
                if not raw_response.strip():
                    print("Received empty or invalid response from AI client.")
                    continue  # Retry if the response is empty
                
                # Process response and log parsed data
                print("Parsing AI response...")  # Debug
                summaries = self._parse_summaries_into_tracks(raw_response)
                print("Parsed AI response into life tracks.")  # Debug
                
                # Log parsed summaries
                if log_path and summaries:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== PARSED LIFE TRACKS ===\n")
                        for track_name, track_data in summaries['digest'].items():
                            f.write(f"\n{track_name}:\n")
                            
                            for section, items in track_data.items():
                                f.write(f"  {section}:\n")
                                
                                if isinstance(items, list):
                                    for item in items:
                                        f.write(f"    - {item}\n")
                                elif isinstance(items, dict):
                                    for sub_section, sub_items in items.items():
                                        f.write(f"  {sub_section}:\n")
                                        for item in sub_items:
                                            f.write(f"    - {item}\n")
                            
                            f.write("\n" + "-"*50 + "\n")
                        
                        # Log validation summary
                        f.write("\n=== VALIDATION SUMMARY ===\n")
                        f.write(f"Total tracks: {len(summaries['digest'])}\n")
                        for track_name, track_data in summaries['digest'].items():
                            f.write(f"{track_name}:\n")
                            for section, items in track_data.items():
                                f.write(f"  {section} items: {len(items) if isinstance(items, list) else sum(len(sub_items) for sub_items in items.values())}\n")
                            print(f"Track {track_name}: {', '.join(f'{section} {len(items) if isinstance(items, list) else sum(len(sub_items) for sub_items in items.values())}' for section, items in track_data.items())}")
                
                return summaries

            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== JSON PARSING ERROR ===\n")
                        f.write(f"Error message: {str(e)}\n")
                        f.write("Response content:\n")
                        f.write(raw_response)
                traceback.print_exc()

            except Exception as e:
                print(f"Error generating digest: {type(e).__name__} - {str(e)}")
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n=== ERROR ===\n")
                        f.write(f"Error type: {type(e).__name__}\n")
                        f.write(f"Error message: {str(e)}\n")
                        f.write("\nTraceback:\n")
                        traceback.print_exc(file=f)
                traceback.print_exc()

            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds... (Attempt {attempt + 1} of {max_retries})")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Failing the request.")
                return None

    def _build_system_prompt(self):
        return """
            Xavier is an AI life simulation exploring the journey from age 18 to 72 over 108 real-world days, with $XVI, a cryptocurrency on Solana, mysteriously linked to his life.

            As the AI generating Xavier's life digest, your tasks are to:
            1. Summarize historical events that have ALREADY occurred in tweets and recent comments.
            2. Project future developments that have NOT YET happened.

            STRUCTURE FOR EACH SECTION:

            Professional:
                Historical Summary:
                - Summarize events from tweets and incorporate recent tweets and comments provided, focusing on events and developments that reflect Xavier’s most recent experiences in his professional life.

                Projected Developments (Short-Term Goals):
                - List actionable, immediate goals (3-6 months simulation time), such as pursuing a new project, expanding skills, or specific networking events.

                Projected Developments (Long-Term Goals):
                - Outline broader goals for the next 1-5 years in simulation, such as leading a major project, starting a company, or achieving a career milestone.

            Personal:
                Historical Summary:
                - Capture significant events or relationships from tweets and recent comments, focusing on personal life, friendships, dating, and key social interactions.

                Projected Developments (Short-Term Goals):
                - List goals over the next 3-6 months, such as deepening friendships or planning a social activity.

                Projected Developments (Long-Term Goals):
                - Describe potential arcs over 1-5 years, like building a long-term relationship or achieving significant personal growth.

            Family:
                Historical Summary:
                - Summarize interactions or events related to Xavier’s family, including calls, visits, or shared experiences, integrating any recent updates from tweets or comments.

                Projected Developments (Short-Term Goals):
                - Identify near-future family-related goals, such as arranging visits or sharing career progress.

                Projected Developments (Long-Term Goals):
                - Describe possible developments in family relationships over 1-5 years, including significant family events or deeper bonds.

            Social:
                Historical Summary:
                - Note events or gatherings with friends, community involvement, and networking that have already occurred, including any relevant recent social events from tweets.

                Projected Developments (Short-Term Goals):
                - Set near-term social activities, such as attending events or building his social network.

                Projected Developments (Long-Term Goals):
                - Outline broader social goals, like becoming an influential figure in his community.

            Reflections:
                Historical Summary:
                - Capture past reflections, philosophies, and realizations shared in tweets, with emphasis on recent contemplations.

                Projected Developments (Short-Term Goals):
                - Include short-term reflections on current trends or personal thoughts on recent events.

                Projected Developments (Long-Term Goals):
                - Suggest evolving worldviews, deeper philosophies, and future musings on technology, society, or his personal journey.

            $XVI:
                Historical Summary:
                - List past interactions with or developments around $XVI, as described in tweets, especially recent discoveries or shifts in perspective.

                Projected Developments (Short-Term Goals):
                - Describe immediate goals related to $XVI, such as monitoring price trends, interacting with $XVI governance, or marketing.

                Projected Developments (Long-Term Goals):
                - Outline the broader trajectory of $XVI over the next 1-5 years, including major milestones and community impact.

            Major Events:
                Historical Summary:
                - Summarize life-altering events like relocations, transitions, or key decisions, integrating any recent life changes from tweets.

                Projected Developments (Short-Term Goals):
                - Describe short-term developments for the next 3-6 months, including new transitions or life changes.

                Projected Developments (Long-Term Goals):
                - Forecast significant events in the next 1-5 years, such as pivotal life changes or major achievements.

            Financial Trajectory:
                Historical Summary:
                - Summarize financial decisions, major investments, or economic insights from past tweets, incorporating any recent financial updates.

                Projected Developments (Short-Term Goals):
                - Include short-term financial goals, such as specific investments or savings milestones.

                Projected Developments (Long-Term Goals):
                - Suggest long-term financial ambitions or significant economic growth over 1-5 years.

            Health & Well-being:
                Historical Summary:
                - Summarize past health decisions, activities, or challenges mentioned in tweets, including any recent wellness or stress-related updates.

                Projected Developments (Short-Term Goals):
                - Focus on health goals over the next few months, including physical or mental wellness activities.

                Projected Developments (Long-Term Goals):
                - Describe projected health or lifestyle improvements over the next 1-5 years.

            Mentorship & Legacy:
                Historical Summary:
                - Summarize past activities related to mentorship, teaching, or legacy-building from tweets, with recent updates where applicable.

                Projected Developments (Short-Term Goals):
                - List short-term goals related to guiding others, sharing knowledge, or legacy-related pursuits.

                Projected Developments (Long-Term Goals):
                - Outline potential legacy-related goals over 1-5 years, such as becoming a mentor, creating lasting contributions, or establishing a legacy.

            Character Development:
                Historical Summary:
                - Summarize recent shifts in Xavier’s beliefs, priorities, or personality traits as expressed in tweets, especially recent self-reflections.

                Projected Developments (Short-Term Goals):
                - Suggest immediate ways Xavier’s character might evolve in the next 3-6 months based on recent events, possibly influenced by new tech.

                Projected Developments (Long-Term Goals):
                - Outline Xavier’s broader personal growth trajectory over 1-5 years, including evolving worldviews or emerging life philosophies. Consider if tech advancements lead to shifts in his ethical or personal values.

            New Relationships and Conflicts:
                Historical Summary:
                - Capture recent relationships or conflicts, such as friendships, rivalries, mentorships, or collaborations, especially recent changes.

                Projected Developments (Short-Term Goals):
                - Identify potential new relationships or conflicts over the next 3-6 months that may impact Xavier’s personal or professional life, possibly driven by recent tech trends.

                Projected Developments (Long-Term Goals):
                - Envision significant relationships or recurring conflicts over 1-5 years that shape Xavier’s growth and social landscape, considering how tech trends may alter his social and professional dynamics.

            Plot Points:
                Tech-Driven Plot Points:
                - Highlight potential plot events arising directly from new or emerging technologies, especially those from the Technology Evolution system. Examples include tech upgrades, ethical dilemmas, or societal shifts due to tech advancements.

                Character-Driven Plot Points:
                - Identify key character-related plot events influenced by recent events or major life changes. Examples include major conflicts, new alliances, and shifts in Xavier’s relationships or values.

            Technology Influences:
                Upcoming Trends:
                - Outline anticipated technological trends that may influence Xavier’s life, career, or social dynamics.

                Societal Shifts:
                - Describe major societal shifts influenced by technology, affecting industries, daily life, or cultural norms Xavier may encounter.

                Tech-Driven Plot Points:
                - Describe possible plot events influenced by these technological trends, highlighting potential challenges, ethical dilemmas, or personal implications for Xavier.

            RETURN FORMAT (JSON):
            {
                "Professional": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Personal": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Family": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Social": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Reflections": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "$XVI": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Major Events": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Financial Trajectory": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Health & Well-being": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Mentorship & Legacy": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Character Development": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "New Relationships and Conflicts": {
                    "historical_summary": [],
                    "projected_short": [],
                    "projected_long": [],
                    "plot_points": {
                        "tech_driven": [],
                        "character_driven": []
                    }
                },
                "Plot Points": {
                    "tech_driven": [],
                    "character_driven": []
                },
                "Technology Influences": {
                    "upcoming_trends": [],
                    "societal_shifts": [],
                    "tech_driven_plot_points": []
                }
            }

            Ensure each section is comprehensive, linking past experiences to projected goals, and consistently includes both tech-driven and character-driven plot points where relevant.
        """

    def _build_prompt(self, mature_tech, maturing_soon, recent_tweets=None, recent_comments=None):
        """Build the prompt for AI with all necessary context"""
        life_phase = self._get_life_phase(self.simulation_age)

        prompt = (
            f"Based on the provided information, create Xavier's life digest at age {self.simulation_age}. "
            "For each category:\n"
            "1. Summarize past events and developments from the tweets\n"
            "2. Project specific developments for the next 3-6 months (Short-Term Goals)\n"
            "3. Project broader goals for the next 1-5 years (Long-Term Goals)\n"
            "4. Suggest plot points where relevant\n\n"
            f"CURRENT LIFE PHASE:\n{life_phase}\n\n"
            "TIMEFRAME RULES:\n"
            "1. Historical Summary: Events from tweets only\n"
            "2. Projected Developments: Only events within next 3-6 months (short-term) and 1-5 years (long-term)\n"
            "3. All projections must be specific, realistic, and align with Xavier's interests and phase of life\n\n"
        )

        # Include Technology Integration
        prompt += self._build_tech_section(mature_tech, maturing_soon)

        # Technology Integration Rules
        prompt += (
            "\nTECHNOLOGY INTEGRATION RULES:\n"
            "1. Professional track MUST reference mature technologies related to trading, blockchain, or AI\n"
            "2. Reflections track MUST explore emerging technologies that align with Xavier's curiosities\n"
            "3. Other tracks MAY reference technologies if they connect logically to Xavier’s life phase\n"
            "4. Technology Influences should include:\n"
            "   - Upcoming tech trends that may impact Xavier\n"
            "   - Societal shifts due to new tech developments\n"
            "   - Tech-driven plot points that could create significant events or conflicts\n\n"
        )

        prompt += (
            "For recent tweets about $XVI, incorporate insights under:\n"
            "- Professional\n"
            "- Financial Trajectory\n"
            "- Reflections\n\n"
        )

        # Existing life track summaries and projections
        prompt += "Combine the following Historical Summary with Recent Tweets and Comments to create updated summaries and projections:\n"
        prompt += self._build_current_tracks_section()

        # Add recent tweets for analysis
        if recent_tweets:
            prompt += "\nRECENT TWEETS TO ANALYZE (from oldest to newest):\n"
            if isinstance(recent_tweets, list):
                counter = 0
                for tweet in recent_tweets:
                    if isinstance(tweet, dict):
                        date = tweet.get('simulated_date', '')
                        content = tweet.get('content', '').get('content', '')
                        prompt += f"[{date}] {content}\n"
                    else:
                        prompt += f"{counter}. {tweet}\n"
                        counter += 1
            else:
                prompt += f"- {recent_tweets}\n"

        # Add recent comments if available
        if recent_comments:
            prompt += "\nRECENT COMMENTS:\n" + "\n".join(f"- {comment}" for comment in recent_comments) + "\n"

        return prompt

def main():
    """Test function to print digest summaries"""
    try:
        simulation_time = "2024-03-21"  # Example date
        simulation_age = 22  # Final age
        tweet_count = 42
        
        # Initialize digest generator
        digest_gen = DigestGenerator(simulation_time, simulation_age, tweet_count)
        
        # Get tweets from XaviersSim.json
        content, _ = digest_gen.github_ops.get_file_content('XaviersSim.json')
        if content:
            # Generate first digest using pre-grouped age brackets
            print("\nGenerating first digest using age brackets...")
            first_digest = digest_gen.generate_first_digest(content)
            
            if first_digest:
                print("Successfully generated first digest")
            else:
                print("Failed to generate first digest")

    except Exception as e:
        print(f"Error in main: {type(e).__name__} - {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()