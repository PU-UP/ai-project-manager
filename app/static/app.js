(() => {
  const statusLabels = {
    active: "当前推进",
    maintain: "维持运行",
    observe: "观察孵化",
    paused: "短期暂停",
    archived: "历史归档",
  };
  const actionLabels = {
    continue: "继续",
    maintain: "维持",
    observe: "观察",
    pause: "暂停",
    delegate_to_ai: "AI执行",
    human_intervene: "人工介入",
    seek_feedback: "找反馈",
    narrow_scope: "收窄",
    change_metric: "调标准",
    archive: "归档",
  };

  function applyGlobalLabels(root = document) {
    root.querySelectorAll("[data-status-value]").forEach((item) => {
      const label = statusLabels[item.dataset.statusValue];
      if (label) item.textContent = label;
    });
    root.querySelectorAll("[data-action-value], [data-priority-action]").forEach((item) => {
      const action = item.dataset.actionValue || item.dataset.priorityAction;
      const label = actionLabels[action];
      if (label) item.textContent = label;
    });
  }

  const timelineBody = document.querySelector("[data-timeline-body]");
  const timelineItems = Array.from(document.querySelectorAll("[data-event-date]"));
  const daysFilter = document.querySelector("[data-days-filter]");
  const collapseTimeline = document.querySelector("[data-collapse-timeline]");
  const timelineEmpty = document.querySelector("[data-timeline-empty]");
  const timelineCount = document.querySelector("[data-timeline-count]");

  function parseLocalDate(value) {
    if (!value) return null;
    const normalized = value.replace(" ", "T");
    const parsed = new Date(normalized);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function renderTimeline() {
    if (!timelineItems.length) return;
    const selected = daysFilter ? daysFilter.value : "30";
    const now = new Date();
    let visibleCount = 0;

    timelineItems.forEach((item) => {
      const eventDate = parseLocalDate(item.dataset.eventDate);
      const visible = selected === "all"
        || (eventDate && (now - eventDate) / 86400000 <= Number(selected));
      item.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    if (timelineEmpty) timelineEmpty.hidden = visibleCount > 0;
    if (timelineCount) {
      timelineCount.textContent = selected === "all"
        ? `${visibleCount} 条记录`
        : `${visibleCount} 条记录 · ${daysFilter.selectedOptions[0].textContent}`;
    }
  }

  if (daysFilter) {
    daysFilter.addEventListener("change", renderTimeline);
  }

  if (collapseTimeline && timelineBody) {
    collapseTimeline.addEventListener("click", () => {
      const collapsed = !timelineBody.hidden;
      timelineBody.hidden = collapsed;
      collapseTimeline.textContent = collapsed ? "展开" : "收起";
      collapseTimeline.setAttribute("aria-expanded", collapsed ? "false" : "true");
    });
  }

  renderTimeline();
  applyGlobalLabels();

  const table = document.querySelector("[data-project-table]");
  if (!table) return;

  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("[data-project-row]"));
  const sortButtons = Array.from(document.querySelectorAll("[data-sort-key]"));
  const filterButtons = Array.from(document.querySelectorAll("[data-status-filter]"));
  const detailButtons = Array.from(document.querySelectorAll("[data-detail-toggle]"));
  const countLabel = document.querySelector("[data-project-count]");
  const activeFilters = new Set();

  const statusRank = {
    active: 1,
    maintain: 2,
    observe: 3,
    paused: 4,
    archived: 5,
  };
  const riskRank = {
    high: 1,
    medium: 2,
    low: 3,
  };
  const actionRank = {
    human_intervene: 1,
    change_metric: 2,
    seek_feedback: 3,
    delegate_to_ai: 4,
    continue: 5,
    maintain: 6,
    observe: 7,
    pause: 8,
    narrow_scope: 9,
    archive: 10,
  };
  let currentSort = { key: "updated", direction: "desc" };

  function applyCompactLabels() {
    rows.forEach((row) => {
      const statusTag = row.querySelector(".tag-status");
      const actionTag = row.querySelector(".tag-action");
      if (statusTag && statusLabels[row.dataset.status]) {
        statusTag.textContent = statusLabels[row.dataset.status];
      }
      if (actionTag && actionLabels[row.dataset.action]) {
        actionTag.textContent = actionLabels[row.dataset.action];
      }
    });
  }

  function sortValue(row, key) {
    if (key === "status") return statusRank[row.dataset.status] || 99;
    if (key === "risk") return riskRank[row.dataset.risk] || 99;
    if (key === "action") return actionRank[row.dataset.action] || 99;
    if (key === "value" || key === "ai" || key === "human") {
      return Number(row.dataset[key] || 0);
    }
    return (row.dataset[key] || "").toString();
  }

  function compareRows(a, b) {
    const key = currentSort.key;
    const dir = currentSort.direction === "asc" ? 1 : -1;
    const av = sortValue(a, key);
    const bv = sortValue(b, key);

    if (typeof av === "number" && typeof bv === "number") {
      return (av - bv) * dir;
    }
    return av.localeCompare(bv, "zh-Hans-CN", { numeric: true }) * dir;
  }

  function render() {
    const sorted = [...rows].sort(compareRows);
    let visibleCount = 0;
    const hasStatusFilter = activeFilters.size > 0;

    sorted.forEach((row) => {
      const visible = !hasStatusFilter || activeFilters.has(row.dataset.status);
      const detailRow = tbody.querySelector(`[data-detail-for="${row.dataset.projectId}"]`);
      const detailButton = document.querySelector(`[data-detail-toggle="${row.dataset.projectId}"]`);
      row.hidden = !visible;
      if (!visible && detailRow) {
        detailRow.hidden = true;
        if (detailButton) {
          detailButton.textContent = "详情";
          detailButton.setAttribute("aria-expanded", "false");
        }
      }
      if (visible) visibleCount += 1;
      tbody.appendChild(row);
      if (detailRow) tbody.appendChild(detailRow);
    });

    if (countLabel) {
      countLabel.textContent = !hasStatusFilter
        ? `${visibleCount} 个项目`
        : `${visibleCount} 个项目 · ${activeFilters.size} 个状态`;
    }

    sortButtons.forEach((button) => {
      const active = button.dataset.sortKey === currentSort.key;
      button.classList.toggle("is-active", active);
      button.dataset.direction = active ? currentSort.direction : "";
      button.setAttribute(
        "aria-sort",
        active ? (currentSort.direction === "asc" ? "ascending" : "descending") : "none",
      );
    });
  }

  sortButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.sortKey;
      const defaultDirection = ["name", "status", "risk", "action"].includes(key)
        ? "asc"
        : "desc";
      currentSort = {
        key,
        direction: currentSort.key === key && currentSort.direction === defaultDirection
          ? (defaultDirection === "asc" ? "desc" : "asc")
          : defaultDirection,
      };
      render();
    });
  });

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const filter = button.dataset.statusFilter;
      if (filter === "all") {
        activeFilters.clear();
      } else if (activeFilters.has(filter)) {
        activeFilters.delete(filter);
      } else {
        activeFilters.add(filter);
      }

      filterButtons.forEach((item) => {
        const itemFilter = item.dataset.statusFilter;
        const active = itemFilter === "all"
          ? activeFilters.size === 0
          : activeFilters.has(itemFilter);
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", active ? "true" : "false");
      });
      render();
    });
  });

  detailButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const detailRow = tbody.querySelector(`[data-detail-for="${button.dataset.detailToggle}"]`);
      if (!detailRow) return;
      const expanded = detailRow.hidden;
      detailRow.hidden = !expanded;
      button.textContent = expanded ? "收起" : "详情";
      button.setAttribute("aria-expanded", expanded ? "true" : "false");
    });
  });

  applyCompactLabels();
  render();
})();
