# Internationalization (i18n)

Internationalization patterns for Nedlia's web portal to support multiple languages and locales.

## Principles

1. **Externalize Strings**: No hardcoded user-facing text
2. **Design for Expansion**: Text may be 30-50% longer in other languages
3. **Locale-Aware Formatting**: Dates, numbers, currencies
4. **RTL Support**: Design for right-to-left languages
5. **Cultural Sensitivity**: Icons, colors, imagery may have different meanings

---

## Supported Locales

| Locale | Language     | Status  |
| ------ | ------------ | ------- |
| en-US  | English (US) | Default |
| en-GB  | English (UK) | Planned |
| es     | Spanish      | Planned |
| fr     | French       | Planned |
| de     | German       | Planned |
| ja     | Japanese     | Planned |

---

## Implementation

### Library: react-i18next

```bash
npm install i18next react-i18next i18next-browser-languagedetector
```

### Configuration

```typescript
// src/i18n/config.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from './locales/en.json';
import es from './locales/es.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      es: { translation: es },
    },
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes
    },
    detection: {
      order: ['querystring', 'localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;
```

### Translation Files

```json
// src/i18n/locales/en.json
{
  "common": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "loading": "Loading...",
    "error": "An error occurred"
  },
  "placements": {
    "title": "Placements",
    "create": "Create Placement",
    "edit": "Edit Placement",
    "delete_confirm": "Are you sure you want to delete this placement?",
    "status": {
      "draft": "Draft",
      "active": "Active",
      "archived": "Archived"
    },
    "fields": {
      "start_time": "Start Time",
      "end_time": "End Time",
      "description": "Description"
    },
    "validation": {
      "time_range_invalid": "End time must be after start time",
      "description_required": "Description is required"
    }
  },
  "errors": {
    "not_found": "{{resource}} not found",
    "unauthorized": "Please log in to continue",
    "rate_limited": "Too many requests. Please try again in {{seconds}} seconds."
  }
}
```

```json
// src/i18n/locales/es.json
{
  "common": {
    "save": "Guardar",
    "cancel": "Cancelar",
    "delete": "Eliminar",
    "loading": "Cargando...",
    "error": "Ocurrió un error"
  },
  "placements": {
    "title": "Colocaciones",
    "create": "Crear Colocación",
    "edit": "Editar Colocación",
    "delete_confirm": "¿Está seguro de que desea eliminar esta colocación?",
    "status": {
      "draft": "Borrador",
      "active": "Activo",
      "archived": "Archivado"
    }
  }
}
```

---

## Usage

### Basic Translation

```tsx
import { useTranslation } from 'react-i18next';

function PlacementList() {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('placements.title')}</h1>
      <button>{t('placements.create')}</button>
    </div>
  );
}
```

### Interpolation

```tsx
// Translation: "Are you sure you want to delete {{name}}?"
<p>{t('placements.delete_confirm_named', { name: placement.name })}</p>

// Translation: "Showing {{count}} of {{total}} placements"
<p>{t('placements.showing', { count: items.length, total: totalCount })}</p>
```

### Pluralization

```json
{
  "placements": {
    "count_zero": "No placements",
    "count_one": "{{count}} placement",
    "count_other": "{{count}} placements"
  }
}
```

```tsx
<p>{t('placements.count', { count: placements.length })}</p>
// count=0: "No placements"
// count=1: "1 placement"
// count=5: "5 placements"
```

### Nested Keys

```tsx
// Access nested translations
{
  t('placements.status.active');
} // "Active"
{
  t('placements.fields.start_time');
} // "Start Time"
```

### Trans Component (Rich Text)

```tsx
import { Trans } from 'react-i18next';

// Translation: "Read our <link>terms of service</link> for more information."
<Trans i18nKey="legal.terms_link">
  Read our <a href="/terms">terms of service</a> for more information.
</Trans>;
```

---

## Date and Number Formatting

### Dates

```tsx
import { useTranslation } from 'react-i18next';

function FormattedDate({ date }: { date: Date }) {
  const { i18n } = useTranslation();

  const formatted = new Intl.DateTimeFormat(i18n.language, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);

  return <time dateTime={date.toISOString()}>{formatted}</time>;
}

// en-US: "Jan 15, 2024, 2:30 PM"
// de: "15. Jan. 2024, 14:30"
// ja: "2024/01/15 14:30"
```

### Numbers

```tsx
function FormattedNumber({ value }: { value: number }) {
  const { i18n } = useTranslation();

  const formatted = new Intl.NumberFormat(i18n.language).format(value);

  return <span>{formatted}</span>;
}

// en-US: "1,234.56"
// de: "1.234,56"
// fr: "1 234,56"
```

### Currency

```tsx
function FormattedCurrency({ value, currency = 'USD' }: Props) {
  const { i18n } = useTranslation();

  const formatted = new Intl.NumberFormat(i18n.language, {
    style: 'currency',
    currency,
  }).format(value);

  return <span>{formatted}</span>;
}

// en-US: "$1,234.56"
// de: "1.234,56 $"
// ja: "$1,234.56"
```

### Relative Time

