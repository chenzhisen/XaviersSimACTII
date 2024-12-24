const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');

class TechEvolutionGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tech');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        
        // 配置
        this.epochYears = 5;  // 每个时代的年数
        this.updateThreshold = 48;  // 更新阈值（推文数）
    }

    async generateTechEvolution() {
        try {
            const [currentTech, sha] = await this.githubOps.getFileContent('tech_evolution.json');
            if (!currentTech) {
                return await this._generateInitialTech();
            }

            const [tweets, _] = await this.githubOps.getFileContent('ongoing_tweets.json');
            if (!tweets || tweets.length === 0) {
                return currentTech;
            }

            // 检查是否需要更新
            const lastTweet = tweets[tweets.length - 1];
            const currentYear = Math.floor(lastTweet.age);
            const nextEpochYear = Math.ceil(currentYear / this.epochYears) * this.epochYears;
            const tweetsUntilNextEpoch = this._calculateTweetsUntilYear(nextEpochYear);

            if (tweetsUntilNextEpoch <= this.updateThreshold) {
                return await this._generateNextEpoch(currentTech, nextEpochYear);
            }

            return currentTech;

        } catch (error) {
            this.logger.error('Error generating tech evolution', error);
            throw error;
        }
    }

    async _generateInitialTech() {
        const prompt = `Generate the initial technology state for the year 2025.
Include:
- Mainstream technologies (fully adopted)
- Emerging technologies (in development)
- Major societal trends
Format as a concise JSON structure.`;

        const response = await this.ai.getCompletion(
            'You are a technology forecasting system.',
            prompt
        );

        const techData = JSON.parse(response);
        await this.githubOps.updateFile(
            'tech_evolution.json',
            techData,
            'Initialize technology evolution'
        );

        return techData;
    }

    async _generateNextEpoch(currentTech, targetYear) {
        const prompt = `Based on the current technology state:
${JSON.stringify(currentTech, null, 2)}

Generate technology evolution for the year ${targetYear}.
Consider:
- Natural progression from current tech
- New breakthroughs and innovations
- Societal impact and adoption rates
Format as a concise JSON structure.`;

        const response = await this.ai.getCompletion(
            'You are a technology forecasting system.',
            prompt
        );

        const newTech = JSON.parse(response);
        await this.githubOps.updateFile(
            'tech_evolution.json',
            newTech,
            `Update technology evolution for ${targetYear}`
        );

        return newTech;
    }

    _calculateTweetsUntilYear(targetYear) {
        const tweetsPerYear = 96;  // 每年的推文数
        return Math.floor((targetYear - 22) * tweetsPerYear);  // 22是起始年龄
    }
}

module.exports = { TechEvolutionGenerator }; 