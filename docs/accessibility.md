# Accessibility Standards

Accessibility (a11y) guidelines for Nedlia's web portal to ensure usability for all users.

## Principles

1. **Perceivable**: Information must be presentable in ways users can perceive
2. **Operable**: UI components must be operable by all users
3. **Understandable**: Information and UI operation must be understandable
4. **Robust**: Content must be robust enough for assistive technologies

---

## Compliance Target

**WCAG 2.1 Level AA** – Required for all user-facing features.

---

## Quick Reference

| Requirement                 | Standard                 | How to Test                    |
| --------------------------- | ------------------------ | ------------------------------ |
| Color contrast (text)       | 4.5:1 minimum            | Browser DevTools, axe          |
| Color contrast (large text) | 3:1 minimum              | Browser DevTools, axe          |
| Keyboard navigation         | All interactive elements | Tab through page               |
| Focus indicators            | Visible focus            | Tab through page               |
| Alt text for images         | Descriptive              | Screen reader, HTML inspection |
| Form labels                 | Associated               | Screen reader, HTML inspection |
| Error messages              | Clear, associated        | Form validation test           |
| Skip links                  | Present                  | Tab from page start            |

---

## Semantic HTML

### Use Correct Elements

```tsx
// ❌ Bad: Div with click handler
<div onClick={handleClick} className="button">
  Submit
</div>

// ✅ Good: Semantic button
<button onClick={handleClick} type="submit">
  Submit
</button>


// ❌ Bad: Styled span for navigation
<span className="nav-link" onClick={() => navigate('/home')}>
  Home
</span>

// ✅ Good: Anchor or Link component
<Link to="/home">Home</Link>


// ❌ Bad: Generic divs for structure
<div className="header">
  <div className="nav">...</div>
</div>

// ✅ Good: Semantic landmarks
<header>
  <nav aria-label="Main navigation">...</nav>
</header>
<main>...</main>
<footer>...</footer>
```

### Heading Hierarchy

```tsx
// ❌ Bad: Skipped heading levels
<h1>Dashboard</h1>
<h3>Recent Placements</h3>  {/* Skipped h2! */}
<h5>Placement Details</h5>  {/* Skipped h4! */}

// ✅ Good: Sequential heading levels
<h1>Dashboard</h1>
<h2>Recent Placements</h2>
<h3>Placement Details</h3>
```

---

## Keyboard Navigation

### Focus Management

```tsx
// Ensure all interactive elements are focusable
<button>Click me</button>  {/* Naturally focusable */}
<a href="/page">Link</a>   {/* Naturally focusable */}

// For custom interactive elements, add tabIndex
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
>
  Custom Button
</div>
```

### Focus Indicators

```css
/* Never remove focus outlines without replacement */
/* ❌ Bad */
*:focus {
  outline: none;
}

/* ✅ Good: Custom focus indicator */
*:focus-visible {
  outline: 2px solid #4f46e5;
  outline-offset: 2px;
}

/* Or use Tailwind */
.focus-visible:ring-2 .focus-visible:ring-indigo-500 .focus-visible:ring-offset-2
```

### Skip Links

```tsx
// Add skip link at the start of the page
function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:text-black"
      >
        Skip to main content
      </a>
      <Header />
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <Footer />
    </>
  );
}
```

### Keyboard Shortcuts

```tsx
// Document keyboard shortcuts
function KeyboardShortcuts() {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Cmd/Ctrl + K for search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        openSearch();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return null;
}

// Provide keyboard shortcut help
<button aria-label="Search (Cmd+K)">Search</button>;
```

---

## ARIA Attributes

### When to Use ARIA

1. **First**: Use semantic HTML
2. **Second**: Add ARIA only when HTML semantics are insufficient

```tsx
// ❌ Bad: ARIA on semantic element (redundant)
<button role="button" aria-pressed="false">
  Click
</button>

// ✅ Good: ARIA for custom components
<div
  role="switch"
  aria-checked={isOn}
  aria-label="Enable notifications"
  tabIndex={0}
  onClick={toggle}
  onKeyDown={(e) => e.key === 'Enter' && toggle()}
>
  <span className={isOn ? 'on' : 'off'} />
</div>
```

### Common ARIA Patterns

```tsx
// Expandable content
<button
  aria-expanded={isOpen}
  aria-controls="panel-content"
  onClick={() => setIsOpen(!isOpen)}
>
  {isOpen ? 'Collapse' : 'Expand'}
</button>
<div id="panel-content" hidden={!isOpen}>
  Panel content
</div>

// Loading states
<button disabled={isLoading} aria-busy={isLoading}>
  {isLoading ? 'Saving...' : 'Save'}
</button>

// Live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

// Dialogs
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
>
  <h2 id="dialog-title">Confirm Delete</h2>
  <p id="dialog-description">Are you sure you want to delete this placement?</p>
</div>
```

