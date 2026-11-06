/* BIMSpend Screen Components */
/* All 16 application screens */

const Screens = {};

// Helper: Get filtered data based on current role
function getVisibleData() {
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();

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

// ==================== 01. EXECUTIVE DASHBOARD ====================
Screens.dashboard = function() {
  const data = getVisibleData();
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();

  // Calculate KPIs
  const totalTrackedHours = data.timesheets.reduce((sum, t) => sum + t.hours, 0);
  const billableHours = data.timesheets
    .filter(t => t.status === 'approved' || t.status === 'billed')
    .reduce((sum, t) => sum + t.hours, 0);
  const nonBillableHours = totalTrackedHours - billableHours;
  const activeProjects = data.projects.filter(p => p.status === 'active').length;
  const pendingApprovals = data.timesheets.filter(t => t.status === 'submitted').length;
  const totalRevenue = data.projects.reduce((sum, p) => sum + (p.billedRevenue || 0), 0);
  const totalCost = data.projects.reduce((sum, p) => sum + (p.approvedCost || 0), 0);

  // Recent activity for designer view
  const myTimesheets = data.timesheets.filter(t => t.employeeId === user?.id).slice(0, 5);
  const myProjects = data.projects.slice(0, 4);
  const myActivity = data.activity.filter(a => a.employeeId === user?.id).slice(0, 5);

  const content = UI.createElement('div', {});

  // Page header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, role === 'designer' ? 'My Overview' : 'Executive Dashboard'),
      UI.createElement('p', { class: 'text-secondary mt-1' },
        role === 'designer'
          ? `Welcome back, ${user?.firstName}. Here's your activity summary.`
          : 'Company-wide project health, time tracking, and financial overview.'
      )
    ]),
    UI.createButton({ text: 'Export Report', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' })
  ]));

  // Date range selector
  content.appendChild(UI.createElement('div', { class: 'flex items-center gap-3 mb-6 flex-wrap' }, [
    UI.createElement('label', { class: 'text-sm text-secondary' }, 'Period:'),
    UI.createSelect({
      options: [
        { value: 'today', label: 'Today' },
        { value: 'week', label: 'This Week', selected: true },
        { value: 'month', label: 'This Month' },
        { value: 'quarter', label: 'This Quarter' },
        { value: 'year', label: 'This Year' },
        { value: 'custom', label: 'Custom Range' }
      ],
      onChange: (val) => console.log('Period changed:', val)
    }),
    role !== 'designer' && UI.createButton({ text: 'Custom Report', variant: 'ghost', size: 'sm' })
  ].filter(Boolean)));

  // KPI Cards
  if (role === 'designer') {
    // Designer KPIs
    content.appendChild(UI.createElement('div', { class: 'kpi-grid' }, [
      UI.createKPICard({
        label: 'My Hours This Week',
        value: UI.formatNumber(myTimesheets.reduce((s, t) => s + t.hours, 0), 1),
        subvalue: `${myTimesheets.length} entries`,
        trend: { value: '+2.5', label: 'vs last week', type: 'positive' },
        icon: '⏱'
      }),
      UI.createKPICard({
        label: 'Billable Hours',
        value: UI.formatNumber(
          myTimesheets.filter(t => t.status === 'approved' || t.status === 'billed').reduce((s, t) => s + t.hours, 0), 1
        ),
        subvalue: 'Approved & billed',
        trend: { value: '+1.2', label: 'vs last week', type: 'positive' },
        icon: '$',
        iconBg: 'teal'
      }),
      UI.createKPICard({
        label: 'Pending Approval',
        value: myTimesheets.filter(t => t.status === 'submitted').length,
        subvalue: 'Awaiting review',
        trend: { value: '0', label: 'no change', type: 'neutral' },
        icon: '⏳',
        iconBg: 'amber'
      }),
      UI.createKPICard({
        label: 'Active Projects',
        value: myProjects.length,
        subvalue: 'Assigned to you',
        trend: { value: '0', label: 'no change', type: 'neutral' },
        icon: '📁',
        iconBg: 'primary'
      })
    ]));
  } else {
    // Manager/Admin KPIs
    content.appendChild(UI.createElement('div', { class: 'kpi-grid' }, [
      UI.createKPICard({
        label: 'Total Tracked Hours',
        value: UI.formatNumber(totalTrackedHours, 1),
        subvalue: 'All time this period',
        trend: { value: '+8.3%', label: 'vs last period', type: 'positive' },
        icon: '⏱'
      }),
      UI.createKPICard({
        label: 'Billable vs Non-Billable',
        value: `${Math.round((billableHours / totalTrackedHours) * 100) || 0}%`,
        subvalue: `${UI.formatNumber(billableHours, 1)}h billable / ${UI.formatNumber(nonBillableHours, 1)}h non-billable`,
        trend: { value: '+1.2%', label: 'billable rate', type: 'positive' },
        icon: '$',
        iconBg: 'teal'
      }),
      UI.createKPICard({
        label: 'Active Projects',
        value: activeProjects,
        subvalue: `${data.projects.length} total projects`,
        trend: { value: '+2', label: 'new this month', type: 'positive' },
        icon: '📁',
        iconBg: 'primary'
      }),
      UI.createKPICard({
        label: 'Pending Approvals',
        value: pendingApprovals,
        subvalue: 'Timesheets awaiting review',
        trend: { value: '-3', label: 'vs yesterday', type: 'positive' },
        icon: '⏳',
        iconBg: 'amber'
      }),
      UI.createKPICard({
        label: 'Revenue (Period)',
        value: UI.formatCurrency(totalRevenue),
        subvalue: 'Billed revenue',
        trend: { value: '+12.5%', label: 'vs last period', type: 'positive' },
        icon: '$',
        iconBg: 'green'
      }),
      UI.createKPICard({
        label: 'Gross Margin',
        value: totalRevenue > 0 ? `${(((totalRevenue - totalCost) / totalRevenue) * 100).toFixed(1)}%` : '0%',
        subvalue: UI.formatCurrency(totalRevenue - totalCost),
        trend: { value: '+0.8%', label: 'margin improvement', type: 'positive' },
        icon: '📈',
        iconBg: 'teal'
      })
    ]));
  }

  // Charts Row
  const chartsRow = UI.createElement('div', { class: 'd-grid gap-4', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' });

  // Project Profitability Chart
  chartsRow.appendChild(Charts.createProjectProfitabilityChart(data.projects.filter(p => p.status === 'active')));

  // Utilization or Activity Chart
  if (role === 'designer') {
    // My Activity Breakdown
    const activityByClass = {};
    myActivity.forEach(a => {
      activityByClass[a.classification] = (activityByClass[a.classification] || 0) + a.duration;
    });
    const activityData = Object.entries(activityByClass).map(([classification, hours]) => ({
      classification,
      hours: hours / 60 // convert to hours
    }));
    chartsRow.appendChild(Charts.createActivityDonut(activityData));
  } else {
    // Team Utilization
    const teamMembers = data.employees.filter(e => e.role === 'designer' && e.status === 'active');
    const utilizationData = teamMembers.map(e => {
      const myTs = data.timesheets.filter(t => t.employeeId === e.id);
      const billable = myTs.filter(t => t.status === 'approved' || t.status === 'billed').reduce((s, t) => s + t.hours, 0);
      const available = 38 * 4; // 4 weeks * 38h/week (approx)
      return { ...e, billableHours: billable, availableHours: available, utilization: available > 0 ? (billable / available) * 100 : 0 };
    });
    chartsRow.appendChild(Charts.createUtilizationChart(utilizationData));
  }

  content.appendChild(chartsRow);

  // Second row - Alerts & Quick Actions
  const secondRow = UI.createElement('div', { class: 'd-grid gap-4 mt-4', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' });

  // Alerts / Items needing attention
  const alerts = [];
  if (role !== 'designer') {
    // Budget warnings
    data.projects.filter(p => p.status === 'active').forEach(p => {
      const pct = p.budgetHours > 0 ? (p.approvedHours / p.budgetHours) * 100 : 0;
      if (pct > 90) {
        alerts.push({ type: 'danger', title: 'Budget Exceeded', message: `${p.name} at ${pct.toFixed(0)}% of budgeted hours` });
      } else if (pct > 80) {
        alerts.push({ type: 'warning', title: 'Budget Warning', message: `${p.name} at ${pct.toFixed(0)}% of budgeted hours` });
      }
    });
    // Overdue invoices
    data.invoices.filter(i => i.status === 'overdue').forEach(i => {
      alerts.push({ type: 'danger', title: 'Invoice Overdue', message: `${i.invoiceNumber} (${UI.formatCurrency(i.balance)}) overdue` });
    });
  } else {
    // Designer alerts
    const unsubmitted = myTimesheets.filter(t => t.status === 'draft').length;
    if (unsubmitted > 0) alerts.push({ type: 'warning', title: 'Draft Timesheets', message: `${unsubmitted} draft timesheet${unsubmitted > 1 ? 's' : ''} need submission` });
    const rejected = myTimesheets.filter(t => t.status === 'rejected').length;
    if (rejected > 0) alerts.push({ type: 'danger', title: 'Returned Timesheets', message: `${rejected} timesheet${rejected > 1 ? 's' : ''} returned for correction` });
    const unclassified = myActivity.filter(a => !a.projectId).length;
    if (unclassified > 0) alerts.push({ type: 'info', title: 'Unclassified Activity', message: `${unclassified} activity entr${unclassified > 1 ? 'ies' : 'y'} need project attribution` });
  }

  secondRow.appendChild(UI.createCard({
    title: role === 'designer' ? 'My Alerts' : 'Alerts Requiring Attention',
    children: alerts.length > 0
      ? alerts.map(a => UI.createElement('div', {
        class: 'd-flex gap-3 p-3',
        style: 'background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md);'
      }, [
        UI.createElement('div', { class: `text-${a.type}` }, a.type === 'danger' ? '⚠' : a.type === 'warning' ? '⚠' : 'ℹ'),
        UI.createElement('div', { class: 'flex-1' }, [
          UI.createElement('div', { class: 'fw-medium' }, a.title),
          UI.createElement('div', { class: 'text-sm text-secondary' }, a.message)
        ]),,
        UI.createButton({ text: 'View', variant: 'ghost', size: 'sm' })
      ]))
      : UI.createElement('div', { class: 'text-center text-muted py-8' }, 'No alerts at this time. Great job!')
  }));

  // Quick Actions / Recent Activity
  if (role === 'designer') {
    // My Recent Timesheets
    secondRow.appendChild(UI.createCard({
      title: 'My Recent Timesheets',
      actions: [UI.createButton({ text: 'View All', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('my-timesheets') })],
      children: myTimesheets.length > 0
        ? UI.createTable({
          columns: [
            { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
            { field: 'projectId', header: 'Project', render: (r) => {
              const p = State.getProject(r.projectId);
              return p ? p.code : r.projectId;
            }},
            { field: 'hours', header: 'Hours', render: (r) => UI.formatNumber(r.hours, 1) },
            { field: 'status', header: 'Status', render: (r) => UI.createBadge(UI.formatStatus(r.status), r.status) },
            { field: 'description', header: 'Description' }
          ],
          data: myTimesheets
        })
        : UI.createEmptyState({ title: 'No timesheets yet', message: 'Start tracking your time to see entries here.', action: { text: 'Create Timesheet', onClick: () => RouterInstance.navigate('my-timesheets') } })
    }));
  } else {
    // Pending Approvals Queue
    const pendingTs = data.timesheets.filter(t => t.status === 'submitted').slice(0, 10);
    secondRow.appendChild(UI.createCard({
      title: 'Timesheets Awaiting Approval',
      actions: [UI.createButton({ text: 'Review All', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('timesheets') })],
      children: pendingTs.length > 0
        ? UI.createTable({
          columns: [
            { field: 'employeeId', header: 'Employee', render: (r) => {
              const e = State.getEmployee(r.employeeId);
              return e ? `${e.firstName} ${e.lastName}` : r.employeeId;
            }},
            { field: 'projectId', header: 'Project', render: (r) => {
              const p = State.getProject(r.projectId);
              return p ? p.code : r.projectId;
            }},
            { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
            { field: 'hours', header: 'Hours', render: (r) => UI.formatNumber(r.hours, 1) },
            { field: 'status', header: 'Status', render: (r) => UI.createBadge('Submitted', 'pending') },
            { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
              UI.createButton({ text: 'Approve', variant: 'success', size: 'sm', onClick: () => { State.approveTimesheet(r.id, State.getCurrentUser().id); Screens.renderCurrent(); } }),
              UI.createButton({ text: 'Review', variant: 'secondary', size: 'sm', onClick: () => Screens.showTimesheetDetail(r.id) })
            ])}
          ],
          data: pendingTs
        })
        : UI.createElement('div', { class: 'text-center text-muted py-8' }, 'No pending approvals. All caught up!')
    }));
  }

  content.appendChild(secondRow);

  return content;
};

// ==================== 02. LIVE ACTIVITY ====================
Screens['live-activity'] = function() {
  const data = getVisibleData();
  const role = State.getCurrentRole();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Live Activity'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Real-time view of team activity and project attribution.')
    ]),
    UI.createElement('div', { class: 'flex gap-2' }, [
      UI.createButton({ text: 'Refresh', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>', onClick: () => Screens.renderCurrent() }),
      UI.createButton({ text: 'Auto-refresh: ON', variant: 'ghost', size: 'sm' })
    ])
  ]));

  // Filters
  content.appendChild(UI.createElement('div', { class: 'card mb-6' }, [
    UI.createElement('div', { class: 'card-body' }, [
      UI.createElement('div', { class: 'd-flex flex-wrap gap-4' }, [
        UI.createSelect({
          label: 'Employee',
          options: [{ value: '', label: 'All Employees' }, ...data.employees.map(e => ({ value: e.id, label: `${e.firstName} ${e.lastName} (${e.department})` }))],
          value: State.getFilters('activity').employee,
          onChange: (v) => { State.setFilter('activity', 'employee', v); Screens.renderCurrent(); }
        }),
        UI.createSelect({
          label: 'Project',
          options: [{ value: '', label: 'All Projects' }, ...data.projects.map(p => ({ value: p.id, label: `${p.code} - ${p.name}` }))],
          value: State.getFilters('activity').project,
          onChange: (v) => { State.setFilter('activity', 'project', v); Screens.renderCurrent(); }
        }),
        UI.createSelect({
          label: 'State',
          options: [
            { value: '', label: 'All States' },
            { value: 'productive', label: 'Productive' },
            { value: 'idle', label: 'Idle' },
            { value: 'unclassified', label: 'Unclassified' }
          ],
          value: State.getFilters('activity').state,
          onChange: (v) => { State.setFilter('activity', 'state', v); Screens.renderCurrent(); }
        }),
        UI.createButton({ text: 'Clear Filters', variant: 'ghost', size: 'sm', onClick: () => { State.resetFilters('activity'); Screens.renderCurrent(); } })
      ])
    ])
  ]));

  // Summary Cards
  const activeNow = data.activity.filter(a => new Date(a.timestamp) > new Date(Date.now() - 30 * 60 * 1000)).length;
  const productiveNow = data.activity.filter(a => a.state === 'productive' && new Date(a.timestamp) > new Date(Date.now() - 30 * 60 * 1000)).length;
  const unclassifiedCount = data.activity.filter(a => a.state === 'unclassified' || !a.projectId).length;

  content.appendChild(UI.createElement('div', { class: 'kpi-grid mb-6' }, [
    UI.createKPICard({ label: 'Active Now', value: activeNow, subvalue: 'Last 30 minutes', icon: '🟢', iconBg: 'teal' }),
    UI.createKPICard({ label: 'Productive', value: productiveNow, subvalue: `${activeNow > 0 ? Math.round((productiveNow/activeNow)*100) : 0}% of active`, icon: '⚡', iconBg: 'primary' }),
    UI.createKPICard({ label: 'Unclassified', value: unclassifiedCount, subvalue: 'Need attribution', icon: '❓', iconBg: 'amber' }),
    UI.createKPICard({ label: 'Tracking Status', value: 'Online', subvalue: 'All agents connected', icon: '🔗', iconBg: 'green' })
  ]));

  // Activity Timeline Table
  const activityColumns = [
    { field: 'timestamp', header: 'Time', render: (r) => UI.formatDateTime(r.timestamp) },
    { field: 'employeeId', header: 'Employee', render: (r) => {
      const e = State.getEmployee(r.employeeId);
      return e ? UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
        UI.createAvatar(`${e.firstName} ${e.lastName}`, 24),
        UI.createElement('span', {}, `${e.firstName} ${e.lastName}`)
      ]) : r.employeeId;
    }},
    { field: 'application', header: 'Application' },
    { field: 'projectId', header: 'Project', render: (r) => {
      if (!r.projectId) return UI.createBadge('Unassigned', 'observed');
      const p = State.getProject(r.projectId);
      return p ? UI.createElement('span', { class: 'fw-medium' }, p.code) : r.projectId;
    }},
    { field: 'classification', header: 'Classification' },
    { field: 'state', header: 'State', render: (r) => UI.createBadge(UI.formatStatus(r.state), r.state) },
    { field: 'confidence', header: 'Confidence', render: (r) => UI.createElement('span', { class: `confidence-chip ${UI.getConfidenceChipClass(r.confidence)}` }, r.confidence) },
    { field: 'duration', header: 'Duration (min)', render: (r) => r.duration }
  ];

  // Hide employee column for designer view
  const columns = role === 'designer' ? activityColumns.filter(c => c.field !== 'employeeId') : activityColumns;

  content.appendChild(UI.createCard({
    title: 'Activity Timeline',
    children: UI.createTable({
      columns,
      data: data.activity.slice(0, 50),
      emptyMessage: 'No activity recorded for the selected filters.'
    })
  }));

  return content;
};

// ==================== 03. TIMESHEETS ====================
Screens.timesheets = function() {
  const data = getVisibleData();
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, role === 'designer' ? 'My Timesheets' : 'Timesheets'),
      UI.createElement('p', { class: 'text-secondary mt-1' },
        role === 'designer' ? 'Manage your time entries and submissions.' : 'Review, approve, and manage team timesheets.'
      )
    ]),
    UI.createElement('div', { class: 'flex gap-2' }, [
      role !== 'designer' && UI.createButton({ text: 'Bulk Approve', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>' }),
      UI.createButton({ text: 'New Entry', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => Screens.showTimesheetModal() })
    ].filter(Boolean))
  ]));

  // View Tabs
  const tabs = role === 'designer'
    ? [
      { id: 'draft', label: 'Draft', count: data.timesheets.filter(t => t.status === 'draft' && t.employeeId === user.id).length },
      { id: 'submitted', label: 'Submitted', count: data.timesheets.filter(t => t.status === 'submitted' && t.employeeId === user.id).length },
      { id: 'approved', label: 'Approved', count: data.timesheets.filter(t => t.status === 'approved' && t.employeeId === user.id).length },
      { id: 'rejected', label: 'Returned', count: data.timesheets.filter(t => t.status === 'rejected' && t.employeeId === user.id).length },
      { id: 'billed', label: 'Billed', count: data.timesheets.filter(t => t.status === 'billed' && t.employeeId === user.id).length }
    ]
    : [
      { id: 'all', label: 'All', count: data.timesheets.length },
      { id: 'draft', label: 'Draft', count: data.timesheets.filter(t => t.status === 'draft').length },
      { id: 'submitted', label: 'Pending Review', count: data.timesheets.filter(t => t.status === 'submitted').length },
      { id: 'approved', label: 'Approved', count: data.timesheets.filter(t => t.status === 'approved').length },
      { id: 'rejected', label: 'Returned', count: data.timesheets.filter(t => t.status === 'rejected').length },
      { id: 'billed', label: 'Billed', count: data.timesheets.filter(t => t.status === 'billed').length }
    ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-4' }, tabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${!content.dataset.activeTab && tab.id === 'all' ? 'active' : tab.id === 'draft' && !content.dataset.activeTab ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        content.dataset.activeTab = tab.id;
        Screens.renderTimesheetTable(content, tab.id);
      }
    }, tab.label + (tab.count > 0 ? ' <span class="badge badge-draft" style="margin-left: 6px; font-size: 10px;">' + tab.count + '</span>' : ''))
  )));

  // Table container
  const tableContainer = UI.createElement('div', { id: 'timesheet-table-container' });
  content.appendChild(tableContainer);

  // Initial render
  setTimeout(() => Screens.renderTimesheetTable(tableContainer, 'all'), 0);

  return content;
};

Screens.renderTimesheetTable = function(container, statusFilter) {
  const data = getVisibleData();
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();

  let timesheets = data.timesheets;
  if (statusFilter && statusFilter !== 'all') {
    timesheets = timesheets.filter(t => t.status === statusFilter);
  }
  if (role === 'designer') {
    timesheets = timesheets.filter(t => t.employeeId === user.id);
  }

  const columns = [
    { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
    { field: 'employeeId', header: 'Employee', render: (r) => {
      const e = State.getEmployee(r.employeeId);
      return e ? `${e.firstName} ${e.lastName}` : r.employeeId;
    }},
    { field: 'projectId', header: 'Project', render: (r) => {
      const p = State.getProject(r.projectId);
      return p ? UI.createElement('div', {}, [
        UI.createElement('div', { class: 'fw-medium' }, p.code),
        UI.createElement('div', { class: 'text-xs text-muted' }, p.name)
      ]) : r.projectId;
    }},
    { field: 'hours', header: 'Hours', render: (r) => UI.formatNumber(r.hours, 1) },
    { field: 'description', header: 'Description' },
    { field: 'source', header: 'Source', render: (r) => UI.createBadge(r.source, r.source === 'suggested' ? 'suggested' : 'draft') },
    { field: 'status', header: 'Status', render: (r) => UI.createBadge(UI.formatStatus(r.status), r.status) },
    { field: 'actions', header: 'Actions', render: (r) => {
      const actions = [];
      if (role === 'designer') {
        if (r.status === 'draft') {
          actions.push(UI.createButton({ text: 'Submit', variant: 'primary', size: 'sm', onClick: () => { State.submitTimesheet(r.id); Screens.renderCurrent(); } }));
          actions.push(UI.createButton({ text: 'Edit', variant: 'ghost', size: 'sm', onClick: () => Screens.showTimesheetModal(r) }));
        } else if (r.status === 'rejected') {
          actions.push(UI.createButton({ text: 'Correct', variant: 'primary', size: 'sm', onClick: () => Screens.showTimesheetModal(r) }));
        }
        actions.push(UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => Screens.showTimesheetDetail(r.id) }));
      } else {
        if (r.status === 'submitted') {
          actions.push(UI.createButton({ text: 'Approve', variant: 'success', size: 'sm', onClick: () => { State.approveTimesheet(r.id, user.id); Screens.renderCurrent(); } }));
          actions.push(UI.createButton({ text: 'Return', variant: 'danger', size: 'sm', onClick: () => {
            const reason = prompt('Reason for returning:');
            if (reason) { State.rejectTimesheet(r.id, user.id, reason); Screens.renderCurrent(); }
          } }));
        }
        actions.push(UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => Screens.showTimesheetDetail(r.id) }));
      }
      return UI.createElement('div', { class: 'table-cell-actions' }, actions);
    }}
  ];

  // Hide employee column for designer
  const finalColumns = role === 'designer' ? columns.filter(c => c.field !== 'employeeId') : columns;

  container.innerHTML = '';
  container.appendChild(UI.createTable({
    columns: finalColumns,
    data: timesheets,
    emptyMessage: 'No timesheets found for the selected filter.'
  }));
};

// Timesheet Modal
Screens.showTimesheetModal = function(timesheet = null) {
  const data = getVisibleData();
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();
  const isEdit = !!timesheet;

  const form = UI.createElement('form', { onSubmit: (e) => { e.preventDefault(); Screens.saveTimesheet(form, timesheet); } }, [
    UI.createElement('div', { class: 'form-row' }, [
      UI.createSelect({
        label: 'Project',
        name: 'projectId',
        options: data.projects.filter(p => p.status === 'active').map(p => ({ value: p.id, label: `${p.code} - ${p.name}` })),
        value: timesheet?.projectId || '',
        required: true
      }),
      UI.createInput({ label: 'Date', type: 'date', name: 'date', value: timesheet?.date || new Date().toISOString().split('T')[0], required: true })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Hours', type: 'number', name: 'hours', step: '0.5', min: '0.5', max: '12', value: timesheet?.hours || '', required: true }),
      UI.createSelect({
        label: 'Source',
        name: 'source',
        options: [
          { value: 'manual', label: 'Manual Entry' },
          { value: 'suggested', label: 'From Suggested Activity' }
        ],
        value: timesheet?.source || 'manual'
      })
    ]),
    UI.createInput({ label: 'Description', name: 'description', placeholder: 'Describe the work performed...', value: timesheet?.description || '', required: true }),
    UI.createElement('div', { class: 'flex justify-end gap-3 mt-6' }, [
      UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => UI.closeModal(UI.createModal.lastId) }),
      UI.createButton({ text: isEdit ? 'Save Changes' : 'Create Entry', variant: 'primary', type: 'submit' })
    ])
  ]);

  const modal = UI.createModal({
    title: isEdit ? 'Edit Timesheet Entry' : 'New Timesheet Entry',
    children: [form],
    size: 'md'
  });

  UI.createModal.lastId = modal.id;
};

