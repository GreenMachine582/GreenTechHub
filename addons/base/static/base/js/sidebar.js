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
    const sidebarState = localStorage.getItem("sidebarState") || "open";
    const icon = select('.icon-sidebar-toggle');
    const body = document.body;

    // Update the sidebar toggle icon
    if (icon) {
      icon.classList.toggle("fa-bars-staggered", sidebarState === "open");
      icon.classList.toggle("fa-bars", sidebarState === "icons-only");
      icon.classList.toggle("fa-not-equal", sidebarState === "close");
    }

    // Apply sidebar state classes to <body>
    if (body) {
      body.classList.remove("sidebar-open", "sidebar-icons-only", "sidebar-close");

      switch (sidebarState) {
        case "open":
          body.classList.add("sidebar-open");
          break;
        case "icons-only":
          body.classList.add("sidebar-icons-only");
          break;
        case "close":
          body.classList.add("sidebar-close");
          break;
      }
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
