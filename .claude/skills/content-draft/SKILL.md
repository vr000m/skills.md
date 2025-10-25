---
name: content-draft
description: This skill should be used when the user asks to "draft a TIL from this session", "write up what we just did", "turn this into a blog post", "summarise this session as a TIL", "create a TIL from this work", or wants to generate written content from the current Claude session context.
argument-hint: [--type til|blog] [--title "optional title"]
---

# Content Draft Skill

Draft a TIL or blog post from the current Claude Code session context.

## Usage

- `/content-draft` — Draft a TIL (default) from the current session
- `/content-draft --type blog` — Draft a full blog post from the current session
- `/content-draft --type til --title "Building content skills for Claude Code"` — Draft with a specific title

## Phase 1: Determine Content Type

Default to `til` unless the user specifies `--type blog` or the session clearly covered enough ground for a full blog post (multiple phases, architectural decisions, significant implementation). Print the chosen type and ask to confirm:

```
Drafting as: TIL (Today I Learned)
Title suggestion: "Creating custom Claude Code skills for content review"
Proceed? (y/n/change to blog)
```

## Phase 2: Gather Session Context

Summarise what was accomplished in the current session. Extract:

- **Problem/goal**: What was the user trying to achieve?
- **Tools and technologies**: What was used (languages, frameworks, tools, services)?
- **Approach and key decisions**: What choices were made and why?
- **Outcome**: What was the result? Did it work? What does it look like?
- **Rough edges**: Any surprises, gotchas, limitations, or things that didn't work?
- **Learnings**: What was non-obvious or worth sharing?

Present this summary and ask the user to confirm or adjust before drafting.

## Phase 3: Draft Content

Generate a draft following these rules:

### For TILs

- **Frontmatter**:
  ```yaml
  ---
  title: 'Descriptive TIL title'
  published_date: 'YYYY-MM-DD'
  status: 'draft'
  ---
  ```
- **Body**: Concise, focused on the learning. Use flowing prose (not bullet lists, unless it's a collection of distinct unrelated ideas).
- **Code examples**: Include relevant code snippets with language identifiers. Ensure code-prose consistency and cross-block identifier consistency.
- **Close**: End with a forward-looking sentence (not a bare code block, bullet list, or link).
- **Length**: Keep it short — TILs are quick reads.

### For Blog Posts

- **Frontmatter**:
  ```yaml
  ---
  title: 'Blog Post Title'
  slug: 'url-slug-here'
  excerpt: '150-160 character description for SEO and social sharing'
  published_date: 'YYYY-MM-DD'
  status: 'draft'
  category: 'Engineering'
  tags: ['tag1', 'tag2', 'tag3']
  authors: ['Varun Singh']
  ---
  ```
- **TL;DR**: Bolded, 1-2 sentences summarising the key message.
- **Hook**: Opening paragraph that sets context or presents a problem. Keep it focused — don't cram multiple links and technical details into the opener.
- **Structure**: H2 for main sections, H3 for subsections. Follow the content-type structure:
  - Technical Deep Dive: Problem -> Analysis -> Solution -> Implementation -> Results
  - Tutorial: Prerequisites -> Step-by-step -> Troubleshooting -> Next Steps
  - Industry Analysis: Context -> Trend Analysis -> Implications -> Predictions
  - Opinion: Thesis -> Supporting Evidence -> Counter-arguments -> Conclusion
- **Close**: Synthesis and forward-looking statement.
- **Length**: 800-1,500 words (or content-type-specific range).

### Style Rules (Both Types)

- **British English** for all content (optimise, realise, behaviour)
- **American English** for slugs and filenames (for SEO)
- **Oxford comma** in all lists
- **Active voice** preferred
- **No comma splices**
- **No bullet lists in body** (except intro outlines, summaries, and tutorial steps)
- **Show the result** — don't just describe process, tell the reader what happened
- **Deliver on the title** — body must fulfil the promise the title makes
- **Include rough edges** — mention limitations and caveats for credibility
- **Attribute references** — link to external sources
- **Technical terms in backticks** — filenames, functions, CLI commands, env vars

## Phase 4: Present Draft

Show the complete draft in the conversation as a markdown code block. Do NOT write to a file unless the user explicitly asks.

## Phase 5: Offer Next Steps

After presenting the draft, offer:

1. **Save to file** — Suggest the appropriate path:
   - TIL: `content/til/{tag}/{slug}.md` (ask which tag directory)
   - Blog: `content/blog/YYYY/{slug}.md`
2. **Run /content-review** — Chain with the review skill to check the draft against the full checklist
3. **Revise** — Adjust tone, length, focus, or structure based on feedback
4. **Change type** — Convert between TIL and blog post

## Key Principles

- The draft skill generates content; the review skill checks it. They chain naturally.
- Present the session summary for user confirmation before drafting — don't assume context is complete.
- Always produce `status: 'draft'` in frontmatter. The user publishes when ready.
- Never write to files without explicit permission.
- When working in the varunsingh.net repo, the project's `.claude/content-guidelines.md` provides additional context. Outside that repo, the style rules embedded above are sufficient.