Screens.saveTimesheet = function(form, existing) {
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.hours = parseFloat(data.hours);

  if (existing) {
    Object.assign(existing, data);
    UI.showToast('success', 'Timesheet Updated', 'Your timesheet entry has been saved.');
  } else {
    const newTs = {
      id: `ts-${Date.now()}`,
      employeeId: State.getCurrentUser().id,
      ...data,
      status: 'draft',
      source: data.source || 'manual',
      submittedAt: null,
      approvedAt: null,
      approvedBy: null,
      billedHours: null,
      billedAt: null
    };
    State.state.timesheets.unshift(newTs);
    UI.showToast('success', 'Timesheet Created', 'New timesheet entry added as draft.');
  }

  UI.closeModal(UI.createModal.lastId);
  Screens.renderCurrent();
};

Screens.showTimesheetDetail = function(timesheetId) {
  const ts = State.state.timesheets.find(t => t.id === timesheetId);
  if (!ts) return;

  const emp = State.getEmployee(ts.employeeId);
  const proj = State.getProject(ts.projectId);

  const modal = UI.createModal({
    title: 'Timesheet Details',
    size: 'md',
    children: [
      UI.createElement('div', { class: 'd-grid gap-4' }, [
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Employee'),
          UI.createElement('span', { class: 'fw-medium' }, emp ? `${emp.firstName} ${emp.lastName}` : ts.employeeId)
        ]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Project'),
          UI.createElement('span', { class: 'fw-medium' }, proj ? `${proj.code} - ${proj.name}` : ts.projectId)
        ]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Date'),
          UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(ts.date))
        ]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Hours'),
          UI.createElement('span', { class: 'fw-medium' }, UI.formatNumber(ts.hours, 1))
        ]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Status'),
          UI.createElement('span', {}, UI.createBadge(UI.formatStatus(ts.status), ts.status))
        ]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Source'),
          UI.createElement('span', {}, UI.createBadge(ts.source, ts.source))
        ]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Description'),
          UI.createElement('span', { class: 'fw-medium' }, ts.description)
        ]),
        ts.submittedAt && UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Submitted'),
          UI.createElement('span', { class: 'fw-medium' }, UI.formatDateTime(ts.submittedAt))
        ]),
        ts.approvedAt && UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Approved'),
          UI.createElement('span', { class: 'fw-medium' }, UI.formatDateTime(ts.approvedAt))
        ]),
        ts.rejectionReason && UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Rejection Reason'),
          UI.createElement('span', { class: 'text-danger' }, ts.rejectionReason)
        ]),
        ts.billedAt && UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('span', { class: 'text-secondary' }, 'Billed'),
          UI.createElement('span', { class: 'fw-medium' }, UI.formatDateTime(ts.billedAt))
        ])
      ].filter(Boolean))
    ]
  });
};

// ==================== 04. PROJECTS ====================
Screens.projects = function() {
  const data = getVisibleData();
  const role = State.getCurrentRole();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Projects'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Manage and monitor all projects.')
    ]),
    role !== 'designer' && UI.createButton({ text: 'New Project', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => Screens.showProjectModal() })
  ].filter(Boolean)));

  // Filters
  content.appendChild(UI.createElement('div', { class: 'card mb-6' }, [
    UI.createElement('div', { class: 'card-body' }, [
      UI.createElement('div', { class: 'd-flex flex-wrap gap-4' }, [
        UI.createInput({ label: 'Search', placeholder: 'Search projects...', value: State.getFilters('projects').search, onChange: (v) => { State.setFilter('projects', 'search', v); Screens.renderCurrent(); } }),
        UI.createSelect({ label: 'Status', options: [{ value: '', label: 'All Status' }, { value: 'active', label: 'Active' }, { value: 'completed', label: 'Completed' }, { value: 'on-hold', label: 'On Hold' }, { value: 'cancelled', label: 'Cancelled' }], value: State.getFilters('projects').status, onChange: (v) => { State.setFilter('projects', 'status', v); Screens.renderCurrent(); } }),
        UI.createSelect({ label: 'Phase', options: [{ value: '', label: 'All Phases' }, { value: 'tender', label: 'Tender' }, { value: 'design-development', label: 'Design Development' }, { value: 'construction-docs', label: 'Construction Docs' }, { value: 'construction', label: 'Construction' }, { value: 'completed', label: 'Completed' }], value: State.getFilters('projects').phase, onChange: (v) => { State.setFilter('projects', 'phase', v); Screens.renderCurrent(); } }),
        UI.createButton({ text: 'Clear', variant: 'ghost', size: 'sm', onClick: () => { State.resetFilters('projects'); Screens.renderCurrent(); } })
      ])
    ])
  ]));

  // Project Table
  const projectColumns = [
    { field: 'code', header: 'Code', render: (r) => UI.createElement('span', { class: 'fw-medium' }, r.code) },
    { field: 'name', header: 'Project Name' },
    { field: 'clientId', header: 'Client', render: (r) => {
      const c = State.getClient(r.clientId);
      return c ? c.name : r.clientId;
    }},
    { field: 'projectManagerId', header: 'Manager', render: (r) => {
      const m = State.getEmployee(r.projectManagerId);
      return m ? `${m.firstName} ${m.lastName}` : r.projectManagerId;
    }},
    { field: 'phase', header: 'Phase', render: (r) => UI.createBadge(r.phase, r.phase) },
    { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
    { field: 'budgetHours', header: 'Budget Hrs', render: (r) => UI.formatNumber(r.budgetHours) },
    { field: 'approvedHours', header: 'Actual Hrs', render: (r) => UI.formatNumber(r.approvedHours) },
    { field: 'variance', header: 'Variance', render: (r) => {
      const varHours = r.approvedHours - r.budgetHours;
      const varPct = r.budgetHours > 0 ? (varHours / r.budgetHours) * 100 : 0;
      return UI.createElement('span', { class: `fw-medium ${varHours > 0 ? 'text-danger' : 'text-success'}` }, `${varHours > 0 ? '+' : ''}${UI.formatNumber(varHours)} (${varPct.toFixed(1)}%)`);
    }},
    { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
      UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('project-detail', { id: r.id }) }),
      role !== 'designer' && UI.createButton({ text: 'Edit', variant: 'ghost', size: 'sm', onClick: () => Screens.showProjectModal(r) })
    ].filter(Boolean)) }
  ];

  // Hide budget columns for designer
  const finalColumns = role === 'designer' ? projectColumns.filter(c => !['budgetHours', 'approvedHours', 'variance'].includes(c.field)) : projectColumns;

  content.appendChild(UI.createCard({
    children: UI.createTable({
      columns: finalColumns,
      data: data.projects,
      onRowClick: (row) => RouterInstance.navigate('project-detail', { id: row.id }),
      emptyMessage: 'No projects found matching the current filters.'
    })
  }));

  return content;
};

Screens.showProjectModal = function(project = null) {
  const data = getVisibleData();
  const isEdit = !!project;

  const form = UI.createElement('form', { onSubmit: (e) => { e.preventDefault(); Screens.saveProject(form, project); } }, [
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Project Code', name: 'code', value: project?.code || '', required: true }),
      UI.createInput({ label: 'Project Name', name: 'name', value: project?.name || '', required: true })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createSelect({ label: 'Client', name: 'clientId', options: [{ value: '', label: 'Select Client' }, ...data.clients.map(c => ({ value: c.id, label: c.name }))], value: project?.clientId || '', required: true }),
      UI.createSelect({ label: 'Project Manager', name: 'projectManagerId', options: [{ value: '', label: 'Select Manager' }, ...data.employees.filter(e => e.role === 'manager').map(e => ({ value: e.id, label: `${e.firstName} ${e.lastName}` }))], value: project?.projectManagerId || '' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createSelect({ label: 'Status', name: 'status', options: [{ value: 'active', label: 'Active' }, { value: 'on-hold', label: 'On Hold' }, { value: 'completed', label: 'Completed' }, { value: 'cancelled', label: 'Cancelled' }], value: project?.status || 'active' }),
      UI.createSelect({ label: 'Phase', name: 'phase', options: [{ value: 'tender', label: 'Tender' }, { value: 'design-development', label: 'Design Development' }, { value: 'construction-docs', label: 'Construction Docs' }, { value: 'construction', label: 'Construction' }, { value: 'completed', label: 'Completed' }], value: project?.phase || 'tender' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Start Date', type: 'date', name: 'startDate', value: project?.startDate || '' }),
      UI.createInput({ label: 'End Date', type: 'date', name: 'endDate', value: project?.endDate || '' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Budget Hours', type: 'number', name: 'budgetHours', value: project?.budgetHours || '' }),
      UI.createInput({ label: 'Budget Cost', type: 'number', name: 'budgetCost', value: project?.budgetCost || '' })
    ]),
    UI.createInput({ label: 'Description', name: 'description', type: 'textarea', value: project?.description || '', placeholder: 'Project description...' }),
    UI.createElement('div', { class: 'flex justify-end gap-3 mt-6' }, [
      UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => UI.closeModal(UI.createModal.lastId) }),
      UI.createButton({ text: isEdit ? 'Save Changes' : 'Create Project', variant: 'primary', type: 'submit' })
    ])
  ]);

  const modal = UI.createModal({ title: isEdit ? 'Edit Project' : 'New Project', children: [form], size: 'lg' });
  UI.createModal.lastId = modal.id;
};

Screens.saveProject = function(form, existing) {
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.budgetHours = parseFloat(data.budgetHours) || 0;
  data.budgetCost = parseFloat(data.budgetCost) || 0;

  if (existing) {
    Object.assign(existing, data);
    existing.updatedAt = new Date().toISOString().split('T')[0];
    UI.showToast('success', 'Project Updated', 'Project details have been saved.');
  } else {
    const newProject = {
      id: `prj-${Date.now()}`,
      ...data,
      approvedHours: 0,
      approvedCost: 0,
      billedHours: 0,
      billedRevenue: 0,
      teamMembers: data.projectManagerId ? [data.projectManagerId] : [],
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0]
    };
    State.state.projects.unshift(newProject);
    UI.showToast('success', 'Project Created', 'New project has been added.');
  }

  UI.closeModal(UI.createModal.lastId);
  Screens.renderCurrent();
};

// ==================== 05. EMPLOYEES & TEAM ====================
Screens.employees = function() {
  const data = getVisibleData();
  const role = State.getCurrentRole();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Employees & Team'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Manage team members, roles, and project assignments.')
    ]),
    UI.createButton({ text: 'Invite Employee', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M16 21h-4"/><path d="M22 21h-4"/></svg>' })
  ]));

  // Filters
  content.appendChild(UI.createElement('div', { class: 'card mb-6' }, [
    UI.createElement('div', { class: 'card-body' }, [
      UI.createElement('div', { class: 'd-flex flex-wrap gap-4' }, [
        UI.createInput({ label: 'Search', placeholder: 'Search employees...', value: State.getFilters('employees').search, onChange: (v) => { State.setFilter('employees', 'search', v); Screens.renderCurrent(); } }),
        UI.createSelect({ label: 'Department', options: [{ value: '', label: 'All Departments' }, ...[...new Set(data.employees.map(e => e.department))].map(d => ({ value: d, label: d }))], value: State.getFilters('employees').department, onChange: (v) => { State.setFilter('employees', 'department', v); Screens.renderCurrent(); } }),
        UI.createSelect({ label: 'Role', options: [{ value: '', label: 'All Roles' }, { value: 'administrator', label: 'Administrator' }, { value: 'manager', label: 'Manager' }, { value: 'designer', label: 'Designer' }], value: State.getFilters('employees').role, onChange: (v) => { State.setFilter('employees', 'role', v); Screens.renderCurrent(); } }),
        UI.createSelect({ label: 'Status', options: [{ value: '', label: 'All Status' }, { value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }], value: State.getFilters('employees').status, onChange: (v) => { State.setFilter('employees', 'status', v); Screens.renderCurrent(); } }),
        UI.createButton({ text: 'Clear', variant: 'ghost', size: 'sm', onClick: () => { State.resetFilters('employees'); Screens.renderCurrent(); } })
      ])
    ])
  ]));

  // Employee Table
  const empColumns = [
    { field: 'avatar', header: '', render: (r) => UI.createAvatar(`${r.firstName} ${r.lastName}`, 32) },
    { field: 'name', header: 'Employee', render: (r) => UI.createElement('div', {}, [
      UI.createElement('div', { class: 'fw-medium' }, `${r.firstName} ${r.lastName}`),
      UI.createElement('div', { class: 'text-xs text-muted' }, r.email)
    ])},
    { field: 'department', header: 'Department' },
    { field: 'position', header: 'Position' },
    { field: 'role', header: 'Role', render: (r) => UI.createBadge(r.role, r.role) },
    { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
    { field: 'hourlyCostRate', header: 'Cost Rate', render: (r) => UI.formatCurrency(r.hourlyCostRate) + '/hr' },
    { field: 'billableRate', header: 'Bill Rate', render: (r) => UI.formatCurrency(r.billableRate) + '/hr' },
    { field: 'projects', header: 'Projects', render: (r) => r.projects.length > 0 ? UI.createElement('span', {}, r.projects.map(pid => {
      const p = State.getProject(pid);
      return p ? UI.createElement('span', { class: 'badge badge-draft', style: 'margin-right: 4px;' }, p.code) : '';
    })) : UI.createElement('span', { class: 'text-muted' }, '—') },
    { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
      UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('employee-detail', { id: r.id }) }),
      UI.createButton({ text: 'Edit', variant: 'ghost', size: 'sm', onClick: () => Screens.showEmployeeModal(r) })
    ])}
  ];

  content.appendChild(UI.createCard({
    children: UI.createTable({
      columns: empColumns,
      data: data.employees,
      onRowClick: (row) => RouterInstance.navigate('employee-detail', { id: row.id }),
      emptyMessage: 'No employees found matching the current filters.'
    })
  }));

  return content;
};

Screens.showEmployeeModal = function(employee = null) {
  const isEdit = !!employee;

  const form = UI.createElement('form', { onSubmit: (e) => { e.preventDefault(); Screens.saveEmployee(form, employee); } }, [
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'First Name', name: 'firstName', value: employee?.firstName || '', required: true }),
      UI.createInput({ label: 'Last Name', name: 'lastName', value: employee?.lastName || '', required: true })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Email', type: 'email', name: 'email', value: employee?.email || '', required: true }),
      UI.createInput({ label: 'Phone', name: 'phone', value: employee?.phone || '' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createSelect({ label: 'Role', name: 'role', options: [{ value: 'administrator', label: 'Administrator' }, { value: 'manager', label: 'Manager' }, { value: 'designer', label: 'Designer' }], value: employee?.role || 'designer', required: true }),
      UI.createSelect({ label: 'Status', name: 'status', options: [{ value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }], value: employee?.status || 'active' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Department', name: 'department', value: employee?.department || '' }),
      UI.createInput({ label: 'Position', name: 'position', value: employee?.position || '' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Hourly Cost Rate', type: 'number', name: 'hourlyCostRate', value: employee?.hourlyCostRate || '' }),
      UI.createInput({ label: 'Billable Rate', type: 'number', name: 'billableRate', value: employee?.billableRate || '' })
    ]),
    UI.createInput({ label: 'Skills (comma separated)', name: 'skills', value: employee?.skills?.join(', ') || '' }),
    UI.createElement('div', { class: 'flex justify-end gap-3 mt-6' }, [
      UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => UI.closeModal(UI.createModal.lastId) }),
      UI.createButton({ text: isEdit ? 'Save Changes' : 'Add Employee', variant: 'primary', type: 'submit' })
    ])
  ]);

  const modal = UI.createModal({ title: isEdit ? 'Edit Employee' : 'New Employee', children: [form], size: 'lg' });
  UI.createModal.lastId = modal.id;
};

Screens.saveEmployee = function(form, existing) {
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.hourlyCostRate = parseFloat(data.hourlyCostRate) || 0;
  data.billableRate = parseFloat(data.billableRate) || 0;
  data.skills = data.skills ? data.skills.split(',').map(s => s.trim()) : [];

  if (existing) {
    Object.assign(existing, data);
    UI.showToast('success', 'Employee Updated', 'Employee details have been saved.');
  } else {
    const newEmp = {
      id: `emp-${Date.now()}`,
      ...data,
      hireDate: new Date().toISOString().split('T')[0],
      avatar: null,
      managerId: null,
      projects: [],
      permissions: data.role === 'administrator' ? ['all'] : data.role === 'manager' ? ['projects:read', 'timesheets:approve'] : ['timesheets:write']
    };
    State.state.employees.push(newEmp);
    UI.showToast('success', 'Employee Added', 'New employee has been added to the team.');
  }

  UI.closeModal(UI.createModal.lastId);
  Screens.renderCurrent();
};

// ==================== 06. FINANCIAL MANAGEMENT ====================
Screens.financial = function() {
  const data = getVisibleData();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Financial Management'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Project financial overview, labour costs, revenue, and profitability analysis.')
    ]),
    UI.createButton({ text: 'Export Financial Report', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' })
  ]));

  // Financial KPIs
  const totalRevenue = data.projects.reduce((sum, p) => sum + (p.billedRevenue || 0), 0);
  const totalCost = data.projects.reduce((sum, p) => sum + (p.approvedCost || 0), 0);
  const totalBudgetCost = data.projects.reduce((sum, p) => sum + (p.budgetCost || 0), 0);
  const totalBudgetRevenue = data.projects.reduce((sum, p) => sum + (p.budgetRevenue || 0), 0);

  content.appendChild(UI.createElement('div', { class: 'kpi-grid mb-6' }, [
    UI.createKPICard({ label: 'Total Revenue (Billed)', value: UI.formatCurrency(totalRevenue), subvalue: 'Invoiced to date', icon: '$', iconBg: 'green' }),
    UI.createKPICard({ label: 'Total Labour Cost', value: UI.formatCurrency(totalCost), subvalue: 'Approved hours × cost rate', icon: '💰', iconBg: 'amber' }),
    UI.createKPICard({ label: 'Gross Margin', value: totalRevenue > 0 ? `${(((totalRevenue - totalCost) / totalRevenue) * 100).toFixed(1)}%` : '0%', subvalue: UI.formatCurrency(totalRevenue - totalCost), trend: { value: '+0.8%', label: 'vs last period', type: 'positive' }, icon: '📈', iconBg: 'teal' }),
    UI.createKPICard({ label: 'Budget Utilization', value: totalBudgetCost > 0 ? `${((totalCost / totalBudgetCost) * 100).toFixed(1)}%` : '0%', subvalue: `${UI.formatCurrency(totalCost)} of ${UI.formatCurrency(totalBudgetCost)}`, icon: '📊', iconBg: 'primary' }),
    UI.createKPICard({ label: 'Revenue vs Budget', value: totalBudgetRevenue > 0 ? `${((totalRevenue / totalBudgetRevenue) * 100).toFixed(1)}%` : '0%', subvalue: `${UI.formatCurrency(totalRevenue)} of ${UI.formatCurrency(totalBudgetRevenue)}`, icon: '🎯', iconBg: 'purple' }),
    UI.createKPICard({ label: 'Outstanding Invoices', value: UI.formatCurrency(data.invoices.filter(i => i.status === 'sent' || i.status === 'overdue').reduce((sum, i) => sum + i.balance, 0)), subvalue: `${data.invoices.filter(i => i.status === 'sent' || i.status === 'overdue').length} invoices`, icon: '📄', iconBg: 'red' })
  ]));

  // Charts Row
  const chartsRow = UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));' });

  // Project Profitability
  chartsRow.appendChild(Charts.createProjectProfitabilityChart(data.projects.filter(p => p.status === 'active')));

  // Budget Variance
  chartsRow.appendChild(Charts.createBudgetVarianceChart(data.projects.filter(p => p.status === 'active')));

  content.appendChild(chartsRow);

  // Detailed Financial Table
  content.appendChild(UI.createCard({
    title: 'Project Financial Detail',
    children: UI.createTable({
      columns: [
        { field: 'code', header: 'Project', render: (r) => UI.createElement('div', {}, [UI.createElement('div', { class: 'fw-medium' }, r.code), UI.createElement('div', { class: 'text-xs text-muted' }, r.name)]) },
        { field: 'budgetHours', header: 'Budget Hours', render: (r) => UI.formatNumber(r.budgetHours) },
        { field: 'approvedHours', header: 'Actual Hours', render: (r) => UI.formatNumber(r.approvedHours) },
        { field: 'budgetCost', header: 'Budget Cost', render: (r) => UI.formatCurrency(r.budgetCost) },
        { field: 'approvedCost', header: 'Actual Cost', render: (r) => UI.formatCurrency(r.approvedCost) },
        { field: 'billedRevenue', header: 'Billed Revenue', render: (r) => UI.formatCurrency(r.billedRevenue) },
        { field: 'grossMargin', header: 'Gross Margin', render: (r) => {
          const margin = (r.billedRevenue || 0) - (r.approvedCost || 0);
          const pct = (r.billedRevenue || 0) > 0 ? (margin / r.billedRevenue) * 100 : 0;
          return UI.createElement('span', { class: `fw-medium ${margin >= 0 ? 'text-success' : 'text-danger'}` }, `${UI.formatCurrency(margin)} (${pct.toFixed(1)}%)`);
        }},
        { field: 'variance', header: 'Cost Variance', render: (r) => {
          const variance = (r.approvedCost || 0) - (r.budgetCost || 0);
          const pct = (r.budgetCost || 0) > 0 ? (variance / r.budgetCost) * 100 : 0;
          return UI.createElement('span', { class: `fw-medium ${variance > 0 ? 'text-danger' : 'text-success'}` }, `${variance > 0 ? '+' : ''}${UI.formatCurrency(variance)} (${pct.toFixed(1)}%)`);
        }}
      ],
      data: data.projects.filter(p => p.status === 'active'),
      emptyMessage: 'No active projects.'
    })
  }));

  return content;
};

// ==================== 07. QUOTES & ESTIMATES ====================
Screens.quotes = function() {
  const data = getVisibleData();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Quotes & Estimates'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Create, manage, and track quotes and estimates.')
    ]),
    UI.createButton({ text: 'New Quote', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => RouterInstance.navigate('quote-builder') })
  ]));

  // Tabs
  content.appendChild(UI.createElement('div', { class: 'tabs mb-4' }, [
    { id: 'all', label: 'All Quotes', count: data.quotes.length },
    { id: 'draft', label: 'Draft', count: data.quotes.filter(q => q.status === 'draft').length },
    { id: 'sent', label: 'Sent', count: data.quotes.filter(q => q.status === 'sent').length },
    { id: 'accepted', label: 'Accepted', count: data.quotes.filter(q => q.status === 'accepted').length },
    { id: 'rejected', label: 'Rejected', count: data.quotes.filter(q => q.status === 'rejected').length }
  ].map(tab => UI.createElement('button', {
    class: `tab ${tab.id === 'all' ? 'active' : ''}`,
    dataset: { tab: tab.id },
    onClick: (e) => {
      $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
      e.currentTarget.classList.add('active');
      Screens.renderQuotesTable(tab.id);
    }
  }, tab.label + (tab.count > 0 ? ' <span class="badge badge-draft" style="margin-left: 6px; font-size: 10px;">' + tab.count + '</span>' : '')))));

  // Table container
  const tableContainer = UI.createElement('div', { id: 'quotes-table-container' });
  content.appendChild(tableContainer);

  setTimeout(() => Screens.renderQuotesTable('all'), 0);

  return content;
};

