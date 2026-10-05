const fs = require('fs');
const path = require('path');
const https = require('https');
const crypto = require('crypto');

// Configuration: Upstream Repositories
const UPSTREAM_SOURCES = [
    {
        name: 'NivinCNC (CNCVerse)',
        baseUrl: 'https://raw.githubusercontent.com/NivinCNC/CNCVerse-Cloud-Stream-Extension/builds',
        manifestUrl: 'https://raw.githubusercontent.com/NivinCNC/CNCVerse-Cloud-Stream-Extension/builds/plugins.json'
    },
    {
        name: 'phisher98 (PhisherRepo)',
        baseUrl: 'https://raw.githubusercontent.com/phisher98/cloudstream-extensions-phisher/builds',
        manifestUrl: 'https://raw.githubusercontent.com/phisher98/cloudstream-extensions-phisher/builds/plugins.json'
    },
    {
        name: 'MrXtron (Xtron)',
        baseUrl: 'https://raw.githubusercontent.com/MrXtron/CloudStream-Extension/builds',
        manifestUrl: 'https://raw.githubusercontent.com/MrXtron/CloudStream-Extension/builds/plugins.json'
    }
];

const LOCAL_REPO_URL = 'https://github.com/shahrukh-hack/yogesh-streamer-plugins';
const LOCAL_RAW_BASE = 'https://raw.githubusercontent.com/shahrukh-hack/yogesh-streamer-plugins/builds';
const BUNDLED_ASSETS_DIR = path.resolve(__dirname, '../yogesh-streamer/app/src/main/assets/plugins');

function fetchJson(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                return fetchJson(res.headers.location).then(resolve).catch(reject);
            }
            if (res.statusCode !== 200) {
                return reject(new Error(`Failed to fetch ${url} (status: ${res.statusCode})`));
            }
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(e);
                }
            });
        }).on('error', reject);
    });
}

function downloadBinary(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                return downloadBinary(res.headers.location).then(resolve).catch(reject);
            }
            if (res.statusCode !== 200) {
                return reject(new Error(`Failed to download ${url} (status: ${res.statusCode})`));
            }
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => resolve(Buffer.concat(chunks)));
        }).on('error', reject);
    });
}

function sha256(buf) {
    return 'sha256-' + crypto.createHash('sha256').update(buf).digest('hex');
}

async function main() {
    console.log('====================================================');
    console.log('   🚀 Yogesh Streamer Plugin Sync Engine');
    console.log('====================================================\n');

    const localManifestPath = path.join(__dirname, 'plugins.json');
    if (!fs.existsSync(localManifestPath)) {
        console.error('Error: plugins.json not found in current directory.');
        process.exit(1);
    }

    const localPlugins = JSON.parse(fs.readFileSync(localManifestPath, 'utf8'));
    console.log(`📦 Loaded ${localPlugins.length} local plugins from plugins.json`);

    // Fetch all upstream manifests
    const upstreams = [];
    for (const source of UPSTREAM_SOURCES) {
        process.stdout.write(`🌐 Fetching manifest from ${source.name}... `);
        try {
            const list = await fetchJson(source.manifestUrl);
            upstreams.push({ source, list });
            console.log(`OK (${list.length} plugins)`);
        } catch (e) {
            console.log(`FAILED (${e.message})`);
        }
    }
    console.log();

    let updatedCount = 0;
    const updateLog = [];

const ALIAS_MAP = {
    'Netmirror': ['CNC Verse', 'CNCVerse', 'Netmirror'],
};

    for (const local of localPlugins) {
        // Find best match in upstream sources
        let bestCandidate = null;
        let bestSource = null;

        const lookupNames = [
            (local.internalName || '').toLowerCase(),
            (local.name || '').toLowerCase(),
            ...((ALIAS_MAP[local.internalName] || []).map(a => a.toLowerCase())),
            ...((ALIAS_MAP[local.name] || []).map(a => a.toLowerCase()))
        ];

        for (const { source, list } of upstreams) {
            const match = list.find(u => 
                (u.internalName && lookupNames.includes(u.internalName.toLowerCase())) ||
                (u.name && lookupNames.includes(u.name.toLowerCase()))
            );
            if (match) {
                if (!bestCandidate || match.version > bestCandidate.version) {
                    bestCandidate = match;
                    bestSource = source;
                }
            }
        }

        if (!bestCandidate) {
            continue;
        }

        const isNewer = bestCandidate.version > local.version;
        const isHashChanged = bestCandidate.version === local.version && bestCandidate.fileHash !== local.fileHash;

        if (isNewer || isHashChanged) {
            const fileName = path.basename(local.url || `${local.internalName}.cs3`);
            const downloadUrl = bestCandidate.url.startsWith('http') 
                ? bestCandidate.url 
                : `${bestSource.baseUrl}/${fileName}`;

            process.stdout.write(`⬇️  Updating [${local.name}] (v${local.version} -> v${bestCandidate.version}) from ${bestSource.name}... `);

            try {
                const bin = await downloadBinary(downloadUrl);
                const newHash = sha256(bin);

                // Write binary
                fs.writeFileSync(path.join(__dirname, fileName), bin);

                // Update manifest entry
                const oldVer = local.version;
                local.version = bestCandidate.version;
                local.fileHash = newHash;
                local.fileSize = bin.length;
                local.repositoryUrl = LOCAL_REPO_URL;
                local.url = `${LOCAL_RAW_BASE}/${fileName}`;
                if (bestCandidate.description) {
                    local.description = bestCandidate.description;
                }

                updatedCount++;
                console.log(`DONE (${(bin.length / 1024).toFixed(1)} KB)`);

                updateLog.push({
                    name: local.name,
                    fileName,
                    oldVer,
                    newVer: local.version,
                    source: bestSource.name,
                    size: bin.length
                });

                // Also check if this is a bundled plugin for the main app
                const bundledDest = path.join(BUNDLED_ASSETS_DIR, fileName);
                if (fs.existsSync(bundledDest)) {
                    fs.writeFileSync(bundledDest, bin);
                    console.log(`   └─> Synced to app bundled assets: ${fileName}`);
                }
            } catch (err) {
                console.log(`ERROR (${err.message})`);
            }
        }
    }

    console.log('\n====================================================');
    if (updatedCount > 0) {
        // Save updated plugins.json
        fs.writeFileSync(localManifestPath, JSON.stringify(localPlugins, null, 4));
        console.log(`✅ Successfully updated ${updatedCount} plugin(s) in plugins.json!`);

        console.log('\n📋 Summary of Updates:');
        updateLog.forEach(u => {
            console.log(` • ${u.name.padEnd(25)} v${u.oldVer} -> v${u.newVer}  (${(u.size/1024).toFixed(1)} KB)  [${u.source}]`);
        });
    } else {
        console.log('✨ All plugins are already up-to-date with upstream!');
    }
    console.log('====================================================\n');
}

main().catch(console.error);
