const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');

class TechEvolutionGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tech');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
    }

    async generateTechEvolution() {
        try {
            console.log('TechEvolution Step 1: Getting current tech state...');
            const [currentTech, sha] = await this.githubOps.getFileContent('tech_evolution.json');
            console.log('Current tech state:', currentTech ? 'Found' : 'Not found');

            if (!currentTech) {
                console.log('TechEvolution Step 2a: Generating initial tech...');
                const initialTech = await this._generateInitialTech();
                console.log('Initial tech generated:', initialTech);

                console.log('TechEvolution Step 2b: Saving initial tech...');
                await this.githubOps.updateFile(
                    'tech_evolution.json',
                    initialTech,
                    'Initial tech evolution'
                );
                return initialTech;
            }

            console.log('TechEvolution Step 3: Checking for update threshold...');
            const [tweets] = await this.githubOps.getFileContent('ongoing_tweets.json');
            const shouldUpdate = this._shouldUpdateTech(tweets, currentTech);
            console.log('Update needed:', shouldUpdate);

            if (shouldUpdate) {
                console.log('TechEvolution Step 4a: Generating next tech epoch...');
                const nextTech = await this._generateNextTech(currentTech, tweets);
                console.log('Next tech epoch generated:', nextTech);

                console.log('TechEvolution Step 4b: Saving next tech epoch...');
                await this.githubOps.updateFile(
                    'tech_evolution.json',
                    nextTech,
                    `Update tech evolution to year ${nextTech.year}`,
                    sha
                );
                return nextTech;
            }

            console.log('TechEvolution Step 5: Returning current tech (no update needed)');
            return currentTech;

        } catch (error) {
            this.logger.error('Error generating tech evolution', error);
            console.error('TechEvolution Error:', {
                message: error.message,
                phase: error.phase || 'unknown',
                details: error.details || {}
            });
            throw error;
        }
    }

    async _generateInitialTech() {
        console.log('Generating initial tech - Preparing prompt...');
        const prompt = `Generate a technology evolution forecast for the year 2025, including:
1. Mainstream technologies that are widely adopted
2. Emerging technologies that show promise

Format the response as a JSON object with:
{
    "year": 2025,
    "mainstream": ["tech1", "tech2", ...],
    "emerging": ["tech1", "tech2", ...]
}`;

        console.log('Sending prompt to AI...');
        const response = await this.ai.getCompletion(
            'You are a technology forecasting system.',
            prompt
        );
        console.log('AI response received, parsing...');

        try {
            return JSON.parse(response);
        } catch (error) {
            console.error('Failed to parse AI response:', error);
            throw new Error('Invalid tech evolution format');
        }
    }

    async _generateNextTech(currentTech, tweets) {
        console.log('Generating next tech - Preparing context...');
        const prompt = `Current technology state (${currentTech.year}):
${JSON.stringify(currentTech, null, 2)}

Recent developments:
${tweets.slice(-5).map(t => t.text).join('\n')}

Generate the next technology evolution state for year ${currentTech.year + 5}, following the same format.`;

        console.log('Sending prompt to AI...');
        const response = await this.ai.getCompletion(
            'You are a technology forecasting system.',
            prompt
        );
        console.log('AI response received, parsing...');

        try {
            return JSON.parse(response);
        } catch (error) {
            console.error('Failed to parse AI response:', error);
            throw new Error('Invalid tech evolution format');
        }
    }

    _shouldUpdateTech(tweets, currentTech) {
        if (!tweets || tweets.length === 0) return false;
        
        // 计算最新推文的年龄
        const latestTweet = tweets[tweets.length - 1];
        const yearsSinceLastUpdate = latestTweet.age - 22.0;
        const yearsSinceCurrentTech = currentTech.year - 2025;

        console.log('Update check:', {
            tweetAge: latestTweet.age,
            yearsSinceLastUpdate,
            yearsSinceCurrentTech
        });

        // 每5年更新一次
        return yearsSinceLastUpdate >= yearsSinceCurrentTech + 5;
    }
}

module.exports = { TechEvolutionGenerator };