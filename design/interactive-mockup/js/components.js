/* BIMSpend Components */
/* Reusable UI components for the prototype */

// Utility functions
const $ = (selector, context = document) => context.querySelector(selector);
const $$ = (selector, context = document) => Array.from(context.querySelectorAll(selector));

function createElement(tag, props = {}, children = []) {
  const el = document.createElement(tag);
  Object.entries(props).forEach(([key, value]) => {
    if (key === 'class') el.className = value;
    else if (key === 'dataset') Object.entries(value).forEach(([k, v]) => el.dataset[k] = v);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2).toLowerCase(), value);
    else el.setAttribute(key, value);
  });
  // Normalize children to array
  const childArray = Array.isArray(children) ? children : [children];
  childArray.forEach(child => {
    if (child == null) return; // Skip null/undefined
    if (typeof child === 'string' || typeof child === 'number') el.appendChild(document.createTextNode(String(child)));
    else if (child instanceof Node) el.appendChild(child);
  });
  return el;
}

function formatDate(dateStr, options = {}) {
  const defaultOptions = { year: 'numeric', month: 'short', day: 'numeric', ...options };
  return new Date(dateStr).toLocaleDateString('en-AU', defaultOptions);
}

function formatDateTime(dateStr) {
  return new Date(dateStr).toLocaleString('en-AU', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

function formatCurrency(amount, currency = 'AUD') {
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2
  }).format(amount);
}