Screens.renderQuotesTable = function(statusFilter) {
  const data = getVisibleData();
  let quotes = data.quotes;
  if (statusFilter && statusFilter !== 'all') {
    quotes = quotes.filter(q => q.status === statusFilter);
  }

  const container = $('#quotes-table-container');
  if (!container) return;

  container.innerHTML = '';
  container.appendChild(UI.createTable({
    columns: [
      { field: 'quoteNumber', header: 'Quote #', render: (r) => UI.createElement('span', { class: 'fw-medium' }, r.quoteNumber) },
      { field: 'clientId', header: 'Client', render: (r) => {
        const c = State.getClient(r.clientId);
        return c ? c.name : r.clientId;
      }},
      { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
      { field: 'validUntil', header: 'Valid Until', render: (r) => UI.formatDate(r.validUntil) },
      { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
      { field: 'total', header: 'Total', render: (r) => UI.formatCurrency(r.total) },
      { field: 'estimatedMargin', header: 'Est. Margin', render: (r) => UI.createElement('span', { class: `fw-medium ${r.estimatedMargin > 0.3 ? 'text-success' : r.estimatedMargin > 0.2 ? 'text-warning' : 'text-danger'}` }, `${(r.estimatedMargin * 100).toFixed(1)}%`) },
      { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
        UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('quote-detail', { id: r.id }) }),
        r.status === 'draft' && UI.createButton({ text: 'Send', variant: 'primary', size: 'sm', onClick: () => { r.status = 'sent'; r.sentAt = new Date().toISOString(); Screens.renderCurrent(); UI.showToast('success', 'Quote Sent', 'Quote has been sent to client.'); } }),
        r.status === 'sent' && UI.createButton({ text: 'Mark Accepted', variant: 'success', size: 'sm', onClick: () => { r.status = 'accepted'; r.acceptedAt = new Date().toISOString(); Screens.renderCurrent(); UI.showToast('success', 'Quote Accepted', 'Client has accepted the quote.'); } })
      ].filter(Boolean)) }
    ],
    data: quotes,
    emptyMessage: 'No quotes found for the selected filter.'
  }));
};

// Quote Builder (Interactive Calculator)
Screens['quote-builder'] = function() {
  const data = getVisibleData();
  let quoteData = {
    clientId: '',
    projectId: '',
    scopeDescription: '',
    items: [{ id: `item-${Date.now()}`, description: '', quantity: 0, unit: 'hours', rate: 0, amount: 0 }],
    markupPercent: 15,
    contingencyPercent: 10,
    discountPercent: 0,
    notes: ''
  };

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Create Quote'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Build a professional quote with real-time calculations.')
    ]),
    UI.createButton({ text: 'Save as Draft', variant: 'secondary', onClick: () => Screens.saveQuote(quoteData, 'draft') })
  ]));

  // Client & Project Info
  content.appendChild(UI.createCard({
    title: 'Quote Information',
    children: UI.createElement('div', { class: 'form-row' }, [
      UI.createSelect({
        label: 'Client',
        options: [{ value: '', label: 'Select Client' }, ...data.clients.map(c => ({ value: c.id, label: c.name }))],
        onChange: (v) => { quoteData.clientId = v; updateTotals(); }
      }),
      UI.createSelect({
        label: 'Related Project (Optional)',
        options: [{ value: '', label: 'No Project' }, ...data.projects.map(p => ({ value: p.id, label: `${p.code} - ${p.name}` }))],
        onChange: (v) => { quoteData.projectId = v; }
      })
    ])
  }));

  // Scope Description
  content.appendChild(UI.createCard({
    title: 'Scope Description',
    children: UI.createElement('textarea', {
      class: 'form-textarea',
      placeholder: 'Describe the scope of work...',
      onInput: (e) => { quoteData.scopeDescription = e.target.value; }
    })
  }));

  // Quote Items
  content.appendChild(UI.createCard({
    title: 'Quote Items',
    actions: [
      UI.createButton({ text: 'Add Item', variant: 'secondary', size: 'sm', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => { quoteData.items.push({ id: `item-${Date.now()}`, description: '', quantity: 0, unit: 'hours', rate: 0, amount: 0 }); renderItems(); } })
    ],
    children: [
      UI.createElement('div', { id: 'quote-items-container' })
    ]
  }));

  // Totals Panel
  const totalsPanel = UI.createCard({
    title: 'Quote Totals',
    className: 'sticky-top',
    style: 'position: sticky; top: 80px;',
    children: UI.createElement('div', { id: 'quote-totals' })
  });
  content.appendChild(totalsPanel);

  // Notes
  content.appendChild(UI.createCard({
    title: 'Notes & Terms',
    children: UI.createElement('textarea', {
      class: 'form-textarea',
      placeholder: 'Additional notes, terms, or conditions...',
      onInput: (e) => { quoteData.notes = e.target.value; }
    })
  }));

  // Actions
  content.appendChild(UI.createElement('div', { class: 'flex justify-end gap-3 mt-6' }, [
    UI.createButton({ text: 'Cancel', variant: 'secondary', onClick: () => RouterInstance.navigate('quotes') }),
    UI.createButton({ text: 'Save as Draft', variant: 'secondary', onClick: () => Screens.saveQuote(quoteData, 'draft') }),
    UI.createButton({ text: 'Preview Quote', variant: 'primary', onClick: () => Screens.previewQuote(quoteData) })
  ]));

  // Render functions
  function renderItems() {
    const container = $('#quote-items-container');
    if (!container) return;

    container.innerHTML = '';
    quoteData.items.forEach((item, index) => {
      const itemEl = UI.createElement('div', { class: 'd-flex gap-2 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md); margin-bottom: 8px;' }, [
        UI.createInput({ label: 'Description', style: 'flex: 2;', value: item.description, onChange: (v) => { item.description = v; } }),
        UI.createInput({ label: 'Qty', type: 'number', step: '0.5', min: '0', style: 'width: 80px;', value: item.quantity, onChange: (v) => { item.quantity = parseFloat(v) || 0; updateTotals(); } }),
        UI.createSelect({ label: 'Unit', options: [{ value: 'hours', label: 'Hours' }, { value: 'days', label: 'Days' }, { value: 'weeks', label: 'Weeks' }, { value: 'lump', label: 'Lump Sum' }], value: item.unit, onChange: (v) => { item.unit = v; } }),
        UI.createInput({ label: 'Rate', type: 'number', step: '1', min: '0', style: 'width: 100px;', value: item.rate, onChange: (v) => { item.rate = parseFloat(v) || 0; updateTotals(); } }),
        UI.createElement('div', { class: 'd-flex items-end', style: 'width: 140px;' }, [
          UI.createElement('label', { class: 'form-label' }, 'Amount'),
          UI.createElement('div', { class: 'fw-semibold text-primary', style: 'font-size: 16px;' }, UI.formatCurrency(item.quantity * item.rate))
        ]),
        quoteData.items.length > 1 && UI.createIconButton({ icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>', ariaLabel: 'Remove item', onClick: () => { quoteData.items.splice(index, 1); renderItems(); updateTotals(); } })
      ]);
      container.appendChild(itemEl);
    });
  }

  function updateTotals() {
    const totals = State.calculateQuoteTotals(
      quoteData.items.filter(i => i.quantity > 0 && i.rate > 0),
      quoteData.markupPercent,
      quoteData.contingencyPercent,
      quoteData.discountPercent,
      State.state.settings.company.taxRate
    );

    const container = $('#quote-totals');
    if (!container) return;

    container.innerHTML = '';
    container.appendChild(UI.createElement('div', { class: 'd-grid gap-2' }, [
      UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', {}, 'Subtotal'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(totals.subtotal))]),
      UI.createElement('div', { class: 'd-flex justify-between' }, [
        UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
          UI.createElement('span', {}, `Markup (${totals.markupPercent}%)`),
          UI.createInput({ type: 'number', step: '1', min: '0', max: '100', value: totals.markupPercent, style: 'width: 60px;', onChange: (v) => { quoteData.markupPercent = parseFloat(v) || 0; updateTotals(); } })
        ]),
        UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(totals.markupAmount))
      ]),
      UI.createElement('div', { class: 'd-flex justify-between' }, [
        UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
          UI.createElement('span', {}, `Contingency (${totals.contingencyPercent}%)`),
          UI.createInput({ type: 'number', step: '1', min: '0', max: '100', value: totals.contingencyPercent, style: 'width: 60px;', onChange: (v) => { quoteData.contingencyPercent = parseFloat(v) || 0; updateTotals(); } })
        ]),
        UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(totals.contingencyAmount))
      ]),
      UI.createElement('div', { class: 'd-flex justify-between' }, [
        UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
          UI.createElement('span', {}, `Discount (${totals.discountPercent}%)`),
          UI.createInput({ type: 'number', step: '1', min: '0', max: '100', value: totals.discountPercent, style: 'width: 60px;', onChange: (v) => { quoteData.discountPercent = parseFloat(v) || 0; updateTotals(); } })
        ]),
        UI.createElement('span', { class: 'fw-medium text-danger' }, `-${UI.formatCurrency(totals.discountAmount)}`)
      ]),
      UI.createElement('hr', {}),
      UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', {}, `Tax (${(State.state.settings.company.taxRate * 100).toFixed(0)}%)`), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(totals.taxAmount))]),
      UI.createElement('div', { class: 'd-flex justify-between text-lg fw-bold', style: 'border-top: 2px solid var(--color-border); padding-top: 8px;' }, [UI.createElement('span', {}, 'Total'), UI.createElement('span', {}, UI.formatCurrency(totals.total))]),
      UI.createElement('div', { class: 'd-flex justify-between text-sm text-muted' }, [UI.createElement('span', {}, 'Estimated Cost'), UI.createElement('span', {}, UI.formatCurrency(totals.estimatedCost))]),
      UI.createElement('div', { class: 'd-flex justify-between text-sm', style: `color: ${totals.estimatedMargin > 0.3 ? 'var(--status-approved)' : totals.estimatedMargin > 0.2 ? 'var(--status-suggested)' : 'var(--status-rejected)'}` }, [UI.createElement('span', {}, 'Estimated Margin'), UI.createElement('span', { class: 'fw-bold' }, `${(totals.estimatedMargin * 100).toFixed(1)}%`)])
    ]));
  }

  renderItems();
  updateTotals();

  return content;
};

Screens.saveQuote = function(quoteData, status) {
  const validItems = quoteData.items.filter(i => i.quantity > 0 && i.rate > 0);
  if (validItems.length === 0) {
    UI.showToast('error', 'Invalid Quote', 'Please add at least one line item with quantity and rate.');
    return;
  }

  if (!quoteData.clientId) {
    UI.showToast('error', 'Missing Client', 'Please select a client for this quote.');
    return;
  }

  const totals = State.calculateQuoteTotals(validItems, quoteData.markupPercent, quoteData.contingencyPercent, quoteData.discountPercent);

  const newQuote = {
    id: `qt-${Date.now()}`,
    quoteNumber: `QT-${new Date().getFullYear()}-${String(State.state.quotes.length + 1).padStart(3, '0')}`,
    clientId: quoteData.clientId,
    projectId: quoteData.projectId || null,
    status,
    date: new Date().toISOString().split('T')[0],
    validUntil: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    preparedBy: State.getCurrentUser().id,
    scopeDescription: quoteData.scopeDescription,
    items: validItems.map((item, i) => ({ ...item, id: `qi-${Date.now()}-${i}`, amount: item.quantity * item.rate })),
    subtotal: totals.subtotal,
    markupPercent: quoteData.markupPercent,
    markupAmount: totals.markupAmount,
    contingencyPercent: quoteData.contingencyPercent,
    contingencyAmount: totals.contingencyAmount,
    discountPercent: quoteData.discountPercent,
    discountAmount: totals.discountAmount,
    taxAmount: totals.taxAmount,
    total: totals.total,
    estimatedCost: totals.estimatedCost,
    estimatedMargin: totals.estimatedMargin,
    notes: quoteData.notes,
    sentAt: status === 'sent' ? new Date().toISOString() : null,
    acceptedAt: null,
    rejectedAt: null,
    rejectedReason: null
  };

  State.state.quotes.unshift(newQuote);
  UI.showToast('success', status === 'sent' ? 'Quote Sent' : 'Quote Saved', `Quote ${newQuote.quoteNumber} has been ${status === 'sent' ? 'sent to client' : 'saved as draft'}.`);
  RouterInstance.navigate('quotes');
};

Screens.previewQuote = function(quoteData) {
  const validItems = quoteData.items.filter(i => i.quantity > 0 && i.rate > 0);
  const totals = State.calculateQuoteTotals(validItems, quoteData.markupPercent, quoteData.contingencyPercent, quoteData.discountPercent);
  const client = State.getClient(quoteData.clientId);
  const company = State.state.company;

  const modal = UI.createModal({
    title: 'Quote Preview',
    size: 'xl',
    children: [
      UI.createElement('div', { style: 'font-family: var(--font-family); max-width: 800px; margin: 0 auto; padding: 40px; background: white; color: #172B3A;', }, [
        // Header
        UI.createElement('div', { class: 'd-flex justify-between mb-8' }, [
          UI.createElement('div', {}, [
            UI.createElement('h1', { style: 'font-size: 28px; font-weight: 700; color: #1976A5;' }, 'BIMSpend'),
            UI.createElement('p', { class: 'text-muted' }, 'Apex BIM Solutions Pty Ltd')
          ]),
          UI.createElement('div', { style: 'text-align: right;' }, [
            UI.createElement('h2', { style: 'font-size: 24px; font-weight: 700;' }, 'QUOTE'),
            UI.createElement('p', {}, `QT-2024-${String(State.state.quotes.length + 1).padStart(3, '0')}`)
          ])
        ]),
        // Meta
        UI.createElement('div', { class: 'd-grid gap-4 mb-8', style: 'grid-template-columns: 1fr 1fr;' }, [
          UI.createElement('div', {}, [
            UI.createElement('h4', { style: 'font-size: 12px; text-transform: uppercase; color: #546B7D; margin-bottom: 8px;' }, 'FROM'),
            UI.createElement('p', {}, `${company.name}<br>${company.address}<br>ABN: ${company.abn}<br>Email: ${company.email}`)
          ]),
          UI.createElement('div', { style: 'text-align: right;' }, [
            UI.createElement('h4', { style: 'font-size: 12px; text-transform: uppercase; color: #546B7D; margin-bottom: 8px;' }, 'TO'),
            UI.createElement('p', {}, `${client?.name || 'Client Name'}<br>${client?.address || 'Client Address'}<br>ABN: ${client?.abn || '—'}`)
          ])
        ]),
        // Details
        UI.createElement('div', { class: 'd-grid gap-2 mb-8', style: 'grid-template-columns: repeat(4, 1fr); font-size: 14px;' }, [
          UI.createElement('div', {}, [UI.createElement('span', { class: 'text-muted' }, 'Date'), UI.createElement('div', { class: 'fw-medium' }, new Date().toLocaleDateString('en-AU'))]),
          UI.createElement('div', {}, [UI.createElement('span', { class: 'text-muted' }, 'Valid Until'), UI.createElement('div', { class: 'fw-medium' }, new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-AU'))]),
          UI.createElement('div', {}, [UI.createElement('span', { class: 'text-muted' }, 'Prepared By'), UI.createElement('div', { class: 'fw-medium' }, State.getCurrentUser()?.firstName + ' ' + State.getCurrentUser()?.lastName)]),
          UI.createElement('div', {}, [UI.createElement('span', { class: 'text-muted' }, 'Status'), UI.createElement('div', { class: 'fw-medium' }, 'Draft')])
        ]),
        // Scope
        UI.createElement('div', { class: 'mb-8' }, [
          UI.createElement('h4', { style: 'font-size: 12px; text-transform: uppercase; color: #546B7D; margin-bottom: 8px;' }, 'SCOPE OF WORK'),
          UI.createElement('p', { style: 'white-space: pre-wrap;' }, quoteData.scopeDescription || 'Scope description to be added.')
        ]),
        // Items Table
        UI.createElement('table', { style: 'width: 100%; border-collapse: collapse; margin-bottom: 24px;' }, [
          UI.createElement('thead', {}, [
            UI.createElement('tr', { style: 'background: #14324A; color: white;' }, [
              'Description', 'Qty', 'Unit', 'Rate', 'Amount'
            ].map(h => UI.createElement('th', { style: 'padding: 12px; text-align: left; font-weight: 600;' }, h)))
          ]),
          UI.createElement('tbody', {}, validItems.map((item, i) => UI.createElement('tr', { style: i % 2 === 0 ? 'background: #F4F7F9' : '' }, [
            UI.createElement('td', { style: 'padding: 12px; border-bottom: 1px solid #D9E1E7;' }, item.description),
            UI.createElement('td', { style: 'padding: 12px; border-bottom: 1px solid #D9E1E7; text-align: center;' }, item.quantity),
            UI.createElement('td', { style: 'padding: 12px; border-bottom: 1px solid #D9E1E7; text-align: center;' }, item.unit),
            UI.createElement('td', { style: 'padding: 12px; border-bottom: 1px solid #D9E1E7; text-align: right;' }, UI.formatCurrency(item.rate)),
            UI.createElement('td', { style: 'padding: 12px; border-bottom: 1px solid #D9E1E7; text-align: right; font-weight: 600;' }, UI.formatCurrency(item.quantity * item.rate))
          ])))
        ]),
        // Totals
        UI.createElement('div', { style: 'width: 300px; margin-left: auto; font-size: 14px;' }, [
          UI.createElement('div', { class: 'd-flex justify-between py-1' }, ['Subtotal', UI.formatCurrency(totals.subtotal)]),
          UI.createElement('div', { class: 'd-flex justify-between py-1' }, [`Markup (${totals.markupPercent}%)`, UI.formatCurrency(totals.markupAmount)]),
          UI.createElement('div', { class: 'd-flex justify-between py-1' }, [`Contingency (${totals.contingencyPercent}%)`, UI.formatCurrency(totals.contingencyAmount)]),
          UI.createElement('div', { class: 'd-flex justify-between py-1 text-danger' }, [`Discount (${totals.discountPercent}%)`, `-${UI.formatCurrency(totals.discountAmount)}`]),
          UI.createElement('hr', {}),
          UI.createElement('div', { class: 'd-flex justify-between py-1' }, [`Tax (${(State.state.settings.company.taxRate * 100).toFixed(0)}%)`, UI.formatCurrency(totals.taxAmount)]),
          UI.createElement('div', { class: 'd-flex justify-between py-2 fw-bold', style: 'font-size: 16px; border-top: 2px solid #14324A;' }, ['TOTAL', UI.formatCurrency(totals.total)])
        ]),
        // Notes
        quoteData.notes && UI.createElement('div', { class: 'mt-8 p-4', style: 'background: #F4F7F9; border-radius: 8px;' }, [
          UI.createElement('h4', { style: 'font-size: 12px; text-transform: uppercase; color: #546B7D; margin-bottom: 8px;' }, 'NOTES & TERMS'),
          UI.createElement('p', { style: 'white-space: pre-wrap;' }, quoteData.notes)
        ])
      ])
    ]
  });
};

// ==================== 08. REPORTS & ANALYTICS ====================
Screens.reports = function() {
  const data = getVisibleData();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Reports & Analytics'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Comprehensive reporting on time, projects, employees, and financials.')
    ]),
    UI.createButton({ text: 'Export All Data', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' })
  ]));

  // Report Selector Tabs
  const reportTabs = [
    { id: 'timesheet', label: 'Timesheet Report', icon: '📋' },
    { id: 'utilization', label: 'Employee Utilization', icon: '👥' },
    { id: 'project-performance', label: 'Project Performance', icon: '📊' },
    { id: 'budget-variance', label: 'Budget Variance', icon: '📈' },
    { id: 'activity-classification', label: 'Activity Classification', icon: '🔍' },
    { id: 'profitability', label: 'Profitability Analysis', icon: '💰' }
  ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-6' }, reportTabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${tab.id === 'timesheet' ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        Screens.renderReport(tab.id);
      }
    }, `${tab.icon} ${tab.label}`)
  )));

  // Date Range & Filters
  content.appendChild(UI.createElement('div', { class: 'card mb-6' }, [
    UI.createElement('div', { class: 'card-body' }, [
      UI.createElement('div', { class: 'd-flex flex-wrap gap-4 items-end' }, [
        UI.createInput({ label: 'From Date', type: 'date', value: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] }),
        UI.createInput({ label: 'To Date', type: 'date', value: new Date().toISOString().split('T')[0] }),
        UI.createSelect({ label: 'Project', options: [{ value: '', label: 'All Projects' }, ...data.projects.map(p => ({ value: p.id, label: p.name }))] }),
        UI.createSelect({ label: 'Employee', options: [{ value: '', label: 'All Employees' }, ...data.employees.map(e => ({ value: e.id, label: `${e.firstName} ${e.lastName}` }))] }),
        UI.createButton({ text: 'Generate Report', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>' }),
        UI.createButton({ text: 'Export CSV', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>', onClick: () => Screens.exportCurrentReportCSV() })
      ])
    ])
  ]));

  // Report Content Container
  const reportContainer = UI.createElement('div', { id: 'report-container' });
  content.appendChild(reportContainer);

  // Initial render
  setTimeout(() => Screens.renderReport('timesheet'), 0);

  return content;
};

Screens.renderReport = function(reportType) {
  const data = getVisibleData();
  const container = $('#report-container');
  if (!container) return;

  container.innerHTML = '';

  switch (reportType) {
    case 'timesheet':
      container.appendChild(UI.createCard({
        title: 'Timesheet Report',
        children: UI.createTable({
          columns: [
            { field: 'employeeId', header: 'Employee', render: (r) => { const e = State.getEmployee(r.employeeId); return e ? `${e.firstName} ${e.lastName}` : r.employeeId; }},
            { field: 'projectId', header: 'Project', render: (r) => { const p = State.getProject(r.projectId); return p ? p.code : r.projectId; }},
            { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
            { field: 'hours', header: 'Hours', render: (r) => UI.formatNumber(r.hours, 1) },
            { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
            { field: 'description', header: 'Description' }
          ],
          data: data.timesheets,
          emptyMessage: 'No timesheet data for the selected period.'
        })
      }));
      break;

    case 'utilization':
      const utilData = data.employees.filter(e => e.role === 'designer').map(e => {
        const myTs = data.timesheets.filter(t => t.employeeId === e.id);
        const billable = myTs.filter(t => t.status === 'approved' || t.status === 'billed').reduce((s, t) => s + t.hours, 0);
        const available = 38 * 4;
        return { ...e, billableHours: billable, availableHours: available, utilization: available > 0 ? (billable / available) * 100 : 0 };
      });
      container.appendChild(Charts.createUtilizationChart(utilData));
      break;

    case 'project-performance':
      container.appendChild(Charts.createProjectProfitabilityChart(data.projects.filter(p => p.status === 'active')));
      container.appendChild(Charts.createBudgetVarianceChart(data.projects.filter(p => p.status === 'active')));
      break;

    case 'budget-variance':
      container.appendChild(Charts.createBudgetVarianceChart(data.projects.filter(p => p.status === 'active')));
      break;

    case 'activity-classification':
      const actData = [
        { classification: 'design', hours: 3456 },
        { classification: 'coordination', hours: 892 },
        { classification: 'meeting', hours: 567 },
        { classification: 'research', hours: 334 },
        { classification: 'admin', hours: 298 }
      ];
      container.appendChild(Charts.createActivityDonut(actData));
      break;

    case 'profitability':
      const profData = data.reports.projectProfitability || [];
      container.appendChild(UI.createCard({
        title: 'Project Profitability Comparison',
        children: UI.createTable({
          columns: [
            { field: 'code', header: 'Project', render: (r) => UI.createElement('div', {}, [UI.createElement('div', { class: 'fw-medium' }, r.code), UI.createElement('div', { class: 'text-xs text-muted' }, r.name)]) },
            { field: 'revenue', header: 'Revenue', render: (r) => UI.formatCurrency(r.revenue) },
            { field: 'laborCost', header: 'Labour Cost', render: (r) => UI.formatCurrency(r.laborCost) },
            { field: 'grossMargin', header: 'Gross Margin', render: (r) => UI.formatCurrency(r.grossMargin) },
            { field: 'marginPercent', header: 'Margin %', render: (r) => UI.createElement('span', { class: `fw-medium ${r.marginPercent > 30 ? 'text-success' : r.marginPercent > 20 ? 'text-warning' : 'text-danger'}` }, `${r.marginPercent.toFixed(1)}%`) }
          ],
          data: profData,
          emptyMessage: 'No profitability data available.'
        })
      }));
      break;
  }
};

Screens.exportCurrentReportCSV = function() {
  // Simulate CSV export
  UI.showToast('success', 'Export Ready', 'CSV file has been generated and downloaded.');
};

// ==================== 09. CLIENTS ====================
Screens.clients = function() {
  const data = getVisibleData();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Clients'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Manage client relationships, contacts, and billing history.')
    ]),
    UI.createButton({ text: 'New Client', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => Screens.showClientModal() })
  ]));

  // Client Table
  const clientColumns = [
    { field: 'name', header: 'Client Name', render: (r) => UI.createElement('div', {}, [UI.createElement('div', { class: 'fw-medium' }, r.name), UI.createElement('div', { class: 'text-xs text-muted' }, r.type)]) },
    { field: 'contactPerson', header: 'Contact' },
    { field: 'email', header: 'Email' },
    { field: 'phone', header: 'Phone' },
    { field: 'projects', header: 'Projects', render: (r) => {
      const clientProjects = data.projects.filter(p => p.clientId === r.id);
      return clientProjects.length > 0 ? UI.createElement('span', {}, clientProjects.map(p => UI.createElement('span', { class: 'badge badge-draft', style: 'margin-right: 4px;' }, p.code))) : '—';
    }},
    { field: 'paymentTerms', header: 'Terms', render: (r) => `${r.paymentTerms} days` },
    { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
    { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
      UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('client-detail', { id: r.id }) }),
      UI.createButton({ text: 'Edit', variant: 'ghost', size: 'sm', onClick: () => Screens.showClientModal(r) })
    ])}
  ];

  content.appendChild(UI.createCard({
    children: UI.createTable({
      columns: clientColumns,
      data: data.clients,
      onRowClick: (row) => RouterInstance.navigate('client-detail', { id: row.id }),
      emptyMessage: 'No clients found.'
    })
  }));

  return content;
};

