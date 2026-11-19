const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1]
    .replace('        fetchData();\n        startCountdown();', '');
const elements = {};
let scroll;
let timer;
let cleared = 0;
const context = {
    document: {getElementById: id => elements[id] ??= {innerHTML: '', textContent: '', hidden: true}},
    window: {scrollY: 123, scrollTo: (x, y) => { scroll = y; }},
    AbortController,
    URL,
    setTimeout: callback => { timer = callback; return 1; },
    clearTimeout: () => { cleared++; },
    setInterval: () => {},
};
vm.createContext(context);
vm.runInContext(source, context);
const run = code => vm.runInContext(code, context);
const coin = (symbol, change) => ({symbol, current_price: 0, price_change_percentage_24h: change});
context.coins = [coin('<b>injected</b>', 2), coin('worst', -8), coin('loser', -1),
    coin('best', 5), coin('zero', 0), null, {}, {symbol: 'bad', current_price: '<img>'}];
context.coins[0].image = 'https://example.com/" onerror="bad';

(async () => {
    run('renderReport({}, coins)');
    const html = elements.content.innerHTML;
    assert(html.includes('&lt;B&gt;INJECTED&lt;/B&gt;'));
    assert(!html.includes('<B>INJECTED</B>'));
    assert(!html.includes('src="https://example.com/" onerror='));
    assert.equal(run('imageUrl("javascript:alert(1)")'), '');
    for (const value of ['javascript:alert(1)', 'data:image/svg+xml,x', '//example.com/x', null, 'http://[']) {
        context.rejectedImage = value;
        run('renderReport({}, [{symbol: "coin", image: rejectedImage}])');
        assert(!elements.content.innerHTML.includes('<img'));
    }
    console.log('PASS: injected markup escaped; rejected image URLs emit no img element');
    assert(html.indexOf('BEST') < html.indexOf('&lt;B&gt;'));
    assert(html.indexOf('WORST') < html.indexOf('LOSER'));
    assert(!html.includes('+-'));
    assert(html.includes('0.00%'));
    assert(!html.includes('BAD'));
    run('renderReport({}, [])');
    console.log('PASS: movers filtered/sorted, zero formatted, malformed coins skipped, empty data supported');

    context.fetch = async url => ({ok: true, status: 200, json: async () => url.endsWith('/global') ? {data: {}} : context.coins});
    await run('fetchData()');
    assert.equal(scroll, 123);
    assert(elements.lastUpdate.textContent.includes('GMT+8'));
    const previous = elements.content.innerHTML;
    const timestamp = elements.lastUpdate.textContent;
    context.fetch = async () => ({ok: false, status: 429});
    await run('fetchData()');
    assert.equal(elements.content.innerHTML, previous);
    assert.equal(elements.lastUpdate.textContent, timestamp);
    assert.equal(elements.errorBanner.hidden, false);
    assert(elements.errorBanner.textContent.includes('429'));
    assert.equal(run('countdown'), 60);
    await run('fetchData()');
    assert.equal(run('countdown'), 120);
    console.log('PASS: failed refresh keeps old data/timestamp; error banner and 429 backoff preserved');

    context.fetch = (url, {signal}) => new Promise((resolve, reject) => {
        signal.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), {name: 'AbortError'})));
    });
    const pending = run('fetchJson("https://example.com")');
    timer();
    await assert.rejects(pending, /timed out/);
    assert(cleared > 0);
    assert.equal(run('isFetching'), false);
    context.fetch = async url => ({ok: true, status: 200, json: async () => url.endsWith('/global') ? {data: {}} : []});
    await run('fetchData()');
    assert.equal(elements.errorBanner.hidden, true);
    assert.equal(run('countdown'), 30);
    console.log('PASS: AbortController timeout; recovery clears banner and resets backoff; GMT+8 and scroll preserved');
})().catch(error => { console.error(error); process.exitCode = 1; });
