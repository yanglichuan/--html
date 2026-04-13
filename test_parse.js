const fs = require('fs');

async function test() {
    const url = "https://yanglc.top/api/eastmoney/kline?secid=0.000021&fields1=f1,f2&fields2=f51,f52,f53,f54,f55,f56,f59&klt=101&fqt=1&end=20500101&lmt=250&ut=fa5fd1943c7b386f172d6893dbf24fe0";
    const response = await fetch(url);
    const res = await response.json();

    const rawData = res.data.klines.map(x => {
        const p = x.split(',');
        return { 
            date: p[0], 
            o: parseFloat(p[1]), 
            c: parseFloat(p[2]), 
            h: parseFloat(p[3]), 
            l: parseFloat(p[4]), 
            v: parseFloat(p[5]), 
            pct: parseFloat(p[6]) 
        };
    });

    function calculateMA(dayCount, data) {
        var result = [];
        for (var i = 0, len = data.length; i < len; i++) {
            if (i < dayCount) {
                result.push('-');
                continue;
            }
            var sum = 0;
            for (var j = 0; j < dayCount; j++) {
                sum += data[i - j].c;
            }
            result.push((sum / dayCount).toFixed(2));
        }
        return result;
    }

    const dates = rawData.map(item => item.date);
    const values = rawData.map(item => [item.o, item.c, item.l, item.h]);
    const volumes = rawData.map((item, i) => [i, item.v, item.c >= item.o ? 1 : -1]);

    const ma5 = calculateMA(5, rawData);
    console.log("Success! Dates:", dates.length, "MA5:", ma5.length);
}

test();