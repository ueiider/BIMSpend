/* BIMSpend Router */
/* Client-side routing for SPA navigation */

class Router {
  constructor() {
    this.routes = new Map();
    this.currentRoute = null;
    this.beforeHooks = [];
    this.afterHooks = [];

    // Define routes
    this.defineRoutes();

    // Listen for popstate
    window.addEventListener('popstate', (e) => {
      if (e.state && e.state.route) {
        this.navigateTo(e.state.route, false);
      }
    });

    // Initial load
    this.handleInitialRoute();
  }

  defineRoutes() {
    // Public routes (all roles)
    this.addRoute('dashboard', '/', 'Executive Dashboard', ['administrator', 'manager', 'designer']);
    this.addRoute('live-activity', '/live-activity', 'Live Activity', ['administrator', 'manager']);
    this.addRoute('timesheets', '/timesheets', 'Timesheets', ['administrator', 'manager', 'designer']);
    this.addRoute('projects', '/projects', 'Projects', ['administrator', 'manager', 'designer']);
    this.addRoute('employees', '/employees', 'Employees & Team', ['administrator', 'manager']);
    this.addRoute('financial', '/financial', 'Financial Management', ['administrator', 'manager']);
    this.addRoute('quotes', '/quotes', 'Quotes & Estimates', ['administrator', 'manager']);
    this.addRoute('reports', '/reports', 'Reports & Analytics', ['administrator', 'manager']);
    this.addRoute('clients', '/clients', 'Clients', ['administrator', 'manager']);
    this.addRoute('billing', '/billing', 'Billing & Invoices', ['administrator', 'manager']);
    this.addRoute('integrations', '/integrations', 'Integrations', ['administrator']);
    this.addRoute('notifications', '/notifications', 'Notifications', ['administrator', 'manager', 'designer']);
    this.addRoute('company-settings', '/settings', 'Company Settings', ['administrator']);
    this.addRoute('profile', '/profile', 'User Profile', ['administrator', 'manager', 'designer']);
    this.addRoute('desktop-agent', '/desktop-agent', 'Desktop Agent', ['administrator', 'manager', 'designer']);
    this.addRoute('onboarding', '/onboarding', 'Onboarding', ['administrator']);

    // Designer-specific routes
    this.addRoute('my-dashboard', '/my-dashboard', 'My Overview', ['designer']);
    this.addRoute('my-activity', '/my-activity', 'My Activity', ['designer']);
    this.addRoute('my-timesheets', '/my-timesheets', 'My Timesheets', ['designer']);
    this.addRoute('my-projects', '/my-projects', 'My Projects', ['designer']);

    // Detail routes with params
    this.addRoute('project-detail', '/projects/:id', 'Project Details', ['administrator', 'manager', 'designer']);
    this.addRoute('employee-detail', '/employees/:id', 'Employee Details', ['administrator', 'manager']);
    this.addRoute('client-detail', '/clients/:id', 'Client Details', ['administrator', 'manager']);
    this.addRoute('quote-detail', '/quotes/:id', 'Quote Details', ['administrator', 'manager']);
    this.addRoute('quote-builder', '/quotes/new', 'Create Quote', ['administrator', 'manager']);
    this.addRoute('invoice-detail', '/invoices/:id', 'Invoice Details', ['administrator', 'manager']);
  }

  addRoute(name, path, title, allowedRoles = []) {
    // Convert path to regex
    const paramNames = [];
    const regexPath = path.replace(/:([^/]+)/g, (_, paramName) => {
      paramNames.push(paramName);
      return '([^/]+)';
    });

    this.routes.set(name, {
      name,
      path,
      regex: new RegExp(`^${regexPath}$`),
      paramNames,
      title,
      allowedRoles
    });
  }

  matchRoute(pathname) {
    for (const [name, route] of this.routes) {
      const match = pathname.match(route.regex);
      if (match) {
        const params = {};
        route.paramNames.forEach((paramName, index) => {
          params[paramName] = match[index + 1];
        });
        return { route, params };
      }
    }
    return null;
  }

  canAccess(routeName, role) {
    const route = this.routes.get(routeName);
    if (!route) return false;
    if (route.allowedRoles.length === 0) return true;
    return route.allowedRoles.includes(role);
  }

