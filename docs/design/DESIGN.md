---
name: Keitaro Wrapper
description: A quiet operational workspace for campaign drafts and explicit publication.
colors:
  paper: "#f5f6f3"
  surface: "#fff"
  ink: "#22342f"
  muted: "#586b64"
  line: "#d8dfd9"
  accent: "#285c46"
  accent-hover: "#1c4634"
  warn: "#805400"
  warn-bg: "#fff4d6"
  danger: "#9b3029"
  danger-bg: "#fff0ec"
  control-hover: "#edf1eb"
  field-border: "#b8c5bc"
  focus: "#c88a24"
  stream-heading: "#edf2ec"
typography:
  headline:
    fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "34px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "20px"
    fontWeight: 650
    lineHeight: 1.5
  stream-title:
    fontSize: "18px"
    fontWeight: 650
    lineHeight: 1.5
  body:
    fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.5
  metadata:
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  allocation:
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.5
rounded:
  control: "6px"
spacing:
  compact-gap: "8px"
  mobile-inset: "16px"
  panel-inset: "24px"
  workspace-inset: "28px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-danger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.danger}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 11px"
  create-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "24px"
  stream:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.control}"
  notice-warning:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn}"
    rounded: "{rounded.control}"
    padding: "14px 18px"
---

# Design System: Keitaro Wrapper

## Overview

**Creative North Star: "Operate — the operational log"**

Paper-like surfaces, green ink, ordered strips and a visible journal give campaign work the character of an operational record. Density serves comparison and repeated editing. Controls remain flat, with status expressed in words as well as color.

This is a code-derived system for a desktop-first operational application. The durable accessibility commitments in [PRODUCT.md](PRODUCT.md) are visible keyboard focus, labeled controls, narrow-screen adaptation and live status messages. Page composition is an expression of this system, not a compulsory template for every future surface.

**Key Characteristics:**
- Pale paper ground and white working surfaces.
- Green actions, amber changes and explicit text statuses.
- Compact sans-serif hierarchy with tabular allocation values.
- Flat controls, fine rules and ordered operational records.

Source of truth: [app.css](../../src/keitaro_wrapper/web/static/app.css), [index.html](../../src/keitaro_wrapper/web/templates/index.html) and [app.js](../../src/keitaro_wrapper/web/static/app.js). This records the implemented artifact, not an approved visual comp. The eleven colors from `paper` through `danger-bg` map directly to same-named CSS custom properties; `rounded.control` maps to `--radius`. The four remaining colors and all typography, spacing and component roles are extracted CSS literals, not additional named CSS tokens. The sidecar's synthesized tonal ramps are preview metadata, not an implemented palette scale.

## Colors

The palette uses subdued green neutrals with distinct amber and red operational states; exact primitives are in the frontmatter.

### Primary
- **Green ink** (`accent`): primary buttons, links, positive status text and allocation bars.
- **Deep green ink** (`accent-hover`): primary-button hover.

### Secondary
- **Amber ink and wash** (`warn`, `warn-bg`): changed streams, uncertain or unfinished operation statuses and reconciliation surfaces.
- **Red ink and wash** (`danger`, `danger-bg`): error notices and the manual-resolution action.

### Neutral
- **Paper** (`paper`) and **working white** (`surface`): page ground and work surfaces.
- **Dark green text** (`ink`), **muted green text** (`muted`) and **fine rule** (`line`): hierarchy and boundaries.
- **Control wash** (`control-hover`), **field edge** (`field-border`) and **stream heading wash** (`stream-heading`): extracted reusable literals.
- **Focus amber** (`focus`): keyboard focus, distinct from the muted operational warning color.

**The Written Status Rule.** Pair state color with explicit text; color alone must not communicate whether a stream has changes or an operation needs attention.

## Typography

**Body and heading font:** the shared sans-serif stack recorded in the frontmatter. Inter is preferred when installed; the implementation ships no font asset or remote font request. There is no separate display face or monospace family.

### Hierarchy
- **Headline:** campaign or page title; the recorded desktop size reduces to 28px at the narrow breakpoint.
- **Title:** section and creation-panel headings; stream headings use the smaller `stream-title` role.
- **Body:** ordinary controls and prose.
- **Label:** field labels; muted helper prose uses the same size with normal weight and, for form notes, 1.6 line-height.
- **Metadata:** identifiers, status-adjacent detail and footers. Table headings and offer-state annotations use an additional 11px literal.
- **Allocation:** traffic percentage; it reduces to 17px on narrow screens. Stream totals use a 20px literal.

