// Create N blank pages in the current Roll20 game.
//
// WHY THIS EXISTS
// createObj('page', ...) returns null from a Mod script: the API can modify
// pages but not create them. The browser client can. LL_Maps.js then "adopts"
// these blanks -- renames, sizes, sets grid and scale, places the image.
//
// HOW TO USE
//   1. Open your game in Roll20 and let it finish loading.
//   2. DevTools -> Console, paste this file, then:   await makeBlankPages(76)
//   3. Reload the page and confirm the count survived (it is a real save, but
//      check anyway -- a client-only object would vanish).
//   4. In game chat:  !llmaps adopt
//
// Pages are created named "Untitled" and empty, which is exactly what adopt
// looks for; it will not touch a page that has anything on it or has been
// renamed. Each create takes roughly a second and a half, so this is slow.
async function makeBlankPages(n, batch) {
    const P = window.Campaign.pages;
    const start = P.length;
    batch = batch || 15;
    for (let done = 0; done < n; done += batch) {
        const take = Math.min(batch, n - done);
        for (let i = 0; i < take; i++) {
            try { P.create({ name: 'Untitled' }); }
            catch (e) { console.error('create failed:', e); return; }
        }
        const untitled = P.filter(p => /^untitled/i.test(String(p.get('name') || ''))).length;
        console.log(`  ${done + take}/${n} requested - pages ${P.length}, untitled ${untitled}`);
        await new Promise(r => setTimeout(r, 500));
    }
    console.log(`done: ${P.length - start} new pages (was ${start}, now ${P.length})`);
    console.log('Reload and re-check before running !llmaps adopt.');
}
function countBlankPages() {
    const P = window.Campaign.pages;
    const un = P.filter(p => /^untitled/i.test(String(p.get('name') || '')));
    console.log(`pages ${P.length}, untitled ${un.length}`);
    return un.length;
}
console.log('ready:  await makeBlankPages(76)   /   countBlankPages()');