---

## Forms

### Labels

```tsx
// ❌ Bad: No label association
<label>Email</label>
<input type="email" />

// ✅ Good: Explicit association
<label htmlFor="email">Email</label>
<input type="email" id="email" />

// ✅ Good: Implicit association
<label>
  Email
  <input type="email" />
</label>

// For icon-only inputs, use aria-label
<input
  type="search"
  aria-label="Search placements"
  placeholder="Search..."
/>
```

### Error Messages

```tsx
function FormField({ error, ...props }: FormFieldProps) {
  const errorId = `${props.id}-error`;

  return (
    <div>
      <label htmlFor={props.id}>{props.label}</label>
      <input {...props} aria-invalid={!!error} aria-describedby={error ? errorId : undefined} />
      {error && (
        <span id={errorId} role="alert" className="text-red-600">
          {error}
        </span>
      )}
    </div>
  );
}
```

### Required Fields

```tsx
<label htmlFor="name">
  Name <span aria-hidden="true">*</span>
  <span className="sr-only">(required)</span>
</label>
<input
  type="text"
  id="name"
  required
  aria-required="true"
/>
```

---

## Images and Media

### Alt Text

```tsx
// Informative images: Describe the content
<img src="/chart.png" alt="Bar chart showing 50% increase in placements this month" />

// Decorative images: Empty alt
<img src="/decorative-border.png" alt="" role="presentation" />

// Complex images: Provide detailed description
<figure>
  <img src="/workflow.png" alt="Placement workflow diagram" aria-describedby="workflow-desc" />
  <figcaption id="workflow-desc">
    The workflow starts with video upload, then placement creation,
    validation, and finally publishing.
  </figcaption>
</figure>
```

### Video

```tsx
<video controls>
  <source src="/demo.mp4" type="video/mp4" />
  <track kind="captions" src="/demo-captions.vtt" srclang="en" label="English" />
  <track kind="descriptions" src="/demo-descriptions.vtt" srclang="en" label="Audio descriptions" />
  Your browser does not support video.
</video>
```

---

## Color and Contrast

### Color Contrast

```css
/* ❌ Bad: Low contrast */
.text-light {
  color: #999999; /* 2.8:1 on white - fails AA */
  background: white;
}

/* ✅ Good: Sufficient contrast */
.text-accessible {
  color: #595959; /* 7:1 on white - passes AAA */
  background: white;
}
```

### Don't Rely on Color Alone

```tsx
// ❌ Bad: Status indicated only by color
<span className={status === 'error' ? 'text-red-500' : 'text-green-500'}>
  {status}
</span>

// ✅ Good: Color + icon + text
<span className={status === 'error' ? 'text-red-500' : 'text-green-500'}>
  {status === 'error' ? <XIcon aria-hidden /> : <CheckIcon aria-hidden />}
  {status === 'error' ? 'Failed' : 'Success'}
</span>
```

---

## Component Patterns

### Modal Dialog

```tsx
function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const titleId = useId();
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      previousFocus.current = document.activeElement as HTMLElement;
      // Focus first focusable element in modal
    } else {
      previousFocus.current?.focus();
    }
  }, [isOpen]);

  // Trap focus within modal
  // Close on Escape key

  if (!isOpen) return null;

  return (
    <div role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <h2 id={titleId}>{title}</h2>
      {children}
      <button onClick={onClose}>Close</button>
    </div>
  );
}
```

### Tabs

```tsx
function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div>
      <div role="tablist" aria-label="Content tabs">
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map(tab => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={activeTab !== tab.id}
          tabIndex={0}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
```

---

## Testing

### Automated Testing

```bash
# Install axe-core for React
npm install @axe-core/react --save-dev
```

```tsx
// src/index.tsx (development only)
if (process.env.NODE_ENV === 'development') {
  import('@axe-core/react').then(axe => {
    axe.default(React, ReactDOM, 1000);
  });
}
```

### Manual Testing Checklist

- [ ] Navigate entire page using only keyboard
- [ ] Test with screen reader (VoiceOver, NVDA)
- [ ] Zoom to 200% - content still usable
- [ ] Test with high contrast mode
- [ ] Verify focus order is logical
- [ ] Check all images have appropriate alt text
- [ ] Verify form errors are announced

### Testing Tools

| Tool              | Purpose                       |
| ----------------- | ----------------------------- |
| axe DevTools      | Browser extension for audits  |
| Lighthouse        | Chrome DevTools accessibility |
| WAVE              | Web accessibility evaluator   |
| VoiceOver (macOS) | Screen reader testing         |
| NVDA (Windows)    | Screen reader testing         |
| Contrast Checker  | Color contrast validation     |

---

## Related Documentation

- [TypeScript Style Guide](typescript-style-guide.md) – React patterns
- [Testing Strategy](testing-strategy.md) – Accessibility testing
