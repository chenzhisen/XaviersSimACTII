const fs = require('fs').promises;
const path = require('path');

class PathUtils {
    static async ensureDir(dirPath) {
        try {
            await fs.access(dirPath);
        } catch {
            await fs.mkdir(dirPath, { recursive: true });
        }
    }

    static async getLogDir(baseDir, component) {
        const logDir = path.join('logs', baseDir, component);
        await this.ensureDir(logDir);
        return logDir;
    }

    static async getDataDir(baseDir, component) {
        const dataDir = path.join('data', baseDir, component);
        await this.ensureDir(dataDir);
        return dataDir;
    }

    static async getCacheDir(baseDir, component) {
        const cacheDir = path.join('.cache', baseDir, component);
        await this.ensureDir(cacheDir);
        return cacheDir;
    }

    static async readJsonFile(filePath, defaultValue = null) {
        try {
            const content = await fs.readFile(filePath, 'utf-8');
            return JSON.parse(content);
        } catch (error) {
            if (error.code === 'ENOENT') {
                return defaultValue;
            }
            throw error;
        }
    }

    static async writeJsonFile(filePath, data) {
        await this.ensureDir(path.dirname(filePath));
        await fs.writeFile(filePath, JSON.stringify(data, null, 2));
    }

    static async listFiles(dirPath, pattern = null) {
        try {
            const files = await fs.readdir(dirPath);
            if (pattern) {
                const regex = new RegExp(pattern);
                return files.filter(file => regex.test(file));
            }
            return files;
        } catch (error) {
            if (error.code === 'ENOENT') {
                return [];
            }
            throw error;
        }
    }

    static async removeFile(filePath) {
        try {
            await fs.unlink(filePath);
            return true;
        } catch (error) {
            if (error.code === 'ENOENT') {
                return false;
            }
            throw error;
        }
    }
}

module.exports = { PathUtils }; 