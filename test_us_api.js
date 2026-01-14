const https = require('https');

const url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:105,m:106,m:107&fields=f12,f13,f14,f1,f2,f3,f4,f127';

https.get(url, (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
        try {
            const json = JSON.parse(data);
            console.log(JSON.stringify(json, null, 2));
        } catch (e) {
            console.error('Error parsing JSON:', e);
        }
    });
}).on('error', (e) => {
    console.error('Error fetching data:', e);
});
