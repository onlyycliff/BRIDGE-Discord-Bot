import { BarChart3, ClipboardList, Bot, Calendar, PlayCircle } from "lucide-react"
import { ThemeToggle } from "./ThemeToggle"

const navItems = [
  { path: "/polls", label: "Poll Results", icon: BarChart3 },
  { path: "/votes", label: "Vote Log", icon: ClipboardList },
  { path: "/bot-status", label: "Bot Status", icon: Bot },
  { path: "/schedule", label: "Schedule", icon: Calendar },
  { path: "/live-control", label: "Live Control", icon: PlayCircle },
]

interface NavBarProps {
  activePath: string
  onNavigate: (path: string) => void
}

export function NavBar({ activePath, onNavigate }: NavBarProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 gap-4">
        <div className="font-bold text-lg mr-4">
          <span className="text-primary-violet-500">Bridge</span>
          <span className="text-primary-emerald-500"> 2026</span>
        </div>
        <nav className="flex items-center gap-1 flex-1 overflow-x-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activePath === item.path
            return (
              <button
                key={item.path}
                onClick={() => onNavigate(item.path)}
                className={`inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                  ${isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                  }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            )
          })}
        </nav>
        <ThemeToggle />
      </div>
    </header>
  )
}
