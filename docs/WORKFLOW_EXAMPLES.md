# Workflow Examples

## Example 1: Simple Text Change

### WhatsApp Message
```
Change the hero button to say "Book a Free Audit"
```

### Generated Task (CHANGE.json)
```json
{
  "id": "abc12345",
  "type": "copy_change",
  "description": "Change the hero button to say 'Book a Free Audit'",
  "scope": ["app/components/Hero.tsx"],
  "rules": [
    "Do not change layout structure",
    "Do not remove existing functionality",
    "Preserve all existing imports",
    "Only modify text content",
    "Do not touch styles or classes",
    "Keep the same element types"
  ],
  "auto_commit": true
}
```

### Copilot Prompt
```
Apply the following change strictly:

## Task Type
copy_change

## Description
Change the hero button to say 'Book a Free Audit'

## Target Files (ONLY modify these)
- app/components/Hero.tsx

## Rules (MUST follow)
- Do not change layout structure
- Do not remove existing functionality
- Preserve all existing imports
- Only modify text content
- Do not touch styles or classes
- Keep the same element types

## Important
- Make ONLY the requested change
- Do NOT modify any other code
- Do NOT change layout or structure unless explicitly requested
- Preserve all existing functionality
- Keep the same code style and formatting

Please apply this change now.
```

### Result
- Copilot changes `<Button>Get Started</Button>` to `<Button>Book a Free Audit</Button>`
- Auto-commits: `🤖 Auto: Change the hero button to say 'Book a Free Audit'`
- Pushes to origin
- Vercel auto-deploys

---

## Example 2: SEO Update

### WhatsApp Message
```
Update the SEO title to "Premium Digital Marketing | YourBrand"
```

### Generated Task
```json
{
  "id": "def67890",
  "type": "seo_update",
  "description": "Update the SEO title to 'Premium Digital Marketing | YourBrand'",
  "scope": ["app/layout.tsx"],
  "rules": [
    "Only modify meta tags",
    "Keep valid HTML structure",
    "Do not change page content"
  ],
  "auto_commit": true
}
```

---

## Example 3: Color Change

### WhatsApp Message
```
Change the primary button color to #2563eb
```

### Generated Task
```json
{
  "id": "ghi11111",
  "type": "color_change",
  "description": "Change the primary button color to #2563eb",
  "scope": ["tailwind.config.ts"],
  "rules": [
    "Only modify color values",
    "Keep the same variable names",
    "Do not change other style properties"
  ],
  "auto_commit": true
}
```

---

## Example 4: Complex Change (Manual Review)

### WhatsApp Message
```
Add a new testimonials section below the features section
```

### Generated Task
```json
{
  "id": "jkl22222",
  "type": "component_edit",
  "description": "Add a new testimonials section below the features section",
  "scope": ["app/page.tsx", "app/components/Testimonials.tsx"],
  "rules": [
    "Do not change layout structure",
    "Do not remove existing functionality",
    "Preserve all existing imports"
  ],
  "auto_commit": false
}
```

**Note**: `auto_commit: false` because this is a structural change that requires manual review.

---

## Safety Checks

### Auto-commit is ALLOWED when:
- Task type is: `copy_change`, `color_change`, or `seo_update`
- All changed files match safe patterns (*.tsx, *.ts, *.css, *.json, *.md)
- Diff is less than 50 lines
- Only files in `scope` are modified

### Auto-commit is BLOCKED when:
- Task type is: `component_edit`, `section_reorder`, `add_content`
- Files outside `scope` are modified
- Diff exceeds 50 lines
- Unexpected files are created

### When blocked:
1. Task status set to `manual_review`
2. Notification sent to WhatsApp
3. User must manually review and commit
