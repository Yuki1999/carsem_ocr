# Frontend Workspace UX Refresh Design

## Goal

Refresh the frontend into a more modern, friendly, and operationally efficient customs-document workspace without changing the backend APIs or adding UI dependencies.

## Product Direction

This is an internal operations tool, not a marketing site. The UI should feel calm, dense, scannable, and reliable. Visual emphasis should help users move through the workflow:

```text
Template setup -> Extract upload -> Task/history review -> Evidence check -> Customs draft review -> Submit
```

## Scope

- Keep Vue 3 + Element Plus.
- Keep the existing navigation sections and backend behavior.
- Improve the shell, navigation, cards, upload area, task/history list, result workspace, review states, and form ergonomics.
- Improve responsive behavior for tablet and mobile.
- Avoid new design frameworks, large dependencies, decorative orbs, and one-note palettes.

## UX Changes

- Replace the heavy dark sidebar look with a cleaner operational rail and clearer active states.
- Add a compact top context bar with current vendor, doc type, model, and automation state.
- Make section headers smaller and more work-focused.
- Make upload and task cards feel like action surfaces with strong loading and hover states.
- Make result and review areas easier to scan with stable cards, better spacing, and clearer warning states.
- Ensure long field names and values wrap instead of overflowing.
- Keep touch targets at least 44px where practical.
- Respect reduced motion.

## Visual System

- Neutral light workspace background.
- Use slate/blue-gray as structural color, teal for primary actions, green for success, amber for review/warning, red for destructive actions.
- Use 8px border radius for cards and controls where possible.
- Use restrained shadows and stronger borders for depth.
- Avoid large hero treatment inside dashboard pages.

## Testing

- Add focused tests for UI summary helpers where behavior changes.
- Run existing Vitest suite and production build.
- Use browser screenshots at desktop and mobile widths to catch layout regressions.
