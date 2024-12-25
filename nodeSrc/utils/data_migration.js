const fs = require('fs').promises;
const path = require('path');
const { Logger } = require('./logger');

class DataMigration {
    constructor() {
        this.logger = new Logger('migration');
        this.paths = {
            oldFile: path.resolve(__dirname, '..', 'data', 'oldVersion.json'),
            newFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };
    }

    async migrateData() {
        try {
            // 读取旧数据
            const oldData = JSON.parse(await fs.readFile(this.paths.oldFile, 'utf8'));
            
            // 读取新数据结构模板
            const newData = JSON.parse(await fs.readFile(this.paths.newFile, 'utf8'));

            // 迁移数据
            const migratedData = this._transformData(oldData, newData);

            // 保存迁移后的数据
            await fs.writeFile(
                this.paths.newFile,
                JSON.stringify(migratedData, null, 2),
                'utf8'
            );

            this.logger.info('Data migration completed successfully');
            return true;
        } catch (error) {
            this.logger.error('Data migration failed', error);
            throw error;
        }
    }

    _transformData(oldData, newData) {
        // 保持新数据结构，填充旧数据
        return {
            ...newData,
            metadata: {
                ...newData.metadata,
                currentAge: oldData.currentAge || newData.metadata.currentAge,
                lastUpdate: oldData.lastUpdate || newData.metadata.lastUpdate
            },
            story: {
                ...newData.story,
                tweets: this._migrateTweets(oldData.tweets || []),
                digests: this._migrateDigests(oldData.digests || []),
                keyPlotPoints: this._migrateKeyPlotPoints(oldData.keyPlotPoints || [])
            },
            tech: {
                ...newData.tech,
                updates: this._migrateTechUpdates(oldData.techUpdates || [])
            },
            career: {
                ...newData.career,
                milestones: this._migrateMilestones(oldData.milestones || [])
            },
            stats: {
                ...newData.stats,
                totalTweets: (oldData.tweets || []).length,
                digestCount: (oldData.digests || []).length,
                techUpdateCount: (oldData.techUpdates || []).length,
                yearProgress: this._calculateYearProgress((oldData.tweets || []).length)
            }
        };
    }

    _migrateTweets(oldTweets) {
        return oldTweets.map(tweet => ({
            text: tweet.text,
            id: tweet.id,
            age: tweet.age,
            timestamp: tweet.timestamp
        }));
    }

    _migrateDigests(oldDigests) {
        return oldDigests.map(digest => ({
            content: digest.content,
            age: digest.age,
            timestamp: digest.timestamp,
            tweetCount: digest.tweetCount
        }));
    }

    _migrateKeyPlotPoints(oldPlotPoints) {
        return oldPlotPoints.map(point => ({
            type: point.type,
            content: point.content,
            age: point.age,
            timestamp: point.timestamp
        }));
    }

    _migrateTechUpdates(oldUpdates) {
        return oldUpdates.map(update => ({
            content: update.content,
            phase: update.phase,
            focus: update.focus,
            challenges: update.challenges,
            age: update.age,
            timestamp: update.timestamp
        }));
    }

    _migrateMilestones(oldMilestones) {
        return oldMilestones.map(milestone => ({
            type: milestone.type,
            description: milestone.description,
            age: milestone.age,
            timestamp: milestone.timestamp
        }));
    }

    _calculateYearProgress(tweetCount) {
        const tweetsPerYear = 48;
        return ((tweetCount % tweetsPerYear) / tweetsPerYear * 100).toFixed(1);
    }
}

// 执行迁移
async function runMigration() {
    const migration = new DataMigration();
    try {
        await migration.migrateData();
        console.log('Migration completed successfully');
    } catch (error) {
        console.error('Migration failed:', error);
        process.exit(1);
    }
}

if (require.main === module) {
    runMigration();
}

module.exports = { DataMigration }; 