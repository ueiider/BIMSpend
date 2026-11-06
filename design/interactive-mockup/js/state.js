/* BIMSpend State Management */
/* Centralized application state with reactivity */

class StateManager {
  constructor() {
    this.state = {
      // User & Auth
      currentUser: null,
      currentRole: 'administrator', // administrator, manager, designer
      userPermissions: [],

      // UI State
      theme: 'light', // light, dark
      sidebarCollapsed: false,
      sidebarOpen: false, // mobile
      currentPage: 'dashboard',
      currentProjectId: null,
      breadcrumbs: [],

      // Data
      employees: [],
      projects: [],
      clients: [],
      timesheets: [],
      activityEvents: [],
      quotes: [],
      invoices: [],
      notifications: [],
      settings: {},
      reports: {},

      // Filters & Search
      filters: {
        timesheets: { employee: '', project: '', status: '', dateFrom: '', dateTo: '' },
        projects: { status: '', phase: '', manager: '', search: '' },
        employees: { department: '', role: '', status: '', search: '' },
        activity: { employee: '', project: '', state: '', dateFrom: '', dateTo: '' },
        quotes: { status: '', client: '', dateFrom: '', dateTo: '' },
        invoices: { status: '', client: '', project: '', dateFrom: '', dateTo: '' }
      },

      // Modals & UI
      activeModal: null,
      modalData: null,
      toasts: [],

      // Loading states
      loading: {}
    };

    this.listeners = new Map();
    this.initFromStorage();
    this.loadDemoData();
  }

  initFromStorage() {
    try {
      const stored = localStorage.getItem('bimspend_ui_state');
      if (stored) {
        const parsed = JSON.parse(stored);
        this.state.theme = parsed.theme || 'light';
        this.state.sidebarCollapsed = parsed.sidebarCollapsed || false;
        this.state.currentRole = parsed.currentRole || 'administrator';
        this.state.currentPage = parsed.currentPage || 'dashboard';
        document.documentElement.setAttribute('data-theme', this.state.theme);
      }
    } catch (e) {
      console.warn('Failed to load UI state from storage:', e);
    }
  }

  saveToStorage() {
    try {
      const toSave = {
        theme: this.state.theme,
        sidebarCollapsed: this.state.sidebarCollapsed,
        currentRole: this.state.currentRole,
        currentPage: this.state.currentPage
      };
      localStorage.setItem('bimspend_ui_state', JSON.stringify(toSave));
    } catch (e) {
      console.warn('Failed to save UI state to storage:', e);
    }
  }

  loadDemoData() {
    this.state.employees = DemoData.employees;
    this.state.projects = DemoData.projects;
    this.state.clients = DemoData.clients;
    this.state.timesheets = DemoData.timesheets;
    this.state.activityEvents = DemoData.activityEvents;
    this.state.quotes = DemoData.quotes;
    this.state.invoices = DemoData.invoices;
    this.state.notifications = DemoData.notifications;
    this.state.settings = DemoData.settings;
    this.state.reports = DemoData.reports;
    this.setCurrentUser(this.state.currentRole);
  }

  setCurrentUser(role) {
    this.state.currentRole = role;
    const userMap = {
      administrator: this.state.employees.find(e => e.id === 'emp-001'),
      manager: this.state.employees.find(e => e.id === 'emp-002'),
      designer: this.state.employees.find(e => e.id === 'emp-004')
    };
    this.state.currentUser = userMap[role] || userMap.administrator;
    this.state.userPermissions = this.state.currentUser?.permissions || ['all'];
    this.updateRoleBasedNavigation();
    this.emit('userChanged', { role, user: this.state.currentUser });
  }

