"""Stage 2: turn npcs.json into the Roll20 mod scripts.

    python src/build_npcs.py

Emits LL_Payload_1..N.js (the data, split so no single script is enormous) and
LL_Importer.js (the paced driver). Run src/extract_npcs.py first.
"""
import json, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r20.config import CFG, out_path

NPCS = json.load(open(out_path("npcs.json"), encoding="utf-8"))
LABEL = CFG["campaign_label"]
OUT = os.path.dirname(out_path("npcs.json"))
CHUNK_BYTES = 70_000

chunks, cur, size = [], [], 0
for n in NPCS:
    j = json.dumps(n, ensure_ascii=False)
    if size + len(j) > CHUNK_BYTES and cur:
        chunks.append(cur); cur, size = [], 0
    cur.append(n); size += len(j)
if cur: chunks.append(cur)

for i, ch in enumerate(chunks, 1):
    body = json.dumps(ch, ensure_ascii=False, separators=(",", ":"))
    js = f"""// {LABEL}: NPC payload {i} of {len(chunks)}
// Generated from the vault -- do not hand-edit; re-run build_npcs.py instead.
// Install alongside LL_Importer.js and 5e_NPC_JSON_Importer.js, then run
//   !llimport start
// in chat.
on('ready', function () {{
    var LL = (globalThis.LLPayload = globalThis.LLPayload || []);
    Array.prototype.push.apply(LL, {body});
    log('[LL] payload {i}/{len(chunks)} loaded — ' + LL.length + ' NPCs queued');
}});
"""
    open(f"{OUT}/LL_Payload_{i}.js", "w", encoding="utf-8").write(js)

