import { useLocation } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"
import { ThemeToggle } from "./ThemeToggle"
import { Button } from "@/components/ui/button"
import { LogOut } from "lucide-react"

const navItems = [
  { path: "/polls", label: "Polls" },
  { path: "/votes", label: "Votes" },
  { path: "/bot-status", label: "Status" },
  { path: "/schedule", label: "Schedule" },
  { path: "/live-control", label: "Control" },
]

export function NavBar() {
  const { pathname } = useLocation()
  const { logout } = useAuth()

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background">
      <div className="mx-auto max-w-7xl px-4 md:px-6">
        <div className="flex h-12 items-center justify-between">
          <div className="font-display font-bold text-lg tracking-tight">
            <span className="text-primary">Bridge</span>
            <span className="text-emerald-400 ml-1">2026</span>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
              <LogOut className="h-4 w-4" />
            </Button>
            <ThemeToggle />
          </div>
        </div>

        <nav aria-label="Main navigation" className="relative pb-3">
          <div
            className="absolute bottom-[18px] left-0 right-0 h-[2px] rounded-full"
            style={{ background: "var(--gradient-bridge)", opacity: 0.35 }}
          />

          <div className="flex items-end justify-between relative">
            {navItems.map((item) => {
              const isActive = pathname === item.path
              return (
                <a
                  key={item.path}
                  href={item.path}
                  aria-current={isActive ? "page" : undefined}
                  className="flex flex-col items-center gap-1.5 relative z-10 group px-2"
                >
                  <div
                    className={`w-2 h-2 rounded-full transition-all duration-200 ${
                      isActive
                        ? "bg-primary scale-150 shadow-[0_0_8px_rgba(129,140,248,0.6)]"
                        : "bg-border group-hover:bg-primary/50"
                    }`}
                  />
                  <span
                    className={`text-[11px] font-medium tracking-wide transition-colors duration-200 ${
                      isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                    }`}
                  >
                    {item.label}
                  </span>
                </a>
              )
            })}
          </div>
        </nav>
      </div>
    </header>
  )
}
