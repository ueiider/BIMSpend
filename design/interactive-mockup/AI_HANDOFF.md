# BIMSpend Interactive Prototype - AI Handoff Document

## For Next AI Agent / Session

### Quick Start
```bash
cd C:/Users/UeiderAndradeMoreira/BIMSpend/design/interactive-mockup
python3 -m http.server 8080
# Open http://localhost:8080
```

### Current State: ✅ FULLY FUNCTIONAL
- All 20 screens working (16 primary + 4 designer-specific)
- 5 detail screens working with route parameters
- 3 roles with proper RBAC
- Light/Dark theme switching
- Responsive at 4 breakpoints
- Zero console errors

---

## Architecture Summary

### Tech Stack
- **Vanilla HTML5/CSS3/JavaScript** - No frameworks
- **CSS Custom Properties** - Design token system (tokens.css)
- **Client-side SPA Router** - Hash/history routing with role guards
- **Event-driven State** - StateManager with reactivity + localStorage
- **Component Factory** - UI.createElement, createTable, createCard, etc.
- **Chart Library** - Canvas-based charts (charts.js)

### Key Files
```
design/interactive-mockup/
├── index.html          # Main HTML with sidebar, header, content area
├── css/
│   ├── tokens.css      # Design tokens (colors, spacing, typography)
│   ├── main.css        # Layout, components, utilities
│   └── charts.css      # Chart-specific styles
├── js/
│   ├── state.js        # StateManager - central state + reactivity
│   ├── router.js       # Router - SPA routing + role guards
│   ├── components.js   # UI component factory
│   ├── charts.js       # Chart rendering (profitability, utilization, donut)
│   ├── screens.js      # 26 screen render functions (3928 lines)
│   └── app.js          # App bootstrap, event wiring, global helpers
└── data/
    └── demo-data.js    # Fictional Australian BIM company data
```

### Global Objects (window)
- `State` - StateManager instance
- `RouterInstance` - Router instance
- `UI` - Component factory namespace
- `Charts` - Chart rendering namespace
- `Screens` - Screen render functions namespace
- `DemoData` - Demo data object
- `App` - App helper functions (init, renderScreen, etc.)

---

## Demo Data (Australian Context)

### Company
- **Apex BIM Solutions Pty Ltd** (Melbourne VIC 3000)
- ABN: 12 345 678 901
- Currency: AUD ($)
- Tax Rate: 10% GST
- Fiscal Year: July 1

### Employees (8)
| ID | Name | Role | Dept | Rate (AUD/hr) |
|----|------|------|------|---------------|
| emp-001 | John Doe | Administrator | Management | 280 |
| emp-002 | Sarah Chen | Manager | Fire Protection | 220 |
| emp-003 | Michael Roberts | Manager | Hydraulic Services | 210 |
| emp-004 | Emily Watson | Designer | Fire Protection | 165 |
| emp-005 | James Park | Designer | Fire Protection | 155 |
| emp-006 | Lisa Thompson | Designer | Hydraulic Services | 150 |
| emp-007 | David Kim | Designer | Fire Protection | 145 |
| emp-008 | Rachel Green | Designer | Hydraulic Services | 140 |

### Projects (8)
- MRV-FP-2024-001: Metro Tunnel Fire Protection ($2.4M)
- LL-FP-2024-003: Lakelands Hospital Fire Protection ($1.8M)
- KAN-HY-2024-003: Kangan Institute Hydraulic Services ($950K)
- + 5 more active/planned projects

### Financial Data
- Timesheets: 24 entries across statuses
- Quotes: 8 (draft/sent/accepted/rejected)
- Invoices: 12 (draft/sent/overdue/paid)
- Activity Events: 50+ tracked activities
- Reports: Profitability, utilization, budget variance

---

## Role Permissions (Demo)

### Administrator (John Doe)
- All 16 nav sections visible
- All data visible (no filtering)
- Company Settings, Integrations, Onboarding access

