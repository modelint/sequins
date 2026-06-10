# `.mls` Edit Commands

Named, repeatable editing operations on Flatland layout (`.mls`) files
(e.g. `documentation/models/sequins.mls`). Leon invokes a command by name plus the
connector(s)/node(s) it applies to; this file is the portable record of what each does.
**We add to this list over time.**

For the underlying `.mls` grammar see the Flatland wiki (pointer in
`documentation/notation/xcm-format.md`). The commands here are shorthand for common
edits, not new syntax.

---

## Connector line anatomy (reference)

```
<±>R<n>[.<priority>] : <stem> : <stem>[, <stem>] [: <bends>]
```

Each **stem**:
```
<±>/<wrap> <face>[<pos>][*]|<Class Name>
```
- Leading `<±>` on the connector name = which side of the connector line the **relationship
  name** (e.g. `R16`) sits.
- Leading `<±>` on a stem (before `/`) = which side the **stem name** (verb phrase) sits.
- `<wrap>` = name wrap count; `<face>` = `t|b|l|r`; `<pos>` = `* +1 +2 -1 -2`
  (`*` floating); `*` after the face marks the floating/anchor stem.

---

## Commands

### `swap sides`

**Usage:** `swap sides R16` &nbsp;·&nbsp; multiple: `swap sides R16, R18, R21`

Flip the connector name **and** every stem name to the opposite side of the line — i.e.
toggle the leading `±` sign on the connector name and the leading `±` sign on each stem.
Nothing else changes (wrap counts, faces, positions, `*`, class names, bends all stay put).

Toggle rule: `-` ⇄ `+`.

**Example**

Before:
```
-R16 : +/2 t*|Canvas : +/2 b-2|Diagram Theme
```
After `swap sides R16`:
```
+R16 : -/2 t*|Canvas : -/2 b-2|Diagram Theme
```
