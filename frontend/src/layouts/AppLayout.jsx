import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopNavbar from './TopNavbar'

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="app-layout">
      {/* Role-Aware Collapsible Sidebar */}
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      {/* Main Viewport */}
      <main className="app-main">
        {/* Top Header Navbar */}
        <TopNavbar />

        {/* Dynamic Route Content */}
        <div className="page-content-wrapper">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