function formatNumber(num, decimals = 0) {
  return new Intl.NumberFormat('en-AU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num);
}

function formatPercent(value, decimals = 1) {
  return `${(value * 100).toFixed(decimals)}%`;
}

function getInitials(name) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

function getStatusBadgeClass(status) {
  return `badge-${status.toLowerCase().replace('_', '-')}`;
}

function getConfidenceChipClass(confidence) {
  return `confidence-${confidence.toLowerCase()}`;
}

// Avatar Component
function createAvatar(name, size = 32, className = '') {
  const initials = getInitials(name);
  const colors = [
    'bg-primary', 'bg-teal', 'bg-amber', 'bg-red', 'bg-green',
    'bg-purple', 'bg-pink', 'bg-indigo', 'bg-cyan', 'bg-orange'
  ];
  const colorIndex = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % colors.length;

  return createElement('div', {
    class: `avatar ${colors[colorIndex]} ${className}`,
    style: `--avatar-size: ${size}px; width: var(--avatar-size); height: var(--avatar-size); font-size: ${size * 0.4}px;`
  }, initials);
}

// Badge Component
function createBadge(text, variant = 'default') {
  const className = `badge ${variant ? `badge-${variant}` : ''}`;
  return createElement('span', { class: className }, text);
}

// Button Component
function createButton(props = {}) {
  const {
    text = '',
    variant = 'secondary',
    size = '',
    icon = null,
    iconOnly = false,
    disabled = false,
    onClick = null,
    className = '',
    type = 'button',
    ariaLabel = null
  } = props;

  const classes = `btn btn-${variant} ${size ? `btn-${size}` : ''} ${className}`.trim();
  const children = [];

  if (icon && !iconOnly) {
    children.push(createElement('span', { class: 'btn-icon', 'aria-hidden': 'true' }, icon));
  }
  if (!iconOnly) {
    children.push(createElement('span', {}, text));
  } else if (icon) {
    children.push(createElement('span', { class: 'btn-icon', 'aria-hidden': 'true' }, icon));
  }

  return createElement('button', {
    class: classes,
    type,
    disabled,
    onClick,
    'aria-label': ariaLabel || (iconOnly ? text : null)
  }, children);
}

// Icon Button
function createIconButton(props = {}) {
  const { icon, onClick, className = '', ariaLabel, disabled = false } = props;
  return createElement('button', {
    class: `icon-btn ${className}`,
    onClick,
    'aria-label': ariaLabel,
    disabled
  }, icon);
}

// Input Component
function createInput(props = {}) {
  const {
    type = 'text',
    id,
    name,
    label,
    placeholder = '',
    value = '',
    required = false,
    disabled = false,
    error = null,
    hint = null,
    className = '',
    onChange = null,
    onBlur = null
  } = props;

  const inputId = id || name || `input-${Math.random().toString(36).slice(2)}`;
  const children = [];

  if (label) {
    children.push(createElement('label', {
      class: 'form-label',
      htmlFor: inputId
    }, label + (required ? ' <span class="text-danger">*</span>' : '')));
  }

  const input = createElement('input', {
    type,
    id: inputId,
    name,
    class: `form-input ${className}`,
    placeholder,
    value,
    required,
    disabled,
    'aria-invalid': error ? 'true' : 'false',
    'aria-describedby': error ? `${inputId}-error` : (hint ? `${inputId}-hint` : null),
    onChange: e => onChange?.(e.target.value, e),
    onBlur
  });
  children.push(input);

  if (hint) {
    children.push(createElement('span', { class: 'form-hint', id: `${inputId}-hint` }, hint));
  }
  if (error) {
    children.push(createElement('span', { class: 'form-error', id: `${inputId}-error` }, error));
  }

  return createElement('div', { class: 'form-group' }, children);
}

// Select Component
function createSelect(props = {}) {
  const {
    id,
    name,
    label,
    options = [],
    value = '',
    required = false,
    disabled = false,
    error = null,
    hint = null,
    className = '',
    onChange = null,
    placeholder = 'Select...'
  } = props;

  const selectId = id || name || `select-${Math.random().toString(36).slice(2)}`;
  const children = [];

  if (label) {
    children.push(createElement('label', {
      class: 'form-label',
      htmlFor: selectId
    }, label + (required ? ' <span class="text-danger">*</span>' : '')));
  }

  const optionElements = options.map(opt =>
    createElement('option', { value: opt.value, selected: opt.value === value }, opt.label)
  );

  if (placeholder && !value) {
    optionElements.unshift(createElement('option', { value: '', disabled: true, selected: true }, placeholder));
  }

  const select = createElement('select', {
    id: selectId,
    name,
    class: `form-select ${className}`,
    required,
    disabled,
    'aria-invalid': error ? 'true' : 'false',
    onChange: e => onChange?.(e.target.value, e)
  }, optionElements);
  children.push(select);

  if (hint) {
    children.push(createElement('span', { class: 'form-hint' }, hint));
  }
  if (error) {
    children.push(createElement('span', { class: 'form-error' }, error));
  }

  return createElement('div', { class: 'form-group' }, children);
}

// Modal Component
function createModal(props = {}) {
  const {
    id = `modal-${Math.random().toString(36).slice(2)}`,
    title = '',
    children = [],
    footer = [],
    size = 'md',
    onClose = null,
    closeOnBackdrop = true
  } = props;

  const sizeClasses = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl', full: 'max-w-full mx-4' };

  const backdrop = createElement('div', {
    class: 'modal-backdrop',
    id: `${id}-backdrop`,
    onClick: closeOnBackdrop ? () => closeModal(id) : null
  });

  const modal = createElement('div', {
    class: `modal ${sizeClasses[size] || sizeClasses.md}`,
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': `${id}-title`
  }, [
    createElement('div', { class: 'modal-header' }, [
      createElement('h2', { class: 'modal-title', id: `${id}-title` }, title),
      createIconButton({
        icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        ariaLabel: 'Close modal',
        onClick: () => closeModal(id)
      })
    ]),
    createElement('div', { class: 'modal-body' }, children),
    footer.length > 0 ? createElement('div', { class: 'modal-footer' }, footer) : null
  ].filter(Boolean));

  backdrop.appendChild(modal);
  document.body.appendChild(backdrop);

  // Trigger animation
  requestAnimationFrame(() => {
    backdrop.classList.add('active');
  });

  // Store close handler
  window[`closeModal_${id}`] = () => {
    backdrop.classList.remove('active');
    setTimeout(() => {
      backdrop.remove();
      delete window[`closeModal_${id}`];
      onClose?.();
    }, 200);
  };

  // ESC key handling
  const escHandler = (e) => {
    if (e.key === 'Escape') {
      closeModal(id);
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);

  return { id, close: () => closeModal(id) };
}

function closeModal(id) {
  const handler = window[`closeModal_${id}`];
  if (handler) handler();
}

// Toast Component
function showToast(type, title, message, duration = 5000) {
  const container = $('#toast-container');
  if (!container) return;

  const icons = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
  };

  const toast = createElement('div', {
    class: `toast toast-${type}`,
    role: 'alert',
    'aria-live': 'polite'
  }, [
    createElement('div', { class: 'toast-icon' }, icons[type] || icons.info),
    createElement('div', { class: 'toast-content' }, [
      createElement('div', { class: 'toast-title' }, title),
      createElement('div', { class: 'toast-message' }, message)
    ]),
    createIconButton({
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
      ariaLabel: 'Dismiss',
      onClick: () => toast.remove()
    })
  ]);

  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(() => {
      toast.style.animation = 'slideIn 0.3s ease reverse';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
}

// Dropdown Component
function createDropdown(props = {}) {
  const {
    trigger,
    items = [],
    align = 'right',
    className = ''
  } = props;

  const dropdownId = `dropdown-${Math.random().toString(36).slice(2)}`;

  const menu = createElement('div', {
    class: `dropdown-menu ${align === 'left' ? 'left-0' : 'right-0'} ${className}`,
    id: dropdownId,
    role: 'menu'
  }, items.map(item => {
    if (item.divider) {
      return createElement('div', { class: 'dropdown-divider', role: 'separator' });
    }
    return createElement('button', {
      class: 'dropdown-item',
      role: 'menuitem',
      onClick: () => {
        item.onClick?.();
        closeAllDropdowns();
      }
    }, [
      item.icon ? createElement('span', { 'aria-hidden': 'true' }, item.icon) : null,
      createElement('span', {}, item.label)
    ].filter(Boolean));
  }));

  const wrapper = createElement('div', { class: 'dropdown' }, [trigger, menu]);

  // Toggle logic
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    closeAllDropdowns(dropdownId);
    menu.classList.toggle('active');
    trigger.setAttribute('aria-expanded', menu.classList.contains('active'));
  });

  return wrapper;
}

function closeAllDropdowns(exceptId = null) {
  $$('.dropdown-menu').forEach(menu => {
    if (menu.id !== exceptId) {
      menu.classList.remove('active');
      const trigger = menu.parentElement?.querySelector('[aria-expanded]');
      trigger?.setAttribute('aria-expanded', 'false');
    }
  });
}

// Close dropdowns on outside click
document.addEventListener('click', () => closeAllDropdowns());

// Table Component
function createTable(props = {}) {
  const {
    columns = [],
    data = [],
    keyField = 'id',
    onRowClick = null,
    selectable = false,
    onSelectionChange = null,
    emptyMessage = 'No data available',
    className = '',
    renderRow = null
  } = props;

  const tableId = `table-${Math.random().toString(36).slice(2)}`;
  let selectedRows = new Set();

  const headerRow = createElement('tr', {},
    columns.map(col => createElement('th', {
      scope: 'col',
      style: col.width ? `width: ${col.width}` : '',
      'aria-sort': 'none'
    }, col.header))
  );

  if (selectable) {
    const selectAll = createElement('th', { scope: 'col', style: 'width: 40px' }, [
      createElement('input', {
        type: 'checkbox',
        'aria-label': 'Select all rows',
        onChange: (e) => {
          const checked = e.target.checked;
          $$(`#${tableId} tbody input[type="checkbox"]`).forEach(cb => {
            cb.checked = checked;
            const rowId = cb.closest('tr').dataset.id;
            if (checked) selectedRows.add(rowId);
            else selectedRows.delete(rowId);
          });
          onSelectionChange?.(Array.from(selectedRows));
        }
      })
    ]);
    headerRow.prepend(selectAll);
  }

  const header = createElement('thead', {}, [headerRow]);

  const bodyRows = data.map(row => {
    const rowId = row[keyField];
    const tr = createElement('tr', {
      'data-id': rowId,
      onClick: onRowClick ? () => onRowClick(row) : null,
      style: onRowClick ? 'cursor: pointer;' : ''
    });

    if (selectable) {
      const checkbox = createElement('td', {}, [
        createElement('input', {
          type: 'checkbox',
          'aria-label': `Select row ${rowId}`,
          onChange: (e) => {
            e.stopPropagation();
            if (e.target.checked) selectedRows.add(rowId);
            else selectedRows.delete(rowId);
            onSelectionChange?.(Array.from(selectedRows));
          }
        })
      ]);
      tr.appendChild(checkbox);
    }

    columns.forEach(col => {
      const td = createElement('td', {});
      if (col.render) {
        const rendered = col.render(row, col);
        if (rendered instanceof Node) {
          td.appendChild(rendered);
        } else if (rendered != null) {
          td.textContent = String(rendered);
        }
      } else if (renderRow) {
        const rendered = renderRow(row, col);
        if (rendered instanceof Node) {
          td.appendChild(rendered);
        } else if (rendered != null) {
          td.textContent = String(rendered);
        }
      } else {
        const value = row[col.field];
        td.textContent = value ?? '';
      }
      tr.appendChild(td);
    });

    return tr;
  });

  const body = createElement('tbody', {}, bodyRows);

  if (bodyRows.length === 0) {
    const colCount = columns.length + (selectable ? 1 : 0);
    body.innerHTML = `<tr><td colspan="${colCount}" class="text-center text-muted py-8">${emptyMessage}</td></tr>`;
  }

  const table = createElement('table', { class: `table ${className}`, id: tableId }, [header, body]);

  return createElement('div', { class: 'table-container' }, [table]);
}

// KPI Card Component
function createKPICard(props = {}) {
  const {
    label,
    value,
    subvalue = null,
    trend = null, // { value: 5.2, label: 'vs last month', type: 'positive|negative|neutral' }
    icon = null,
    iconBg = 'primary',
    className = ''
  } = props;

  const trendEl = trend ? createElement('span', {
    class: `kpi-card-trend ${trend.type || 'neutral'}`
  }, [
    createElement('span', { 'aria-hidden': 'true' },
      trend.type === 'positive' ? '↑' : trend.type === 'negative' ? '↓' : '→'
    ),
    createElement('span', {}, `${trend.value}${trend.label ? ` ${trend.label}` : ''}`)
  ]) : null;

  return createElement('div', { class: `kpi-card ${className}` }, [
    createElement('div', { class: 'kpi-card-header' }, [
      createElement('span', { class: 'kpi-card-label' }, label),
      trendEl
    ]),
    createElement('div', { class: 'kpi-card-value' }, value),
    subvalue ? createElement('div', { class: 'kpi-card-subvalue' }, subvalue) : null,
    createElement('div', { class: 'kpi-card-footer' }, [
      icon ? createElement('div', { class: `avatar bg-${iconBg} avatar-sm`, style: 'width: 32px; height: 32px; font-size: 12px;' }, icon) : null,
      createElement('span', { class: 'kpi-card-period' }, 'Updated just now')
    ].filter(Boolean))
  ].filter(Boolean));
}

// Tabs Component
function createTabs(props = {}) {
  const {
    tabs = [],
    activeTab = tabs[0]?.id,
    onChange = null,
    className = ''
  } = props;

  const tabList = createElement('div', { class: `tabs ${className}`, role: 'tablist' },
    tabs.map(tab => createElement('button', {
      class: `tab ${tab.id === activeTab ? 'active' : ''}`,
      role: 'tab',
      'aria-selected': tab.id === activeTab,
      'aria-controls': `${tab.id}-panel`,
      id: `${tab.id}-tab`,
      onClick: () => {
        $$('.tab', tabList).forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');

        $$('.tab-panel', tabContainer).forEach(p => p.classList.remove('active'));
        $(`#${tab.id}-panel`, tabContainer)?.classList.add('active');

        onChange?.(tab.id);
      }
    }, tab.label))
  );

  const tabContainer = createElement('div', {},
    tabs.map(tab => createElement('div', {
      class: `tab-content tab-panel ${tab.id === activeTab ? 'active' : ''}`,
      role: 'tabpanel',
      'aria-labelledby': `${tab.id}-tab`,
      id: `${tab.id}-panel`,
      hidden: tab.id !== activeTab
    }, tab.content))
  );

  return createElement('div', {}, [tabList, tabContainer]);
}

// Card Component
function createCard(props = {}) {
  const {
    title,
    subtitle,
    actions = [],
    children = [],
    className = '',
    headerClass = '',
    bodyClass = ''
  } = props;

  const header = (title || actions.length > 0) ? createElement('div', {
    class: `card-header ${headerClass}`
  }, [
    title ? createElement('h3', { class: 'card-title' }, title) : null,
    subtitle ? createElement('p', { class: 'text-sm text-muted mt-1' }, subtitle) : null,
    actions.length > 0 ? createElement('div', { class: 'flex gap-2' }, actions) : null
  ].filter(Boolean)) : null;

  return createElement('div', { class: `card ${className}` }, [
    header,
    createElement('div', { class: `card-body ${bodyClass}` }, children)
  ].filter(Boolean));
}

// Empty State Component
function createEmptyState(props = {}) {
  const {
    icon,
    title,
    message,
    action = null,
    className = ''
  } = props;

  return createElement('div', { class: `empty-state ${className}` }, [
    icon ? createElement('div', { class: 'empty-state-icon' }, icon) : null,
    title ? createElement('h3', { class: 'empty-state-title' }, title) : null,
    message ? createElement('p', { class: 'empty-state-message' }, message) : null,
    action ? createButton({ ...action, variant: 'primary' }) : null
  ].filter(Boolean));
}

// Skeleton Loader
function createSkeleton(type = 'text', props = {}) {
  const { className = '', ...rest } = props;
  const classes = `skeleton ${type === 'text' ? 'skeleton-text' : type === 'title' ? 'skeleton-title' : 'skeleton-card'} ${className}`;
  return createElement('div', { class: classes, ...rest });
}

// Confirmation Dialog
function confirmDialog(props = {}) {
  const {
    title = 'Confirm',
    message = 'Are you sure?',
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'danger',
    onConfirm = null,
    onCancel = null
  } = props;

  return new Promise((resolve) => {
    const modal = createModal({
      title,
      size: 'sm',
      children: [createElement('p', { class: 'text-secondary' }, message)],
      footer: [
        createButton({ text: cancelText, variant: 'secondary', onClick: () => { modal.close(); resolve(false); onCancel?.(); } }),
        createButton({ text: confirmText, variant, onClick: () => { modal.close(); resolve(true); onConfirm?.(); } })
      ]
    });
  });
}

// Progress Bar
function createProgressBar(props = {}) {
  const { value = 0, max = 100, label = '', showValue = true, className = '', color = 'primary' } = props;
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return createElement('div', { class: `progress-bar ${className}` }, [
    label ? createElement('div', { class: 'flex justify-between mb-1' }, [
      createElement('span', { class: 'text-sm text-secondary' }, label),
      showValue ? createElement('span', { class: 'text-sm fw-medium' }, `${percentage.toFixed(0)}%`) : null
    ].filter(Boolean)) : null,
    createElement('div', {
      class: 'progress-track',
      style: 'height: 8px; background: var(--color-canvas); border-radius: var(--radius-full); overflow: hidden;'
    }, [
      createElement('div', {
        class: 'progress-fill',
        style: `width: ${percentage}%; height: 100%; background: var(--color-${color}); border-radius: var(--radius-full); transition: width var(--transition-normal);`
      })
    ])
  ].filter(Boolean));
}

// Export all components
window.UI = {
  $,
  $$,
  createElement,
  formatDate,
  formatDateTime,
  formatCurrency,
  formatNumber,
  formatPercent,
  getInitials,
  getStatusBadgeClass,
  getConfidenceChipClass,
  createAvatar,
  createBadge,
  createButton,
  createIconButton,
  createInput,
  createSelect,
  createModal,
  closeModal,
  showToast,
  createDropdown,
  createTable,
  createKPICard,
  createTabs,
  createCard,
  createEmptyState,
  createSkeleton,
  confirmDialog,
  createProgressBar
};