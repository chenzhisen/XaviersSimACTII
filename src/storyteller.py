import json
from src.generation.tweet_generator import TweetGenerator

def main():
    generator = TweetGenerator()
    
    while True:
        # Check simulation state
        state, _ = generator.get_simulation_state()
        current_year = state.get("current_year", 2025)
        
        if current_year >= 2075:  # Xavier would be 72 years old (started at 22 in 2025)
            print("Xavier has reached 72 years old. His story is complete!")
            return
            
        # Generate tweet if under age limit
        tweet = generator.generate_tweet()
        if tweet:
            print("Generated tweet:")
            print(json.dumps(tweet, indent=2))
        else:
            print("No tweet generated this time")
            break  # Exit if tweet generation fails

if __name__ == "__main__":
    main() 