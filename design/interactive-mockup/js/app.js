/* BIMSpend Main Application */
/* Initializes the app, handles routing, renders screens */

(function() {
  'use strict';

  // Global references
  let currentScreen = null;
  let isInitialized = false;

  // DOM Elements
  const elements = {
    app: null,
    sidebar: null,
    sidebarToggle: null,
    sidebarBackdrop: null,
    mobileMenuBtn: null,
    content: null,
    pageTitle: null,
    breadcrumb: null,
    themeToggle: null,
    notificationBtn: null,
    notificationBadge: null,
    notificationMenu: null,
    notificationsList: null,
    roleBtn: null,
    roleMenu: null,
    currentRoleLabel: null,
    userBtn: null,
    userMenu: null,
    headerAvatar: null,
    headerUserName: null,
    headerUserRole: null,
    headerUserEmail: null,
    toastContainer: null
  };

  // Initialize the application
  async function init() {
    if (isInitialized) return;

    // Cache DOM elements
    cacheElements();

    // State is already initialized in its constructor (StateManager)
    // Initialize Router (already instantiated globally as RouterInstance)
    setupRouterHooks();

    // Setup event listeners
    setupEventListeners();

    // Apply initial theme
    applyTheme(State.state.theme);

    // Update UI for current role
    updateRoleUI();

    // Update navigation visibility
    updateNavigationVisibility();

    // Render initial route
    const currentRoute = RouterInstance.getCurrentRoute();
    const currentParams = RouterInstance.getCurrentParams();
    if (currentRoute) {
      renderScreen(currentRoute, currentParams);
    }

    // Update badge counts
    updateBadgeCounts();

    isInitialized = true;
    console.log('BIMSpend initialized');
  }

  // Cache DOM elements
  function cacheElements() {
    elements.app = $('#app');
    elements.sidebar = $('#sidebar');
    elements.sidebarToggle = $('#sidebar-toggle');
    elements.sidebarBackdrop = $('#sidebar-backdrop');
    elements.mobileMenuBtn = $('#mobile-menu-btn');
    elements.content = $('#content');
    elements.pageTitle = $('#page-title');
    elements.breadcrumb = $('#breadcrumb');
    elements.themeToggle = $('#theme-toggle');
    elements.notificationBtn = $('#notifications-btn');
    elements.notificationBadge = $('#notification-badge');
    elements.notificationMenu = $('#notifications-menu');
    elements.notificationsList = $('#notifications-list');
    elements.roleBtn = $('#role-btn');
    elements.roleMenu = $('#role-menu');
    elements.currentRoleLabel = $('#current-role-label');
    elements.userBtn = $('#user-btn');
    elements.userMenu = $('#user-menu');
    elements.headerAvatar = $('#header-avatar');
    elements.headerUserName = $('#header-user-name');
    elements.headerUserRole = $('#header-user-role');
    elements.headerUserEmail = $('#header-user-email');
    elements.toastContainer = $('#toast-container');
  }

  // Setup router hooks
  function setupRouterHooks() {
    RouterInstance.beforeEach((routeName, params, previousRoute) => {
      // Check if route requires authentication
      if (!State.getCurrentUser()) {
        State.showToast('error', 'Not Authenticated', 'Please log in to access this page.');
        return false;
      }
      return true;
    });

    RouterInstance.afterEach((routeName, params, previousRoute) => {
      // Update page title
      const route = RouterInstance.routes.get(routeName);
      if (route) {
        elements.pageTitle.textContent = route.title;
        document.title = `${route.title} - BIMSpend`;
      }

      // Update navigation active state
      updateNavigationActive(routeName);

      // Close mobile sidebar
      closeSidebar();

      // Update badge counts
      updateBadgeCounts();

      // Scroll to top
      window.scrollTo(0, 0);
    });
  }

  // Setup event listeners
  function setupEventListeners() {
    // Sidebar toggle
    elements.sidebarToggle?.addEventListener('click', toggleSidebar);
    elements.sidebarBackdrop?.addEventListener('click', closeSidebar);
    elements.mobileMenuBtn?.addEventListener('click', toggleSidebar);

    // Navigation clicks
    $$('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const routeName = item.dataset.nav;
        if (routeName) {
          RouterInstance.navigate(routeName);
        }
      });
    });

    // Theme toggle
    elements.themeToggle?.addEventListener('click', toggleTheme);

    // Notification dropdown
    elements.notificationBtn?.addEventListener('click', () => toggleDropdown('notifications'));
    elements.notificationsList?.addEventListener('click', handleNotificationClick);

    // Role dropdown
    elements.roleBtn?.addEventListener('click', () => toggleDropdown('role'));
    $$('#role-menu .dropdown-item[data-role]').forEach(item => {
      item.addEventListener('click', () => switchRole(item.dataset.role));
    });

    // User dropdown
    elements.userBtn?.addEventListener('click', () => toggleDropdown('user'));
    $$('#user-menu .dropdown-item[data-nav]').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        RouterInstance.navigate(item.dataset.nav);
        closeDropdown('user');
      });
    });

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.dropdown')) {
        closeAllDropdowns();
      }
    });

    // Keyboard navigation
    document.addEventListener('keydown', handleKeydown);

    // Window resize
    window.addEventListener('resize', handleResize);

    // State change listeners
    State.on('themeChanged', ({ value }) => applyTheme(value));
    State.on('roleChanged', () => {
      updateRoleUI();
      updateNavigationVisibility();
      // Re-render current screen
      const currentRoute = RouterInstance.getCurrentRoute();
      const currentParams = RouterInstance.getCurrentParams();
      if (currentRoute) {
        renderScreen(currentRoute, currentParams);
      }
      updateBadgeCounts();
    });
    State.on('toast', (toast) => UI.showToast(toast.type, toast.title, toast.message));
    State.on('notificationsChanged', () => {
      updateNotificationBadge();
      updateNotificationDropdown();
    });
    State.on('timesheetChanged', () => {
      updateBadgeCounts();
      // Re-render if on timesheet screen
      if (RouterInstance.getCurrentRoute() === 'timesheets' || RouterInstance.getCurrentRoute() === 'my-timesheets') {
        renderScreen(RouterInstance.getCurrentRoute(), RouterInstance.getCurrentParams());
      }
    });
    State.on('quoteChanged', () => {
      updateBadgeCounts();
    });
    State.on('invoiceChanged', () => {
      updateBadgeCounts();
    });
    State.on('projectChanged', () => {
      updateBadgeCounts();
    });
  }

  // Render screen based on route
  function renderScreen(routeName, params = {}) {
    const screenFunc = Screens[routeName];
    if (!screenFunc) {
      console.warn(`Screen not found: ${routeName}`);
      renderNotFound(routeName);
      return;
    }

    try {
      // Clear content
      elements.content.innerHTML = '';

      // Render screen
      const screenContent = screenFunc(params);
      if (screenContent) {
        elements.content.appendChild(screenContent);
      }

      currentScreen = routeName;

      // Initialize any screen-specific functionality
      initializeScreen(routeName, params);

    } catch (error) {
      console.error(`Error rendering screen ${routeName}:`, error);
      renderError(routeName, error);
    }
  }

  // Screen-specific initialization
  function initializeScreen(routeName, params) {
    // Re-attach event listeners for dynamically created elements
    // This is handled by the component system, but some screens need extra init
  }

  // Render 404
  function renderNotFound(routeName) {
    elements.content.innerHTML = '';
    elements.content.appendChild(UI.createCard({
      children: [
        UI.createElement('div', { class: 'text-center py-12' }, [
          UI.createElement('div', { class: 'text-6xl mb-4' }, '🔍'),
          UI.createElement('h2', { class: 'mb-2' }, 'Page Not Found'),
          UI.createElement('p', { class: 'text-secondary mb-6' }, `The screen "${routeName}" could not be found.`),
          UI.createButton({ text: 'Go to Dashboard', variant: 'primary', onClick: () => RouterInstance.navigate('dashboard') })
        ])
      ]
    }));
  }

  // Render error
  function renderError(routeName, error) {
    elements.content.innerHTML = '';
    elements.content.appendChild(UI.createCard({
      children: [
        UI.createElement('div', { class: 'text-center py-12' }, [
          UI.createElement('div', { class: 'text-6xl mb-4' }, '⚠️'),
          UI.createElement('h2', { class: 'mb-2' }, 'Something Went Wrong'),
          UI.createElement('p', { class: 'text-secondary mb-4' }, `Error loading "${routeName}"`),
          UI.createElement('details', { class: 'text-left text-sm text-muted mt-4' }, [
            UI.createElement('summary', {}, 'Error Details'),
            UI.createElement('pre', { style: 'margin-top: 8px; overflow: auto;' }, error.stack || error.message)
          ]),
          UI.createButton({ text: 'Retry', variant: 'primary', onClick: () => renderScreen(routeName, RouterInstance.getCurrentParams()) })
        ])
      ]
    }));
  }

  // Update navigation active state
  function updateNavigationActive(routeName) {
    $$('.nav-item').forEach(item => {
      item.classList.remove('active');
      if (item.dataset.nav === routeName) {
        item.classList.add('active');
      }
    });
  }

  // Update navigation visibility based on role
  function updateNavigationVisibility() {
    const role = State.getCurrentRole();
    $$('.nav-section').forEach(section => {
      const sectionRole = section.dataset.roleSection;
      if (sectionRole === 'admin') {
        section.style.display = (role === 'administrator') ? '' : 'none';
      } else if (sectionRole === 'designer') {
        section.style.display = (role === 'designer') ? '' : 'none';
      } else {
        section.style.display = '';
      }
    });

    // Also hide individual nav items based on data-roles
    $$('.nav-item').forEach(item => {
      const roles = item.dataset.roles?.split(',') || [];
      if (roles.length > 0 && !roles.includes(role)) {
        item.style.display = 'none';
      } else {
        item.style.display = '';
      }
    });
  }

  // Update role UI
  function updateRoleUI() {
    const role = State.getCurrentRole();
    const user = State.getCurrentUser();

    // Update role label
    const roleLabels = {
      administrator: 'Administrator',
      manager: 'Project Manager',
      designer: 'Designer'
    };
    elements.currentRoleLabel.textContent = roleLabels[role] || role;

    // Update user info in header
    if (user) {
      elements.headerAvatar.textContent = UI.getInitials(`${user.firstName} ${user.lastName}`);
      elements.headerUserName.textContent = `${user.firstName} ${user.lastName}`;
      elements.headerUserRole.textContent = roleLabels[role] || role;
      elements.headerUserEmail.textContent = user.email;
    }

    // Update role dropdown active state
    $$('#role-menu .dropdown-item').forEach(item => {
      item.classList.toggle('active', item.dataset.role === role);
    });
  }

  // Toggle theme
  function toggleTheme() {
    const currentTheme = State.state.theme;
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    State.set('theme', newTheme);
  }

  // Apply theme
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('bimspend_theme', theme);

    // Update theme toggle icon
    const sunIcon = elements.themeToggle?.querySelector('.icon-sun');
    const moonIcon = elements.themeToggle?.querySelector('.icon-moon');
    if (sunIcon && moonIcon) {
      if (theme === 'dark') {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
      } else {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
      }
    }
  }

  // Toggle sidebar
  function toggleSidebar() {
    elements.app.classList.toggle('sidebar-open');
    elements.sidebarBackdrop.classList.toggle('visible');
    elements.mobileMenuBtn?.setAttribute('aria-expanded', elements.app.classList.contains('sidebar-open'));
  }

  // Close sidebar
  function closeSidebar() {
    elements.app.classList.remove('sidebar-open');
    elements.sidebarBackdrop.classList.remove('visible');
    elements.mobileMenuBtn?.setAttribute('aria-expanded', 'false');
  }

  // Toggle dropdown
  function toggleDropdown(name) {
    const btn = elements[`${name}Btn`];
    const menu = elements[`${name}Menu`];
    if (!btn || !menu) return;

    const isOpen = menu.classList.contains('show');
    closeAllDropdowns();

    if (!isOpen) {
      menu.classList.add('show');
      btn.setAttribute('aria-expanded', 'true');

      // Populate dropdown content if needed
      if (name === 'notifications') {
        updateNotificationDropdown();
      }
    }
  }

  // Close dropdown
  function closeDropdown(name) {
    const menu = elements[`${name}Menu`];
    const btn = elements[`${name}Btn`];
    if (menu) {
      menu.classList.remove('show');
    }
    if (btn) {
      btn.setAttribute('aria-expanded', 'false');
    }
  }

  // Close all dropdowns
  function closeAllDropdowns() {
    $$('.dropdown-menu.show').forEach(menu => menu.classList.remove('show'));
    $$('.dropdown > button[aria-expanded="true"]').forEach(btn => btn.setAttribute('aria-expanded', 'false'));
  }

  // Handle notification click
  function handleNotificationClick(e) {
    const item = e.target.closest('[data-notification-id]');
    if (item) {
      const notifId = item.dataset.notificationId;
      const notif = State.state.notifications.find(n => n.id === notifId);
      if (notif) {
        State.markNotificationRead(notifId);
        Screens.navigateToReference(notif);
      }
    }
  }

  // Update notification badge
  function updateNotificationBadge() {
    const unreadCount = State.state.notifications.filter(n => !n.read).length;
    if (elements.notificationBadge) {
      elements.notificationBadge.textContent = unreadCount > 9 ? '9+' : unreadCount;
      elements.notificationBadge.style.display = unreadCount > 0 ? 'flex' : 'none';
    }
  }

  // Update notification dropdown
  function updateNotificationDropdown() {
    if (!elements.notificationsList) return;

    const notifications = State.state.notifications.slice(0, 5);
    elements.notificationsList.innerHTML = '';

    if (notifications.length === 0) {
      elements.notificationsList.innerHTML = '<div class="dropdown-item" style="cursor: default; justify-content: center; color: var(--color-text-muted);">No notifications</div>';
      return;
    }

    notifications.forEach(notif => {
      const typeIcons = {
        timesheet_approval: '📋',
        timesheet_rejected: '↩️',
        budget_warning: '⚠️',
        invoice_overdue: '📄',
        quote_accepted: '✅',
        activity_classification: '🔍',
        project_update: '📁'
      };

      const el = UI.createElement('div', {
        class: `dropdown-item ${!notif.read ? 'unread' : ''}`,
        dataset: { notificationId: notif.id }
      }, [
        UI.createElement('span', { style: 'font-size: 16px;' }, typeIcons[notif.type] || '🔔'),
        UI.createElement('div', { class: 'flex-1', style: 'min-width: 0;' }, [
          UI.createElement('div', { class: 'fw-medium text-sm' }, notif.title),
          UI.createElement('div', { class: 'text-xs text-muted' }, notif.message)
        ])
      ]);
      elements.notificationsList.appendChild(el);
    });
  }

  // Switch role
  function switchRole(role) {
    State.set('currentRole', role);
    closeDropdown('role');
  }

  // Update badge counts
  function updateBadgeCounts() {
    const data = getVisibleData();

    // Timesheets badge
    const pendingTs = data.timesheets.filter(t => t.status === 'submitted').length;
    const timesheetsBadge = $('#timesheets-badge');
    if (timesheetsBadge) {
      timesheetsBadge.textContent = pendingTs > 9 ? '9+' : pendingTs;
      timesheetsBadge.style.display = pendingTs > 0 ? 'inline-flex' : 'none';
    }

    // Live activity badge
    const activeNow = data.activity.filter(a => new Date(a.timestamp) > new Date(Date.now() - 30 * 60 * 1000)).length;
    const activityBadge = $('#live-activity-badge');
    if (activityBadge) {
      activityBadge.textContent = activeNow > 9 ? '9+' : activeNow;
      activityBadge.style.display = activeNow > 0 ? 'inline-flex' : 'none';
    }

    // Quotes badge
    const pendingQuotes = data.quotes.filter(q => q.status === 'draft' || q.status === 'sent').length;
    const quotesBadge = $('#quotes-badge');
    if (quotesBadge) {
      quotesBadge.textContent = pendingQuotes > 9 ? '9+' : pendingQuotes;
      quotesBadge.style.display = pendingQuotes > 0 ? 'inline-flex' : 'none';
    }

    // Billing badge
    const pendingInvoices = data.invoices.filter(i => i.status === 'sent' || i.status === 'overdue').length;
    const billingBadge = $('#billing-badge');
    if (billingBadge) {
      billingBadge.textContent = pendingInvoices > 9 ? '9+' : pendingInvoices;
      billingBadge.style.display = pendingInvoices > 0 ? 'inline-flex' : 'none';
    }

    // Notifications badge
    updateNotificationBadge();
  }

  // Get visible data (reused from screens)
  function getVisibleData() {
    return {
      projects: State.getProjects(State.getFilters('projects')),
      timesheets: State.getTimesheets(State.getFilters('timesheets')),
      employees: State.state.employees.filter(e => {
        const f = State.getFilters('employees');
        if (f.department && e.department !== f.department) return false;
        if (f.role && e.role !== f.role) return false;
        if (f.status && e.status !== f.status) return false;
        if (f.search) {
          const s = f.search.toLowerCase();
          if (!e.firstName.toLowerCase().includes(s) &&
              !e.lastName.toLowerCase().includes(s) &&
              !e.email.toLowerCase().includes(s)) return false;
        }
        return true;
      }),
      activity: State.getActivityEvents(State.getFilters('activity')),
      clients: State.state.clients,
      quotes: State.getQuotes(State.getFilters('quotes')),
      invoices: State.getInvoices(State.getFilters('invoices')),
      notifications: State.getNotifications()
    };
  }

  // Handle keyboard shortcuts
  function handleKeydown(e) {
    // Escape closes dropdowns and modals
    if (e.key === 'Escape') {
      closeAllDropdowns();
      UI.closeModal();
    }

    // Ctrl/Cmd + K for command palette (future)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      // TODO: Command palette
    }

    // Ctrl/Cmd + / for shortcuts help
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      showShortcutsHelp();
    }
  }

  // Show shortcuts help
  function showShortcutsHelp() {
    const shortcuts = [
      { key: 'Esc', action: 'Close dropdowns/modals' },
      { key: 'Ctrl/Cmd + K', action: 'Command palette (coming soon)' },
      { key: 'Ctrl/Cmd + /', action: 'Show this help' },
      { key: 'Tab', action: 'Navigate between elements' },
      { key: 'Enter/Space', action: 'Activate buttons/links' }
    ];

    UI.createModal({
      title: 'Keyboard Shortcuts',
      children: [
        UI.createElement('div', { class: 'd-grid gap-2' }, shortcuts.map(s =>
          UI.createElement('div', { class: 'd-flex justify-between py-2' }, [
            UI.createElement('kbd', { style: 'background: var(--color-canvas); padding: 2px 8px; border-radius: var(--radius-sm); font-family: monospace; font-size: 12px;' }, s.key),
            UI.createElement('span', { class: 'text-secondary' }, s.action)
          ])
        ))
      ],
      size: 'sm'
    });
  }

  // Handle resize
  function handleResize() {
    // Close mobile sidebar on desktop
    if (window.innerWidth >= 768) {
      closeSidebar();
    }
  }

  // Make functions globally available
  window.App = {
    init,
    renderScreen,
    toggleSidebar,
    closeSidebar,
    toggleTheme,
    switchRole,
    updateBadgeCounts,
    getVisibleData
  };

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();