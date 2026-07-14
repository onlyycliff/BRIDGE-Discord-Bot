import type { PropsWithChildren } from "react"
import { NavBar } from "./NavBar"

interface LayoutProps {
  activePath: string
  onNavigate: (path: string) => void
}

export function Layout({ children, activePath, onNavigate }: PropsWithChildren<LayoutProps>) {
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[9999] focus:p-4 focus:bg-background focus:text-foreground">
        Skip to main content
      </a>
      <NavBar activePath={activePath} onNavigate={onNavigate} />
      <main id="main-content" className="flex-1 p-4 md:p-6">
        <div className="mx-auto max-w-7xl">
          {children}
        </div>
      </main>
      <footer className="border-t py-4 px-6 text-center text-xs text-muted-foreground">
        Bridge 2026 Dashboard
      </footer>
    </div>
  )
}
