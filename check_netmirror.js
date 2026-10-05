const fs = require('fs');
const zlib = require('zlib');

const buf = fs.readFileSync('Netmirror.cs3');
let offset = 0;
while (offset < buf.length - 4) {
    if (buf.readUInt32LE(offset) === 0x04034b50) {
        const compMethod = buf.readUInt16LE(offset + 8);
        const compSize = buf.readUInt32LE(offset + 18);
        const fnLen = buf.readUInt16LE(offset + 26);
        const extraLen = buf.readUInt16LE(offset + 28);
        const fn = buf.subarray(offset + 30, offset + 30 + fnLen).toString('utf8');
        const dataStart = offset + 30 + fnLen + extraLen;
        const data = buf.subarray(dataStart, dataStart + compSize);
        if (fn === 'manifest.json') {
            let content = compMethod === 0 ? data.toString('utf8') : zlib.inflateRawSync(data).toString('utf8');
            console.log('Local Netmirror Manifest:', JSON.parse(content));
        }
        if (fn === 'classes.dex') {
            let content = compMethod === 0 ? data : zlib.inflateRawSync(data);
            const text = content.toString('latin1');
            const urls = text.match(/https?:\/\/[a-zA-Z0-9_\-\.]+\.[a-zA-Z]{2,6}[^\s\x00"'<>]*/g) || [];
            const unique = [...new Set(urls)];
            console.log('URLs in Local Netmirror.cs3 (v46):');
            console.log(unique);
        }
        offset += 30 + fnLen + extraLen + compSize;
    } else offset++;
}