**The Aligned Numbers Rule.** Use tabular numerals for stream IDs, offer IDs, traffic weights and totals so changes remain easy to compare.

## Layout

The workspace is centered with a maximum width of 1220px and desktop padding of 42px 28px 72px. The home screen uses a flexible campaign register beside a 340px creation panel, separated by 56px. The editor places its heading before ordered stream strips, their allocation tables and the operation journal. This describes the current surfaces rather than prescribing every future page.

At 900px and below, the home sidebar narrows to 310px, its gap becomes 28px, stream footers stack and heading actions become vertical. At 650px and below, the home screen becomes one column with a 36px gap, workspace padding becomes 28px 16px 48px, headings and stream headers stack, and stream actions share a row. The current narrow reference is 390px.

Tables preserve three semantic columns on narrow screens. Their first two widths change from 46% / 24% to 38% / 34%; padding contracts, offer names wrap, and pin controls wrap. Compact gaps, mobile insets and panel insets in the frontmatter are recurring extracted measures, not a newly imposed global spacing scale.

## Elevation & Depth

There are no shadows. White surfaces, pale heading bands, fine borders and the stronger campaign-register rule establish grouping. Keyboard focus uses a 3px amber outline offset by 3px; it is an accessibility state, not elevation.

**The Flat Record Rule.** Separate operational regions with surface tone and rules rather than floating-card shadows.

Motion is limited to state feedback: a changed stream heading moves from a brighter amber literal to the warning wash over 350ms with ease-out timing. This runs only when reduced motion is not requested. It does not establish an entrance or decorative animation vocabulary.

## Shapes

Controls, notices, stream containers and the creation panel share the recorded corner radius. Borders are generally 1px; the campaign-register section boundary is 2px. Stream containers clip their heading bands to the outer corners. Allocation progress is a thin 3px horizontal bar, subordinate to its numeric label. Status labels are plain text, not pills.

## Components

### Buttons

Primary green buttons identify publication and creation actions. Secondary buttons are white with fine borders. Text buttons retain the normal button dimensions but remove the visible border and fill; danger buttons use red text. All use a 40px minimum height, semibold text and the shared corner radius. Secondary hover uses the control wash; primary hover uses deep green. Text-button fill remains transparent on hover. Every variant inherits the visible focus outline.

Disabled buttons use muted literal fills and text with 0.75 opacity and a not-allowed cursor. These implementation state values are reproduced in sidecar snippets, not promoted into additional palette tokens. The disabled Fetch control has a contextual explanation connected with `aria-describedby`; creation unavailability is also explained beside its form.

### Inputs / Fields

Inputs, selects and textareas use white fill, a field-edge border, green caret, the shared radius and a 43px minimum height. Visible labels precede fields; helpers follow. The compact weight editor uses a 34px minimum height and narrower input. Native select and checkbox behavior is retained.

### Navigation

The brand returns to the campaign list. A simple back link returns from the editor. Campaign rows are full-row links, separated by fine rules and using the control wash on hover. The implementation has no tabs or sidebar navigation.

### Cards / Containers

The creation panel is a restrained bordered white container with the recorded panel inset, reduced to 20px on narrow screens. It is a working form, without illustration or decorative elevation.

### Stream strips and allocation table

Each stream groups a heading, ID, written state, Cancel / Push actions, offer rows and a total. Changed state uses an amber header and border. Offer rows show identity, numeric weight, the subordinate progress bar and the available action; inactive rows retain identity and status with reduced emphasis. Changes remain legible independently of the bar.

### Notices and operation journal

Notices group the message and any next action in a colored, bordered region. Error and warning roles use the corresponding frontmatter pairs; the success notice currently uses its own literal green wash and text. The journal is a vertical sequence of ruled articles, with text statuses, IDs and conditional reconciliation actions. Manual review expands inline into an amber form.

## Do's and Don'ts

### Do:
- Do pair state color with explicit status text.
- Do preserve tabular numbers for allocation and identifiers.
- Do keep keyboard focus visible and connect unavailable actions to useful explanations.
- Do use flat surfaces and fine rules to organize operational work.

### Don't:
- Don't turn text status labels into decorative badges without a product need.
- Don't add marketing imagery or a display-type hierarchy to operational forms.
- Don't add ornamental or entrance animation; retain the reduced-motion gate for changed-state feedback.
- Don't treat synthesized sidecar tonal ramps as shipped CSS tokens.
