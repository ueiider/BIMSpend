/* BIMSpend Charts */
/* Chart utilities and visualization components */

// Color palette for charts
const CHART_COLORS = {
  primary: '#1976A5',
  teal: '#287E72',
  amber: '#A96512',
  red: '#B23B3B',
  green: '#1E7E34',
  purple: '#7C3AED',
  pink: '#DB2777',
  indigo: '#4F46E5',
  cyan: '#0891B2',
  orange: '#EA580C',
  gray: '#546B7D',
  lightGray: '#D9E1E7'
};

const CHART_COLORS_DARK = {
  primary: '#3B9BD9',
  teal: '#40C9B3',
  amber: '#D4A03A',
  red: '#E87A7A',
  green: '#50D06C',
  purple: '#A78BFA',
  pink: '#F472B6',
  indigo: '#818CF8',
  cyan: '#22D3EE',
  orange: '#FB923C',
  gray: '#A8B8C8',
  lightGray: '#3A5A75'
};

function getChartColors() {
  return document.documentElement.dataset.theme === 'dark' ? CHART_COLORS_DARK : CHART_COLORS;
}

// Generate color array for multiple series
function generateChartColors(count) {
  const colors = Object.values(getChartColors());
  const result = [];
  for (let i = 0; i < count; i++) {
    result.push(colors[i % colors.length]);
  }
  return result;
}

// Simple Bar Chart (CSS-based)
function createSimpleBarChart(data, options = {}) {
  const {
    container,
    xKey = 'label',
    yKey = 'value',
    maxHeight = 200,
    showValues = true,
    color = 'primary',
    onClick = null
  } = options;

  const maxValue = Math.max(...data.map(d => d[yKey]), 1);
  const colors = getChartColors();

  const chart = UI.createElement('div', { class: 'simple-bar-chart chart-animate' },
    data.map((item, index) => {
      const height = (item[yKey] / maxValue) * maxHeight;
      const barColor = color === 'multi' ? generateChartColors(data.length)[index] : colors[color];

      return UI.createElement('div', { class: 'simple-bar-item' }, [
        UI.createElement('div', {
          class: 'simple-bar-bar',
          style: `--target-height: ${height}px; background: ${barColor};`,
          'data-value': showValues ? UI.formatNumber(item[yKey]) : '',
          onClick: () => onClick?.(item, index)
        }),
        UI.createElement('span', { class: 'simple-bar-label' }, item[xKey])
      ]);
    })
  );

  if (container) {
    container.innerHTML = '';
    container.appendChild(chart);
  }

  return chart;
}

// Sparkline
function createSparkline(data, options = {}) {
  const { width = 100, height = 32, color = 'primary', lineWidth = 2, fill = false } = options;
  const colors = getChartColors();

  if (!data || data.length < 2) {
    return UI.createElement('div', { class: 'sparkline' }, '');
  }

  const maxVal = Math.max(...data);
  const minVal = Math.min(...data);
  const range = maxVal - minVal || 1;

  const points = data.map((val, i) => ({
    x: (i / (data.length - 1)) * width,
    y: height - ((val - minVal) / range) * height
  }));

  const pathData = points.map((p, i) =>
    `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`
  ).join(' ');

  const svg = UI.createElement('svg', {
    viewBox: `0 0 ${width} ${height}`,
    class: 'sparkline',
    width,
    height
  }, [
    fill && UI.createElement('path', {
      d: `${pathData} L ${width} ${height} L 0 ${height} Z`,
      fill: colors[color],
      opacity: 0.15
    }),
    UI.createElement('path', {
      d: pathData,
      fill: 'none',
      stroke: colors[color],
      'stroke-width': lineWidth,
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round'
    })
  ].filter(Boolean));

  return svg;
}

