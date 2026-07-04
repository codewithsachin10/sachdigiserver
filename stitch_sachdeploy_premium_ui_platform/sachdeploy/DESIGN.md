---
name: SachDeploy
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191b23'
  surface-container: '#1d2027'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e1e2ec'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e1e2ec'
  inverse-on-surface: '#2e3038'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#c0c6db'
  on-secondary: '#293040'
  secondary-container: '#404758'
  on-secondary-container: '#aeb5c9'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#dce2f7'
  secondary-fixed-dim: '#c0c6db'
  on-secondary-fixed: '#141b2b'
  on-secondary-fixed-variant: '#404758'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#10131a'
  on-background: '#e1e2ec'
  surface-variant: '#32353c'
typography:
  display-xl:
    fontFamily: Geist
    fontSize: 64px
    fontWeight: '700'
    lineHeight: 72px
    letterSpacing: -0.04em
  headline-lg:
    fontFamily: Geist
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.03em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  title-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  label-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  stack-sm: 12px
  stack-md: 24px
  stack-lg: 48px
  section-gap: 96px
---

## Brand & Style
The design system is engineered for a premium, enterprise-grade cloud deployment experience. It communicates technical mastery, reliability, and "developer-first" luxury. The aesthetic is rooted in **Modern Minimalism** with a heavy influence from **Glassmorphism**, aiming for the high-fidelity polish seen in industry-leading platforms like Vercel and Apple.

The experience should feel expansive and breathable, utilizing high-contrast typography against deep obsidian surfaces. Visual hierarchy is established through translucent layering, subtle refractive indices, and ultra-soft ambient shadows that give the UI a sense of physical weightlessness and depth.

## Colors
This design system utilizes a "Dark Mode First" palette. The core is built on `#09090B`, a deep charcoal-black that provides the infinite-canvas feel required for high-contrast glass effects.

- **Primary Accent:** Blue (`#3B82F6`) is used sparingly for primary actions, progress indicators, and focus states.
- **Surface Layering:** Cards and modals use `#18181B` with varying levels of opacity to allow backdrop blurs to resolve clearly.
- **Borders:** Borders are never solid; they are consistently `rgba(255,255,255,0.08)`, acting as "light-catching" edges rather than structural dividers.
- **Semantic Colors:** Success, Warning, and Danger colors are saturated and vibrant to ensure they pierce through the dark interface during critical deployment events.

## Typography
The typography system balances the technical precision of **Geist** for headings and **JetBrains Mono** for technical data, with the ubiquitous readability of **Inter** for body copy.

- **Headings:** Should use tight letter-spacing (`-0.02em` to `-0.04em`) to create a compact, modern editorial look.
- **Hierarchy:** Use white (`#FFFFFF`) for all headlines and titles. Move to `Gray-400` (`#A1A1AA`) for body text to reduce eye strain and emphasize primary content.
- **Code & Logs:** All terminal outputs, environment variables, and deployment logs must use JetBrains Mono to ensure character distinctness (0 vs O, l vs 1).

## Layout & Spacing
This design system employs a **Fixed Grid** philosophy for dashboard content, centered on a 1280px max-width container, while utilizing a **Fluid Grid** for the marketing and onboarding flows.

- **Rhythm:** A 4px baseline grid ensures mathematical consistency.
- **Generous White Space:** Sections are separated by large gaps (`96px`) to reinforce the premium, "un-cluttered" feel. 
- **Responsive Behavior:** 
  - **Desktop:** 12-column grid, 24px gutters.
  - **Tablet:** 8-column grid, 20px gutters.
  - **Mobile:** 4-column grid, 16px margins.
- **Safe Areas:** Cards and glass containers should maintain a minimum of `32px` internal padding to ensure content feels framed rather than squeezed.

## Elevation & Depth
Depth in the design system is achieved through "Optical Layering" rather than traditional heavy drop shadows.

- **Backdrop Blur:** All floating surfaces (modals, dropdowns, navigation bars) must apply a `blur(12px)` to the background. 
- **Shadows:** Use large-radius, ultra-low opacity shadows: `0 20px 40px rgba(0,0,0,0.4)`. The shadow should feel like a soft ambient occlusion rather than a hard edge.
- **The "Inner Glow":** To simulate glass thickness, apply a subtle 1px inner border using `rgba(255,255,255,0.05)` on the top and left edges of cards.
- **Z-Index Tiers:**
  - `Base`: #09090B
  - `Surface`: #18181B (Flat)
  - `Float`: #18181B + Blur + Shadow (Cards, Popovers)
  - `Overlay`: Semi-transparent black + Heavy blur (Modals)

## Shapes
The design system uses a **Highly Rounded** shape language to soften the technical nature of cloud infrastructure.

- **Primary Radius:** Cards and main containers use a `24px` (2xl) or `32px` (3xl) radius.
- **Component Radius:** Buttons and input fields use a more controlled `10px` to `12px` radius to maintain a professional, sharp tool-like appearance within the soft containers.
- **Consistency:** Never mix sharp corners with rounded ones. Even "terminal" windows should have a minimum `12px` radius to remain consistent with the premium aesthetic.

## Components

### Buttons
- **Primary:** Background of `#3B82F6`, white text. On hover, apply a subtle outer glow (`box-shadow: 0 0 20px rgba(59, 130, 246, 0.4)`) and `scale(1.02)`.
- **Glass (Secondary):** Background `rgba(255,255,255,0.03)`, backdrop-filter `blur(8px)`, border `rgba(255,255,255,0.08)`. 
- **Interactions:** All buttons should use a `200ms ease-out` transition for scale and shadow transforms.

### Cards
- **Construction:** Background `#18181B` at `80%` opacity, `1px` border `rgba(255,255,255,0.08)`, and `24px` corner radius.
- **Hover:** Increase border opacity to `0.2` and slightly lift the card via a negative Y-translation.

### Input Fields
- **Default:** Dark background with a subtle inset shadow.
- **Focus:** The border transitions to `#3B82F6` and a soft blue outer glow is applied (`0 0 0 4px rgba(59, 130, 246, 0.15)`).
- **Typography:** Use JetBrains Mono for inputs that require technical precision (e.g., Repo URLs, Environment Variable keys).

### Status Chips
- Small, pill-shaped indicators with a low-opacity background of the status color (e.g., `rgba(34, 197, 94, 0.1)`) and a solid text color. Include a small pulsing dot for "Live" or "Building" states.

### Terminal / Log Viewer
- Use a solid `#000000` background to differentiate from the `#09090B` UI.
- Use `code-md` typography.
- Syntax highlighting should follow a "Sublime" or "One Dark" inspired scheme for maximum readability.