driver = """// Batch driver for 5e_NPC_JSON_Importer
//
// Feeds the queued NPC payloads to the 5e NPC JSON importer one at a time, paced so
// the importer has time to finish each sheet. Progress survives a sandbox restart.
//
// NOTE ON DELIVERY: ImportNpcJson's chat handler begins with
//     if (msg.playerid === 'API') return;
// so sendChat() from a mod is ignored by design. Two delivery paths are tried:
//
//   1. direct call, if handleChatMessage happens to be in the shared global scope;
//   2. handout delivery: the NPC JSON is written to a handout and only a short
//      '!5enpcimport handout|LL-IMPORT' command goes down the chat channel.
//
// Raw JSON must never go through sendChat: Roll20's chat parser tries to resolve
// '@{...}' attribute references and '[[...]]' inline rolls inside the message and
// throws in textchat.js. The handout carries the payload; chat carries a name.
//
// For path 2 the importer needs a one-line change so it lets our tagged messages by:
//
//     if (msg.playerid === 'API' && msg.who !== 'LL-DRIVER') return;
//
// That keeps its loop protection for every other API message.
//
//   !llimport start        begin (or resume) the run
//   !llimport status       how far along
//   !llimport pause        stop after the current NPC
//   !llimport retry        re-queue everything that failed
//   !llimport reset        clear all progress (does NOT delete characters)
//   !llimport delay 25     seconds between NPCs (default 20)
//   !llimport test         import ONE NPC only, so you can verify the chain works
//   !llimport test Talon   import one NPC by name
//
// Safe to re-run: an NPC whose character already exists is skipped unless you
// pass  !llimport start force .
on('ready', function () {
    'use strict';
    var DEFAULT_DELAY = 20;

    function st() {
        if (!state.LLIMPORT) state.LLIMPORT = { i: 0, done: [], failed: [], delay: DEFAULT_DELAY, running: false, gm: null };
        if (state.LLIMPORT.gm === undefined) state.LLIMPORT.gm = null;
        return state.LLIMPORT;
    }

    var HANDOUT = 'LL-IMPORT';

    function scratchHandout() {
        var h = findObjs({ _type: 'handout', name: HANDOUT })[0];
        if (!h) h = createObj('handout', { name: HANDOUT, inplayerjournals: '', controlledby: '' });
        return h;
    }

    // Hand one NPC to the importer, then call done().
    function deliver(npc, gmid, done) {
        if (typeof handleChatMessage === 'function') {
            handleChatMessage({
                who: 'Lost Lands', playerid: gmid, type: 'api',
                content: '!5enpcimport ' + JSON.stringify(npc), selected: []
            });
            if (done) done();
            return;
        }
        var h = scratchHandout();
        h.set('notes', JSON.stringify(npc));
        // give Roll20 a moment to persist the notes before the importer reads them
        setTimeout(function () {
            sendChat('LL-DRIVER', '!5enpcimport handout|' + HANDOUT);
            if (done) done();
        }, 1200);
    }

    function probe() {
        return (typeof handleChatMessage === 'function')
            ? 'direct call into ImportNpcJson (handleChatMessage found)'
            : "handout '" + HANDOUT + "' + a short chat command as 'LL-DRIVER' " +
              "(needs the importer's one-line guard edit — see the note at the top of this script)";
    }
    function say(m) { sendChat('Lost Lands', '/w gm ' + m); }
    function queue() { return globalThis.LLPayload || []; }

    function exists(name) {
        return findObjs({ _type: 'character', name: name }).length > 0;
    }

    function step(force) {
        var s = st(), q = queue();
        if (!s.running) return;
        if (s.i >= q.length) {
            s.running = false;
            say('<b>Import complete.</b> ' + s.done.length + ' imported, ' +
                s.failed.length + ' failed.' +
                (s.failed.length ? '<br>Failed: ' + s.failed.join(', ') : ''));
            return;
        }
        var npc = q[s.i], name = npc.name;
        s.i += 1;

        if (!force && exists(name)) {
            say('skip (already exists): ' + name);
            setTimeout(function () { step(force); }, 500);
            return;
        }
        try {
            deliver(npc, s.gm);
            s.done.push(name);
        } catch (e) {
            s.failed.push(name);
            log('[LL] failed ' + name + ': ' + e.message);
            say('failed: ' + name + ' — ' + e.message);
        }
        if (s.i % 10 === 0) say('progress: ' + s.i + '/' + q.length);
        setTimeout(function () { step(force); }, s.delay * 1000);
    }

    on('chat:message', function (msg) {
        if (msg.type !== 'api' || !/^!llimport\\b/.test(msg.content)) return;
        if (!playerIsGM(msg.playerid)) return;
        var args = msg.content.split(/\\s+/).slice(1);
        var cmd = (args[0] || 'status').toLowerCase();
        var s = st(), q = queue();

        if (cmd === 'test') {
            var want = args.slice(1).join(' ').toLowerCase();
            var one = want ? q.find(function (n) { return n.name.toLowerCase() === want; }) : q[0];
            if (!one) return say('No such NPC in the payload.');
            s.gm = msg.playerid;
            say('Test importing <b>' + one.name + '</b> via ' + probe() + '.');
            deliver(one, s.gm);
            return;
        }
        if (cmd === 'start') {
            if (!q.length) return say('No payload loaded. Install the LL_Payload_*.js scripts first.');
            if (s.running) return say('Already running — ' + s.i + '/' + q.length);
            s.gm = msg.playerid;
            s.running = true;
            say('Delivery method: ' + probe());
            say('Starting at ' + s.i + '/' + q.length + ', ' + s.delay + 's apart. ' +
                'Estimated ' + Math.ceil((q.length - s.i) * s.delay / 60) + ' minutes.');
            step(args[1] === 'force');
        } else if (cmd === 'pause') {
            s.running = false; say('Paused at ' + s.i + '/' + q.length + '. !llimport start resumes.');
        } else if (cmd === 'retry') {
            var f = s.failed.slice();
            s.failed = [];
            globalThis.LLPayload = q.filter(function (n) { return f.indexOf(n.name) >= 0; });
            s.i = 0; say('Re-queued ' + f.length + ' failed NPCs. !llimport start to run.');
        } else if (cmd === 'reset') {
            state.LLIMPORT = null; say('Progress cleared. Characters already created are untouched.');
        } else if (cmd === 'delay') {
            s.delay = Math.max(3, parseInt(args[1], 10) || DEFAULT_DELAY);
            say('Delay set to ' + s.delay + 's.');
        } else {
            say('queued ' + q.length + ' | position ' + s.i + ' | imported ' + s.done.length +
                ' | failed ' + s.failed.length + ' | ' + (s.running ? 'running' : 'idle') +
                '<br>delivery: ' + probe());
        }
    });

    log('[LL] importer driver ready — !llimport status');
});
"""
open(f"{OUT}/LL_Importer.js", "w", encoding="utf-8").write(driver)
print(f"{len(NPCS)} NPCs -> {len(chunks)} payload scripts + driver")
for i, ch in enumerate(chunks, 1):
    print(f"  LL_Payload_{i}.js  {len(ch):3d} NPCs  {os.path.getsize(f'{OUT}/LL_Payload_{i}.js')/1024:6.0f} KB")
print(f"  LL_Importer.js    driver  {os.path.getsize(f'{OUT}/LL_Importer.js')/1024:.0f} KB")
