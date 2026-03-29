/* notepad C:\Users\Owner\nova\static\css\nova-main.css */

/* desktop open/close state support */
.nova-app-shell.sidebar-closed {
  grid-template-columns: 0 minmax(0, 1fr) var(--rail-w);
}

.nova-app-shell.sidebar-closed .nova-sidebar {
  width: 0;
  min-width: 0;
  padding-left: 0;
  padding-right: 0;
  border-right: 0;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

.nova-app-shell.rail-closed {
  grid-template-columns: var(--sidebar-w) minmax(0, 1fr) 0;
}

.nova-app-shell.rail-closed .nova-right-rail {
  width: 0;
  min-width: 0;
  padding-left: 0;
  padding-right: 0;
  border-left: 0;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

.nova-app-shell.sidebar-closed.rail-closed {
  grid-template-columns: 0 minmax(0, 1fr) 0;
}

@media (max-width: 980px) {
  .nova-app-shell.sidebar-closed {
    grid-template-columns: minmax(0, 1fr);
  }

  .nova-app-shell.rail-closed {
    grid-template-columns: minmax(0, 1fr);
  }

  .nova-app-shell.sidebar-closed .nova-sidebar,
  .nova-app-shell.rail-closed .nova-right-rail {
    opacity: 1;
  }
}