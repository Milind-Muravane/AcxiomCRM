/**
 * AcxiomCRM Dashboard Analytics
 *
 * Renders three Chart.js charts using real data supplied by Flask.
 *
 * Required HTML canvas IDs:
 *   1. leadStatusChart
 *   2. pipelineStageChart
 *   3. monthlySalesChart
 */

document.addEventListener("DOMContentLoaded", function () {

  // ------------------------------------------
  // Common chart colors
  // ------------------------------------------

  const colors = {
    blue: "#2563eb",
    indigo: "#4f46e5",
    teal: "#0d9488",
    emerald: "#059669",
    amber: "#d97706",
    rose: "#e11d48",
    gray: "#94a3b8",
    lightGray: "#e2e8f0"
  };

  // ------------------------------------------
  // Helper: Safely get chart data
  // ------------------------------------------

  function getChartData(data, property, defaultValue) {
    if (!data || !Array.isArray(data[property])) {
      return defaultValue;
    }

    return data[property];
  }

  // ------------------------------------------
  // Helper: Format numbers as currency
  // ------------------------------------------

  function formatCurrency(value) {
    return "$" + Number(value || 0).toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    });
  }

  // ------------------------------------------
  // Helper: Check Chart.js availability
  // ------------------------------------------

  if (typeof Chart === "undefined") {
    console.error(
      "Chart.js is not loaded. Check the Chart.js script in base.html."
    );
    return;
  }

  // ==========================================
  // CHART 1: Lead Status Distribution
  // Doughnut chart
  // ==========================================

  const leadCanvas = document.getElementById("leadStatusChart");

  if (leadCanvas) {

    const data = window.chart1Data || {};

    const labels = getChartData(data, "labels", []);
    const counts = getChartData(data, "counts", []);

    const totalLeads = counts.reduce(function (total, count) {
      return total + Number(count || 0);
    }, 0);

    new Chart(leadCanvas, {
      type: "doughnut",

      data: {
        labels: labels,

        datasets: [{
          label: "Number of Leads",
          data: counts,

          backgroundColor: [
            "#3b82f6",
            "#06b6d4",
            "#10b981",
            "#64748b",
            "#8b5cf6",
            "#ef4444"
          ],

          borderWidth: 2,
          borderColor: "#ffffff",
          hoverOffset: 6
        }]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        cutout: "68%",

        plugins: {
          legend: {
            position: "bottom",

            labels: {
              boxWidth: 12,
              padding: 14
            }
          },

          tooltip: {
            callbacks: {
              label: function (context) {

                const count = Number(context.raw || 0);

                const percentage = totalLeads > 0
                  ? ((count / totalLeads) * 100).toFixed(1)
                  : "0.0";

                return (
                  context.label + ": " +
                  count + " leads (" +
                  percentage + "%)"
                );
              }
            }
          }
        }
      }
    });
  }

  // ==========================================
  // CHART 2: Opportunity Pipeline Stages
  // Grouped bar chart
  // ==========================================

  const pipelineCanvas = document.getElementById("pipelineStageChart");

  if (pipelineCanvas) {

    const data = window.chart2Data || {};

    const labels = getChartData(data, "labels", []);
    const values = getChartData(data, "values", []);
    const counts = getChartData(data, "counts", []);

    new Chart(pipelineCanvas, {
      type: "bar",

      data: {
        labels: labels,

        datasets: [
          {
            label: "Total Value",
            data: values,

            backgroundColor: colors.blue,
            borderRadius: 6,

            yAxisID: "y"
          },

          {
            label: "Deal Count",
            data: counts,

            backgroundColor: "#93c5fd",
            borderRadius: 6,

            yAxisID: "y1"
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
          mode: "index",
          intersect: false
        },

        scales: {
          x: {
            grid: {
              display: false
            }
          },

          y: {
            type: "linear",
            display: true,
            position: "left",

            beginAtZero: true,

            title: {
              display: true,
              text: "Opportunity Value"
            },

            ticks: {
              callback: function (value) {
                return formatCurrency(value);
              }
            },

            grid: {
              color: "#f1f5f9"
            }
          },

          y1: {
            type: "linear",
            display: true,
            position: "right",

            beginAtZero: true,

            title: {
              display: true,
              text: "Number of Deals"
            },

            grid: {
              drawOnChartArea: false
            },

            ticks: {
              precision: 0
            }
          }
        },

        plugins: {
          legend: {
            position: "top"
          },

          tooltip: {
            callbacks: {
              label: function (context) {

                const value = Number(context.raw || 0);

                if (context.dataset.yAxisID === "y") {
                  return (
                    context.dataset.label + ": " +
                    formatCurrency(value)
                  );
                }

                return (
                  context.dataset.label + ": " +
                  value
                );
              }
            }
          }
        }
      }
    });
  }

  // ==========================================
  // CHART 3: Monthly Sales / Opportunity Outcomes
  // Grouped bar chart
  // ==========================================

  const monthlyCanvas = document.getElementById("monthlySalesChart");

  if (monthlyCanvas) {

    const data = window.chart3Data || {};

    const labels = getChartData(data, "labels", []);
    const won = getChartData(data, "won", []);
    const lost = getChartData(data, "lost", []);

    new Chart(monthlyCanvas, {
      type: "bar",

      data: {
        labels: labels,

        datasets: [
          {
            label: "Won Deals",
            data: won,

            backgroundColor: colors.emerald,
            borderRadius: 6
          },

          {
            label: "Lost Deals",
            data: lost,

            backgroundColor: colors.rose,
            borderRadius: 6
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,

        scales: {
          x: {
            grid: {
              display: false
            }
          },

          y: {
            beginAtZero: true,

            title: {
              display: true,
              text: "Opportunity Value"
            },

            ticks: {
              callback: function (value) {
                return formatCurrency(value);
              }
            },

            grid: {
              color: "#f1f5f9"
            }
          }
        },

        plugins: {
          legend: {
            position: "top"
          },

          tooltip: {
            callbacks: {
              label: function (context) {

                return (
                  context.dataset.label + ": " +
                  formatCurrency(context.raw)
                );
              }
            }
          }
        }
      }
    });
  }

  // ------------------------------------------
  // Dashboard initialization complete
  // ------------------------------------------

  console.log("AcxiomCRM dashboard charts initialized.");

});