// Progress Ring
function createProgressRing(percent, options = {}) {
  const { size = 64, strokeWidth = 4, color = 'primary', showLabel = true } = options;
  const colors = getChartColors();
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  const svg = UI.createElement('svg', {
    class: 'progress-ring',
    width: size,
    height: size,
    viewBox: `0 0 ${size} ${size}`
  }, [
    UI.createElement('circle', {
      class: 'progress-ring-circle progress-ring-bg',
      cx: size / 2,
      cy: size / 2,
      r: radius,
      stroke: colors.gray,
      'stroke-width': strokeWidth
    }),
    UI.createElement('circle', {
      class: 'progress-ring-circle progress-ring-progress',
      cx: size / 2,
      cy: size / 2,
      r: radius,
      stroke: colors[color],
      'stroke-width': strokeWidth,
      style: `--progress: ${percent}; stroke-dashoffset: ${offset};`
    })
  ]);

  if (showLabel) {
    const wrapper = UI.createElement('div', { style: 'display: inline-flex; flex-direction: column; align-items: center; gap: 4px;' }, [
      svg,
      UI.createElement('span', { class: 'text-sm fw-semibold' }, `${percent.toFixed(0)}%`)
    ]);
    return wrapper;
  }

  return svg;
}

// Mini Stats Grid
function createMiniStats(stats, options = {}) {
  const { columns = 4 } = options;

  const grid = UI.createElement('div', {
    class: 'mini-stats',
    style: `grid-template-columns: repeat(${Math.min(columns, stats.length)}, 1fr);`
  }, stats.map(stat => {
    const colors = getChartColors();
    return UI.createElement('div', { class: 'mini-stat' }, [
      UI.createElement('div', { class: 'mini-stat-value', style: stat.color ? `color: ${colors[stat.color]}` : '' }, stat.value),
      UI.createElement('div', { class: 'mini-stat-label' }, stat.label),
      stat.trend ? UI.createElement('span', { class: `trend-indicator ${stat.trend.type}` }, stat.trend.label) : null
    ].filter(Boolean));
  }));

  return grid;
}

// Project Profitability Chart (Horizontal Bar)
function createProjectProfitabilityChart(projects, options = {}) {
  const { container, maxBars = 10 } = options;
  const sorted = [...projects]
    .sort((a, b) => b.grossMargin - a.grossMargin)
    .slice(0, maxBars);

  const maxMargin = Math.max(...sorted.map(p => p.grossMargin), 1);

  const chart = UI.createElement('div', { class: 'chart-container' }, [
    UI.createElement('div', { class: 'chart-header' }, [
      UI.createElement('h3', { class: 'chart-title' }, 'Project Profitability'),
      UI.createElement('span', { class: 'text-sm text-muted' }, `${sorted.length} projects`)
    ]),
    UI.createElement('div', { style: 'height: 300px;' }, sorted.map(project => {
      const width = (project.grossMargin / maxMargin) * 100;
      const marginPercent = project.revenue > 0 ? (project.grossMargin / project.revenue) * 100 : 0;

      return UI.createElement('div', {
        class: 'simple-bar-item',
        style: 'flex-direction: row; align-items: center; height: 40px; gap: 12px; padding: 0 8px;'
      }, [
        UI.createElement('div', {
          class: 'simple-bar-label',
          style: 'width: 180px; text-align: left; flex-shrink: 0; font-weight: 500;',
          title: project.name
        }, project.name.length > 25 ? project.name.slice(0, 22) + '...' : project.name),
        UI.createElement('div', {
          style: 'flex: 1; height: 28px; background: var(--color-canvas); border-radius: var(--radius-sm); overflow: hidden; position: relative;'
        }, [
          UI.createElement('div', {
            style: `width: ${width}%; height: 100%; background: linear-gradient(90deg, var(--color-teal), var(--color-green)); border-radius: var(--radius-sm); transition: width var(--transition-normal);`
          })
        ]),
        UI.createElement('div', {
          class: 'text-sm fw-medium',
          style: 'width: 80px; text-align: right; color: var(--color-teal);'
        }, UI.formatCurrency(project.grossMargin)),
        UI.createElement('div', {
          class: 'text-sm',
          style: 'width: 50px; text-align: right; color: var(--color-text-muted);'
        }, `${marginPercent.toFixed(1)}%`)
      ]);
    }))
  ]);

  if (container) {
    container.innerHTML = '';
    container.appendChild(chart);
  }

  return chart;
}