  updateRoleBasedNavigation() {
    const navItems = document.querySelectorAll('[data-nav]');
    navItems.forEach(item => {
      const roles = item.dataset.roles?.split(',') || [];
      const roleSection = item.closest('[data-role-section]');
      const sectionRoles = roleSection?.dataset.roleSection;

      let visible = true;

      if (sectionRoles === 'admin' && this.state.currentRole === 'designer') {
        visible = false;
      } else if (sectionRoles === 'designer' && this.state.currentRole !== 'designer') {
        visible = false;
      } else if (roles.length > 0 && !roles.includes(this.state.currentRole)) {
        visible = false;
      }

      item.style.display = visible ? 'flex' : 'none';

      // Also handle section titles
      if (roleSection) {
        const visibleItems = roleSection.querySelectorAll('[data-nav]:not([style*="display: none"])');
        roleSection.style.display = visibleItems.length > 0 ? 'block' : 'none';
      }
    });
  }

  // Getters
  get(key) {
    return this.state[key];
  }

  getCurrentUser() {
    return this.state.currentUser;
  }

  getCurrentRole() {
    return this.state.currentRole;
  }

  hasPermission(permission) {
    if (this.state.userPermissions.includes('all')) return true;
    return this.state.userPermissions.includes(permission);
  }

  // Setters with reactivity
  set(key, value) {
    const oldValue = this.state[key];
    this.state[key] = value;

    if (key === 'theme') {
      document.documentElement.setAttribute('data-theme', value);
    }

    if (key === 'sidebarCollapsed') {
      document.getElementById('sidebar')?.classList.toggle('collapsed', value);
      this.saveToStorage();
    }

    if (key === 'currentRole') {
      this.setCurrentUser(value);
      this.saveToStorage();
    }

    if (key === 'currentPage') {
      this.updateActiveNavigation(value);
      this.saveToStorage();
    }

    this.emit('change', { key, value, oldValue });
    this.emit(`${key}Changed`, { value, oldValue });
  }

