# Xavier's Story Generator (ACT II)

A narrative AI system that generates a continuous story through the lens of Xavier's social media posts, chronicling his journey from 2025 to 2075.

## Overview

This project uses AI to generate a coherent, long-form narrative through the medium of social media posts. It follows Xavier, a character navigating through five decades of life, technology, and personal growth, starting from 2025.

## Features

- **Dynamic Story Generation**: Creates contextually aware posts that build upon previous events
- **Timeline Management**: Tracks story progression from 2025 to 2075
- **Character Development**: Maintains consistent character voice while allowing for growth and change
- **State Management**: Preserves story continuity and character relationships
- **Natural Variation**: Generates posts of varying lengths and tones, from quick updates to reflective essays

## Project Structure

XaviersSimACTII/
├── data/ # Data storage directory
│ ├── XaviersSim.json # Compilation of existing tweets from XaviersSimACTI
│ ├── digest.json # Up to date digest of story events 
│ ├── last_acti_tweets.json # Last ten tweets from XaviersSimACTI
│ ├── ongoing_tweets.json # Active story threads
│ ├── comments.json # Comments to active story threads
│ ├── simulation_state.json # Current simulation state
│ └── tech_evolution.json # Technology progression data
│
├── src/ # Source code
│ ├── generation/ # Content generation modules
│ │ ├── tweet_generator.py # Main tweet generation logic
│ │ ├── digest_generator.py # Story digest generation
│ │ └── tech_evolution_generator.py # Tech timeline generator
│ │
│ ├── storage/ # Data persistence layer
│ │ ├── cleanup.py # Data cleanup utilities
│ │ └── github_operations.py # GitHub integration
│ │
│ ├── twitter/ # Twitter integration
│ │ ├── twitter_client.py # Twitter API client
│ │ └── twitter_client_v2.py # Twitter API v2 client
│ │
│ └── utils/ # Utility functions
│ └── config.py # Configuration management
│
├── tests/ # Test suite
│ └── test_github_operations.py # GitHub operations tests
│
├── requirements.txt # Project dependencies
└── README.md # Project documentation

### Key Components

#### Data Layer
- Storage for simulation state, tweets, and story progression
- Maintains technology evolution timeline
- Tracks ongoing narrative threads and digests

#### Generation
- `tweet_generator.py`: Core story generation
- `digest_generator.py`: Creates story summaries
- `tech_evolution_generator.py`: Manages future tech progression

#### Storage
- GitHub integration for data persistence
- Cleanup utilities for maintaining data integrity

#### Twitter Integration
- Multiple Twitter API client versions
- Handles social media interaction

#### Utils
- Configuration management
- Helper functions



## Contributing

Feel free to open issues or submit pull requests for improvements to the story generation system.

## License

MIT License

Copyright (c) 2024 0xDatapunk

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.