Screens.showClientModal = function(client = null) {
  const isEdit = !!client;

  const form = UI.createElement('form', { onSubmit: (e) => { e.preventDefault(); Screens.saveClient(form, client); } }, [
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Client Name', name: 'name', value: client?.name || '', required: true }),
      UI.createSelect({ label: 'Type', name: 'type', options: [{ value: 'commercial', label: 'Commercial' }, { value: 'government', label: 'Government' }, { value: 'non-profit', label: 'Non-Profit' }], value: client?.type || 'commercial' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Contact Person', name: 'contactPerson', value: client?.contactPerson || '' }),
      UI.createInput({ label: 'Email', type: 'email', name: 'email', value: client?.email || '' })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Phone', name: 'phone', value: client?.phone || '' }),
      UI.createInput({ label: 'ABN', name: 'abn', value: client?.abn || '' })
    ]),
    UI.createInput({ label: 'Address', name: 'address', type: 'textarea', value: client?.address || '' }),
    UI.createInput({ label: 'Billing Address', name: 'billingAddress', type: 'textarea', value: client?.billingAddress || '' }),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Payment Terms (days)', type: 'number', name: 'paymentTerms', value: client?.paymentTerms || 30 }),
      UI.createSelect({ label: 'Status', name: 'status', options: [{ value: 'active', label: 'Active' }, { value: 'inactive', label: 'Inactive' }], value: client?.status || 'active' })
    ]),
    UI.createInput({ label: 'Notes', name: 'notes', type: 'textarea', value: client?.notes || '' }),
    UI.createElement('div', { class: 'flex justify-end gap-3 mt-6' }, [
      UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => UI.closeModal(UI.createModal.lastId) }),
      UI.createButton({ text: isEdit ? 'Save Changes' : 'Create Client', variant: 'primary', type: 'submit' })
    ])
  ]);

  const modal = UI.createModal({ title: isEdit ? 'Edit Client' : 'New Client', children: [form], size: 'lg' });
  UI.createModal.lastId = modal.id;
};

Screens.saveClient = function(form, existing) {
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.paymentTerms = parseInt(data.paymentTerms) || 30;

  if (existing) {
    Object.assign(existing, data);
    UI.showToast('success', 'Client Updated', 'Client details have been saved.');
  } else {
    const newClient = { id: `cli-${Date.now()}`, ...data, createdAt: new Date().toISOString().split('T')[0] };
    State.state.clients.push(newClient);
    UI.showToast('success', 'Client Created', 'New client has been added.');
  }

  UI.closeModal(UI.createModal.lastId);
  Screens.renderCurrent();
};

// ==================== 10. BILLING & INVOICES ====================
Screens.billing = function() {
  const data = getVisibleData();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Billing & Invoices'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Manage invoices, track payments, and monitor receivables.')
    ]),
    UI.createButton({ text: 'Create Invoice', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', onClick: () => Screens.showInvoiceModal() })
  ]));

  // Summary KPIs
  const totalOutstanding = data.invoices.filter(i => i.status === 'sent' || i.status === 'overdue').reduce((sum, i) => sum + i.balance, 0);
  const overdueCount = data.invoices.filter(i => i.status === 'overdue').length;
  const overdueAmount = data.invoices.filter(i => i.status === 'overdue').reduce((sum, i) => sum + i.balance, 0);
  const paidThisMonth = data.invoices.filter(i => i.status === 'paid' && new Date(i.paidDate) > new Date(new Date().getFullYear(), new Date().getMonth(), 1)).reduce((sum, i) => sum + i.total, 0);

  content.appendChild(UI.createElement('div', { class: 'kpi-grid mb-6' }, [
    UI.createKPICard({ label: 'Outstanding', value: UI.formatCurrency(totalOutstanding), subvalue: `${data.invoices.filter(i => i.status === 'sent' || i.status === 'overdue').length} invoices`, icon: '📄', iconBg: 'amber' }),
    UI.createKPICard({ label: 'Overdue', value: UI.formatCurrency(overdueAmount), subvalue: `${overdueCount} invoices past due`, trend: { value: overdueCount > 0 ? '⚠' : '✓', label: overdueCount > 0 ? 'Action needed' : 'All current', type: overdueCount > 0 ? 'negative' : 'positive' }, icon: '⚠', iconBg: 'red' }),
    UI.createKPICard({ label: 'Paid This Month', value: UI.formatCurrency(paidThisMonth), subvalue: 'Collected revenue', icon: '✅', iconBg: 'green' }),
    UI.createKPICard({ label: 'Draft Invoices', value: data.invoices.filter(i => i.status === 'draft').length, subvalue: 'Ready to send', icon: '📝', iconBg: 'primary' })
  ]));

  // Tabs
  content.appendChild(UI.createElement('div', { class: 'tabs mb-4' }, [
    { id: 'all', label: 'All', count: data.invoices.length },
    { id: 'draft', label: 'Draft', count: data.invoices.filter(i => i.status === 'draft').length },
    { id: 'sent', label: 'Sent', count: data.invoices.filter(i => i.status === 'sent').length },
    { id: 'overdue', label: 'Overdue', count: data.invoices.filter(i => i.status === 'overdue').length },
    { id: 'paid', label: 'Paid', count: data.invoices.filter(i => i.status === 'paid').length }
  ].map(tab => UI.createElement('button', {
    class: `tab ${tab.id === 'all' ? 'active' : ''}`,
    dataset: { tab: tab.id },
    onClick: (e) => {
      $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
      e.currentTarget.classList.add('active');
      Screens.renderInvoiceTable(tab.id);
    }
  }, tab.label + (tab.count > 0 ? ' <span class="badge badge-draft" style="margin-left: 6px; font-size: 10px;">' + tab.count + '</span>' : '')))));

  const tableContainer = UI.createElement('div', { id: 'invoice-table-container' });
  content.appendChild(tableContainer);

  setTimeout(() => Screens.renderInvoiceTable('all'), 0);

  return content;
};

Screens.renderInvoiceTable = function(statusFilter) {
  const data = getVisibleData();
  let invoices = data.invoices;
  if (statusFilter && statusFilter !== 'all') {
    invoices = invoices.filter(i => i.status === statusFilter);
  }

  const container = $('#invoice-table-container');
  if (!container) return;

  container.innerHTML = '';
  container.appendChild(UI.createTable({
    columns: [
      { field: 'invoiceNumber', header: 'Invoice #', render: (r) => UI.createElement('span', { class: 'fw-medium' }, r.invoiceNumber) },
      { field: 'clientId', header: 'Client', render: (r) => { const c = State.getClient(r.clientId); return c ? c.name : r.clientId; }},
      { field: 'projectId', header: 'Project', render: (r) => { const p = State.getProject(r.projectId); return p ? p.code : r.projectId; }},
      { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
      { field: 'dueDate', header: 'Due Date', render: (r) => UI.formatDate(r.dueDate) },
      { field: 'total', header: 'Total', render: (r) => UI.formatCurrency(r.total) },
      { field: 'amountPaid', header: 'Paid', render: (r) => UI.formatCurrency(r.amountPaid) },
      { field: 'balance', header: 'Balance', render: (r) => UI.createElement('span', { class: `fw-medium ${r.balance > 0 ? 'text-danger' : 'text-success'}` }, UI.formatCurrency(r.balance)) },
      { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
      { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
        UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('invoice-detail', { id: r.id }) }),
        r.status === 'draft' && UI.createButton({ text: 'Send', variant: 'primary', size: 'sm', onClick: () => { r.status = 'sent'; r.date = new Date().toISOString().split('T')[0]; Screens.renderCurrent(); UI.showToast('success', 'Invoice Sent', 'Invoice has been sent to client.'); } }),
        (r.status === 'sent' || r.status === 'overdue') && UI.createButton({ text: 'Mark Paid', variant: 'success', size: 'sm', onClick: () => { r.status = 'paid'; r.paidDate = new Date().toISOString().split('T')[0]; r.amountPaid = r.total; r.balance = 0; Screens.renderCurrent(); UI.showToast('success', 'Payment Recorded', 'Invoice marked as paid.'); } })
      ].filter(Boolean)) }
    ],
    data: invoices,
    emptyMessage: 'No invoices found for the selected filter.'
  }));
};

Screens.showInvoiceModal = function() {
  const data = getVisibleData();

  const form = UI.createElement('form', { onSubmit: (e) => { e.preventDefault(); Screens.saveInvoice(form); } }, [
    UI.createElement('div', { class: 'form-row' }, [
      UI.createSelect({ label: 'Client', name: 'clientId', options: [{ value: '', label: 'Select Client' }, ...data.clients.map(c => ({ value: c.id, label: c.name }))], required: true }),
      UI.createSelect({ label: 'Project', name: 'projectId', options: [{ value: '', label: 'No Project' }, ...data.projects.map(p => ({ value: p.id, label: `${p.code} - ${p.name}` }))] })
    ]),
    UI.createInput({ label: 'Invoice Date', type: 'date', name: 'date', value: new Date().toISOString().split('T')[0], required: true }),
    UI.createInput({ label: 'Due Date', type: 'date', name: 'dueDate', value: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], required: true }),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Description', name: 'description', placeholder: 'Invoice description...', required: true }),
      UI.createInput({ label: 'Quantity', type: 'number', name: 'quantity', step: '0.5', min: '0.5', value: '1', required: true })
    ]),
    UI.createElement('div', { class: 'form-row' }, [
      UI.createInput({ label: 'Unit', name: 'unit', value: 'hours' }),
      UI.createInput({ label: 'Rate', type: 'number', name: 'rate', step: '1', min: '0', required: true })
    ]),
    UI.createElement('div', { class: 'flex justify-end gap-3 mt-6' }, [
      UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => UI.closeModal(UI.createModal.lastId) }),
      UI.createButton({ text: 'Save as Draft', variant: 'secondary', type: 'submit' })
    ])
  ]);

  const modal = UI.createModal({ title: 'Create Invoice', children: [form], size: 'lg' });
  UI.createModal.lastId = modal.id;
};

Screens.saveInvoice = function(form) {
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);
  data.quantity = parseFloat(data.quantity);
  data.rate = parseFloat(data.rate);

  const client = State.getClient(data.clientId);
  const project = data.projectId ? State.getProject(data.projectId) : null;

  const newInvoice = {
    id: `inv-${Date.now()}`,
    invoiceNumber: `INV-${new Date().getFullYear()}-${String(State.state.invoices.length + 1).padStart(3, '0')}`,
    clientId: data.clientId,
    projectId: data.projectId || null,
    status: 'draft',
    date: data.date,
    dueDate: data.dueDate,
    paidDate: null,
    items: [{ description: data.description, quantity: data.quantity, unit: data.unit, rate: data.rate, amount: data.quantity * data.rate }],
    subtotal: data.quantity * data.rate,
    taxAmount: data.quantity * data.rate * State.state.settings.company.taxRate,
    total: data.quantity * data.rate * (1 + State.state.settings.company.taxRate),
    amountPaid: 0,
    balance: data.quantity * data.rate * (1 + State.state.settings.company.taxRate),
    notes: ''
  };

  State.state.invoices.unshift(newInvoice);
  UI.showToast('success', 'Invoice Created', `Invoice ${newInvoice.invoiceNumber} saved as draft.`);
  UI.closeModal(UI.createModal.lastId);
  Screens.renderCurrent();
};

// ==================== 11. INTEGRATIONS ====================
Screens.integrations = function() {
  const settings = State.state.settings.integrations;

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Integrations'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Configure and monitor external system connections.')
    ])
  ]));

  // Integration Cards
  const integrations = [
    {
      id: 'autodesk',
      name: 'Autodesk Construction Cloud',
      description: 'Sync projects, models, and user data with Autodesk Construction Cloud (BIM 360).',
      status: settings.autodesk.enabled ? 'connected' : 'available',
      icon: '🏗️',
      features: ['Project sync', 'Model access', 'User provisioning', 'Issue tracking'],
      config: settings.autodesk
    },
    {
      id: 'revit',
      name: 'Revit Connector',
      description: 'Read-only Revit connector for document identity, workset, and project signals.',
      status: settings.revit.enabled ? 'connected' : 'available',
      icon: '📐',
      features: ['Journal parsing', 'Model identification', 'Sync events', 'Worksharing monitoring'],
      config: settings.revit
    },
    {
      id: 'activitywatch',
      name: 'ActivityWatch',
      description: 'Local activity tracking for window focus, idle detection, and application usage.',
      status: settings.activitywatch.enabled ? 'connected' : 'available',
      icon: '📊',
      features: ['Window tracking', 'Idle detection', 'AFK monitoring', 'Local data storage'],
      config: settings.activitywatch
    },
    {
      id: 'windows-agent',
      name: 'Windows Desktop Agent',
      description: 'Background agent for automatic time capture, project attribution, and privacy controls.',
      status: 'planned',
      icon: '🖥️',
      features: ['Auto-start with Windows', 'Revit/AutoCAD detection', 'Privacy controls', 'Offline queue'],
      config: {}
    },
    {
      id: 'accounting',
      name: 'Accounting Software (Xero/MYOB)',
      description: 'Push approved invoices and sync contacts with accounting platforms.',
      status: 'planned',
      icon: '💰',
      features: ['Invoice sync', 'Contact sync', 'Payment tracking', 'Tax compliance'],
      config: {}
    },
    {
      id: 'calendar',
      name: 'Calendar Integration (Outlook/Google)',
      description: 'Import meetings and calendar events for improved activity classification.',
      status: 'planned',
      icon: '📅',
      features: ['Meeting import', 'Attendee mapping', 'Project linking', 'Time blocking'],
      config: {}
    }
  ];

  content.appendChild(UI.createElement('div', { class: 'd-grid gap-4', style: 'grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));' }, integrations.map(int => {
    const statusColors = {
      connected: { badge: 'approved', text: 'Connected', desc: 'Active and syncing' },
      available: { badge: 'pending', text: 'Available', desc: 'Not configured' },
      planned: { badge: 'observed', text: 'Planned', desc: 'Future integration' }
    };
    const status = statusColors[int.status];

    return UI.createCard({
      children: [
        UI.createElement('div', { class: 'd-flex gap-4 mb-4' }, [
          UI.createElement('div', { class: 'avatar avatar-lg', style: 'width: 56px; height: 56px; font-size: 24px; background: var(--color-primary-light); color: var(--color-primary);' }, int.icon),
          UI.createElement('div', { class: 'flex-1' }, [
            UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
              UI.createElement('h3', { class: 'card-title', style: 'margin: 0;' }, int.name),
              UI.createBadge(status.text, status.badge)
            ]),
            UI.createElement('p', { class: 'text-secondary text-sm mt-1' }, int.description)
          ])
        ]),
        UI.createElement('div', { class: 'mb-4' }, [
          UI.createElement('h4', { style: 'font-size: 12px; text-transform: uppercase; color: var(--color-text-muted); margin-bottom: 8px;' }, 'Features'),
          UI.createElement('div', { class: 'd-flex flex-wrap gap-2' }, int.features.map(f => UI.createElement('span', { class: 'badge badge-draft', style: 'font-size: 11px;' }, f)))
        ]),
        int.config.enabled !== undefined && UI.createElement('div', { class: 'd-flex items-center justify-between p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md);' }, [
          UI.createElement('div', {}, [
            UI.createElement('div', { class: 'fw-medium' }, 'Status'),
            UI.createElement('div', { class: 'text-sm text-secondary' }, status.desc)
          ]),
          UI.createElement('label', { class: 'd-flex items-center gap-3 cursor-pointer' }, [
            UI.createElement('input', { type: 'checkbox', checked: int.config.enabled, onChange: (e) => { int.config.enabled = e.target.checked; Screens.renderCurrent(); } }),
            UI.createElement('span', {}, int.config.enabled ? 'Disable' : 'Enable')
          ])
        ]),
        int.config.host && UI.createElement('div', { class: 'd-grid gap-2 mt-3', style: 'font-size: 13px; color: var(--color-text-secondary);' }, [
          UI.createElement('div', {}, `Host: ${int.config.host}:${int.config.port || ''}`),
          UI.createElement('div', {}, `Sync: ${int.config.syncFrequency || 'N/A'}`)
        ])
      ]
    });
  })));

  return content;
};

// ==================== 12. NOTIFICATIONS ====================
Screens.notifications = function() {
  const data = getVisibleData();
  const notifications = data.notifications;

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Notifications'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Stay informed about approvals, budget alerts, and system updates.')
    ]),
    UI.createElement('div', { class: 'flex gap-2' }, [
      UI.createButton({ text: 'Mark All Read', variant: 'secondary', size: 'sm', onClick: () => { State.markAllNotificationsRead(); Screens.renderCurrent(); } }),
      UI.createButton({ text: 'Preferences', variant: 'ghost', size: 'sm' })
    ])
  ]));

  // Tabs
  content.appendChild(UI.createElement('div', { class: 'tabs mb-4' }, [
    { id: 'all', label: 'All', count: notifications.length },
    { id: 'unread', label: 'Unread', count: notifications.filter(n => !n.read).length },
    { id: 'timesheet', label: 'Timesheets', count: notifications.filter(n => n.type === 'timesheet_approval' || n.type === 'timesheet_rejected').length },
    { id: 'budget', label: 'Budget', count: notifications.filter(n => n.type === 'budget_warning').length },
    { id: 'billing', label: 'Billing', count: notifications.filter(n => n.type === 'invoice_overdue' || n.type === 'quote_accepted').length }
  ].map(tab => UI.createElement('button', {
    class: `tab ${tab.id === 'all' ? 'active' : ''}`,
    dataset: { tab: tab.id },
    onClick: (e) => {
      $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
      e.currentTarget.classList.add('active');
      Screens.renderNotificationList(tab.id);
    }
  }, tab.label + (tab.count > 0 ? ' <span class="badge badge-draft" style="margin-left: 6px; font-size: 10px;">' + tab.count + '</span>' : '')))));

  const listContainer = UI.createElement('div', { id: 'notification-list-container' });
  content.appendChild(listContainer);

  setTimeout(() => Screens.renderNotificationList('all'), 0);

  return content;
};

Screens.renderNotificationList = function(filter) {
  const data = getVisibleData();
  let notifications = data.notifications;

  if (filter === 'unread') {
    notifications = notifications.filter(n => !n.read);
  } else if (filter !== 'all') {
    notifications = notifications.filter(n => n.type.includes(filter) || (filter === 'timesheet' && (n.type === 'timesheet_approval' || n.type === 'timesheet_rejected')) || (filter === 'billing' && (n.type === 'invoice_overdue' || n.type === 'quote_accepted')));
  }

  const container = $('#notification-list-container');
  if (!container) return;

  container.innerHTML = '';

  if (notifications.length === 0) {
    container.appendChild(UI.createEmptyState({ title: 'No notifications', message: 'You\'re all caught up!', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>' }));
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

    const card = UI.createElement('div', {
      class: `d-flex gap-3 p-4 ${!notif.read ? 'bg-primary' : ''}`,
      style: `background: ${!notif.read ? 'var(--color-primary-light)' : 'var(--color-surface)'}; border: 1px solid var(--color-border); border-radius: var(--radius-lg); margin-bottom: 8px; transition: all var(--transition-fast);`
    }, [
      UI.createElement('div', { class: 'text-2xl' }, typeIcons[notif.type] || '🔔'),
      UI.createElement('div', { class: 'flex-1' }, [
        UI.createElement('div', { class: 'd-flex justify-between' }, [
          UI.createElement('h4', { class: `${!notif.read ? 'fw-bold' : 'fw-medium'}` }, notif.title),
          UI.createElement('span', { class: 'text-xs text-muted' }, UI.formatDateTime(notif.createdAt))
        ]),
        UI.createElement('p', { class: 'text-sm text-secondary mt-1' }, notif.message),
        notif.referenceId && UI.createElement('button', { class: 'btn btn-ghost btn-xs mt-2', onClick: () => Screens.navigateToReference(notif) }, 'View Details')
      ]),
      !notif.read && UI.createIconButton({ icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>', ariaLabel: 'Mark as read', onClick: () => { State.markNotificationRead(notif.id); Screens.renderCurrent(); } })
    ]);
    container.appendChild(card);
  });
};

Screens.navigateToReference = function(notif) {
  switch (notif.referenceType) {
    case 'timesheet':
      RouterInstance.navigate('timesheets');
      break;
    case 'project':
      RouterInstance.navigate('project-detail', { id: notif.referenceId });
      break;
    case 'invoice':
      RouterInstance.navigate('invoice-detail', { id: notif.referenceId });
      break;
    case 'quote':
      RouterInstance.navigate('quote-detail', { id: notif.referenceId });
      break;
  }
};

// ==================== 13. COMPANY SETTINGS ====================
Screens['company-settings'] = function() {
  const settings = State.state.settings;

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Company Settings'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Configure company details, policies, and system preferences.')
    ]),
    UI.createButton({ text: 'Save All Changes', variant: 'primary', onClick: () => { UI.showToast('success', 'Settings Saved', 'All company settings have been updated.'); } })
  ]));

  // Settings Tabs
  const settingTabs = [
    { id: 'profile', label: 'Company Profile' },
    { id: 'timesheet', label: 'Timesheet Policies' },
    { id: 'approval', label: 'Approval Workflows' },
    { id: 'privacy', label: 'Privacy & Data' },
    { id: 'billing', label: 'Billing Settings' },
    { id: 'integrations', label: 'Integrations' }
  ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-6' }, settingTabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${tab.id === 'profile' ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        Screens.renderSettingsTab(tab.id);
      }
    }, tab.label)
  )));

  const tabContainer = UI.createElement('div', { id: 'settings-tab-container' });
  content.appendChild(tabContainer);

  setTimeout(() => Screens.renderSettingsTab('profile'), 0);

  return content;
};

