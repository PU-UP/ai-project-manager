(() => {
  const statusLabels = {
    active: "当前推进",
    maintain: "维持运行",
    observe: "观察孵化",
    paused: "短期暂停",
    archived: "历史归档",
  };

  function applyGlobalLabels(root = document) {
    root.querySelectorAll("[data-status-value]").forEach((item) => {
      const label = statusLabels[item.dataset.statusValue];
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

  const backButton = document.querySelector(".back-btn");
  if (backButton) {
    const from = new URLSearchParams(window.location.search).get("from");
    if (from && from.startsWith("/") && !from.startsWith("//")) {
      backButton.href = from;
    }
  }

  const table = document.querySelector("[data-project-table]");
  if (!table) return;

  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("[data-project-row]"));
  const sortButtons = Array.from(document.querySelectorAll("[data-sort-key]"));
  const filterButtons = Array.from(document.querySelectorAll("[data-status-filter]"));
  const detailButtons = Array.from(document.querySelectorAll("[data-detail-toggle]"));
  const countLabel = document.querySelector("[data-project-count]");
  const projectLinks = Array.from(document.querySelectorAll(".table-project-link"));
  const activeFilters = new Set();
  const validStatuses = ["active", "maintain", "observe", "paused", "archived"];
  const defaultStatuses = validStatuses.filter((status) => status !== "archived");
  const validSortKeys = ["name", "status", "updated"];

  const statusRank = {
    active: 1,
    maintain: 2,
    observe: 3,
    paused: 4,
    archived: 5,
  };
  let currentSort = { key: "updated", direction: "desc" };

  function readOverviewState() {
    const params = new URLSearchParams(window.location.search);
    const statusParam = params.get("status");
    const sortKey = params.get("sort");
    const sortDirection = params.get("dir");

    activeFilters.clear();
    if (statusParam === "all") {
      // Show every status, including historical archives.
    } else if (statusParam) {
      statusParam.split(",")
        .filter((status) => validStatuses.includes(status))
        .forEach((status) => activeFilters.add(status));
      if (activeFilters.size === 0) {
        defaultStatuses.forEach((status) => activeFilters.add(status));
      }
    } else {
      defaultStatuses.forEach((status) => activeFilters.add(status));
    }

    currentSort = {
      key: validSortKeys.includes(sortKey) ? sortKey : "updated",
      direction: sortDirection === "asc" ? "asc" : "desc",
    };
  }

  function updateOverviewUrl() {
    const params = new URLSearchParams(window.location.search);
    const sortedFilters = validStatuses.filter((status) => activeFilters.has(status));

    if (activeFilters.size === 0) {
      params.set("status", "all");
    } else {
      params.set("status", sortedFilters.join(","));
    }
    params.set("sort", currentSort.key);
    params.set("dir", currentSort.direction);

    const nextUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, "", nextUrl);
    updateProjectLinks();
  }

  function updateFilterButtons() {
    filterButtons.forEach((item) => {
      const itemFilter = item.dataset.statusFilter;
      const active = itemFilter === "all"
        ? activeFilters.size === 0
        : activeFilters.has(itemFilter);
      item.classList.toggle("is-active", active);
      item.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function updateProjectLinks() {
    const from = `${window.location.pathname}${window.location.search}`;
    projectLinks.forEach((link) => {
      const url = new URL(link.getAttribute("href"), window.location.origin);
      url.searchParams.set("from", from);
      link.href = `${url.pathname}${url.search}`;
    });
  }

  function applyCompactLabels() {
    rows.forEach((row) => {
      const statusTag = row.querySelector(".tag-status");
      if (statusTag && statusLabels[row.dataset.status]) {
        statusTag.textContent = statusLabels[row.dataset.status];
      }
    });
  }

  function sortValue(row, key) {
    if (key === "status") return statusRank[row.dataset.status] || 99;
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
      const defaultDirection = ["name", "status"].includes(key) ? "asc" : "desc";
      currentSort = {
        key,
        direction: currentSort.key === key && currentSort.direction === defaultDirection
          ? (defaultDirection === "asc" ? "desc" : "asc")
          : defaultDirection,
      };
      updateOverviewUrl();
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

      updateFilterButtons();
      updateOverviewUrl();
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
  readOverviewState();
  updateFilterButtons();
  updateProjectLinks();
  render();
})();
