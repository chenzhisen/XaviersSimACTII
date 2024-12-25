const fs = require('fs').promises;
const path = require('path');

async function initializeDataStructure() {
    const structure = {
        'data': {
            'dev': {
                'epochs': {},
                'summary.json': {
                    currentAge: 22.0,
                    totalTweets: 0,
                    epochs: [],
                    keyPlotPoints: [],
                    lastUpdate: new Date().toISOString()
                }
            },
            'prod': {
                'epochs': {},
                'summary.json': {
                    currentAge: 22.0,
                    totalTweets: 0,
                    epochs: [],
                    keyPlotPoints: [],
                    lastUpdate: new Date().toISOString()
                }
            }
        }
    };

    await createDirectoryStructure(structure);
}

async function createDirectoryStructure(structure, basePath = '.') {
    for (const [name, content] of Object.entries(structure)) {
        const fullPath = path.join(basePath, name);
        
        if (typeof content === 'object' && !Array.isArray(content)) {
            await fs.mkdir(fullPath, { recursive: true });
            await createDirectoryStructure(content, fullPath);
        } else {
            await fs.writeFile(
                fullPath,
                JSON.stringify(content, null, 2),
                'utf8'
            );
        }
    }
}

module.exports = { initializeDataStructure }; 