Screens.renderSettingsTab = function(tabId) {
  const settings = State.state.settings;
  const container = $('#settings-tab-container');
  if (!container) return;

  container.innerHTML = '';

  switch (tabId) {
    case 'profile':
      container.appendChild(UI.createCard({
        title: 'Company Information',
        children: UI.createElement('form', {}, [
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Company Name', name: 'name', value: settings.company.name }),
            UI.createInput({ label: 'ABN', name: 'abn', value: settings.company.abn })
          ]),
          UI.createInput({ label: 'Address', name: 'address', type: 'textarea', value: settings.company.address }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Phone', name: 'phone', value: settings.company.phone }),
            UI.createInput({ label: 'Email', type: 'email', name: 'email', value: settings.company.email })
          ]),
          UI.createInput({ label: 'Website', name: 'website', value: settings.company.website }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createSelect({ label: 'Currency', name: 'currency', options: [{ value: 'AUD', label: 'AUD ($)' }, { value: 'USD', label: 'USD ($)' }, { value: 'EUR', label: 'EUR (€)' }], value: settings.company.currency }),
            UI.createInput({ label: 'Tax Rate (%)', type: 'number', step: '0.01', name: 'taxRate', value: settings.company.taxRate * 100 })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createSelect({ label: 'Fiscal Year Start', name: 'fiscalYearStart', options: [{ value: '01-01', label: 'January 1' }, { value: '04-01', label: 'April 1' }, { value: '07-01', label: 'July 1' }, { value: '10-01', label: 'October 1' }], value: settings.company.fiscalYearStart }),
            UI.createSelect({ label: 'Timezone', name: 'timezone', options: [{ value: 'Australia/Melbourne', label: 'Australia/Melbourne' }, { value: 'Australia/Sydney', label: 'Australia/Sydney' }, { value: 'Australia/Brisbane', label: 'Australia/Brisbane' }, { value: 'Australia/Perth', label: 'Australia/Perth' }], value: settings.company.timezone })
          ])
        ])
      }));
      break;

    case 'timesheet':
      container.appendChild(UI.createCard({
        title: 'Timesheet Policies',
        children: UI.createElement('form', {}, [
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Auto-submit timesheets'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.timesheet.autoSubmit }),
              UI.createElement('span', {}, 'Automatically submit timesheets at period end')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Require description'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.timesheet.requireDescription }),
              UI.createElement('span', {}, 'Users must enter a description for each entry')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Max Hours Per Day', type: 'number', name: 'maxHoursPerDay', value: settings.timesheet.maxHoursPerDay }),
            UI.createInput({ label: 'Default Hours Per Day', type: 'number', step: '0.1', name: 'defaultHoursPerDay', value: settings.timesheet.defaultHoursPerDay })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Approval required'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.timesheet.approvalRequired }),
              UI.createElement('span', {}, 'Timesheets require manager approval')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Allow retroactive entries'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.timesheet.allowRetroactive }),
              UI.createElement('span', {}, 'Allow editing past timesheets')
            ])
          ]),
          UI.createInput({ label: 'Retroactive window (days)', type: 'number', name: 'retroactiveDays', value: settings.timesheet.retroactiveDays }),
          UI.createSelect({ label: 'Work week starts', name: 'workWeekStart', options: [{ value: '0', label: 'Sunday' }, { value: '1', label: 'Monday' }], value: String(settings.timesheet.workWeekStart) })
        ])
      }));
      break;

    case 'approval':
      container.appendChild(UI.createCard({
        title: 'Approval Workflows',
        children: UI.createElement('form', {}, [
          UI.createSelect({ label: 'Approval workflow', name: 'workflow', options: [{ value: 'manager', label: 'Manager approval' }, { value: 'admin', label: 'Admin approval' }, { value: 'both', label: 'Manager then Admin' }], value: settings.approval.workflow }),
          UI.createInput({ label: 'Auto-approve threshold (hours)', type: 'number', name: 'autoApproveThreshold', value: settings.approval.autoApproveThreshold }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Require reason for rejection'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.approval.requireReasonForRejection }),
              UI.createElement('span', {}, 'Managers must provide reason when returning timesheets')
            ])
          ]),
          UI.createInput({ label: 'Escalation period (days)', type: 'number', name: 'escalationDays', value: settings.approval.escalationDays }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Enable reminders'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.approval.remindersEnabled }),
              UI.createElement('span', {}, 'Send reminder notifications for pending approvals')
            ])
          ]),
          UI.createSelect({ label: 'Reminder frequency', name: 'reminderFrequency', options: [{ value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }], value: settings.approval.reminderFrequency })
        ])
      }));
      break;

    case 'privacy':
      container.appendChild(UI.createCard({
        title: 'Privacy & Data Retention',
        children: UI.createElement('form', {}, [
          UI.createInput({ label: 'Data retention (days)', type: 'number', name: 'dataRetentionDays', value: settings.privacy.dataRetentionDays }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Allow personal time tracking'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.privacy.allowPersonalTime }),
              UI.createElement('span', {}, 'Users can mark time as personal/non-work')
            ])
          ]),
          UI.createInput({ label: 'Max personal hours per day', type: 'number', step: '0.5', name: 'personalTimeMaxHoursPerDay', value: settings.privacy.personalTimeMaxHoursPerDay }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Require user consent'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.privacy.requireConsent }),
              UI.createElement('span', {}, 'Users must consent before tracking begins')
            ])
          ]),
          UI.createInput({ label: 'Idle timeout (minutes)', type: 'number', name: 'idleTimeoutMinutes', value: settings.privacy.idleTimeoutMinutes }),
          UI.createInput({ label: 'Captured applications (comma separated)', name: 'captureApplications', value: settings.privacy.captureApplications.join(', ') }),
          UI.createInput({ label: 'Excluded applications (comma separated)', name: 'excludeApplications', value: settings.privacy.excludeApplications.join(', ') })
        ])
      }));
      break;

    case 'billing':
      container.appendChild(UI.createCard({
        title: 'Billing Settings',
        children: UI.createElement('form', {}, [
          UI.createInput({ label: 'Default payment terms (days)', type: 'number', name: 'defaultPaymentTerms', value: settings.billing.defaultPaymentTerms }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Invoice prefix', name: 'invoicePrefix', value: settings.billing.invoicePrefix }),
            UI.createInput({ label: 'Quote prefix', name: 'quotePrefix', value: settings.billing.quotePrefix })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Timesheet prefix', name: 'timesheetPrefix', value: settings.billing.timesheetPrefix }),
            UI.createInput({ label: 'Project prefix', name: 'projectPrefix', value: settings.billing.projectPrefix })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Enable late fees'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: settings.billing.enableLateFees }),
              UI.createElement('span', {}, 'Automatically apply late fees to overdue invoices')
            ])
          ]),
          UI.createInput({ label: 'Late fee (% per month)', type: 'number', step: '0.1', name: 'lateFeePercent', value: settings.billing.lateFeePercent }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Default markup (%)', type: 'number', name: 'defaultMarkupPercent', value: settings.billing.defaultMarkupPercent }),
            UI.createInput({ label: 'Default contingency (%)', type: 'number', name: 'defaultContingencyPercent', value: settings.billing.defaultContingencyPercent })
          ])
        ])
      }));
      break;

    case 'integrations':
      container.appendChild(UI.createCard({
        title: 'Integration Settings',
        children: UI.createElement('div', { class: 'd-grid gap-6' }, [
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Autodesk Construction Cloud'),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Client ID', name: 'autodeskClientId', value: settings.integrations.autodesk.clientId }),
              UI.createInput({ label: 'Account ID', name: 'autodeskAccountId', value: settings.integrations.autodesk.accountId })
            ]),
            UI.createSelect({ label: 'Sync frequency', name: 'autodeskSyncFrequency', options: [{ value: 'realtime', label: 'Real-time' }, { value: 'hourly', label: 'Hourly' }, { value: 'daily', label: 'Daily' }], value: settings.integrations.autodesk.syncFrequency })
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'ActivityWatch'),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Host', name: 'activitywatchHost', value: settings.integrations.activitywatch.host }),
              UI.createInput({ label: 'Port', type: 'number', name: 'activitywatchPort', value: settings.integrations.activitywatch.port })
            ]),
            UI.createSelect({ label: 'Sync frequency', name: 'activitywatchSyncFrequency', options: [{ value: 'realtime', label: 'Real-time' }, { value: '15min', label: 'Every 15 minutes' }, { value: 'hourly', label: 'Hourly' }], value: settings.integrations.activitywatch.syncFrequency })
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Revit Connector'),
            UI.createSelect({ label: 'Revit Version', name: 'revitVersion', options: [{ value: '2024', label: '2024' }, { value: '2025', label: '2025' }, { value: '2026', label: '2026' }], value: settings.integrations.revit.version }),
            UI.createInput({ label: 'Journal Path', name: 'revitJournalPath', value: settings.integrations.revit.journalPath }),
            UI.createSelect({ label: 'Sync frequency', name: 'revitSyncFrequency', options: [{ value: 'realtime', label: 'Real-time' }, { value: 'hourly', label: 'Hourly' }], value: settings.integrations.revit.syncFrequency })
          ])
        ])
      }));
      break;
  }
};

// ==================== 14. USER PROFILE ====================
Screens.profile = function() {
  const user = State.getCurrentUser();
  const role = State.getCurrentRole();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'User Profile'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Manage your personal details, preferences, and privacy settings.')
    ]),
    UI.createButton({ text: 'Save Changes', variant: 'primary', onClick: () => { UI.showToast('success', 'Profile Saved', 'Your profile has been updated.'); } })
  ]));

  // Profile Tabs
  const profileTabs = [
    { id: 'details', label: 'Personal Details' },
    { id: 'preferences', label: 'Preferences' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'privacy', label: 'Privacy & Activity' },
    { id: 'timesheet', label: 'Timesheet Settings' }
  ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-6' }, profileTabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${tab.id === 'details' ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        Screens.renderProfileTab(tab.id);
      }
    }, tab.label)
  )));

  const tabContainer = UI.createElement('div', { id: 'profile-tab-container' });
  content.appendChild(tabContainer);

  setTimeout(() => Screens.renderProfileTab('details'), 0);

  return content;
};

Screens.renderProfileTab = function(tabId) {
  const user = State.getCurrentUser();
  const container = $('#profile-tab-container');
  if (!container) return;

  container.innerHTML = '';

  switch (tabId) {
    case 'details':
      container.appendChild(UI.createCard({
        title: 'Personal Information',
        children: UI.createElement('form', {}, [
          UI.createElement('div', { class: 'd-flex gap-4 mb-6' }, [
            UI.createElement('div', { class: 'avatar avatar-xl', style: 'width: 80px; height: 80px; font-size: 32px; background: var(--color-primary); color: white; flex-shrink: 0;' }, UI.getInitials(`${user.firstName} ${user.lastName}`)),
            UI.createElement('div', { class: 'flex-1 d-flex flex-col justify-center' }, [
              UI.createElement('h3', { style: 'font-size: 20px; font-weight: 600;' }, `${user.firstName} ${user.lastName}`),
              UI.createElement('span', { class: `badge badge-${user.role}` }, user.role),
              UI.createElement('p', { class: 'text-sm text-muted mt-1' }, user.email)
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'First Name', name: 'firstName', value: user.firstName }),
            UI.createInput({ label: 'Last Name', name: 'lastName', value: user.lastName })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Email', type: 'email', name: 'email', value: user.email }),
            UI.createInput({ label: 'Phone', name: 'phone', value: user.phone })
          ]),
          UI.createInput({ label: 'Department', name: 'department', value: user.department }),
          UI.createInput({ label: 'Position', name: 'position', value: user.position }),
          UI.createInput({ label: 'Skills (comma separated)', name: 'skills', value: user.skills?.join(', ') || '' })
        ])
      }));
      break;

    case 'preferences':
      container.appendChild(UI.createCard({
        title: 'Display Preferences',
        children: UI.createElement('form', {}, [
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Theme'),
            UI.createElement('div', { class: 'd-flex gap-4' }, [
              UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
                UI.createElement('input', { type: 'radio', name: 'theme', value: 'light', checked: State.state.theme === 'light', onChange: () => State.set('theme', 'light') }),
                UI.createElement('span', {}, 'Light')
              ]),
              UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
                UI.createElement('input', { type: 'radio', name: 'theme', value: 'dark', checked: State.state.theme === 'dark', onChange: () => State.set('theme', 'dark') }),
                UI.createElement('span', {}, 'Dark')
              ]),
              UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
                UI.createElement('input', { type: 'radio', name: 'theme', value: 'system', onChange: () => State.set('theme', 'system') }),
                UI.createElement('span', {}, 'System')
              ])
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Sidebar collapsed by default'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: State.state.sidebarCollapsed, onChange: (e) => State.set('sidebarCollapsed', e.target.checked) }),
              UI.createElement('span', {}, 'Start with collapsed sidebar')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Compact density'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox' }),
              UI.createElement('span', {}, 'Use compact spacing for tables and lists')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Reduce motion'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox' }),
              UI.createElement('span', {}, 'Disable animations and transitions')
            ])
          ])
        ])
      }));
      break;

    case 'notifications':
      container.appendChild(UI.createCard({
        title: 'Notification Preferences',
        children: UI.createElement('form', {}, [
          UI.createElement('p', { class: 'text-sm text-secondary mb-4' }, 'Choose which notifications you want to receive and how.'),
          [
            { id: 'timesheet_approval', label: 'Timesheet approval requests', desc: 'When timesheets are submitted for your review' },
            { id: 'timesheet_rejected', label: 'Timesheet returned for correction', desc: 'When your timesheet is rejected' },
            { id: 'budget_warning', label: 'Budget warnings', desc: 'When projects approach or exceed budget' },
            { id: 'invoice_overdue', label: 'Invoice overdue alerts', desc: 'When client invoices become overdue' },
            { id: 'quote_accepted', label: 'Quote accepted', desc: 'When a client accepts a quote' },
            { id: 'activity_classification', label: 'Activity classification reminders', desc: 'When unclassified activity needs attention' },
            { id: 'project_update', label: 'Project updates', desc: 'Changes to projects you\'re assigned to' }
          ].forEach(notif => {
            container.appendChild(UI.createElement('div', { class: 'd-flex justify-between items-center py-3 border-bottom', style: 'border-color: var(--color-border);' }, [
              UI.createElement('div', {}, [
                UI.createElement('div', { class: 'fw-medium' }, notif.label),
                UI.createElement('div', { class: 'text-sm text-muted' }, notif.desc)
              ]),
              UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
                UI.createElement('input', { type: 'checkbox', checked: true }),
                UI.createElement('span', {}, 'Enabled')
              ])
            ]));
          })
        ])
      }));
      break;

    case 'privacy':
      container.appendChild(UI.createCard({
        title: 'Privacy & Activity Visibility',
        children: UI.createElement('form', {}, [
          UI.createElement('p', { class: 'text-sm text-secondary mb-4' }, 'Control what activity data is visible to managers and how your data is used.'),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Show my activity to managers'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'Allow managers to see my application usage and project attribution')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Allow activity-based suggestions'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'System can suggest timesheet entries based on detected activity')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Include in team utilization reports'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'My hours included in team utilization calculations')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Data retention consent'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'I consent to my activity data being retained per company policy')
            ])
          ]),
          UI.createElement('div', { class: 'mt-6 p-4', style: 'background: var(--color-amber-light); border-radius: var(--radius-md); border: 1px solid var(--color-border);' }, [
            UI.createElement('h4', { class: 'fw-semibold mb-2' }, 'Your Rights'),
            UI.createElement('ul', { class: 'text-sm text-secondary', style: 'margin-left: 20px;' }, [
              'Request a copy of all your personal data',
              'Request correction of inaccurate data',
              'Request deletion of your data (subject to legal retention requirements)',
              'Withdraw consent for activity tracking at any time',
              'File a complaint with the privacy regulator'
            ].map(item => UI.createElement('li', {}, item)))
          ])
        ])
      }));
      break;

    case 'timesheet':
      container.appendChild(UI.createCard({
        title: 'Timesheet Preferences',
        children: UI.createElement('form', {}, [
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Default view'),
            UI.createSelect({ name: 'defaultTimesheetView', options: [{ value: 'weekly', label: 'Weekly' }, { value: 'daily', label: 'Daily' }, { value: 'monthly', label: 'Monthly' }], value: 'weekly' })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Auto-save draft entries'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'Automatically save draft timesheets as you type')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Show suggested entries'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'Display AI-suggested timesheet entries from activity data')
            ])
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Remind me to submit'),
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
              UI.createElement('input', { type: 'checkbox', checked: true }),
              UI.createElement('span', {}, 'Send reminder when timesheet is due')
            ])
          ]),
          UI.createSelect({ label: 'Reminder timing', options: [{ value: 'morning', label: 'Morning of due date' }, { value: 'day-before', label: 'Day before due date' }, { value: 'week-before', label: 'Week before due date' }], value: 'day-before' }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createElement('label', { class: 'form-label' }, 'Default hours per day'),
            UI.createInput({ type: 'number', step: '0.1', min: '0', max: '12', value: '7.6' })
          ])
        ])
      }));
      break;
  }
};

// ==================== 15. DESKTOP AGENT ====================
Screens['desktop-agent'] = function() {
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'Desktop Agent'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Windows desktop tracking application - UI simulation.')
    ])
  ]));

  // Agent Status Card
  content.appendChild(UI.createCard({
    title: 'Tracking Status',
    children: UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));' }, [
      // Status Panel
      UI.createElement('div', { class: 'd-flex flex-col gap-4' }, [
        UI.createElement('div', { class: 'd-flex items-center gap-4 p-4', style: 'background: var(--color-teal-light); border-radius: var(--radius-lg); border: 1px solid var(--color-teal);' }, [
          UI.createElement('div', { class: 'avatar avatar-lg', style: 'width: 56px; height: 56px; background: var(--color-teal); color: white; font-size: 24px;' }, '🟢'),
          UI.createElement('div', {}, [
            UI.createElement('h3', { style: 'font-size: 18px; font-weight: 600; color: var(--color-teal);' }, 'Tracking Active'),
            UI.createElement('p', { class: 'text-sm text-secondary' }, 'Connected to BIMSpend server • Last sync: 2 minutes ago')
          ])
        ]),
        UI.createElement('div', { class: 'd-flex gap-2 flex-wrap' }, [
          UI.createButton({ text: 'Pause Tracking', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>', onClick: () => UI.showToast('info', 'Tracking Paused', 'Desktop agent tracking has been paused.') }),
          UI.createButton({ text: 'Resume', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>', onClick: () => UI.showToast('success', 'Tracking Resumed', 'Desktop agent tracking has been resumed.') }),
          UI.createButton({ text: 'Settings', variant: 'ghost', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' })
        ])
      ]),

      // Current Activity
      UI.createElement('div', {}, [
        UI.createElement('h4', { class: 'mb-3' }, 'Current Activity'),
        UI.createElement('div', { class: 'd-flex items-center gap-3 p-3', style: 'background: var(--color-primary-light); border-radius: var(--radius-md); border: 1px solid var(--color-primary);' }, [
          UI.createElement('div', { class: 'avatar', style: 'width: 48px; height: 48px; background: var(--color-primary); color: white; font-size: 20px;' }, '📐'),
          UI.createElement('div', { class: 'flex-1' }, [
            UI.createElement('div', { class: 'fw-medium' }, 'Revit 2025'),
            UI.createElement('div', { class: 'text-sm text-secondary' }, 'MRV-FP-2024-001 - Sprinkler Layout Level B2.rvt'),
            UI.createElement('div', { class: 'text-xs text-muted mt-1' }, 'Project: Metro Tunnel Fire Protection • Active for 45 minutes')
          ])
        ])
      ])
    ])
  }));

  // Activity Timeline
  content.appendChild(UI.createCard({
    title: 'Today\'s Activity Timeline',
    children: UI.createElement('div', { class: 'd-flex flex-col gap-3' }, [
      { time: '09:00', app: 'Revit 2025', project: 'MRV-FP-2024-001', activity: 'Sprinkler layout - Level B2', duration: '2h 15m', state: 'productive' },
      { time: '11:15', app: 'Microsoft Teams', project: 'MRV-FP-2024-001', activity: 'Coordination meeting', duration: '45m', state: 'productive' },
      { time: '12:00', app: 'Chrome', project: '—', activity: 'Lunch break', duration: '1h', state: 'idle' },
      { time: '13:00', app: 'Revit 2025', project: 'MRV-FP-2024-001', activity: 'Clash detection review', duration: '1h 30m', state: 'productive' },
      { time: '14:30', app: 'Navisworks', project: 'MRV-FP-2024-001', activity: 'Model coordination', duration: '1h', state: 'productive' },
      { time: '15:30', app: 'Outlook', project: '—', activity: 'Email correspondence', duration: '30m', state: 'productive' },
      { time: '16:00', app: 'Revit 2025', project: 'LL-FP-2024-003', activity: 'Hydrant layout - Basement', duration: '1h 30m', state: 'productive' }
    ].map(item => UI.createElement('div', { class: 'd-flex gap-3 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md);' }, [
      UI.createElement('div', { class: 'fw-medium text-secondary', style: 'width: 80px; flex-shrink: 0;' }, item.time),
      UI.createElement('div', { class: 'flex-1' }, [
        UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
          UI.createElement('span', { class: `badge badge-${item.state}` }, item.state),
          UI.createElement('span', { class: 'fw-medium' }, item.app),
          UI.createElement('span', { class: 'text-muted' }, '•'),
          UI.createElement('span', { class: 'text-primary fw-medium' }, item.project)
        ]),
        UI.createElement('div', { class: 'text-sm text-secondary mt-1' }, item.activity),
        UI.createElement('div', { class: 'text-xs text-muted mt-1' }, `Duration: ${item.duration}`)
      ])
    ])))
  }));

  // Privacy & Consent
  content.appendChild(UI.createCard({
    title: 'Privacy Controls',
    children: UI.createElement('div', { class: 'd-grid gap-4' }, [
      UI.createElement('div', { class: 'd-flex items-center justify-between' }, [
        UI.createElement('div', {}, [
          UI.createElement('div', { class: 'fw-medium' }, 'Activity Tracking'),
          UI.createElement('div', { class: 'text-sm text-secondary' }, 'Allow the agent to capture application usage and window titles')
        ]),
        UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
          UI.createElement('input', { type: 'checkbox', checked: true, onChange: (e) => UI.showToast(e.target.checked ? 'success' : 'warning', e.target.checked ? 'Tracking Enabled' : 'Tracking Disabled', 'Activity tracking has been ' + (e.target.checked ? 'enabled' : 'disabled') + '.') }),
          UI.createElement('span', {}, 'Enabled')
        ])
      ]),
      UI.createElement('div', { class: 'd-flex items-center justify-between' }, [
        UI.createElement('div', {}, [
          UI.createElement('div', { class: 'fw-medium' }, 'Project Attribution'),
          UI.createElement('div', { class: 'text-sm text-secondary' }, 'Automatically attribute time to projects based on Revit model')
        ]),
        UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
          UI.createElement('input', { type: 'checkbox', checked: true }),
          UI.createElement('span', {}, 'Enabled')
        ])
      ]),
      UI.createElement('div', { class: 'd-flex items-center justify-between' }, [
        UI.createElement('div', {}, [
          UI.createElement('div', { class: 'fw-medium' }, 'Idle Detection'),
          UI.createElement('div', { class: 'text-sm text-secondary' }, 'Automatically detect when you\'re away from your computer')
        ]),
        UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
          UI.createElement('input', { type: 'checkbox', checked: true }),
          UI.createElement('span', {}, 'Enabled')
        ])
      ]),
      UI.createElement('div', { class: 'd-flex items-center justify-between' }, [
        UI.createElement('div', {}, [
          UI.createElement('div', { class: 'fw-medium' }, 'Data Sync'),
          UI.createElement('div', { class: 'text-sm text-secondary' }, 'Automatically sync tracked data to BIMSpend server')
        ]),
        UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer' }, [
          UI.createElement('input', { type: 'checkbox', checked: true }),
          UI.createElement('span', {}, 'Enabled')
        ])
      ]),
      UI.createElement('div', { class: 'pt-4 border-top', style: 'border-color: var(--color-border);' }, [
        UI.createElement('h4', { class: 'mb-2' }, 'Data Retention'),
        UI.createElement('p', { class: 'text-sm text-secondary' }, 'Your activity data is stored locally and synced to the server. You can request a copy or deletion of your data at any time through your profile settings.')
      ])
    ])
  }));

  // Connection Diagnostics
  content.appendChild(UI.createCard({
    title: 'Connection Diagnostics',
    children: UI.createElement('div', { class: 'd-grid gap-3' }, [
      { label: 'Server Connection', status: 'connected', detail: 'api.bimspend.com • 24ms latency' },
      { label: 'Authentication', status: 'connected', detail: 'Token valid • Expires in 23h 45m' },
      { label: 'Revit Connector', status: 'connected', detail: 'Revit 2025 detected • Journal path accessible' },
      { label: 'ActivityWatch', status: 'connected', detail: 'localhost:5600 • Last heartbeat 30s ago' },
      { label: 'Offline Queue', status: 'connected', detail: '0 items pending • 0 bytes queued' },
      { label: 'Auto-start', status: 'connected', detail: 'Enabled • Runs on Windows login' }
    ].map(item => UI.createElement('div', { class: 'd-flex items-center justify-between p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md);' }, [
      UI.createElement('div', {}, [
        UI.createElement('div', { class: 'fw-medium' }, item.label),
        UI.createElement('div', { class: 'text-sm text-secondary' }, item.detail)
      ]),
      UI.createElement('span', { class: `badge badge-${item.status === 'connected' ? 'active' : 'offline'}` }, item.status)
    ])))
  }));

  return content;
};