  updateActiveNavigation(page) {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.nav === page);
    });
  }

  // Filter management
  setFilter(category, key, value) {
    if (this.state.filters[category]) {
      this.state.filters[category][key] = value;
      this.emit('filterChanged', { category, filters: this.state.filters[category] });
    }
  }

  getFilters(category) {
    return this.state.filters[category] || {};
  }

  resetFilters(category) {
    const defaults = {
      timesheets: { employee: '', project: '', status: '', dateFrom: '', dateTo: '' },
      projects: { status: '', phase: '', manager: '', search: '' },
      employees: { department: '', role: '', status: '', search: '' },
      activity: { employee: '', project: '', state: '', dateFrom: '', dateTo: '' },
      quotes: { status: '', client: '', dateFrom: '', dateTo: '' },
      invoices: { status: '', client: '', project: '', dateFrom: '', dateTo: '' }
    };
    this.state.filters[category] = { ...defaults[category] };
    this.emit('filterChanged', { category, filters: this.state.filters[category] });
  }

  // Data helpers
  getEmployee(id) {
    return this.state.employees.find(e => e.id === id);
  }

  getProject(id) {
    return this.state.projects.find(p => p.id === id);
  }

  getClient(id) {
    return this.state.clients.find(c => c.id === id);
  }

  getTimesheets(filters = {}) {
    let results = [...this.state.timesheets];

    if (filters.employee) {
      results = results.filter(t => t.employeeId === filters.employee);
    }
    if (filters.project) {
      results = results.filter(t => t.projectId === filters.project);
    }
    if (filters.status) {
      results = results.filter(t => t.status === filters.status);
    }
    if (filters.dateFrom) {
      results = results.filter(t => t.date >= filters.dateFrom);
    }
    if (filters.dateTo) {
      results = results.filter(t => t.date <= filters.dateTo);
    }

    // Role-based filtering
    if (this.state.currentRole === 'designer') {
      results = results.filter(t => t.employeeId === this.state.currentUser?.id);
    } else if (this.state.currentRole === 'manager') {
      const managedProjects = this.state.projects
        .filter(p => p.projectManagerId === this.state.currentUser?.id)
        .map(p => p.id);
      results = results.filter(t => managedProjects.includes(t.projectId));
    }

    return results.sort((a, b) => new Date(b.date) - new Date(a.date));
  }

  getProjects(filters = {}) {
    let results = [...this.state.projects];

    if (filters.status) {
      results = results.filter(p => p.status === filters.status);
    }
    if (filters.phase) {
      results = results.filter(p => p.phase === filters.phase);
    }
    if (filters.manager) {
      results = results.filter(p => p.projectManagerId === filters.manager);
    }
    if (filters.search) {
      const search = filters.search.toLowerCase();
      results = results.filter(p =>
        p.name.toLowerCase().includes(search) ||
        p.code.toLowerCase().includes(search)
      );
    }

    // Role-based filtering
    if (this.state.currentRole === 'designer') {
      results = results.filter(p => p.teamMembers.includes(this.state.currentUser?.id));
    } else if (this.state.currentRole === 'manager') {
      results = results.filter(p => p.projectManagerId === this.state.currentUser?.id);
    }

    return results;
  }

  getActivityEvents(filters = {}) {
    let results = [...this.state.activityEvents];

    if (filters.employee) {
      results = results.filter(a => a.employeeId === filters.employee);
    }
    if (filters.project) {
      results = results.filter(a => a.projectId === filters.project);
    }
    if (filters.state) {
      results = results.filter(a => a.state === filters.state);
    }
    if (filters.dateFrom) {
      results = results.filter(a => a.timestamp.split('T')[0] >= filters.dateFrom);
    }
    if (filters.dateTo) {
      results = results.filter(a => a.timestamp.split('T')[0] <= filters.dateTo);
    }

    // Role-based filtering
    if (this.state.currentRole === 'designer') {
      results = results.filter(a => a.employeeId === this.state.currentUser?.id);
    } else if (this.state.currentRole === 'manager') {
      const managedProjects = this.state.projects
        .filter(p => p.projectManagerId === this.state.currentUser?.id)
        .map(p => p.id);
      results = results.filter(a => managedProjects.includes(a.projectId));
    }

    return results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  }

  getQuotes(filters = {}) {
    let results = [...this.state.quotes];

    if (filters.status) {
      results = results.filter(q => q.status === filters.status);
    }
    if (filters.client) {
      results = results.filter(q => q.clientId === filters.client);
    }
    if (filters.dateFrom) {
      results = results.filter(q => q.date >= filters.dateFrom);
    }
    if (filters.dateTo) {
      results = results.filter(q => q.date <= filters.dateTo);
    }

    return results.sort((a, b) => new Date(b.date) - new Date(a.date));
  }

  getInvoices(filters = {}) {
    let results = [...this.state.invoices];

    if (filters.status) {
      results = results.filter(i => i.status === filters.status);
    }
    if (filters.client) {
      results = results.filter(i => i.clientId === filters.client);
    }
    if (filters.project) {
      results = results.filter(i => i.projectId === filters.project);
    }
    if (filters.dateFrom) {
      results = results.filter(i => i.date >= filters.dateFrom);
    }
    if (filters.dateTo) {
      results = results.filter(i => i.date <= filters.dateTo);
    }

    return results.sort((a, b) => new Date(b.date) - new Date(a.date));
  }

  getNotifications(userId = null) {
    const targetId = userId || this.state.currentUser?.id;
    return this.state.notifications
      .filter(n => n.userId === targetId)
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  }

  getUnreadNotificationCount(userId = null) {
    return this.getNotifications(userId).filter(n => !n.read).length;
  }

  // Actions
  toggleTheme() {
    this.set('theme', this.state.theme === 'light' ? 'dark' : 'light');
  }

  toggleSidebar() {
    this.set('sidebarCollapsed', !this.state.sidebarCollapsed);
  }

  toggleMobileSidebar() {
    this.set('sidebarOpen', !this.state.sidebarOpen);
  }

  closeMobileSidebar() {
    this.set('sidebarOpen', false);
  }

  navigate(page) {
    this.set('currentPage', page);
    this.closeMobileSidebar();
    window.scrollTo(0, 0);
  }

  openModal(modalType, data = null) {
    this.state.activeModal = modalType;
    this.state.modalData = data;
    this.emit('modalOpened', { modalType, data });
  }

  closeModal() {
    this.state.activeModal = null;
    this.state.modalData = null;
    this.emit('modalClosed');
  }

  showToast(type, title, message, duration = 5000) {
    const toast = {
      id: `toast-${Date.now()}`,
      type,
      title,
      message,
      duration
    };
    this.state.toasts.push(toast);
    this.emit('toastAdded', toast);

    if (duration > 0) {
      setTimeout(() => this.dismissToast(toast.id), duration);
    }

    return toast.id;
  }

  dismissToast(id) {
    const index = this.state.toasts.findIndex(t => t.id === id);
    if (index !== -1) {
      this.state.toasts.splice(index, 1);
      this.emit('toastRemoved', id);
    }
  }

  markNotificationRead(id) {
    const notification = this.state.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
      this.emit('notificationRead', notification);
    }
  }

  markAllNotificationsRead(userId = null) {
    const targetId = userId || this.state.currentUser?.id;
    this.state.notifications
      .filter(n => n.userId === targetId && !n.read)
      .forEach(n => n.read = true);
    this.emit('allNotificationsRead');
  }

  // Timesheet actions
  submitTimesheet(timesheetId) {
    const ts = this.state.timesheets.find(t => t.id === timesheetId);
    if (ts && ts.status === 'draft') {
      ts.status = 'submitted';
      ts.submittedAt = new Date().toISOString();
      this.emit('timesheetSubmitted', ts);
      this.showToast('success', 'Timesheet Submitted', 'Your timesheet has been submitted for approval');
    }
  }

  approveTimesheet(timesheetId, approverId) {
    const ts = this.state.timesheets.find(t => t.id === timesheetId);
    if (ts && ts.status === 'submitted') {
      ts.status = 'approved';
      ts.approvedAt = new Date().toISOString();
      ts.approvedBy = approverId;
      this.emit('timesheetApproved', ts);
      this.showToast('success', 'Timesheet Approved', 'Timesheet has been approved');
    }
  }

  rejectTimesheet(timesheetId, approverId, reason) {
    const ts = this.state.timesheets.find(t => t.id === timesheetId);
    if (ts && ts.status === 'submitted') {
      ts.status = 'rejected';
      ts.approvedAt = new Date().toISOString();
      ts.approvedBy = approverId;
      ts.rejectionReason = reason;
      this.emit('timesheetRejected', ts);
      this.showToast('warning', 'Timesheet Rejected', 'Timesheet has been returned for correction');
    }
  }

  // Quote calculator
  calculateQuoteTotals(items, markupPercent = 15, contingencyPercent = 10, discountPercent = 0, taxRate = 0.10) {
    const subtotal = items.reduce((sum, item) => sum + (item.quantity * item.rate), 0);
    const markupAmount = subtotal * (markupPercent / 100);
    const afterMarkup = subtotal + markupAmount;
    const contingencyAmount = afterMarkup * (contingencyPercent / 100);
    const afterContingency = afterMarkup + contingencyAmount;
    const discountAmount = afterContingency * (discountPercent / 100);
    const beforeTax = afterContingency - discountAmount;
    const taxAmount = beforeTax * taxRate;
    const total = beforeTax + taxAmount;

    // Estimated cost (internal cost basis)
    const estimatedCost = items.reduce((sum, item) => {
      const emp = this.state.employees.find(e => e.billableRate === item.rate);
      const costRate = emp?.hourlyCostRate || (item.rate * 0.6);
      return sum + (item.quantity * costRate);
    }, 0);

    const estimatedMargin = estimatedCost > 0 ? (total - estimatedCost) / total : 0;

    return {
      subtotal,
      markupPercent,
      markupAmount,
      contingencyPercent,
      contingencyAmount,
      discountPercent,
      discountAmount,
      taxAmount,
      total,
      estimatedCost,
      estimatedMargin
    };
  }

  // Event system
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index !== -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (e) {
          console.error(`Error in ${event} listener:`, e);
        }
      });
    }
  }
}

// Create global state instance
const State = new StateManager();
window.State = State;