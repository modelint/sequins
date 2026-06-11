# `.xcm` Executable Class Model — file format

Reference for reading/editing `.xcm` files (e.g. `documentation/models/sequins.xcm`).
The companion layout format (`.mls`) is **not** documented here — it is fully covered by the
Flatland wiki (see [Layout sheet (`.mls`)](#layout-sheet-mls-format) at the bottom).

## Overall structure

```
metadata
    <Item> : <value>
    <Item> > <image-prefix>
domain <Name>, <Alias>
subsystem <Name>, <Alias> <class-number-range>
class <Name>
attributes
    <Attr> : <Type> {tags}
    ...
--
... more class blocks ...
relationships
    <Rn>
    ...
--
... more relationship blocks ...
```

Blocks (class and relationship) are terminated by a line containing `--`.

## metadata

Key/value items. Two value operators:
- `:` — a literal value (`Version : 0.7.2`).
- `>` — an **image filename prefix**; resolves to a `.png` in `~/.config/mi-tablet/images/`
  (`Organization logo > mint` → `mint*.png`).

When updating a model, the only metadata normally edited are **`Version`** (bump patch level)
and **`Modification date`** (set to today, format `Month D, YYYY`).

## class blocks

```
class <Class Name>
attributes
    <Attribute Name> : <Type Name> [{tags}] [= <default>]
--
```

- Class/attribute/type names are multi-word and unquoted.
- `= <default>` gives an initial value (`Compressed : Boolean = True`).
- A class **requires at least one identifier**. Attribute order is not semantically
  significant; by convention front-load the primary-identifier attributes for readability.
- Types are currently free-form (no type-definition section); resolved elsewhere.

### Attribute tags `{...}` — comma-separated

| Tag | Meaning |
|-----|---------|
| `I`, `I2`, `I3`, … | Identifier membership (primary / secondary / …). One attribute may join several identifiers, and an identifier may span several attributes (composite). |
| `Rn` | Referential attribute formalizing relationship *n* (the foreign-key side). |
| `Rnc` | Referential for *n* **with an additional constraint** (documented on that relationship's wiki page). The `c` here is **not** "conditional". |
| `ORn` | Referential / ranking attribute for an **ordinal** relationship *n*. |

## Naming conventions (strict)

- **Type names** — initial uppercase, title-cased across words (`Element ID`, `Sequence Number`, `Rect Size`).
- **Enum type names** — when an enumerated type has no more than ~3–4 values, name the type by its
  value set joined with underscores (`Color_Position` for values `color`/`position`). The
  underscores are intentional and make the value set self-documenting.
- **Class names** — initial uppercase, title-cased (`Bounded String Material`, `Thread to Bead Gap`).
- **Attribute names** — single leading uppercase, remaining words lowercase
  (`Compressed depth`, `Slip knot blocking bead`, `From string`).
  Exception: acronyms / single-letter words stay uppercase even when not first
  (`ID`, `String ID`, `X`, `Y top`).

## relationships section

Opens with the `relationships` keyword; one `--`-terminated block per relationship.
A formalization line uses `->` meaning "**refers to / is constrained to match**", with the
**referencing** side on the left and the **referenced** (identifier) side on the right.
Composite keys are parenthesized: `Element.(Material, Curtain style) -> Material.(Name, Curtain style)`.

### Binary association
```
Rn
<verb phrase A>, <mult> <Class B>
<verb phrase B>, <mult> <Class A>
<referencing Class>.<attr> -> <referenced Class>.<attr>
```
Multiplicities: `1` exactly one, `M` many (`1..*`), `1c` zero-or-one (`0..1`),
`Mc` zero-or-more (`*`). The `c` = *conditional* only here in the Relationships section.

### Association with an association class
```
Rn
<verb phrase A>, <mult> <Class B>
<verb phrase B>, <mult> <Class A>
<assoc-class mult> <Assoc Class>
<Assoc Class>.<attr> -> <Class>.<attr>   (one line per formalized role)
```
**Shlaer-Mellor departure from UML:** the association class carries an *independent*
multiplicity — "for a given mapped pair of the two participants, how many association-class
instances exist."
- `1` — exactly one per mapped pair (the UML reading).
- `M` — a mapped pair may have several; the association class's **identifier must then gain an
  extra component** (an added discriminator folded into the composite, or a new identifier
  attribute) so the many instances are distinguishable.

### Generalization
```
Rn
<Superclass> +
    <Subclass>
    <Subclass>
<subclass>.<attr> -> <Superclass>.<attr>
```
The literal token `<subclass>` in the formalization line means "each subclass."

### Ordinal (`ORn`)
```
ORn
<phrase A> / <phrase B>, <Class>
<ranking attr> : <identifier>
```
- The **ranking attribute** is part or all of *some* identifier; its only hard constraint is
  that its **type must be ordered** (integer-like).
- If the ranking attribute is a *proper subset* of a composite identifier, the other
  component(s) partition the ordering into independent sequences. The composite identifier is
  itself the proof of scope: e.g. Bead's `{I2} = (String ID, Sequence)` requires both to
  identify a Bead, so `Sequence` ranks only *within* a `String ID` (per-string ordering).

## Layout sheet (`.mls`) format

The `.mls` layout grammar (nodes, connectors, stems, bends, tree/ternary connectors, header
keywords) is fully documented in the **Flatland wiki**:
`/Users/starr/SDEV/GitHub/flatland-model-diagram-editor.wiki`
(GitHub: `modelint/flatland-model-diagram-editor` wiki). Start at `connectors-section.md`,
`binary-connectors.md`, `tree-connectors.md`, `ternary-connector.md`, and `nodes-section.md`.

Sequins-local quick notes (not in the wiki):
- `<Class>/N` after a node name splits the displayed name across **N lines**.
- `>face` (`>top`/`>bottom`/`>left`/`>right`) **aligns** the node toward that face within its
  cell or spanned group; centered is the default.