// ==================== 16. ONBOARDING ====================
Screens.onboarding = function() {
  const steps = [
    { id: 1, title: 'Welcome', icon: '👋', description: 'Welcome to BIMSpend! Let\'s get your company set up in a few simple steps.' },
    { id: 2, title: 'Company Setup', icon: '🏢', description: 'Enter your company details, ABN, address, and billing preferences.' },
    { id: 3, title: 'Invite Team', icon: '👥', description: 'Add your employees, assign roles, and set their hourly rates.' },
    { id: 4, title: 'Create Projects', icon: '📁', description: 'Set up your first projects, link clients, and define budgets.' },
    { id: 5, title: 'Rates & Billing', icon: '💰', description: 'Configure labour cost rates, billable rates, and default markup.' },
    { id: 6, title: 'Desktop Agent', icon: '🖥️', description: 'Install the Windows agent for automatic time tracking.' },
    { id: 7, title: 'Privacy & Consent', icon: '🔒', description: 'Review privacy settings and obtain team consent for tracking.' },
    { id: 8, title: 'Complete', icon: '✅', description: 'You\'re all set! Start tracking time and improving project profitability.' }
  ];

  let currentStep = parseInt(localStorage.getItem('bimspend_onboarding_step') || '1');

  const content = UI.createElement('div', { style: 'max-width: 700px; margin: 0 auto;' });

  // Progress Indicator
  content.appendChild(UI.createElement('div', { class: 'mb-8' }, [
    UI.createElement('div', { class: 'd-flex justify-between mb-4' }, steps.map((step, i) =>
      UI.createElement('div', { class: 'd-flex flex-col items-center', style: `flex: 1; position: relative;` }, [
        i < steps.length - 1 && UI.createElement('div', { class: 'absolute top-8 left-50% w-full h-2', style: `background: ${i + 1 < currentStep ? 'var(--color-teal)' : 'var(--color-border)'}; z-index: 0; transform: translateX(-50%);` }),
        UI.createElement('div', { class: 'relative z-10 d-flex items-center justify-center', style: `width: 36px; height: 36px; border-radius: 50%; background: ${i + 1 <= currentStep ? 'var(--color-teal)' : 'var(--color-border)'}; color: ${i + 1 <= currentStep ? 'white' : 'var(--color-text-muted)'}; font-weight: 600;` }, i + 1 <= currentStep ? '✓' : (i + 1)),
        UI.createElement('span', { class: 'text-xs text-center mt-2', style: 'width: 100px; font-weight: ' + (i + 1 === currentStep ? '600' : '400') + '; color: ' + (i + 1 === currentStep ? 'var(--color-teal)' : 'var(--color-text-secondary)') + ';' }, step.title)
      ])
    )),
    UI.createElement('div', { class: 'mt-4 text-center text-sm text-secondary' }, `Step ${currentStep} of ${steps.length}`)
  ]));

  // Step Content
  const step = steps[currentStep - 1];
  const stepContent = UI.createElement('div', { id: 'onboarding-step-content' });
  content.appendChild(stepContent);

  function renderStep() {
    const s = steps[currentStep - 1];
    stepContent.innerHTML = '';

    if (s.id === 1) {
      // Welcome
      stepContent.appendChild(UI.createCard({
        children: [
          UI.createElement('div', { class: 'text-center py-8' }, [
            UI.createElement('div', { class: 'text-6xl mb-4' }, '👋'),
            UI.createElement('h2', { style: 'font-size: 28px; font-weight: 700; margin-bottom: 16px;' }, 'Welcome to BIMSpend'),
            UI.createElement('p', { class: 'text-secondary text-lg', style: 'max-width: 500px; margin: 0 auto 24px;' }, 'BIMSpend helps BIM and engineering firms track time, manage projects, and improve profitability. This guided setup will configure your workspace in about 10 minutes.'),
            UI.createElement('div', { class: 'd-flex gap-3 justify-center', style: 'margin-top: 24px;' }, [
              UI.createElement('div', { class: 'p-4', style: 'background: var(--color-canvas); border-radius: var(--radius-lg); min-width: 150px;' }, [
                UI.createElement('div', { class: 'text-2xl fw-bold text-primary' }, '8'),
                UI.createElement('div', { class: 'text-xs text-muted' }, 'Setup Steps')
              ]),
              UI.createElement('div', { class: 'p-4', style: 'background: var(--color-canvas); border-radius: var(--radius-lg); min-width: 150px;' }, [
                UI.createElement('div', { class: 'text-2xl fw-bold text-teal' }, '10'),
                UI.createElement('div', { class: 'text-xs text-muted' }, 'Minutes')
              ]),
              UI.createElement('div', { class: 'p-4', style: 'background: var(--color-canvas); border-radius: var(--radius-lg); min-width: 150px;' }, [
                UI.createElement('div', { class: 'text-2xl fw-bold text-amber' }, '∞'),
                UI.createElement('div', { class: 'text-xs text-muted' }, 'Projects')
              ])
            ])
          ])
        ]
      }));
    } else if (s.id === 2) {
      // Company Setup
      stepContent.appendChild(UI.createCard({
        title: 'Company Information',
        children: UI.createElement('form', { id: 'company-setup-form', onSubmit: (e) => { e.preventDefault(); nextStep(); } }, [
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Company Name', name: 'name', value: State.state.company.name, required: true }),
            UI.createInput({ label: 'ABN', name: 'abn', value: State.state.company.abn, required: true })
          ]),
          UI.createInput({ label: 'Address', name: 'address', type: 'textarea', value: State.state.company.address, required: true }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createInput({ label: 'Phone', name: 'phone', value: State.state.company.phone }),
            UI.createInput({ label: 'Email', type: 'email', name: 'email', value: State.state.company.email, required: true })
          ]),
          UI.createInput({ label: 'Website', name: 'website', value: State.state.company.website }),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createSelect({ label: 'Currency', name: 'currency', options: [{ value: 'AUD', label: 'AUD ($)' }, { value: 'USD', label: 'USD ($)' }, { value: 'EUR', label: 'EUR (€)' }], value: State.state.company.currency }),
            UI.createInput({ label: 'Tax Rate (%)', type: 'number', step: '0.01', name: 'taxRate', value: State.state.company.taxRate * 100 })
          ]),
          UI.createElement('div', { class: 'form-row' }, [
            UI.createSelect({ label: 'Fiscal Year Start', name: 'fiscalYearStart', options: [{ value: '01-01', label: 'January 1' }, { value: '04-01', label: 'April 1' }, { value: '07-01', label: 'July 1' }, { value: '10-01', label: 'October 1' }], value: State.state.company.fiscalYearStart }),
            UI.createSelect({ label: 'Timezone', name: 'timezone', options: [{ value: 'Australia/Melbourne', label: 'Australia/Melbourne' }, { value: 'Australia/Sydney', label: 'Australia/Sydney' }, { value: 'Australia/Brisbane', label: 'Australia/Brisbane' }, { value: 'Australia/Perth', label: 'Australia/Perth' }], value: State.state.company.timezone })
          ])
        ])
      }));
    } else if (s.id === 3) {
      // Invite Team
      stepContent.appendChild(UI.createCard({
        title: 'Team Members',
        children: [
          UI.createElement('p', { class: 'text-secondary mb-4' }, 'Add your team members. You can invite them via email or create accounts manually.'),
          UI.createElement('div', { id: 'team-members-list' }, [
            UI.createElement('div', { class: 'd-flex gap-3 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md); margin-bottom: 8px;' }, [
              UI.createElement('div', { class: 'avatar', style: 'width: 48px; height: 48px; background: var(--color-primary); color: white; font-size: 18px;' }, 'JD'),
              UI.createElement('div', { class: 'flex-1' }, [
                UI.createElement('div', { class: 'fw-medium' }, 'John Doe (You)'),
                UI.createElement('div', { class: 'text-sm text-secondary' }, 'Administrator • Managing Director')
              ]),
              UI.createBadge('Owner', 'approved')
            ])
          ]),
          UI.createButton({ text: '+ Add Team Member', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M16 21h-4"/><path d="M22 21h-4"/></svg>', onClick: () => addTeamMember() }),
          UI.createElement('form', { id: 'team-member-form', style: 'display: none; margin-top: 16px;', onSubmit: (e) => { e.preventDefault(); saveTeamMember(); } }, [
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'First Name', name: 'firstName', required: true }),
              UI.createInput({ label: 'Last Name', name: 'lastName', required: true })
            ]),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Email', type: 'email', name: 'email', required: true }),
              UI.createSelect({ label: 'Role', name: 'role', options: [{ value: 'manager', label: 'Manager' }, { value: 'designer', label: 'Designer' }], required: true })
            ]),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Department', name: 'department' }),
              UI.createInput({ label: 'Position', name: 'position' })
            ]),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Hourly Cost Rate', type: 'number', name: 'hourlyCostRate', required: true }),
              UI.createInput({ label: 'Billable Rate', type: 'number', name: 'billableRate', required: true })
            ]),
            UI.createElement('div', { class: 'flex gap-2' }, [
              UI.createButton({ text: 'Save', variant: 'primary', type: 'submit' }),
              UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => { $('#team-member-form').style.display = 'none'; } })
            ])
          ])
        ]
      }));
    } else if (s.id === 4) {
      // Create Projects
      stepContent.appendChild(UI.createCard({
        title: 'Project Setup',
        children: [
          UI.createElement('p', { class: 'text-secondary mb-4' }, 'Create your first projects. Link them to clients and set budgets.'),
          UI.createElement('div', { id: 'projects-onboarding-list' }, State.state.projects.length > 0 ? State.state.projects.map(p => UI.createElement('div', { class: 'd-flex gap-3 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md); margin-bottom: 8px;' }, [
            UI.createElement('div', { class: 'avatar', style: 'width: 48px; height: 48px; background: var(--color-teal); color: white; font-size: 18px;' }, '📁'),
            UI.createElement('div', { class: 'flex-1' }, [
              UI.createElement('div', { class: 'fw-medium' }, p.name),
              UI.createElement('div', { class: 'text-sm text-secondary' }, p.code + ' • ' + p.budgetHours + 'h budget')
            ])
          ])) : '<p class="text-muted text-center py-8">No projects created yet</p>'),
          UI.createButton({ text: '+ Create Project', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>', onClick: () => showProjectForm() }),
          UI.createElement('form', { id: 'project-onboarding-form', style: 'display: none; margin-top: 16px;', onSubmit: (e) => { e.preventDefault(); saveOnboardingProject(); } }, [
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Project Code', name: 'code', required: true }),
              UI.createInput({ label: 'Project Name', name: 'name', required: true })
            ]),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createSelect({ label: 'Client', name: 'clientId', options: [{ value: '', label: 'Select Client' }, ...State.state.clients.map(c => ({ value: c.id, label: c.name }))], required: true }),
              UI.createSelect({ label: 'Phase', name: 'phase', options: [{ value: 'tender', label: 'Tender' }, { value: 'design-development', label: 'Design Development' }, { value: 'construction-docs', label: 'Construction Docs' }, { value: 'construction', label: 'Construction' }], required: true })
            ]),
            UI.createElement('div', { class: 'form-row' }, [
              UI.createInput({ label: 'Budget Hours', type: 'number', name: 'budgetHours', required: true }),
              UI.createInput({ label: 'Budget Cost', type: 'number', name: 'budgetCost', required: true })
            ]),
            UI.createElement('div', { class: 'flex gap-2' }, [
              UI.createButton({ text: 'Create', variant: 'primary', type: 'submit' }),
              UI.createButton({ text: 'Cancel', variant: 'secondary', type: 'button', onClick: () => { $('#project-onboarding-form').style.display = 'none'; } })
            ])
          ])
        ]
      }));
    } else if (s.id === 5) {
      // Rates & Billing
      stepContent.appendChild(UI.createCard({
        title: 'Labour & Billing Rates',
        children: [
          UI.createElement('p', { class: 'text-secondary mb-4' }, 'Review and adjust the default rates for your team. These will be used for cost calculations and quote generation.'),
          UI.createElement('div', { class: 'table-container' }, [
            UI.createElement('table', { class: 'table' }, [
              UI.createElement('thead', {}, [
                UI.createElement('tr', {}, ['Employee', 'Role', 'Cost Rate/hr', 'Bill Rate/hr', 'Margin'].map(h => UI.createElement('th', {}, h)))
              ]),
              UI.createElement('tbody', {}, State.state.employees.map(e => UI.createElement('tr', {}, [
                UI.createElement('td', {}, `${e.firstName} ${e.lastName}`),
                UI.createElement('td', {}, UI.createBadge(e.role, e.role)),
                UI.createElement('td', {}, UI.formatCurrency(e.hourlyCostRate)),
                UI.createElement('td', {}, UI.formatCurrency(e.billableRate)),
                UI.createElement('td', { class: 'fw-medium' }, e.billableRate > 0 ? `${(((e.billableRate - e.hourlyCostRate) / e.billableRate) * 100).toFixed(0)}%` : '—')
              ])))
            ])
          ]),
          UI.createElement('div', { class: 'mt-4 p-4', style: 'background: var(--color-primary-light); border-radius: var(--radius-md); border: 1px solid var(--color-primary);' }, [
            UI.createElement('h4', { class: 'mb-2' }, 'Default Quote Settings'),
            UI.createElement('div', { class: 'd-flex flex-wrap gap-4' }, [
              UI.createInput({ label: 'Default Markup (%)', type: 'number', name: 'defaultMarkup', value: State.state.settings.billing.defaultMarkupPercent }),
              UI.createInput({ label: 'Default Contingency (%)', type: 'number', name: 'defaultContingency', value: State.state.settings.billing.defaultContingencyPercent }),
              UI.createInput({ label: 'Default Payment Terms (days)', type: 'number', name: 'defaultTerms', value: State.state.settings.billing.defaultPaymentTerms })
            ])
          ])
        ]
      }));
    } else if (s.id === 6) {
      // Desktop Agent
      stepContent.appendChild(UI.createCard({
        title: 'Windows Desktop Agent',
        children: [
          UI.createElement('div', { class: 'd-flex gap-6' }, [
            UI.createElement('div', { class: 'flex-1' }, [
              UI.createElement('h3', { class: 'mb-3' }, 'Automatic Time Tracking'),
              UI.createElement('p', { class: 'text-secondary mb-4' }, 'The BIMSpend Desktop Agent runs in the background on Windows, automatically detecting when you work in Revit, AutoCAD, Navisworks, and other supported applications.'),
              UI.createElement('ul', { class: 'text-secondary', style: 'margin-left: 20px; line-height: 2;' }, [
                'Auto-starts with Windows',
                'Detects Revit, AutoCAD, Navisworks, Civil 3D',
                'Reads Revit journal files for project identification',
                'Tracks active window, idle time, and application switches',
                'Respects privacy settings and excluded applications',
                'Syncs data securely to BIMSpend server'
              ].map(item => UI.createElement('li', {}, item)))
            ]),
            UI.createElement('div', { style: 'width: 200px; height: 200px; background: var(--color-navy); border-radius: var(--radius-lg); display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; flex-shrink: 0;' }, [
              UI.createElement('div', { style: 'font-size: 64px; margin-bottom: 16px;' }, '🖥️'),
              UI.createElement('div', { class: 'fw-bold', style: 'font-size: 18px;' }, 'BIMSpend Agent'),
              UI.createElement('div', { class: 'text-sm', style: 'color: var(--color-teal); margin-top: 8px;' }, '● Running')
            ])
          ]),
          UI.createElement('div', { class: 'mt-6 p-4', style: 'background: var(--color-amber-light); border-radius: var(--radius-md); border: 1px solid var(--color-amber);' }, [
            UI.createElement('h4', { class: 'mb-2' }, 'Download & Install'),
            UI.createElement('p', { class: 'text-sm text-secondary mb-3' }, 'The Desktop Agent is available as a Windows installer. Download from the BIMSpend portal or GitHub releases.'),
            UI.createElement('div', { class: 'd-flex gap-2' }, [
              UI.createButton({ text: 'Download Installer', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>', onClick: () => UI.showToast('info', 'Download', 'In production, this would download the Windows installer.') }),
              UI.createButton({ text: 'View Requirements', variant: 'ghost', size: 'sm' })
            ])
          ])
        ]
      }));
    } else if (s.id === 7) {
      // Privacy & Consent
      stepContent.appendChild(UI.createCard({
        title: 'Privacy & Consent',
        children: [
          UI.createElement('p', { class: 'text-secondary mb-4' }, 'BIMSpend is designed with privacy-first principles. Review and configure the privacy settings for your team.'),
          UI.createElement('div', { class: 'd-grid gap-4' }, [
            { title: 'Employee Consent', desc: 'All employees must provide informed consent before activity tracking begins. Consent records are stored and auditable.', required: true },
            { title: 'Data Minimization', desc: 'Only application names, window titles (redacted), and timestamps are captured. No keystrokes, screenshots, or file contents.', required: true },
            { title: 'Personal Time', desc: 'Employees can mark time as personal/non-work. Personal time is excluded from project attribution and utilization reports.', required: false },
            { title: 'Data Retention', desc: 'Activity data is retained for 7 years (configurable) per Australian tax law requirements. Employees can request data export or deletion.', required: true },
            { title: 'Access Control', desc: 'Managers only see aggregated team data. Individual activity details require explicit permission. Designers see only their own data.', required: true }
          ].map(item => UI.createElement('div', { class: 'd-flex items-start gap-3 p-4', style: 'background: var(--color-canvas); border-radius: var(--radius-md);' }, [
            UI.createElement('label', { class: 'd-flex items-center gap-2 cursor-pointer mt-1' }, [
              UI.createElement('input', { type: 'checkbox', checked: item.required, disabled: item.required }),
              UI.createElement('span', {}, item.required ? 'Required' : 'Optional')
            ]),
            UI.createElement('div', { class: 'flex-1' }, [
              UI.createElement('div', { class: 'fw-medium' }, item.title),
              UI.createElement('div', { class: 'text-sm text-secondary' }, item.desc)
            ])
          ]))),
          UI.createElement('div', { class: 'd-flex gap-2' }, [
            UI.createButton({ text: 'Download Privacy Policy', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>' }),
            UI.createButton({ text: 'Generate Consent Forms', variant: 'primary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>' })
          ])
        ]
      }));
    } else if (s.id === 8) {
      // Complete
      stepContent.appendChild(UI.createCard({
        children: [
          UI.createElement('div', { class: 'text-center py-12' }, [
            UI.createElement('div', { class: 'text-8xl mb-4' }, '🎉'),
            UI.createElement('h2', { style: 'font-size: 32px; font-weight: 700; margin-bottom: 16px;' }, 'You\'re All Set!'),
            UI.createElement('p', { class: 'text-secondary text-lg mb-8', style: 'max-width: 500px; margin: 0 auto;' }, 'BIMSpend is now configured for your company. Your team can start tracking time, managing projects, and improving profitability right away.'),
            UI.createElement('div', { class: 'd-flex gap-3 justify-center flex-wrap mb-8' }, [
              UI.createButton({ text: 'Go to Dashboard', variant: 'primary', size: 'lg', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>', onClick: () => { localStorage.removeItem('bimspend_onboarding_step'); RouterInstance.navigate('dashboard'); } }),
              UI.createButton({ text: 'Invite Team Now', variant: 'secondary', size: 'lg', onClick: () => { currentStep = 3; localStorage.setItem('bimspend_onboarding_step', '3'); renderStep(); updateProgress(); } })
            ]),
            UI.createElement('div', { class: 'd-grid gap-3', style: 'max-width: 400px; margin: 0 auto; text-align: left;' }, [
              UI.createElement('a', { class: 'd-flex gap-3 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md); color: inherit; text-decoration: none;', href: '#' }, [
                UI.createElement('div', { class: 'avatar', style: 'width: 40px; height: 40px; background: var(--color-primary); color: white; font-size: 16px;' }, '📖'),
                UI.createElement('div', {}, [
                  UI.createElement('div', { class: 'fw-medium' }, 'User Guide'),
                  UI.createElement('div', { class: 'text-sm text-muted' }, 'Learn how to use BIMSpend effectively')
                ])
              ]),
              UI.createElement('a', { class: 'd-flex gap-3 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md); color: inherit; text-decoration: none;', href: '#' }, [
                UI.createElement('div', { class: 'avatar', style: 'width: 40px; height: 40px; background: var(--color-teal); color: white; font-size: 16px;' }, '🖥️'),
                UI.createElement('div', {}, [
                  UI.createElement('div', { class: 'fw-medium' }, 'Desktop Agent Docs'),
                  UI.createElement('div', { class: 'text-sm text-muted' }, 'Install and configure the Windows agent')
                ])
              ]),
              UI.createElement('a', { class: 'd-flex gap-3 p-3', style: 'background: var(--color-canvas); border-radius: var(--radius-md); color: inherit; text-decoration: none;', href: '#' }, [
                UI.createElement('div', { class: 'avatar', style: 'width: 40px; height: 40px; background: var(--color-amber); color: white; font-size: 16px;' }, '🔒'),
                UI.createElement('div', {}, [
                  UI.createElement('div', { class: 'fw-medium' }, 'Privacy Guide'),
                  UI.createElement('div', { class: 'text-sm text-muted' }, 'Understand your data rights and controls')
                ])
              ])
            ])
          ])
        ]
      }));
    }

    updateProgress();
  }

  function updateProgress() {
    $$('.d-flex.flex-col.items-center', content.querySelectorAll('> div:first-child > div')).forEach((el, i) => {
      const stepNum = i + 1;
      const circle = el.querySelector('div[style*="width: 36px"]');
      const label = el.querySelector('span');
      if (circle) {
        circle.style.background = stepNum <= currentStep ? 'var(--color-teal)' : 'var(--color-border)';
        circle.style.color = stepNum <= currentStep ? 'white' : 'var(--color-text-muted)';
        circle.innerHTML = stepNum <= currentStep ? '✓' : stepNum;
      }
      if (label) {
        label.style.fontWeight = stepNum === currentStep ? '600' : '400';
        label.style.color = stepNum === currentStep ? 'var(--color-teal)' : 'var(--color-text-secondary)';
      }
    });
    const progressText = content.querySelector('.text-center.text-sm.text-secondary');
    if (progressText) progressText.textContent = `Step ${currentStep} of ${steps.length}`;
  }

  function nextStep() {
    if (currentStep < steps.length) {
      currentStep++;
      localStorage.setItem('bimspend_onboarding_step', String(currentStep));
      renderStep();
    }
  }

  function prevStep() {
    if (currentStep > 1) {
      currentStep--;
      localStorage.setItem('bimspend_onboarding_step', String(currentStep));
      renderStep();
    }
  }

  function addTeamMember() {
    $('#team-member-form').style.display = 'block';
  }

  function saveTeamMember() {
    const formData = new FormData($('#team-member-form'));
    const data = Object.fromEntries(formData);
    data.hourlyCostRate = parseFloat(data.hourlyCostRate);
    data.billableRate = parseFloat(data.billableRate);

    const newEmp = {
      id: `emp-${Date.now()}`,
      ...data,
      hireDate: new Date().toISOString().split('T')[0],
      avatar: null,
      managerId: 'emp-001',
      projects: [],
      permissions: data.role === 'manager' ? ['projects:read', 'timesheets:approve'] : ['timesheets:write']
    };
    State.state.employees.push(newEmp);
    UI.showToast('success', 'Team Member Added', `${newEmp.firstName} ${newEmp.lastName} has been added.`);
    $('#team-member-form').style.display = 'none';
    $('#team-member-form').reset();
    renderStep();
  }

  function showProjectForm() {
    $('#project-onboarding-form').style.display = 'block';
  }

  function saveOnboardingProject() {
    const formData = new FormData($('#project-onboarding-form'));
    const data = Object.fromEntries(formData);
    data.budgetHours = parseFloat(data.budgetHours);
    data.budgetCost = parseFloat(data.budgetCost);

    const newProject = {
      id: `prj-${Date.now()}`,
      ...data,
      status: 'active',
      approvedHours: 0,
      approvedCost: 0,
      billedHours: 0,
      billedRevenue: 0,
      teamMembers: [],
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0]
    };
    State.state.projects.unshift(newProject);
    UI.showToast('success', 'Project Created', `${newProject.name} has been added.`);
    $('#project-onboarding-form').style.display = 'none';
    $('#project-onboarding-form').reset();
    renderStep();
  }

  renderStep();

  // Navigation buttons
  content.appendChild(UI.createElement('div', { class: 'd-flex justify-between mt-8' }, [
    UI.createButton({ text: 'Previous', variant: 'secondary', disabled: currentStep === 1, onClick: prevStep }),
    UI.createButton({ text: currentStep === steps.length ? 'Complete' : 'Next', variant: 'primary', disabled: currentStep === steps.length, onClick: nextStep })
  ]));

  return content;
}

// ==================== DESIGNER: MY OVERVIEW ====================
Screens['my-dashboard'] = function() {
  return Screens.dashboard();
};

// ==================== DESIGNER: MY ACTIVITY ====================
Screens['my-activity'] = function() {
  const data = getVisibleData();
  const user = State.getCurrentUser();

  const content = UI.createElement('div', {});

  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('h1', { class: 'page-title' }, 'My Activity'),
      UI.createElement('p', { class: 'text-secondary mt-1' }, 'Your recent application usage and project attribution.')
    ]),
    UI.createButton({ text: 'Refresh', variant: 'secondary', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>' })
  ]));

  // Filters
  content.appendChild(UI.createElement('div', { class: 'card mb-6' }, [
    UI.createElement('div', { class: 'card-body' }, [
      UI.createElement('div', { class: 'd-flex flex-wrap gap-4' }, [
        UI.createSelect({
          label: 'Project',
          options: [{ value: '', label: 'All Projects' }, ...data.projects.map(p => ({ value: p.id, label: `${p.code} - ${p.name}` }))],
          value: State.getFilters('activity').project,
          onChange: (v) => { State.setFilter('activity', 'project', v); Screens.renderCurrent(); }
        }),
        UI.createSelect({
          label: 'State',
          options: [
            { value: '', label: 'All States' },
            { value: 'productive', label: 'Productive' },
            { value: 'idle', label: 'Idle' },
            { value: 'unclassified', label: 'Unclassified' }
          ],
          value: State.getFilters('activity').state,
          onChange: (v) => { State.setFilter('activity', 'state', v); Screens.renderCurrent(); }
        }),
        UI.createButton({ text: 'Clear Filters', variant: 'ghost', size: 'sm', onClick: () => { State.resetFilters('activity'); Screens.renderCurrent(); } })
      ])
    ])
  ]));

  // My Activity Summary
  const myActivity = data.activity.filter(a => a.employeeId === user?.id);
  const productiveHours = myActivity.filter(a => a.state === 'productive').reduce((s, a) => s + a.duration, 0) / 60;
  const idleHours = myActivity.filter(a => a.state === 'idle').reduce((s, a) => s + a.duration, 0) / 60;
  const unclassifiedCount = myActivity.filter(a => a.state === 'unclassified' || !a.projectId).length;
  const projectMap = {};
  myActivity.filter(a => a.projectId).forEach(a => {
    projectMap[a.projectId] = (projectMap[a.projectId] || 0) + a.duration;
  });
  const topProjects = Object.entries(projectMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([pid, mins]) => {
      const p = State.getProject(pid);
      return { code: p?.code || pid, hours: (mins / 60).toFixed(1) };
    });

  content.appendChild(UI.createElement('div', { class: 'kpi-grid mb-6' }, [
    UI.createKPICard({ label: 'Productive Time', value: `${productiveHours.toFixed(1)}h`, subvalue: 'Active work', icon: '⚡', iconBg: 'primary' }),
    UI.createKPICard({ label: 'Idle Time', value: `${idleHours.toFixed(1)}h`, subvalue: 'Away from desk', icon: '💤', iconBg: 'amber' }),
    UI.createKPICard({ label: 'Unclassified', value: unclassifiedCount, subvalue: 'Need attribution', icon: '❓', iconBg: 'red' }),
    UI.createKPICard({ label: 'Projects Worked', value: topProjects.length, subvalue: 'This period', icon: '📁', iconBg: 'teal' })
  ]));

  // Charts row
  const chartsRow = UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' });

  // Activity classification donut
  const actByClass = {};
  myActivity.forEach(a => {
    actByClass[a.classification] = (actByClass[a.classification] || 0) + a.duration / 60;
  });
  chartsRow.appendChild(Charts.createActivityDonut(
    Object.entries(actByClass).map(([classification, hours]) => ({ classification, hours })),
    { totalHours: productiveHours + idleHours }
  ));

  // Top projects bar chart
  chartsRow.appendChild(UI.createCard({
    title: 'Top Projects by Time',
    children: UI.createElement('div', { style: 'display: flex; flex-direction: column; gap: 12px;' }, topProjects.map(p =>
      UI.createElement('div', { style: 'display: flex; align-items: center; gap: 12px;' }, [
        UI.createElement('div', { style: 'width: 100px; font-weight: 500; color: var(--color-primary);' }, p.code),
        UI.createElement('div', { style: 'flex: 1; height: 24px; background: var(--color-canvas); border-radius: var(--radius-full); overflow: hidden;' }, [
          UI.createElement('div', {
            style: `width: ${Math.min(100, (p.hours / (topProjects[0]?.hours || 1)) * 100)}%; height: 100%; background: linear-gradient(90deg, var(--color-teal), var(--color-primary)); border-radius: var(--radius-full);`
          })
        ]),
        UI.createElement('div', { class: 'fw-medium text-teal', style: 'width: 60px; text-align: right;' }, `${p.hours}h`)
      ])
    ))
  }));

  content.appendChild(chartsRow);

  // Activity timeline table
  content.appendChild(UI.createCard({
    title: 'Activity Timeline',
    children: UI.createTable({
      columns: [
        { field: 'timestamp', header: 'Time', render: (r) => UI.formatDateTime(r.timestamp) },
        { field: 'application', header: 'Application' },
        { field: 'projectId', header: 'Project', render: (r) => {
          if (!r.projectId) return UI.createBadge('Unassigned', 'observed');
          const p = State.getProject(r.projectId);
          return p ? UI.createElement('span', { class: 'fw-medium' }, p.code) : r.projectId;
        }},
        { field: 'classification', header: 'Classification' },
        { field: 'state', header: 'State', render: (r) => UI.createBadge(r.state, r.state) },
        { field: 'confidence', header: 'Confidence', render: (r) => UI.createElement('span', { class: `confidence-chip ${UI.getConfidenceChipClass(r.confidence)}` }, r.confidence) },
        { field: 'duration', header: 'Duration (min)', render: (r) => r.duration }
      ],
      data: myActivity.slice(0, 50),
      emptyMessage: 'No activity recorded for the selected filters.'
    })
  }));

  return content;
};

