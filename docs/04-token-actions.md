# 4. Token actions

**Run this after the NPC import. Nothing else works until you do.**

```
!llfix test          # one character, verbosely
!llfix apply         # all of them
!llfix status        # how many still hold the broken form
!llfix revert        # put the originals back
```

`LL_Fix.js` ships ready to use — it carries no generated data and reads
everything it needs off the characters at runtime. Paste it into Mods as-is.

## What is broken and why

The importer creates token actions that look like this:

```
%{Abyssal Giant Dire Frog|repeating_npcaction_-1VBFcAFFauQDzOrQUqA_rollbase}
```

`%{...}` is an **ability** call. It can only find abilities. But `rollbase` is an
**attribute** on the repeating row, so Roll20 never finds it and you get:

```
No ability was found for %{... |repeating_npcaction_rollbase}
```

The documented index form, `repeating_npcaction_$0_rollbase`, fails the same way
— `%{}` strips the `$0` before looking anything up.

There is a second, nastier failure underneath. If the call *does* resolve, the
row's `rollbase` is written with row-relative references:

```
@{wtype}&{template:npcfullatk} {{rname=@{name}}} {{r1=[[@{d20}+(@{attack_tohit}+0)]]}}
```

`@{name}` and `@{attack_tohit}` only mean *this row's* values inside the row's
context. Called from outside, they fall through to the character's global
namespace — so every action on the sheet rolls the same attack. Clicking
Multiattack produces a Bite.

## The fix

`LL_Fix.js` copies each row's `rollbase` **into** the ability and rewrites every
row-relative reference to its fully-qualified attribute name:

```
{{rname=@{name}}}  ->  {{rname=@{repeating_npcaction_-1VBFcAFFauQDzOrQUqA_name}}}
```

Fully-qualified attribute names are plain lookups — no row context needed, so
they resolve anywhere. Character-level references (`@{wtype}`, `@{d20}`,
`@{rtype}`) are left alone because those are already correct.

It also repoints the template's description field. The sheet passes
`{{description=@{show_desc}}}`, and `show_desc` is a flag whose value is the
literal `1` — so the roll prints "1" where the text belongs, and
description-only actions show nothing. It is repointed at the row's real
`description`.

Optional row fields the rollbase mentions but the row lacks (`attack_damage2`
and friends) are created empty, so a qualified reference resolves to blank
instead of erroring.

## Checking it worked

After `!llfix test`, select the character's token and click every action button.
Each should show **its own name** in the template header and roll its own
numbers. All five showing the same attack means the fix has not applied.

## Notes

- Only abilities still holding the broken `%{...}` form are rewritten. Already
  fixed ones are skipped — so if you need to re-run after a change, `!llfix
  revert` first.
- Originals are kept in `state`, so `revert` survives a sandbox restart.