### Manager (Sarah Chen / Michael Roberts)
- 13 nav sections (no Integrations, Company Settings, Onboarding)
- Data filtered to managed projects/team
- Can approve timesheets

### Designer (Emily Watson)
- 5 nav sections (My Workspace only)
- Data filtered to assigned projects only
- Own timesheets/activity only

---

## Key Interactions Verified

### Navigation
- Sidebar items click → route change → screen render
- Browser back/forward works
- Deep linking to detail screens works

### Forms & Modals
- Timesheet create/edit modal
- Project create/edit modal
- Employee create/edit modal
- Client create/edit modal
- Quote builder (multi-step)
- Invoice create modal
- Onboarding wizard (8 steps)

### Data Operations
- Timesheet: draft → submit → approve/reject → bill
- Quote: build → save draft → send → accept/reject
- Invoice: create → send → mark paid
- Project: create → assign team → track budget
- Filters: multi-field with role-aware results

### Visual
- Theme toggle (persists to localStorage)
- Sidebar collapse (persists to localStorage)
- Badge counts update in real-time
- Toasts for success/warning/error

---

## Common Commands for Testing

```bash
# Start server
python3 -m http.server 8080

# Run Playwright tests
node test-all-screens.js      # All 20 screens
node test-interactions.js     # Detail screens, modals, responsive
node test-theme.js            # Theme switching

# Syntax check all JS
for f in js/*.js; do node --check "$f"; done
```

---

## Known Gotchas

1. **State.set('theme', 'dark')** - Use `State.set()`, not direct assignment
2. **Router navigation** - Use `RouterInstance.navigate('route-name', params)`
3. **Role switching** - `State.set('currentRole', 'designer')` triggers full UI update
4. **Demo data** - All in `DemoData` object, loaded in StateManager constructor
5. **localStorage keys** - `bimspend_ui_state`, `bimspend_theme`

---

## Next Steps if Continuing

### Priority 1 (Polish)
- Fix button text selectors in Playwright tests
- Add manual CSV download verification
- Polish onboarding wizard step 8 (completion screen)

### Priority 2 (Features)
- Add command palette (Ctrl+K)
- Add keyboard shortcuts help (Ctrl+/)
- Add print stylesheets for reports

### Priority 3 (Architecture)
- Consider TypeScript migration
- Add unit tests for StateManager calculations
- Add Storybook for component library

---

## Debugging Tips

### Console Access
```javascript
// In browser console
State.state              // Full state
State.getCurrentUser()   // Current user
State.getCurrentRole()   // Current role
RouterInstance.getCurrentRoute()  // Current route
Screens.dashboard()      // Render dashboard manually
UI.showToast('success', 'Test', 'Message')
```

### Common Errors
| Error | Cause | Fix |
|-------|-------|-----|
| `State.init is not a function` | Called in app.js | Already fixed - State initializes in constructor |
| `children.forEach is not a function` | String passed as children | Fixed in createElement |
| `appendChild not a Node` | Render returns string | Fixed in createTable |
| `nav items hidden` | Role mismatch | Use 'administrator' not 'admin' |

---

## File Change Log (This Session)

| File | Lines Changed | Description |
|------|---------------|-------------|
| js/app.js | ~5 | Removed await State.init(), fixed theme event destructuring |
| js/components.js | ~20 | Fixed createElement children normalization, createTable render handling |
| js/state.js | +1 | Export window.State |
| js/router.js | +1 | Export window.RouterInstance |
| index.html | ~20 | data-roles: admin → administrator |
| test-*.js | New | Playwright test suites |

---

## Contacts / References

- **Design Tokens**: `css/tokens.css` - All colors, spacing, shadows
- **Component API**: `js/components.js` - createElement, createCard, createTable, createKPICard, createBadge, createButton, createSelect, createInput, createModal
- **Screen Registry**: `js/screens.js` - All 26 Screens.* functions
- **Demo Data Schema**: `data/demo-data.js` - DemoData object structure

---

**Last Updated**: 2026-11-06
**Status**: Ready for stakeholder demo / handoff to development team