// Budget Variance Chart
function createBudgetVarianceChart(projects, options = {}) {
  const { container } = options;

  const chart = UI.createElement('div', { class: 'chart-container' }, [
    UI.createElement('div', { class: 'chart-header' }, [
      UI.createElement('h3', { class: 'chart-title' }, 'Budget vs Actual Hours'),
      UI.createElement('span', { class: 'text-sm text-muted' }, `${projects.length} projects`)
    ]),
    UI.createElement('table', { class: 'table' }, [
      UI.createElement('thead', {}, [
        UI.createElement('tr', {}, [
          'Project', 'Budget Hours', 'Actual Hours', 'Variance', 'Variance %'
        ].map(h => UI.createElement('th', {}, h)))
      ]),
      UI.createElement('tbody', {}, projects.map(p => {
        const variance = p.approvedHours - p.budgetHours;
        const variancePercent = p.budgetHours > 0 ? (variance / p.budgetHours) * 100 : 0;
        const isOver = variance > 0;

        return UI.createElement('tr', {}, [
          UI.createElement('td', { class: 'fw-medium' }, p.name),
          UI.createElement('td', {}, UI.formatNumber(p.budgetHours)),
          UI.createElement('td', {}, UI.formatNumber(p.approvedHours)),
          UI.createElement('td', { class: isOver ? 'text-danger fw-medium' : 'text-success fw-medium' },
            `${isOver ? '+' : ''}${UI.formatNumber(variance)}`),
          UI.createElement('td', { class: isOver ? 'text-danger' : 'text-success' },
            `${isOver ? '+' : ''}${variancePercent.toFixed(1)}%`)
        ]);
      }))
    ])
  ]);

  if (container) {
    container.innerHTML = '';
    container.appendChild(chart);
  }

  return chart;
}

// Employee Utilization Chart
function createUtilizationChart(employees, options = {}) {
  const { container, targetUtilization = 75 } = options;

  const chart = UI.createElement('div', { class: 'chart-container' }, [
    UI.createElement('div', { class: 'chart-header' }, [
      UI.createElement('h3', { class: 'chart-title' }, 'Employee Utilization'),
      UI.createElement('span', { class: 'text-sm text-muted' }, `Target: ${targetUtilization}%`)
    ]),
    UI.createElement('div', { style: 'display: flex; flex-direction: column; gap: 12px;' }, employees.map(emp => {
      const isAboveTarget = emp.utilization >= targetUtilization;

      return UI.createElement('div', {
        style: 'display: flex; align-items: center; gap: 12px; padding: 8px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md);'
      }, [
        UI.createElement('div', { style: 'width: 140px; flex-shrink: 0; font-weight: 500;' }, emp.name),
        UI.createElement('div', { style: 'flex: 1; height: 20px; background: var(--color-canvas); border-radius: var(--radius-full); overflow: hidden;' }, [
          UI.createElement('div', {
            style: `width: ${Math.min(100, emp.utilization)}%; height: 100%; background: ${isAboveTarget ? 'var(--color-teal)' : 'var(--color-amber)'}; border-radius: var(--radius-full); transition: width var(--transition-normal);`
          })
        ]),
        UI.createElement('div', {
          class: `fw-medium ${isAboveTarget ? 'text-success' : 'text-warning'}`,
          style: 'width: 55px; text-align: right;'
        }, `${emp.utilization.toFixed(1)}%`),
        UI.createElement('div', { class: 'text-sm text-muted', style: 'width: 80px; text-align: right;' },
          `${UI.formatNumber(emp.billableHours)}h / ${UI.formatNumber(emp.availableHours)}h`)
      ]);
    }))
  ]);

  if (container) {
    container.innerHTML = '';
    container.appendChild(chart);
  }

  return chart;
}