```tsx
function RelativeTime({ date }: { date: Date }) {
  const { i18n } = useTranslation();

  const rtf = new Intl.RelativeTimeFormat(i18n.language, { numeric: 'auto' });
  const diff = (date.getTime() - Date.now()) / 1000;

  let value: number;
  let unit: Intl.RelativeTimeFormatUnit;

  if (Math.abs(diff) < 60) {
    value = Math.round(diff);
    unit = 'second';
  } else if (Math.abs(diff) < 3600) {
    value = Math.round(diff / 60);
    unit = 'minute';
  } else if (Math.abs(diff) < 86400) {
    value = Math.round(diff / 3600);
    unit = 'hour';
  } else {
    value = Math.round(diff / 86400);
    unit = 'day';
  }

  return <span>{rtf.format(value, unit)}</span>;
}

// en: "2 hours ago", "in 3 days", "yesterday"
// es: "hace 2 horas", "dentro de 3 días", "ayer"
```

---

## Language Switcher

```tsx
import { useTranslation } from 'react-i18next';

const LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
];

function LanguageSwitcher() {
  const { i18n } = useTranslation();

  return (
    <select
      value={i18n.language}
      onChange={e => i18n.changeLanguage(e.target.value)}
      aria-label="Select language"
    >
      {LANGUAGES.map(lang => (
        <option key={lang.code} value={lang.code}>
          {lang.flag} {lang.name}
        </option>
      ))}
    </select>
  );
}
```

---

## RTL Support

### CSS

```css
/* Use logical properties instead of physical */
/* ❌ Bad */
.container {
  margin-left: 1rem;
  padding-right: 2rem;
  text-align: left;
}

/* ✅ Good */
.container {
  margin-inline-start: 1rem;
  padding-inline-end: 2rem;
  text-align: start;
}
```

### Tailwind CSS

```tsx
// Use Tailwind's RTL utilities
<div className="ms-4 me-2 text-start">{/* ms = margin-start, me = margin-end */}</div>
```

### Document Direction

```tsx
// Set document direction based on language
useEffect(() => {
  const rtlLanguages = ['ar', 'he', 'fa'];
  const dir = rtlLanguages.includes(i18n.language) ? 'rtl' : 'ltr';
  document.documentElement.dir = dir;
  document.documentElement.lang = i18n.language;
}, [i18n.language]);
```

---

## Backend Integration

### API Responses

```python
# Accept-Language header handling
from fastapi import Header

@router.get("/placements/{id}")
async def get_placement(
    placement_id: UUID,
    accept_language: str = Header(default="en"),
) -> PlacementResponse:
    # Use for localized error messages
    locale = parse_accept_language(accept_language)
    ...
```

### Localized Error Messages

```python
# src/core/i18n.py
ERROR_MESSAGES = {
    "en": {
        "NOT_FOUND": "{resource} not found",
        "VALIDATION_ERROR": "Validation failed",
    },
    "es": {
        "NOT_FOUND": "{resource} no encontrado",
        "VALIDATION_ERROR": "Error de validación",
    },
}


def get_error_message(code: str, locale: str, **kwargs) -> str:
    messages = ERROR_MESSAGES.get(locale, ERROR_MESSAGES["en"])
    template = messages.get(code, code)
    return template.format(**kwargs)
```

---

## Best Practices

### String Guidelines

```tsx
// ❌ Bad: Concatenated strings
const message = 'Hello, ' + userName + '!';

// ✅ Good: Interpolation
const message = t('greeting', { name: userName });
// Translation: "Hello, {{name}}!"

// ❌ Bad: Sentence fragments
const status = isActive ? t('active') : t('inactive');
const message = t('status_is') + status;

// ✅ Good: Complete sentences
const message = isActive ? t('status.active_message') : t('status.inactive_message');

// ❌ Bad: Hardcoded punctuation
const items = names.join(', ');

// ✅ Good: Use Intl.ListFormat
const formatter = new Intl.ListFormat(i18n.language);
const items = formatter.format(names);
// en: "Alice, Bob, and Charlie"
// es: "Alice, Bob y Charlie"
```

### Design for Expansion

```tsx
// Allow text to wrap and expand
<button className="whitespace-normal px-4 py-2">
  {t('placements.create')}  {/* May be longer in German */}
</button>

// Use flexible layouts
<div className="flex flex-wrap gap-2">
  {/* Buttons will wrap if needed */}
</div>
```

---

## Testing

```tsx
// tests/i18n.test.tsx
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n/config';

function renderWithI18n(ui: React.ReactElement, locale = 'en') {
  i18n.changeLanguage(locale);
  return render(<I18nextProvider i18n={i18n}>{ui}</I18nextProvider>);
}

test('renders in English', () => {
  renderWithI18n(<PlacementList />, 'en');
  expect(screen.getByText('Placements')).toBeInTheDocument();
});

test('renders in Spanish', () => {
  renderWithI18n(<PlacementList />, 'es');
  expect(screen.getByText('Colocaciones')).toBeInTheDocument();
});
```

---

## Related Documentation

- [Accessibility](accessibility.md) – Language and screen reader support
- [TypeScript Style Guide](typescript-style-guide.md) – React patterns
