import type { PropsWithChildren } from "react"
import { NavBar } from "./NavBar"

interface LayoutProps {
  hideNav?: boolean
}

export function Layout({ children, hideNav }: PropsWithChildren<LayoutProps>) {
  return (
    <div className="min-h-screen flex flex-col font-body">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[9999] focus:p-4 focus:bg-background focus:text-foreground">
        Skip to main content
      </a>
      {!hideNav && <NavBar />}
      <main id="main-content" className="flex-1 p-4 md:p-6">
        <div className="mx-auto max-w-7xl">
          {children}
        </div>
      </main>
      <footer className="border-t border-border/50 py-4 px-6 text-center text-xs text-muted-foreground">
        Bridge 2026 Dashboard
      </footer>
    </div>
  )
}