// ==================== DESIGNER: MY TIMESHEETS ====================
Screens['my-timesheets'] = function() {
  return Screens.timesheets();
};

// ==================== DESIGNER: MY PROJECTS ====================
Screens['my-projects'] = function() {
  return Screens.projects();
};

// ==================== PROJECT DETAIL ====================
Screens['project-detail'] = function(params) {
  const project = State.getProject(params.id);
  if (!project) {
    return Screens.renderNotFound('Project not found');
  }

  const data = getVisibleData();
  const role = State.getCurrentRole();
  const user = State.getCurrentUser();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('nav', { class: 'breadcrumb mb-2' }, [
        UI.createElement('a', { href: '#', class: 'breadcrumb-link', onClick: (e) => { e.preventDefault(); RouterInstance.navigate('projects'); } }, 'Projects'),
        UI.createElement('span', { class: 'breadcrumb-separator' }, '/'),
        UI.createElement('span', { class: 'breadcrumb-current' }, project.name)
      ]),
      UI.createElement('h1', { class: 'page-title' }, project.name),
      UI.createElement('p', { class: 'text-secondary mt-1' }, `${project.code} • ${project.phase} • ${project.status}`)
    ]),
    UI.createElement('div', { class: 'flex gap-2' }, [
      role !== 'designer' && UI.createButton({ text: 'Edit', variant: 'secondary', onClick: () => Screens.showProjectModal(project) }),
      UI.createButton({ text: 'Export', variant: 'ghost', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' })
    ].filter(Boolean))
  ]));

  // Project KPIs
  const margin = (project.billedRevenue || 0) - (project.approvedCost || 0);
  const marginPct = (project.billedRevenue || 0) > 0 ? (margin / project.billedRevenue) * 100 : 0;
  const hoursVariance = project.approvedHours - project.budgetHours;
  const hoursVariancePct = project.budgetHours > 0 ? (hoursVariance / project.budgetHours) * 100 : 0;

  content.appendChild(UI.createElement('div', { class: 'kpi-grid mb-6' }, [
    UI.createKPICard({ label: 'Budget Hours', value: UI.formatNumber(project.budgetHours), subvalue: `${UI.formatNumber(project.approvedHours)}h actual`, trend: { value: hoursVariancePct > 0 ? '+' : '', label: `${hoursVariancePct.toFixed(1)}% variance`, type: hoursVariance > 0 ? 'negative' : 'positive' }, icon: '⏱' }),
    UI.createKPICard({ label: 'Budget Cost', value: UI.formatCurrency(project.budgetCost), subvalue: UI.formatCurrency(project.approvedCost) + ' actual', icon: '💰', iconBg: 'amber' }),
    UI.createKPICard({ label: 'Billed Revenue', value: UI.formatCurrency(project.billedRevenue), subvalue: UI.formatCurrency(project.budgetRevenue) + ' budgeted', icon: '$', iconBg: 'green' }),
    UI.createKPICard({ label: 'Gross Margin', value: UI.formatCurrency(margin), subvalue: `${marginPct.toFixed(1)}%`, trend: { value: marginPct > 30 ? 'Healthy' : marginPct > 20 ? 'Moderate' : 'Low', type: marginPct > 30 ? 'positive' : marginPct > 20 ? 'neutral' : 'negative' }, icon: '📈', iconBg: marginPct > 30 ? 'teal' : marginPct > 20 ? 'amber' : 'red' })
  ]));

  // Tabs
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'timesheets', label: 'Timesheets' },
    { id: 'activity', label: 'Activity' },
    { id: 'financial', label: 'Financial' },
    { id: 'team', label: 'Team' }
  ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-4', id: 'project-tabs' }, tabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${tab.id === 'overview' ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        Screens.renderProjectTab(tab.id, project, content);
      }
    }, tab.label)
  )));

  const tabContainer = UI.createElement('div', { id: 'project-tab-container' });
  content.appendChild(tabContainer);

  setTimeout(() => Screens.renderProjectTab('overview', project, content), 0);

  return content;
};

Screens.renderProjectTab = function(tabId, project, parentContent) {
  const container = $('#project-tab-container');
  if (!container) return;

  const role = State.getCurrentRole();
  const data = getVisibleData();
  const projectTimesheets = data.timesheets.filter(t => t.projectId === project.id);
  const projectActivity = data.activity.filter(a => a.projectId === project.id);

  container.innerHTML = '';

  switch (tabId) {
    case 'overview':
      container.appendChild(UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' }, [
        // Progress
        UI.createCard({
          title: 'Progress Overview',
          children: UI.createElement('div', { class: 'd-flex flex-col gap-4' }, [
            UI.createElement('div', {}, [
              UI.createElement('div', { class: 'd-flex justify-between mb-2' }, [
                UI.createElement('span', {}, 'Hours Used'),
                UI.createElement('span', { class: 'fw-medium' }, `${UI.formatNumber(project.approvedHours)} / ${UI.formatNumber(project.budgetHours)}`)
              ]),
              UI.createElement('div', { class: 'progress', style: 'height: 8px;' }, [
                UI.createElement('div', {
                  class: 'progress-bar',
                  style: `width: ${Math.min(100, (project.approvedHours / (project.budgetHours || 1)) * 100)}%; background: ${project.approvedHours > project.budgetHours ? 'var(--status-rejected)' : 'var(--color-teal)'};`
                })
              ]),
              UI.createElement('div', { class: 'd-flex justify-between text-xs text-muted mt-1' }, [
                UI.createElement('span', {}, '0h'),
                UI.createElement('span', {}, `${UI.formatNumber(project.budgetHours)}h`)
              ])
            ]),
            UI.createElement('div', {}, [
              UI.createElement('div', { class: 'd-flex justify-between mb-2' }, [
                UI.createElement('span', {}, 'Cost Used'),
                UI.createElement('span', { class: 'fw-medium' }, `${UI.formatCurrency(project.approvedCost)} / ${UI.formatCurrency(project.budgetCost)}`)
              ]),
              UI.createElement('div', { class: 'progress', style: 'height: 8px;' }, [
                UI.createElement('div', {
                  class: 'progress-bar',
                  style: `width: ${Math.min(100, (project.approvedCost / (project.budgetCost || 1)) * 100)}%; background: ${project.approvedCost > project.budgetCost ? 'var(--status-rejected)' : 'var(--color-amber)'};`
                })
              ]),
              UI.createElement('div', { class: 'd-flex justify-between text-xs text-muted mt-1' }, [
                UI.createElement('span', {}, '$0'),
                UI.createElement('span', {}, UI.formatCurrency(project.budgetCost))
              ])
            ]),
            UI.createElement('div', {}, [
              UI.createElement('div', { class: 'd-flex justify-between mb-2' }, [
                UI.createElement('span', {}, 'Revenue'),
                UI.createElement('span', { class: 'fw-medium' }, `${UI.formatCurrency(project.billedRevenue)} / ${UI.formatCurrency(project.budgetRevenue)}`)
              ]),
              UI.createElement('div', { class: 'progress', style: 'height: 8px;' }, [
                UI.createElement('div', {
                  class: 'progress-bar',
                  style: `width: ${Math.min(100, (project.billedRevenue / (project.budgetRevenue || 1)) * 100)}%; background: var(--color-green);`
                })
              ]),
              UI.createElement('div', { class: 'd-flex justify-between text-xs text-muted mt-1' }, [
                UI.createElement('span', {}),
                UI.createElement('span', {}, UI.formatCurrency(project.budgetRevenue))
              ])
            ])
          ])
        }),

        // Details
        UI.createCard({
          title: 'Project Details',
          children: UI.createElement('div', { class: 'd-grid gap-3' }, [
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Client'), UI.createElement('span', { class: 'fw-medium' }, State.getClient(project.clientId)?.name || '—')]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Project Manager'), UI.createElement('span', { class: 'fw-medium' }, State.getEmployee(project.projectManagerId) ? `${State.getEmployee(project.projectManagerId).firstName} ${State.getEmployee(project.projectManagerId).lastName}` : '—')]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Phase'), UI.createElement('span', {}, UI.createBadge(project.phase, project.phase))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Status'), UI.createElement('span', {}, UI.createBadge(project.status, project.status))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Start Date'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(project.startDate))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'End Date'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(project.endDate))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Team Members'), UI.createElement('span', { class: 'fw-medium' }, project.teamMembers.length.toString())]),
            project.description && UI.createElement('div', { class: 'pt-3 border-top', style: 'border-color: var(--color-border);' }, [UI.createElement('div', { class: 'text-secondary mb-1' }, 'Description'), UI.createElement('div', {}, project.description)])
          ].filter(Boolean))
        })
      ]));
      break;

    case 'timesheets':
      container.appendChild(UI.createCard({
        title: 'Project Timesheets',
        actions: [UI.createButton({ text: 'Add Entry', variant: 'primary', size: 'sm', onClick: () => Screens.showTimesheetModal({ projectId: project.id }) })],
        children: UI.createTable({
          columns: [
            { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
            { field: 'employeeId', header: 'Employee', render: (r) => { const e = State.getEmployee(r.employeeId); return e ? `${e.firstName} ${e.lastName}` : r.employeeId; }},
            { field: 'hours', header: 'Hours', render: (r) => UI.formatNumber(r.hours, 1) },
            { field: 'description', header: 'Description' },
            { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
            { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
              UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => Screens.showTimesheetDetail(r.id) })
            ])}
          ],
          data: projectTimesheets,
          emptyMessage: 'No timesheets for this project yet.'
        })
      }));
      break;

    case 'activity':
      container.appendChild(UI.createCard({
        title: 'Project Activity',
        children: projectActivity.length > 0
          ? UI.createTable({
            columns: [
              { field: 'timestamp', header: 'Time', render: (r) => UI.formatDateTime(r.timestamp) },
              { field: 'employeeId', header: 'Employee', render: (r) => { const e = State.getEmployee(r.employeeId); return e ? `${e.firstName} ${e.lastName}` : r.employeeId; }},
              { field: 'application', header: 'Application' },
              { field: 'classification', header: 'Classification' },
              { field: 'state', header: 'State', render: (r) => UI.createBadge(r.state, r.state) },
              { field: 'duration', header: 'Duration (min)', render: (r) => r.duration }
            ],
            data: projectActivity.slice(0, 100)
          })
          : UI.createEmptyState({ title: 'No activity', message: 'No tracked activity for this project yet.' })
      }));
      break;

    case 'financial':
      container.appendChild(UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' }, [
        UI.createCard({
          title: 'Financial Summary',
          children: UI.createElement('div', { class: 'd-grid gap-3' }, [
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Budget Cost'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(project.budgetCost))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Actual Cost'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(project.approvedCost))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Cost Variance'), UI.createElement('span', { class: `fw-medium ${project.approvedCost > project.budgetCost ? 'text-danger' : 'text-success'}` }, `${project.approvedCost > project.budgetCost ? '+' : ''}${UI.formatCurrency(project.approvedCost - project.budgetCost)}`)]),
            UI.createElement('hr', {}),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Budget Revenue'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(project.budgetRevenue))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Billed Revenue'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(project.billedRevenue))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Gross Margin'), UI.createElement('span', { class: 'fw-medium text-teal' }, UI.formatCurrency(project.billedRevenue - project.approvedCost))]),
            UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Margin %'), UI.createElement('span', { class: 'fw-medium' }, `${((project.billedRevenue - project.approvedCost) / (project.billedRevenue || 1) * 100).toFixed(1)}%`)])
          ])
        }),
        Charts.createBudgetVarianceChart([project])
      ]));
      break;

    case 'team':
      const teamMembers = project.teamMembers.map(id => State.getEmployee(id)).filter(Boolean);
      container.appendChild(UI.createCard({
        title: 'Project Team',
        actions: role !== 'designer' ? [UI.createButton({ text: 'Add Member', variant: 'secondary', size: 'sm' })] : [],
        children: teamMembers.length > 0
          ? UI.createTable({
            columns: [
              { field: 'avatar', header: '', render: (r) => UI.createAvatar(`${r.firstName} ${r.lastName}`, 32) },
              { field: 'name', header: 'Team Member', render: (r) => UI.createElement('div', {}, [UI.createElement('div', { class: 'fw-medium' }, `${r.firstName} ${r.lastName}`), UI.createElement('div', { class: 'text-xs text-muted' }, r.email)]) },
              { field: 'role', header: 'Role', render: (r) => UI.createBadge(r.role, r.role) },
              { field: 'department', header: 'Department' },
              { field: 'billableRate', header: 'Bill Rate', render: (r) => UI.formatCurrency(r.billableRate) + '/hr' },
              { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
                UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('employee-detail', { id: r.id }) })
              ])}
            ],
            data: teamMembers
          })
          : UI.createEmptyState({ title: 'No team members', message: 'Add team members to this project.' })
      }));
      break;
  }
};

// ==================== EMPLOYEE DETAIL ====================
Screens['employee-detail'] = function(params) {
  const employee = State.getEmployee(params.id);
  if (!employee) {
    return Screens.renderNotFound('Employee not found');
  }

  const data = getVisibleData();
  const role = State.getCurrentRole();

  const content = UI.createElement('div', {});

  // Header
  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('nav', { class: 'breadcrumb mb-2' }, [
        UI.createElement('a', { href: '#', class: 'breadcrumb-link', onClick: (e) => { e.preventDefault(); RouterInstance.navigate('employees'); } }, 'Employees'),
        UI.createElement('span', { class: 'breadcrumb-separator' }, '/'),
        UI.createElement('span', { class: 'breadcrumb-current' }, `${employee.firstName} ${employee.lastName}`)
      ]),
      UI.createElement('h1', { class: 'page-title' }, `${employee.firstName} ${employee.lastName}`),
      UI.createElement('p', { class: 'text-secondary mt-1' }, `${employee.position} • ${employee.department} • ${employee.role}`)
    ]),
    role !== 'designer' && UI.createButton({ text: 'Edit', variant: 'secondary', onClick: () => Screens.showEmployeeModal(employee) })
  ].filter(Boolean)));

  // Employee KPIs
  const myTs = data.timesheets.filter(t => t.employeeId === employee.id);
  const billableHours = myTs.filter(t => t.status === 'approved' || t.status === 'billed').reduce((s, t) => s + t.hours, 0);
  const totalHours = myTs.reduce((s, t) => s + t.hours, 0);
  const availableHours = 38 * 4;
  const utilization = availableHours > 0 ? (billableHours / availableHours) * 100 : 0;
  const pendingApproval = myTs.filter(t => t.status === 'submitted').length;

  content.appendChild(UI.createElement('div', { class: 'd-flex gap-6 mb-6 flex-wrap' }, [
    UI.createElement('div', { class: 'd-flex items-center gap-4' }, [
      UI.createAvatar(`${employee.firstName} ${employee.lastName}`, 64),
      UI.createElement('div', {}, [
        UI.createElement('div', { class: 'd-flex items-center gap-2' }, [
          UI.createElement('h2', { style: 'font-size: 24px; font-weight: 600; margin: 0;' }, `${employee.firstName} ${employee.lastName}`),
          UI.createBadge(employee.status, employee.status),
          UI.createBadge(employee.role, employee.role)
        ]),
        UI.createElement('div', { class: 'text-secondary mt-1' }, `${employee.position} • ${employee.department}`),
        UI.createElement('div', { class: 'text-sm text-muted mt-1' }, employee.email)
      ])
    ]),
    UI.createElement('div', { class: 'kpi-grid', style: 'flex: 1; min-width: 400px;' }, [
      UI.createKPICard({ label: 'Utilization', value: `${utilization.toFixed(1)}%`, subvalue: `${UI.formatNumber(billableHours, 1)}h / ${availableHours}h`, trend: { value: utilization >= 75 ? 'Target met' : 'Below target', type: utilization >= 75 ? 'positive' : 'negative' }, icon: '📊', iconBg: utilization >= 75 ? 'teal' : 'amber' }),
      UI.createKPICard({ label: 'Total Hours', value: UI.formatNumber(totalHours, 1), subvalue: 'This period', icon: '⏱' }),
      UI.createKPICard({ label: 'Pending Approval', value: pendingApproval, subvalue: 'Timesheets', icon: '⏳', iconBg: pendingApproval > 0 ? 'amber' : 'teal' }),
      UI.createKPICard({ label: 'Assigned Projects', value: employee.projects.length, subvalue: 'Active assignments', icon: '📁', iconBg: 'primary' })
    ])
  ]));

  // Tabs
  const tabs = [
    { id: 'timesheets', label: 'Timesheets' },
    { id: 'projects', label: 'Projects' },
    { id: 'activity', label: 'Activity' },
    { id: 'details', label: 'Details' }
  ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-4', id: 'employee-tabs' }, tabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${tab.id === 'timesheets' ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        Screens.renderEmployeeTab(tab.id, employee, data);
      }
    }, tab.label)
  )));

  const tabContainer = UI.createElement('div', { id: 'employee-tab-container' });
  content.appendChild(tabContainer);

  setTimeout(() => Screens.renderEmployeeTab('timesheets', employee, data), 0);

  return content;
};