// Activity Classification Donut (CSS-based)
function createActivityDonut(data, options = {}) {
  const { container, totalHours = null } = options;
  const colors = getChartColors();
  const colorArray = Object.values(colors);
  const computedTotal = totalHours || data.reduce((sum, d) => sum + d.hours, 0);

  const items = data.map((d, i) => ({
    ...d,
    percentage: (d.hours / computedTotal) * 100,
    color: colorArray[i % colorArray.length]
  }));

  const legend = UI.createElement('div', { class: 'chart-legend' }, items.map(item =>
    UI.createElement('div', { class: 'legend-item' }, [
      UI.createElement('span', { class: 'legend-color', style: `background: ${item.color}` }),
      UI.createElement('span', {}, `${item.classification}: ${item.percentage.toFixed(1)}% (${UI.formatNumber(item.hours)}h)`)
    ])
  ));

  const chart = UI.createElement('div', { class: 'chart-container' }, [
    UI.createElement('div', { class: 'chart-header' }, [
      UI.createElement('h3', { class: 'chart-title' }, 'Activity Classification'),
      UI.createElement('span', { class: 'text-sm text-muted' }, `${UI.formatNumber(computedTotal)}h total`)
    ]),
    UI.createElement('div', { style: 'display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: center; min-height: 200px;' }, [
      UI.createElement('div', {
        style: 'width: 160px; height: 160px; border-radius: 50%; background: conic-gradient(' +
          items.map((item, i) => {
            const start = items.slice(0, i).reduce((sum, d) => sum + d.percentage, 0);
            const end = start + item.percentage;
            return `${item.color} ${start.toFixed(1)}% ${end.toFixed(1)}%`;
          }).join(', ') +
        '); display: flex; align-items: center; justify-content: center; position: relative;'
      }, [
        UI.createElement('div', {
          style: 'width: 100px; height: 100px; border-radius: 50%; background: var(--color-surface); display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: inset 0 2px 8px rgba(0,0,0,0.1);'
        }, [
          UI.createElement('span', { class: 'fw-bold', style: 'font-size: 24px;' }, UI.formatNumber(computedTotal)),
          UI.createElement('span', { class: 'text-xs text-muted' }, 'hours')
        ])
      ]),
      legend
    ])
  ]);

  if (container) {
    container.innerHTML = '';
    container.appendChild(chart);
  }

  return chart;
}

// Financial Trend Chart (Multi-series line - simplified)
function createFinancialTrendChart(data, options = {}) {
  const { container, series = [], height = 300 } = options;
  // This would use a real charting library in production
  // For prototype, we create a simplified table view

  const chart = UI.createElement('div', { class: 'chart-container' }, [
    UI.createElement('div', { class: 'chart-header' }, [
      UI.createElement('h3', { class: 'chart-title' }, options.title || 'Financial Trends'),
      UI.createElement('div', { class: 'chart-actions' }, [
        UI.createElement('select', { class: 'form-select form-select-sm', style: 'width: auto; padding: 4px 8px;' }, [
          UI.createElement('option', { value: 'month' }, 'Monthly'),
          UI.createElement('option', { value: 'quarter' }, 'Quarterly'),
          UI.createElement('option', { value: 'year' }, 'Yearly')
        ])
      ])
    ]),
    UI.createElement('div', { class: 'table-container', style: 'max-height: 400px;' }, [
      UI.createElement('table', { class: 'table' }, [
        UI.createElement('thead', {}, [
          UI.createElement('tr', {}, [
            'Period', ...series.map(s => UI.createElement('th', {}, s.label))
          ].flat())
        ]),
        UI.createElement('tbody', {}, data.map(row => {
          const period = UI.formatDate(row.date, { month: 'short', year: 'numeric' });
          return UI.createElement('tr', {}, [
            UI.createElement('td', { class: 'fw-medium' }, period),
            ...series.map(s => UI.createElement('td', {},
              s.format ? s.format(row[s.key]) : UI.formatCurrency(row[s.key] || 0)
            ))
          ].flat());
        }))
      ])
    ])
  ]);

  if (container) {
    container.innerHTML = '';
    container.appendChild(chart);
  }

  return chart;
}

// Export
window.Charts = {
  CHART_COLORS,
  CHART_COLORS_DARK,
  getChartColors,
  generateChartColors,
  createSimpleBarChart,
  createSparkline,
  createProgressRing,
  createMiniStats,
  createProjectProfitabilityChart,
  createBudgetVarianceChart,
  createUtilizationChart,
  createActivityDonut,
  createFinancialTrendChart
};