  handleInitialRoute() {
    const path = window.location.pathname;
    const match = this.matchRoute(path);
    if (match) {
      this.currentRoute = match.route.name;
      this.currentParams = match.params;
      State.set('currentPage', match.route.name);
    } else {
      this.navigate('dashboard');
    }
  }

  navigate(routeName, params = {}, pushState = true) {
    const route = this.routes.get(routeName);
    if (!route) {
      console.warn(`Route not found: ${routeName}`);
      return false;
    }

    // Check role access
    if (!this.canAccess(routeName, State.getCurrentRole())) {
      State.showToast('error', 'Access Denied', `You don't have permission to access ${route.title}`);
      return false;
    }

    // Build URL
    let url = route.path;
    route.paramNames.forEach(paramName => {
      url = url.replace(`:${paramName}`, params[paramName] || '');
    });

    // Run before hooks
    for (const hook of this.beforeHooks) {
      const result = hook(routeName, params, this.currentRoute);
      if (result === false) return false;
    }

    // Update state
    const previousRoute = this.currentRoute;
    this.currentRoute = routeName;
    this.currentParams = params;

    State.set('currentPage', routeName);

    // Update URL
    if (pushState) {
      window.history.pushState({ route: routeName, params }, '', url);
    }

    // Update breadcrumbs
    this.updateBreadcrumbs(routeName, params);

    // Run after hooks
    for (const hook of this.afterHooks) {
      hook(routeName, params, previousRoute);
    }

    return true;
  }

  navigateTo(pathname, pushState = true) {
    const match = this.matchRoute(pathname);
    if (match) {
      return this.navigate(match.route.name, match.params, pushState);
    }
    return false;
  }

  updateBreadcrumbs(routeName, params) {
    const route = this.routes.get(routeName);
    const breadcrumbs = [];

    // Home
    breadcrumbs.push({ label: 'Home', route: 'dashboard' });

    // Section mapping
    const sectionMap = {
      'live-activity': 'Time & Projects',
      'timesheets': 'Time & Projects',
      'projects': 'Time & Projects',
      'employees': 'Time & Projects',
      'financial': 'Commercial',
      'quotes': 'Commercial',
      'reports': 'Commercial',
      'clients': 'Commercial',
      'billing': 'Commercial',
      'integrations': 'Administration',
      'notifications': 'Administration',
      'company-settings': 'Administration',
      'my-dashboard': 'My Workspace',
      'my-activity': 'My Workspace',
      'my-timesheets': 'My Workspace',
      'my-projects': 'My Workspace'
    };

    if (sectionMap[routeName] && sectionMap[routeName] !== 'Home') {
      breadcrumbs.push({ label: sectionMap[routeName] });
    }

    // Current page
    let title = route.title;
    if (params.id) {
      if (routeName === 'project-detail') {
        const project = State.getProject(params.id);
        title = project ? project.name : 'Project Details';
      } else if (routeName === 'employee-detail') {
        const emp = State.getEmployee(params.id);
        title = emp ? `${emp.firstName} ${emp.lastName}` : 'Employee Details';
      } else if (routeName === 'client-detail') {
        const client = State.getClient(params.id);
        title = client ? client.name : 'Client Details';
      } else if (routeName === 'quote-detail') {
        const quote = State.getQuotes().find(q => q.id === params.id);
        title = quote ? quote.quoteNumber : 'Quote Details';
      } else if (routeName === 'invoice-detail') {
        const invoice = State.getInvoices().find(i => i.id === params.id);
        title = invoice ? invoice.invoiceNumber : 'Invoice Details';
      }
    }
    breadcrumbs.push({ label: title });

    State.state.breadcrumbs = breadcrumbs;
    State.emit('breadcrumbsChanged', breadcrumbs);
  }

  // Hooks
  beforeEach(hook) {
    this.beforeHooks.push(hook);
  }

  afterEach(hook) {
    this.afterHooks.push(hook);
  }

  // Getters
  getCurrentRoute() {
    return this.currentRoute;
  }

  getCurrentParams() {
    return this.currentParams;
  }

  getRouteTitle(routeName) {
    const route = this.routes.get(routeName);
    return route?.title || routeName;
  }
}

// Create global router instance
const RouterInstance = new Router();
window.RouterInstance = RouterInstance;