Screens.renderEmployeeTab = function(tabId, employee, data) {
  const container = $('#employee-tab-container');
  if (!container) return;

  const myTs = data.timesheets.filter(t => t.employeeId === employee.id);
  const myActivity = data.activity.filter(a => a.employeeId === employee.id);
  const myProjects = employee.projects.map(pid => State.getProject(pid)).filter(Boolean);

  container.innerHTML = '';

  switch (tabId) {
    case 'timesheets':
      container.appendChild(UI.createCard({
        title: 'Timesheets',
        children: myTs.length > 0
          ? UI.createTable({
            columns: [
              { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
              { field: 'projectId', header: 'Project', render: (r) => { const p = State.getProject(r.projectId); return p ? p.code : r.projectId; }},
              { field: 'hours', header: 'Hours', render: (r) => UI.formatNumber(r.hours, 1) },
              { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
              { field: 'description', header: 'Description' },
              { field: 'actions', header: 'Actions', render: (r) => UI.createElement('div', { class: 'table-cell-actions' }, [
                UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => Screens.showTimesheetDetail(r.id) })
              ])}
            ],
            data: myTs
          })
          : UI.createEmptyState({ title: 'No timesheets', message: 'This employee has no timesheet entries yet.' })
      }));
      break;

    case 'projects':
      container.appendChild(UI.createCard({
        title: 'Assigned Projects',
        children: myProjects.length > 0
          ? UI.createTable({
            columns: [
              { field: 'code', header: 'Code', render: (r) => UI.createElement('span', { class: 'fw-medium' }, r.code) },
              { field: 'name', header: 'Project' },
              { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
              { field: 'phase', header: 'Phase' },
              { field: 'budgetHours', header: 'Budget Hrs', render: (r) => UI.formatNumber(r.budgetHours) },
              { field: 'approvedHours', header: 'Actual Hrs', render: (r) => UI.formatNumber(r.approvedHours) },
              { field: 'actions', header: 'Actions', render: (r) => UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('project-detail', { id: r.id }) }) }
            ],
            data: myProjects
          })
          : UI.createEmptyState({ title: 'No projects', message: 'This employee is not assigned to any projects.' })
      }));
      break;

    case 'activity':
      container.appendChild(UI.createCard({
        title: 'Recent Activity',
        children: myActivity.length > 0
          ? UI.createTable({
            columns: [
              { field: 'timestamp', header: 'Time', render: (r) => UI.formatDateTime(r.timestamp) },
              { field: 'application', header: 'Application' },
              { field: 'projectId', header: 'Project', render: (r) => { if (!r.projectId) return UI.createBadge('Unassigned', 'observed'); const p = State.getProject(r.projectId); return p ? p.code : r.projectId; }},
              { field: 'classification', header: 'Classification' },
              { field: 'state', header: 'State', render: (r) => UI.createBadge(r.state, r.state) },
              { field: 'duration', header: 'Duration (min)', render: (r) => r.duration }
            ],
            data: myActivity.slice(0, 50)
          })
          : UI.createEmptyState({ title: 'No activity', message: 'No tracked activity for this employee.' })
      }));
      break;

    case 'details':
      container.appendChild(UI.createCard({
        title: 'Employee Details',
        children: UI.createElement('div', { class: 'd-grid gap-4', style: 'grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));' }, [
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Contact Information'),
            UI.createElement('div', { class: 'd-grid gap-2' }, [
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Email'), UI.createElement('span', { class: 'fw-medium' }, employee.email)]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Phone'), UI.createElement('span', { class: 'fw-medium' }, employee.phone || '—')]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Hire Date'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(employee.hireDate))]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Manager'), UI.createElement('span', { class: 'fw-medium' }, employee.managerId ? `${State.getEmployee(employee.managerId)?.firstName} ${State.getEmployee(employee.managerId)?.lastName}` : '—')])
            ])
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Employment Details'),
            UI.createElement('div', { class: 'd-grid gap-2' }, [
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Department'), UI.createElement('span', { class: 'fw-medium' }, employee.department)]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Position'), UI.createElement('span', { class: 'fw-medium' }, employee.position)]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Role'), UI.createElement('span', {}, UI.createBadge(employee.role, employee.role))]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Status'), UI.createElement('span', {}, UI.createBadge(employee.status, employee.status))])
            ])
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Rates'),
            UI.createElement('div', { class: 'd-grid gap-2' }, [
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Hourly Cost Rate'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(employee.hourlyCostRate) + '/hr')]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Billable Rate'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(employee.billableRate) + '/hr')]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Margin'), UI.createElement('span', { class: 'fw-medium text-teal' }, employee.billableRate > 0 ? `${(((employee.billableRate - employee.hourlyCostRate) / employee.billableRate) * 100).toFixed(0)}%` : '—')])
            ])
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Skills'),
            UI.createElement('div', { class: 'd-flex flex-wrap gap-2' }, (employee.skills || []).map(s => UI.createElement('span', { class: 'badge badge-draft' }, s)))
          ])
        ])
      }));
      break;
  }
};

// ==================== CLIENT DETAIL ====================
Screens['client-detail'] = function(params) {
  const client = State.getClient(params.id);
  if (!client) {
    return Screens.renderNotFound('Client not found');
  }

  const data = getVisibleData();
  const clientProjects = data.projects.filter(p => p.clientId === client.id);
  const clientInvoices = data.invoices.filter(i => i.clientId === client.id);

  const content = UI.createElement('div', {});

  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('nav', { class: 'breadcrumb mb-2' }, [
        UI.createElement('a', { href: '#', class: 'breadcrumb-link', onClick: (e) => { e.preventDefault(); RouterInstance.navigate('clients'); } }, 'Clients'),
        UI.createElement('span', { class: 'breadcrumb-separator' }, '/'),
        UI.createElement('span', { class: 'breadcrumb-current' }, client.name)
      ]),
      UI.createElement('h1', { class: 'page-title' }, client.name),
      UI.createElement('p', { class: 'text-secondary mt-1' }, `${client.type} • ${client.status}`)
    ]),
    UI.createButton({ text: 'Edit', variant: 'secondary', onClick: () => Screens.showClientModal(client) })
  ]));

  content.appendChild(UI.createElement('div', { class: 'kpi-grid mb-6' }, [
    UI.createKPICard({ label: 'Active Projects', value: clientProjects.filter(p => p.status === 'active').length, subvalue: `${clientProjects.length} total`, icon: '📁', iconBg: 'primary' }),
    UI.createKPICard({ label: 'Total Invoiced', value: UI.formatCurrency(clientInvoices.reduce((s, i) => s + i.total, 0)), subvalue: `${clientInvoices.length} invoices`, icon: '$', iconBg: 'green' }),
    UI.createKPICard({ label: 'Outstanding', value: UI.formatCurrency(clientInvoices.filter(i => i.status === 'sent' || i.status === 'overdue').reduce((s, i) => s + i.balance, 0)), subvalue: `${clientInvoices.filter(i => i.status === 'sent' || i.status === 'overdue').length} invoices`, icon: '📄', iconBg: 'amber' }),
    UI.createKPICard({ label: 'Payment Terms', value: `${client.paymentTerms} days`, subvalue: 'Net terms', icon: '📅', iconBg: 'teal' })
  ]));

  // Tabs
  const tabs = [
    { id: 'projects', label: 'Projects' },
    { id: 'invoices', label: 'Invoices' },
    { id: 'details', label: 'Details' }
  ];

  content.appendChild(UI.createElement('div', { class: 'tabs mb-4', id: 'client-tabs' }, tabs.map(tab =>
    UI.createElement('button', {
      class: `tab ${tab.id === 'projects' ? 'active' : ''}`,
      dataset: { tab: tab.id },
      onClick: (e) => {
        $$('.tab', e.currentTarget.parentElement).forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        Screens.renderClientTab(tab.id, client, clientProjects, clientInvoices);
      }
    }, tab.label)
  )));

  const tabContainer = UI.createElement('div', { id: 'client-tab-container' });
  content.appendChild(tabContainer);

  setTimeout(() => Screens.renderClientTab('projects', client, clientProjects, clientInvoices), 0);

  return content;
};

Screens.renderClientTab = function(tabId, client, projects, invoices) {
  const container = $('#client-tab-container');
  if (!container) return;

  container.innerHTML = '';

  switch (tabId) {
    case 'projects':
      container.appendChild(UI.createCard({
        title: 'Projects',
        children: projects.length > 0
          ? UI.createTable({
            columns: [
              { field: 'code', header: 'Code', render: (r) => UI.createElement('span', { class: 'fw-medium' }, r.code) },
              { field: 'name', header: 'Project' },
              { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
              { field: 'phase', header: 'Phase' },
              { field: 'budgetHours', header: 'Budget Hrs', render: (r) => UI.formatNumber(r.budgetHours) },
              { field: 'approvedHours', header: 'Actual Hrs', render: (r) => UI.formatNumber(r.approvedHours) },
              { field: 'billedRevenue', header: 'Billed', render: (r) => UI.formatCurrency(r.billedRevenue) },
              { field: 'actions', header: 'Actions', render: (r) => UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('project-detail', { id: r.id }) }) }
            ],
            data: projects
          })
          : UI.createEmptyState({ title: 'No projects', message: 'This client has no projects yet.' })
      }));
      break;

    case 'invoices':
      container.appendChild(UI.createCard({
        title: 'Invoices',
        children: invoices.length > 0
          ? UI.createTable({
            columns: [
              { field: 'invoiceNumber', header: 'Invoice #', render: (r) => UI.createElement('span', { class: 'fw-medium' }, r.invoiceNumber) },
              { field: 'date', header: 'Date', render: (r) => UI.formatDate(r.date) },
              { field: 'dueDate', header: 'Due Date', render: (r) => UI.formatDate(r.dueDate) },
              { field: 'total', header: 'Total', render: (r) => UI.formatCurrency(r.total) },
              { field: 'amountPaid', header: 'Paid', render: (r) => UI.formatCurrency(r.amountPaid) },
              { field: 'balance', header: 'Balance', render: (r) => UI.createElement('span', { class: `fw-medium ${r.balance > 0 ? 'text-danger' : 'text-success'}` }, UI.formatCurrency(r.balance)) },
              { field: 'status', header: 'Status', render: (r) => UI.createBadge(r.status, r.status) },
              { field: 'actions', header: 'Actions', render: (r) => UI.createButton({ text: 'View', variant: 'ghost', size: 'sm', onClick: () => RouterInstance.navigate('invoice-detail', { id: r.id }) }) }
            ],
            data: invoices
          })
          : UI.createEmptyState({ title: 'No invoices', message: 'No invoices for this client yet.' })
      }));
      break;

    case 'details':
      container.appendChild(UI.createCard({
        title: 'Client Details',
        children: UI.createElement('div', { class: 'd-grid gap-4', style: 'grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));' }, [
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Contact Information'),
            UI.createElement('div', { class: 'd-grid gap-2' }, [
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Contact Person'), UI.createElement('span', { class: 'fw-medium' }, client.contactPerson || '—')]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Email'), UI.createElement('span', { class: 'fw-medium' }, client.email || '—')]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Phone'), UI.createElement('span', { class: 'fw-medium' }, client.phone || '—')]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'ABN'), UI.createElement('span', { class: 'fw-medium' }, client.abn || '—')])
            ])
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Addresses'),
            UI.createElement('div', { class: 'd-grid gap-4' }, [
              UI.createElement('div', {}, [UI.createElement('div', { class: 'text-secondary mb-1' }, 'Address'), UI.createElement('pre', { class: 'text-sm', style: 'white-space: pre-wrap; font-family: inherit;' }, client.address || '—')]),
              UI.createElement('div', {}, [UI.createElement('div', { class: 'text-secondary mb-1' }, 'Billing Address'), UI.createElement('pre', { class: 'text-sm', style: 'white-space: pre-wrap; font-family: inherit;' }, client.billingAddress || '—')])
            ])
          ]),
          UI.createElement('div', {}, [
            UI.createElement('h4', { class: 'mb-3' }, 'Terms & Settings'),
            UI.createElement('div', { class: 'd-grid gap-2' }, [
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Payment Terms'), UI.createElement('span', { class: 'fw-medium' }, `${client.paymentTerms} days`)]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Status'), UI.createElement('span', {}, UI.createBadge(client.status, client.status))]),
              UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Type'), UI.createElement('span', { class: 'fw-medium' }, client.type)])
            ])
          ]),
          client.notes && UI.createElement('div', { class: 'col-span-full' }, [
            UI.createElement('h4', { class: 'mb-3' }, 'Notes'),
            UI.createElement('pre', { class: 'text-sm', style: 'white-space: pre-wrap; font-family: inherit; background: var(--color-canvas); padding: var(--space-3); border-radius: var(--radius-md);' }, client.notes)
          ])
        ].filter(Boolean))
      }));
      break;
  }
};

// ==================== QUOTE DETAIL ====================
Screens['quote-detail'] = function(params) {
  const quotes = State.getQuotes();
  const quote = quotes.find(q => q.id === params.id);
  if (!quote) {
    return Screens.renderNotFound('Quote not found');
  }

  const client = State.getClient(quote.clientId);
  const project = quote.projectId ? State.getProject(quote.projectId) : null;

  const content = UI.createElement('div', {});

  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('nav', { class: 'breadcrumb mb-2' }, [
        UI.createElement('a', { href: '#', class: 'breadcrumb-link', onClick: (e) => { e.preventDefault(); RouterInstance.navigate('quotes'); } }, 'Quotes'),
        UI.createElement('span', { class: 'breadcrumb-separator' }, '/'),
        UI.createElement('span', { class: 'breadcrumb-current' }, quote.quoteNumber)
      ]),
      UI.createElement('h1', { class: 'page-title' }, quote.quoteNumber),
      UI.createElement('p', { class: 'text-secondary mt-1' }, `${quote.status} • ${client?.name} • ${UI.formatDate(quote.date)}`)
    ]),
    UI.createElement('div', { class: 'flex gap-2' }, [
      quote.status === 'draft' && UI.createButton({ text: 'Send Quote', variant: 'primary', onClick: () => { quote.status = 'sent'; quote.sentAt = new Date().toISOString(); Screens.renderCurrent(); UI.showToast('success', 'Quote Sent', 'Quote has been sent to client.'); } }),
      quote.status === 'sent' && UI.createButton({ text: 'Mark Accepted', variant: 'success', onClick: () => { quote.status = 'accepted'; quote.acceptedAt = new Date().toISOString(); Screens.renderCurrent(); UI.showToast('success', 'Quote Accepted', 'Client has accepted the quote.'); } }),
      UI.createButton({ text: 'Preview', variant: 'secondary', onClick: () => Screens.previewQuote(quote) })
    ].filter(Boolean))
  ]));

  // Quote Details
  content.appendChild(UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' }, [
    // Details Card
    UI.createCard({
      title: 'Quote Details',
      children: UI.createElement('div', { class: 'd-grid gap-3' }, [
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Client'), UI.createElement('span', { class: 'fw-medium' }, client?.name || '—')]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Project'), UI.createElement('span', { class: 'fw-medium' }, project ? `${project.code} - ${project.name}` : '—')]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Date'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(quote.date))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Valid Until'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(quote.validUntil))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Status'), UI.createElement('span', {}, UI.createBadge(quote.status, quote.status))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Prepared By'), UI.createElement('span', { class: 'fw-medium' }, State.getEmployee(quote.preparedBy) ? `${State.getEmployee(quote.preparedBy).firstName} ${State.getEmployee(quote.preparedBy).lastName}` : '—')]),
        quote.sentAt && UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Sent'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDateTime(quote.sentAt))]),
        quote.acceptedAt && UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Accepted'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDateTime(quote.acceptedAt))]),
        quote.rejectedAt && UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Rejected'), UI.createElement('span', { class: 'fw-medium text-danger' }, UI.formatDateTime(quote.rejectedAt))]),
        quote.rejectedReason && UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Rejection Reason'), UI.createElement('span', { class: 'text-danger' }, quote.rejectedReason)])
      ].filter(Boolean))
    }),

    // Financial Summary
    UI.createCard({
      title: 'Financial Summary',
      children: UI.createElement('div', { class: 'd-grid gap-3' }, [
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Subtotal'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(quote.subtotal))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, `Markup (${quote.markupPercent}%)`), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(quote.markupAmount))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, `Contingency (${quote.contingencyPercent}%)`), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(quote.contingencyAmount))]),
        quote.discountAmount > 0 && UI.createElement('div', { class: 'd-flex justify-between text-danger' }, [UI.createElement('span', { class: 'text-secondary' }, `Discount (${quote.discountPercent}%)`), UI.createElement('span', { class: 'fw-medium' }, `-${UI.formatCurrency(quote.discountAmount)}`)]),
        UI.createElement('hr', {}),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, `Tax (${(State.state.settings.company.taxRate * 100).toFixed(0)}%)`), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(quote.taxAmount))]),
        UI.createElement('div', { class: 'd-flex justify-between text-lg fw-bold', style: 'border-top: 2px solid var(--color-border); padding-top: 8px;' }, [UI.createElement('span', {}, 'Total'), UI.createElement('span', {}, UI.formatCurrency(quote.total))]),
        UI.createElement('div', { class: 'd-flex justify-between text-sm text-muted' }, [UI.createElement('span', {}, 'Estimated Cost'), UI.createElement('span', {}, UI.formatCurrency(quote.estimatedCost))]),
        UI.createElement('div', { class: 'd-flex justify-between text-sm fw-medium', style: `color: ${quote.estimatedMargin > 0.3 ? 'var(--status-approved)' : quote.estimatedMargin > 0.2 ? 'var(--status-suggested)' : 'var(--status-rejected)'}` }, [UI.createElement('span', {}, 'Estimated Margin'), UI.createElement('span', {}, `${(quote.estimatedMargin * 100).toFixed(1)}%`)])
      ].filter(Boolean))
    })
  ]));

  // Line Items
  content.appendChild(UI.createCard({
    title: 'Line Items',
    children: quote.items && quote.items.length > 0
      ? UI.createTable({
        columns: [
          { field: 'description', header: 'Description' },
          { field: 'quantity', header: 'Qty', render: (r) => UI.formatNumber(r.quantity, 1) },
          { field: 'unit', header: 'Unit' },
          { field: 'rate', header: 'Rate', render: (r) => UI.formatCurrency(r.rate) },
          { field: 'amount', header: 'Amount', render: (r) => UI.formatCurrency(r.amount) }
        ],
        data: quote.items
      })
      : UI.createEmptyState({ title: 'No line items', message: 'This quote has no line items.' })
  }));

  // Scope & Notes
  if (quote.scopeDescription || quote.notes) {
    content.appendChild(UI.createCard({
      title: 'Scope & Notes',
      children: UI.createElement('div', { class: 'd-grid gap-4' }, [
        quote.scopeDescription && UI.createElement('div', {}, [UI.createElement('h4', { class: 'mb-2' }, 'Scope of Work'), UI.createElement('p', { style: 'white-space: pre-wrap;' }, quote.scopeDescription)]),
        quote.notes && UI.createElement('div', {}, [UI.createElement('h4', { class: 'mb-2' }, 'Notes & Terms'), UI.createElement('p', { style: 'white-space: pre-wrap;' }, quote.notes)])
      ].filter(Boolean))
    }));
  }

  return content;
};

// ==================== INVOICE DETAIL ====================
Screens['invoice-detail'] = function(params) {
  const invoices = State.getInvoices();
  const invoice = invoices.find(i => i.id === params.id);
  if (!invoice) {
    return Screens.renderNotFound('Invoice not found');
  }

  const client = State.getClient(invoice.clientId);
  const project = invoice.projectId ? State.getProject(invoice.projectId) : null;

  const content = UI.createElement('div', {});

  content.appendChild(UI.createElement('div', { class: 'flex justify-between items-center mb-6 flex-wrap gap-4' }, [
    UI.createElement('div', {}, [
      UI.createElement('nav', { class: 'breadcrumb mb-2' }, [
        UI.createElement('a', { href: '#', class: 'breadcrumb-link', onClick: (e) => { e.preventDefault(); RouterInstance.navigate('billing'); } }, 'Billing'),
        UI.createElement('span', { class: 'breadcrumb-separator' }, '/'),
        UI.createElement('span', { class: 'breadcrumb-current' }, invoice.invoiceNumber)
      ]),
      UI.createElement('h1', { class: 'page-title' }, invoice.invoiceNumber),
      UI.createElement('p', { class: 'text-secondary mt-1' }, `${invoice.status} • ${client?.name} • ${UI.formatDate(invoice.date)}`)
    ]),
    UI.createElement('div', { class: 'flex gap-2' }, [
      (invoice.status === 'draft' || invoice.status === 'sent' || invoice.status === 'overdue') && UI.createButton({ text: 'Mark Paid', variant: 'success', onClick: () => { invoice.status = 'paid'; invoice.paidDate = new Date().toISOString().split('T')[0]; invoice.amountPaid = invoice.total; invoice.balance = 0; Screens.renderCurrent(); UI.showToast('success', 'Payment Recorded', 'Invoice marked as paid.'); } }),
      invoice.status === 'draft' && UI.createButton({ text: 'Send Invoice', variant: 'primary', onClick: () => { invoice.status = 'sent'; invoice.date = new Date().toISOString().split('T')[0]; Screens.renderCurrent(); UI.showToast('success', 'Invoice Sent', 'Invoice has been sent to client.'); } }),
      UI.createButton({ text: 'Export PDF', variant: 'ghost', icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' })
    ].filter(Boolean))
  ]));

  content.appendChild(UI.createElement('div', { class: 'd-grid gap-6', style: 'grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));' }, [
    // Details
    UI.createCard({
      title: 'Invoice Details',
      children: UI.createElement('div', { class: 'd-grid gap-3' }, [
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Client'), UI.createElement('span', { class: 'fw-medium' }, client?.name || '—')]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Project'), UI.createElement('span', { class: 'fw-medium' }, project ? `${project.code} - ${project.name}` : '—')]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Invoice Date'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(invoice.date))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Due Date'), UI.createElement('span', { class: 'fw-medium' }, UI.formatDate(invoice.dueDate))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Status'), UI.createElement('span', {}, UI.createBadge(invoice.status, invoice.status))]),
        invoice.paidDate && UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Paid Date'), UI.createElement('span', { class: 'fw-medium text-success' }, UI.formatDate(invoice.paidDate))])
      ].filter(Boolean))
    }),

    // Financial
    UI.createCard({
      title: 'Amounts',
      children: UI.createElement('div', { class: 'd-grid gap-3' }, [
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Subtotal'), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(invoice.subtotal))]),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, `Tax (${(State.state.settings.company.taxRate * 100).toFixed(0)}%)`), UI.createElement('span', { class: 'fw-medium' }, UI.formatCurrency(invoice.taxAmount))]),
        UI.createElement('hr', {}),
        UI.createElement('div', { class: 'd-flex justify-between text-lg fw-bold', style: 'border-top: 2px solid var(--color-border); padding-top: 8px;' }, [UI.createElement('span', {}, 'Total'), UI.createElement('span', {}, UI.formatCurrency(invoice.total))]),
        UI.createElement('hr', {}),
        UI.createElement('div', { class: 'd-flex justify-between' }, [UI.createElement('span', { class: 'text-secondary' }, 'Amount Paid'), UI.createElement('span', { class: 'fw-medium text-success' }, UI.formatCurrency(invoice.amountPaid))]),
        UI.createElement('div', { class: 'd-flex justify-between text-lg fw-bold', style: `color: ${invoice.balance > 0 ? 'var(--status-rejected)' : 'var(--status-approved)'}` }, [UI.createElement('span', {}, 'Balance Due'), UI.createElement('span', {}, UI.formatCurrency(invoice.balance))])
      ])
    })
  ]));

  // Line Items
  content.appendChild(UI.createCard({
    title: 'Line Items',
    children: invoice.items && invoice.items.length > 0
      ? UI.createTable({
        columns: [
          { field: 'description', header: 'Description' },
          { field: 'quantity', header: 'Qty', render: (r) => UI.formatNumber(r.quantity, 1) },
          { field: 'unit', header: 'Unit' },
          { field: 'rate', header: 'Rate', render: (r) => UI.formatCurrency(r.rate) },
          { field: 'amount', header: 'Amount', render: (r) => UI.formatCurrency(r.amount) }
        ],
        data: invoice.items
      })
      : UI.createEmptyState({ title: 'No line items', message: 'This invoice has no line items.' })
  }));

  // Notes
  if (invoice.notes) {
    content.appendChild(UI.createCard({
      title: 'Notes',
      children: UI.createElement('p', { style: 'white-space: pre-wrap;' }, invoice.notes)
    }));
  }

  return content;
};

// ==================== RENDER CURRENT HELPER ====================
Screens.renderCurrent = function() {
  const route = RouterInstance.getCurrentRoute();
  const params = RouterInstance.getCurrentParams();
  if (route) {
    renderScreen(route, params);
  }
};

// ==================== EXPORT ====================
window.Screens = Screens;