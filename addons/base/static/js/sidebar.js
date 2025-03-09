import {select, on} from "./helpers.js";

export const Sidebar = (() => {
  /**
   * Toggle Sidebar States
   */
  const toggleSidebarState = () => {
    // TODO: update to store preference to signed in user
    let sidebarState = localStorage.getItem("sidebarState") || "open";

    // Cycle through states: open -> icons-only -> close
    if (sidebarState === "close") {
      sidebarState = "open"
    } else if (sidebarState === "open") {
      sidebarState = "icons-only"
    } else if (sidebarState === "icons-only") {
      sidebarState = "close"
    }
    localStorage.setItem("sidebarState", sidebarState);
    applySidebarClasses();
  }

  /**
   * Apply Sidebar Classes
   */
  const applySidebarClasses = () => {
    let sidebarState = localStorage.getItem("sidebarState") || "open";
    const icon = select('.icon-sidebar-toggle');
    const sidebar = select('.sidebar');
    if (icon && sidebar) {
      icon.classList.toggle("fa-bars-staggered", sidebarState === "open");
      icon.classList.toggle("fa-bars", sidebarState === "icons-only");
      icon.classList.toggle("fa-not-equal", sidebarState === "close");

      sidebar.classList.toggle("sidebar-close", sidebarState === "close");
      sidebar.classList.toggle("sidebar-open", sidebarState === "open");
      sidebar.classList.toggle("sidebar-icons-only", sidebarState === "icons-only");
    }
  };

  /**
   * Click Sidebar Toggle Event
   */
  const init = () => {
    if (select('.icon-sidebar-toggle')) {
      on('click', '.icon-sidebar-toggle', toggleSidebarState)
    }

    window.addEventListener('DOMContentLoaded', applySidebarClasses)
  }

  return {
    init,
    toggleSidebarState,
    applySidebarClasses
  };
})();
