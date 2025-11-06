# View Details Modal - Final Fix

## Problem
The modal was opening but tab content was not visible. The console showed logs were working, but the actual JSON/Markdown/HTML content was hidden.

## Root Cause
Bootstrap tab panes were not properly activated/displayed. The `tab-pane` elements had `display: none` by default and Bootstrap's CSS classes weren't properly applying `display: block`.

## Complete Solution

### 1. CSS Fixes (`style.css`)

Added explicit display rules to force tab content visibility:

```css
.tab-content {
    animation: fadeIn 0.3s;
    display: block !important;
    visibility: visible !important;
}

.tab-pane {
    display: none;
}

.tab-pane.active {
    display: block !important;
}

.tab-pane.show {
    display: block !important;
}

#reportModal .modal-body {
    min-height: 400px;
    overflow-y: visible;
}

#reportModal .tab-content {
    min-height: 350px;
}
```

**Key points:**
- `!important` overrides any conflicting Bootstrap styles
- `.tab-pane.active` and `.tab-pane.show` explicitly display content
- Modal body has minimum height to always be visible

### 2. HTML Fixes (`index.html`)

**Added ARIA attributes:**
```html
<button class="nav-link active" id="json-tab" data-bs-toggle="tab" 
        data-bs-target="#json-content" type="button" role="tab" 
        aria-controls="json-content" aria-selected="true">JSON</button>
```

**Added explicit display:**
```html
<div class="tab-pane fade show active" id="json-content" role="tabpanel" 
     aria-labelledby="json-tab" style="display: block;">
```

**Increased min-height:**
```html
<pre style="min-height: 300px; ...">
```

**Better loading text:**
```html
<code id="report-json-content">Loading JSON data...</code>
```

### 3. JavaScript Fixes (`app.js`)

**Added manual tab activation:**
```javascript
// Ensure JSON tab is active
const jsonTab = document.getElementById('json-tab');
const jsonPane = document.getElementById('json-content');
if (jsonTab && jsonPane) {
    // Remove active from all tabs
    document.querySelectorAll('#reportTabs .nav-link').forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('#reportTabContent .tab-pane').forEach(pane => {
        pane.classList.remove('show', 'active');
    });
    
    // Activate JSON tab
    jsonTab.classList.add('active');
    jsonTab.setAttribute('aria-selected', 'true');
    jsonPane.classList.add('show', 'active');
    
    console.log('JSON tab activated');
}
```

**This ensures:**
- All tabs are deactivated first
- JSON tab is explicitly activated
- Classes are properly set before showing modal
- Console logs confirm activation

## Testing Steps

1. **Clear browser cache** (Ctrl+Shift+Delete / Cmd+Shift+Delete)
   - This is CRITICAL as CSS changes are cached

2. **Restart Web UI:**
   ```bash
   python run_web_ui.py
   ```

3. **Hard refresh browser** (Ctrl+Shift+R / Cmd+Shift+R)

4. **Open Console (F12)** to see logs

5. **Click "View Details" on a report**

## What You Should See Now

### Immediate (0ms):
- ✅ Modal opens
- ✅ "Report: run-xxx" title visible
- ✅ JSON, Markdown, HTML tabs visible at top
- ✅ JSON tab is highlighted (active)
- ✅ "Loading JSON data..." visible in dark area below tabs

### After ~100-500ms:
- ✅ JSON content appears (formatted JSON)
- ✅ Can switch to Markdown tab
- ✅ Can switch to HTML tab
- ✅ All content properly displayed

### Console logs should show:
```
Loading report: run-1cf60fb5
Content elements found: {json: true, markdown: true, html: true}
JSON tab activated
Modal shown, starting data fetch...
Fetching JSON...
JSON loaded successfully
Fetching Markdown...
Markdown loaded successfully
Fetching HTML...
HTML loaded successfully
All content loaded
```

## Key Changes Summary

| Component | Change | Why |
|-----------|--------|-----|
| CSS | Added `display: block !important` | Force visibility |
| CSS | Added `.tab-pane.active` rule | Ensure active tab shows |
| CSS | Increased min-height to 300px | Always visible |
| HTML | Added `style="display: block;"` | Explicit display |
| HTML | Added ARIA attributes | Proper accessibility |
| HTML | Better loading text | Clear feedback |
| JS | Manual tab activation | Ensure proper state |
| JS | Remove all active classes first | Clean slate |
| JS | Add active to JSON tab | Explicit activation |

## If Still Not Working

### Step 1: Check Console
Look for these specific logs:
- "JSON tab activated" ← This is KEY
- "Modal shown, starting data fetch..."

If you DON'T see "JSON tab activated", the tab elements aren't being found.

### Step 2: Check Elements
In browser console, run:
```javascript
document.getElementById('json-content')
document.getElementById('json-tab')
```
Both should return elements, not `null`.

### Step 3: Check Computed Style
In browser DevTools:
1. Right-click on the tab content area
2. Select "Inspect"
3. Look at the Computed tab
4. Check `display` property
5. Should be `block`, not `none`

### Step 4: Force Display
In browser console, run:
```javascript
document.getElementById('json-content').style.display = 'block';
document.getElementById('json-content').style.visibility = 'visible';
```

If content appears after this, it confirms the CSS issue.

## Files Modified

1. **`src/chaosmonkey/web/static/style.css`**
   - Added explicit display rules
   - Added modal-specific styling
   - Added min-height rules

2. **`src/chaosmonkey/web/static/app.js`**
   - Added manual tab activation
   - Added class manipulation
   - Added console logging

3. **`src/chaosmonkey/web/templates/index.html`**
   - Added ARIA attributes
   - Added inline `display: block`
   - Increased min-height
   - Better loading messages

## Why This Fix Works

**Previous issue:**
- Bootstrap CSS sets `display: none` on inactive tabs
- When modal opened, tab-pane had conflicting styles
- Content existed but wasn't visible

**New solution:**
- CSS `!important` overrides Bootstrap defaults
- Inline styles provide fallback
- JavaScript explicitly activates first tab
- Multiple layers ensure visibility

## Success Criteria

✅ Modal opens instantly  
✅ JSON tab is active and highlighted  
✅ "Loading JSON data..." visible immediately  
✅ Content appears within 1 second  
✅ Can switch between tabs  
✅ All tabs show content  
✅ No console errors  
✅ Console shows "JSON tab activated"  

## Date
October 10, 2025
