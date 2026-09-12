// ============================================================================
//  LL_Fix.js  -- repair NPC token actions  (v3)
//
//  WHY
//  The 5e NPC importer writes each token action as
//      %{CharName|repeating_npcaction_-ROWID_rollbase}
//  %{...} is an ABILITY call, and rollbase is an ATTRIBUTE, so Roll20 never
//  finds it. The $N index form fails the same way -- %{} strips the index.
//  Either you get "No ability was found", or the macro leaks into chat as text.
//
//  WHAT THIS DOES
//  Each row's rollbase is the real macro, but it is written with row-relative
//  references (@{name}, @{attack_tohit}) that only resolve inside the row.
//  This script copies that rollbase INTO the ability and rewrites every
//  row-relative reference to its fully-qualified attribute name
//  (@{repeating_npcaction_-ROWID_attack_tohit}), which resolves anywhere.
//  Character-level references (@{wtype}, @{d20}, @{rtype}, ...) are left alone.
//
//  Nothing about the sheet changes -- edit a value on the sheet and the token
//  action still picks it up, because it is still reading the same attributes.
//
//  Commands (GM only):
//    !llfix test [name]   one character, prints the rewritten macro
//    !llfix apply         every character
//    !llfix revert        put back what was there before (originals are kept
//                         in state, so this survives a sandbox restart)
//    !llfix status        how many abilities still hold the broken form
//    !llfix ping          prove the command handler is alive
//
//  v3: the sheet's rollbase passes {{description=@{show_desc}}}, and show_desc
//  is a flag whose value is the literal "1" -- so the roll template prints "1"
//  where the description belongs, and description-only actions (Multiattack,
//  Swallow) show nothing at all. v3 repoints that field at the row's real
//  description attribute.
//
//  v2: every command runs inside try/catch and reports the error instead of
//  dying silently, and NOTHING containing @{...}, [[...]] or {{...}} is ever
//  passed to sendChat -- Roll20's chat parser tries to resolve those and throws,
//  which kills the handler mid-run with no output at all. Macro previews go to
//  the API console via log() and reach chat only in a defanged form.
// ============================================================================
on('ready', function () {
    'use strict';

    // Resolved on the character, not the row -- must NOT be qualified.
    var GLOBAL = ['wtype', 'rtype', 'd20', 'npcd20', 'npc_name_flag', 'charname_output',
                  'npc_name', 'character_name', 'globaldamage', 'globaldamage_flag',
                  'globaldamage_type', 'globaldamage_display', 'pb', 'rollsetting',
                  'npc_critdmg', 'npc_challenge'];

    // Row-relative keys the rollbase can reference even when the row has no
    // attribute row for them (blank optional fields). Created empty so the
    // qualified reference resolves instead of erroring.
    var ROWKEYS = ['name', 'description', 'show_desc', 'damage_flag',
                   'attack_tohit', 'attack_damage', 'attack_damagetype',
                   'attack_damage2', 'attack_damagetype2',
                   'attack_crit', 'attack_crit2', 'attack_onhit',
                   'attack_range', 'attack_target', 'attack_type',
                   'attack_tohitrange', 'attack_flag', 'attack_options',
                   'attack_display_flag', 'npc_options-flag'];

    function say(m) {
        // Never let roll/attribute syntax reach the chat parser: it throws.
        var safe = String(m).replace(/@\{/g, '(at){').replace(/\[\[/g, '[(').replace(/\]\]/g, ')]')
                            .replace(/\{\{/g, '{(').replace(/\}\}/g, ')}');
        try { sendChat('Campaign', '/w gm ' + safe); }
        catch (e) { log('LL_Fix: sendChat failed: ' + e.message + ' || ' + safe); }
    }
    function store() {
        if (!state.LLFIX) state.LLFIX = { orig: {} };
        return state.LLFIX;
    }

    // Pull section + row id out of the importer's broken macro.
    var REF = /repeating_([A-Za-z0-9-]+)_(-[A-Za-z0-9_-]{15,})_rollbase/;

    function attrsFor(charid) {
        var map = {};
        findObjs({ _type: 'attribute', _characterid: charid }).forEach(function (a) {
            map[a.get('name')] = a;
        });
        return map;
    }

    function rewriteOne(ch, ab, attrs, verbose) {
        var m = REF.exec(String(ab.get('action') || ''));
        if (!m) return 'notbroken';

        var section = m[1], rid = m[2];
        var prefix = 'repeating_' + section + '_' + rid + '_';
        var baseAttr = attrs[prefix + 'rollbase'];
        if (!baseAttr) return 'norow';

        var base = String(baseAttr.get('current') || '');
        if (!base) return 'norow';

        // Make sure every optional row field exists, so a qualified reference
        // to it resolves to blank rather than throwing "No attribute was found".
        ROWKEYS.forEach(function (k) {
            if (!attrs[prefix + k] && base.indexOf('@{' + k + '}') > -1) {
                attrs[prefix + k] = createObj('attribute', {
                    _characterid: ch.id, name: prefix + k, current: '', max: ''
                });
            }
        });

        var out = base.replace(/@\{([^}|]+)\}/g, function (whole, key) {
            if (GLOBAL.indexOf(key) > -1) return whole;           // character-level
            if (key.indexOf('repeating_') === 0) return whole;    // already qualified
            if (attrs[prefix + key] || ROWKEYS.indexOf(key) > -1) {
                return '@{' + prefix + key + '}';
            }
            return whole;                                          // unknown: leave it
        });

        // The sheet passes the show_desc FLAG as the template's description
        // field, so the roll prints "1" instead of the text. Point it at the
        // row's actual description.
        var esc = prefix.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        out = out.replace(new RegExp('\\{\\{description=@\\{' + esc + 'show_desc\\}\\}\\}', 'g'),
                          '{{description=@{' + prefix + 'description}}}');

        var s = store();
        if (!s.orig[ab.id]) s.orig[ab.id] = String(ab.get('action') || '');
        ab.set('action', out);
        ab.set('istokenaction', true);

        if (verbose) {
            log('=== LL_Fix rewrote ' + ch.get('name') + ' / ' + ab.get('name') + ' ===');
            log(out);
            say(ch.get('name') + ' / <b>' + ab.get('name') + '</b> rewritten, ' +
                out.length + ' chars (full text in the API console)');
        }
        return 'ok';
    }

    function eachCharacter(fn, doneMsg) {
        var chars = findObjs({ _type: 'character' });
        var i = 0, tally = { ok: 0, notbroken: 0, norow: 0, noab: 0 };
        function chunk() {
            var end = Math.min(i + 5, chars.length);
            for (; i < end; i++) fn(chars[i], tally);
            if (i < chars.length) {
                if (i - 50 * Math.floor(i / 50) === 0) say('progress: ' + i + '/' + chars.length);
                setTimeout(chunk, 150);
                return;
            }
            say(doneMsg(tally, chars.length));
        }
        chunk();
    }

    function apply() {
        eachCharacter(function (ch, tally) {
            var abs = findObjs({ _type: 'ability', _characterid: ch.id });
            if (!abs.length) { tally.noab++; return; }
            var attrs = attrsFor(ch.id);
            abs.forEach(function (ab) { tally[rewriteOne(ch, ab, attrs, false)]++; });
        }, function (t, n) {
            return '<b>done.</b> ' + n + ' characters | ' + t.ok + ' abilities rewritten | ' +
                   t.notbroken + ' already fine | ' + t.norow + ' had no matching row | ' +
                   t.noab + ' characters with no abilities' +
                   '<br>Select a token and click its actions to check.';
        });
    }

    function status() {
        var broken = 0, fixed = 0, chars = 0;
        findObjs({ _type: 'character' }).forEach(function (ch) {
            var abs = findObjs({ _type: 'ability', _characterid: ch.id });
            if (abs.length) chars++;
            abs.forEach(function (ab) {
                var a = String(ab.get('action') || '');
                if (a.indexOf('%{') === 0 && REF.test(a)) broken++; else if (a) fixed++;
            });
        });
        say('abilities: ' + broken + ' still broken, ' + fixed + ' rewritten, across ' +
            chars + ' characters with token actions.' +
            (state.LLFIX ? ' Originals kept for ' + Object.keys(state.LLFIX.orig).length + '.' : ''));
    }

    function revert() {
        var s = store(), n = 0;
        Object.keys(s.orig).forEach(function (id) {
            var ab = getObj('ability', id);
            if (ab) { ab.set('action', s.orig[id]); n++; }
        });
        s.orig = {};
        say('reverted ' + n + ' abilities to their original text.');
    }

    on('chat:message', function (msg) {
        if (msg.type !== 'api' || msg.content.indexOf('!llfix') !== 0) return;
        if (!playerIsGM(msg.playerid)) return;
        var a = msg.content.split(/\s+/);
        var rest = a.slice(2).join(' ');
        try {
        switch (a[1]) {
            case 'ping':
                var n = findObjs({ _type: 'character' }).length;
                var one = findObjs({ _type: 'character', name: 'Abyssal Giant Dire Frog' })[0];
                var na = one ? findObjs({ _type: 'ability', _characterid: one.id }).length : -1;
                say('pong. ' + n + ' characters; frog has ' + na + ' abilities findObjs can see.');
                break;
            case 'apply':  apply(); break;
            case 'status': status(); break;
            case 'revert': revert(); break;
            case 'test':
                var name = rest || 'Abyssal Giant Dire Frog';
                var ch = findObjs({ _type: 'character', name: name })[0];
                if (!ch) { say('no character named ' + name); break; }
                var abs = findObjs({ _type: 'ability', _characterid: ch.id });
                if (!abs.length) { say(name + ' has no abilities'); break; }
                var attrs = attrsFor(ch.id);
                var res = {};
                abs.forEach(function (ab, i) {
                    var r = rewriteOne(ch, ab, attrs, i === 1 || abs.length === 1);
                    res[r] = (res[r] || 0) + 1;
                });
                say('<b>' + name + '</b>: ' + JSON.stringify(res) +
                    '<br>Select its token and click each action.');
                break;
            default:
                say('!llfix ping | test [name] | apply | status | revert');
        }
        } catch (err) {
            log('LL_Fix ERROR on "' + msg.content + '": ' + err.message);
            log(err.stack);
            say('<b>error</b> running that command: ' + String(err.message).slice(0, 200));
        }
    });

    log('LL_Fix v3 ready.');
    say('LL_Fix <b>v3</b> loaded. <b>!llfix revert</b> first, then <b>!llfix test</b>, then <b>!llfix apply</b>.');
});
