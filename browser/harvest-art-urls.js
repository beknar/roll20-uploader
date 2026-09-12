// Harvest name -> URL for your uploaded Roll20 art.
//
// WHY THIS EXISTS
// The Mod API cannot read your art library, and it refuses any imgsrc that is
// not already Roll20-hosted. So the only way to set a portrait, token or map
// image from a script is to upload the files first and then find out what URLs
// Roll20 gave them. The library's search endpoint returns URLs but no filenames;
// the sidebar DOM has both. This scrapes the sidebar.
//
// HOW TO USE
//   1. Open your game in Roll20 and let it finish loading.
//   2. Open the Art Library tab in the right sidebar (the palette icon).
//   3. Open DevTools -> Console, paste this whole file, press Enter.
//   4. Wait for it to finish, then run:  copy(LL.json())
//      and paste into library.json next to your config.
//
// Searches are slow (~3-5s each) and the library search caps at roughly 270
// results with no paging, so broad terms alone will not reach everything.
// LL.sweep() runs a few wide terms; LL.find([...]) fills gaps by exact name.
window.LL = (function () {
    const map = {};

    function panel() {
        const d = document.getElementById('imagedialog');
        if (!d) throw new Error('Art Library panel not found - open that tab first.');
        return d;
    }

    async function search(term, ms) {
        const d = panel();
        const input = d.querySelector('input.keywords');
        const results = document.getElementById('libraryresults');
        results.innerHTML = '';
        input.value = term;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, keyCode: 13, which: 13 }));
        await new Promise(r => setTimeout(r, ms || 4000));
        let added = 0;
        [...results.querySelectorAll('li.library-item')].forEach(el => {
            const name = ((el.querySelector('.dd-content') || {}).textContent || '').trim();
            const url = String(el.getAttribute('data-fullsizeurl') || '').split('?')[0];
            if (name && url && !map[name]) { map[name] = url; added++; }
        });
        console.log(`  "${term}" -> +${added} (total ${Object.keys(map).length})`);
        return added;
    }

    return {
        map,
        search,
        // Wide passes. Add your own terms if your filenames share other stems.
        async sweep(terms) {
            for (const t of (terms || ['webp', '-', 'the-', 'png', 'jpg'])) {
                await search(t, 6000);
            }
            return Object.keys(map).length;
        },
        // Exact-name fills for anything sweep missed. Pass filename stems.
        async find(names, ms) {
            const missing = names.filter(n => !map[n] && !map[n + '.webp']);
            console.log(`filling ${missing.length} by exact name...`);
            for (const n of missing) await search(n, ms || 4000);
            return names.filter(n => !map[n] && !map[n + '.webp']);
        },
        missing(names) {
            return names.filter(n => !map[n] && !map[n + '.webp']);
        },
        count() { return Object.keys(map).length; },
        json() { return JSON.stringify(map, null, 1); }
    };
})();
console.log('LL ready.  await LL.sweep()   then   copy(LL.json())');
