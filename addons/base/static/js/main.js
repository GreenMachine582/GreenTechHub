(function() {
  "use strict";

  /**
   * Easy selector helper function
   */
  const select = (el, all = false) => {
    el = el.trim()
    if (all) {
      return [...document.querySelectorAll(el)]
    } else {
      return document.querySelector(el)
    }
  }

  /**
   * Easy event listener function
   */
  const on = (type, el, listener, all = false) => {
    if (all) {
      select(el, all).forEach(e => e.addEventListener(type, listener))
    } else {
      select(el, all).addEventListener(type, listener)
    }
  }

  /**
   * Easy on scroll event listener 
   */
  const onscroll = (el, listener) => {
    el.addEventListener('scroll', listener)
  }

  /**
   * Sidebar toggle
   */
  if (select('.icon-sidebar-toggle')) {
    on('click', '.icon-sidebar-toggle', function(e) {
      // TODO: update to store preference to signed in user
      let sidebarState = localStorage.getItem("sidebarState") || "open";

      // Determine new state after click action
      if (sidebarState === "close") {
        sidebarState = "open"
      } else if (sidebarState === "open") {
        sidebarState = "icons-only"
      } else if (sidebarState === "icons-only") {
        sidebarState = "close"
      }

      // Add classes for the CSS to dynamically adjust DOM/styles
      const icon = select('.icon-sidebar-toggle');
      const sidebar = select('.sidebar');
      icon.classList.toggle("fa-bars-staggered", sidebarState === "open")
      icon.classList.toggle("fa-bars", sidebarState === "icons-only")
      icon.classList.toggle("fa-not-equal", sidebarState === "close")
      sidebar.classList.toggle("sidebar-close", sidebarState === "close")
      sidebar.classList.toggle("sidebar-open", sidebarState === "open")
      sidebar.classList.toggle("sidebar-icons-only", sidebarState === "icons-only")
      localStorage.setItem("sidebarState", sidebarState);
    })
  }

  /**
   * Search bar toggle
   */
  if (select('.search-bar-toggle')) {
    on('click', '.search-bar-toggle', function(e) {
      select('.search-bar').classList.toggle('search-bar-show')
    })
  }

  /**
   * Navbar links active state on scroll
   */
  let navbarlinks = select('#navbar .scrollto', true)
  const navbarlinksActive = () => {
    let position = window.scrollY + 200
    navbarlinks.forEach(navbarlink => {
      if (!navbarlink.hash) return
      let section = select(navbarlink.hash)
      if (!section) return
      if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
        navbarlink.classList.add('active')
      } else {
        navbarlink.classList.remove('active')
      }
    })
  }
  window.addEventListener('load', navbarlinksActive)
  onscroll(document, navbarlinksActive)

  /**
   * Toggle .header-scrolled class to #header when page is scrolled
   */
  let selectHeader = select('#header')
  if (selectHeader) {
    const headerScrolled = () => {
      if (window.scrollY > 100) {
        selectHeader.classList.add('header-scrolled')
      } else {
        selectHeader.classList.remove('header-scrolled')
      }
    }
    window.addEventListener('load', headerScrolled)
    onscroll(document, headerScrolled)
  }

  /**
   * Back to top button
   */
  let backtotop = select('.back-to-top')
  if (backtotop) {
    const toggleBacktotop = () => {
      if (window.scrollY > 100) {
        backtotop.classList.add('active')
      } else {
        backtotop.classList.remove('active')
      }
    }
    window.addEventListener('load', toggleBacktotop)
    onscroll(document, toggleBacktotop)
  }

})();