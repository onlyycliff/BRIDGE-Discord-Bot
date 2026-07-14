import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AlertCircle } from "lucide-react"

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    const err = await login(email, password)
    if (err) {
      setError(err)
      setSubmitting(false)
    } else {
      navigate("/", { replace: true })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 font-body">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25 }}
        className="w-full max-w-[380px] bg-card border border-border rounded-2xl p-8"
      >
        <h1 className="text-xl font-bold font-display mb-1">Coach Login</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Sign in to access the Bridge 2026 dashboard
        </p>

        {error && (
          <div className="flex items-center gap-2 bg-destructive/10 text-destructive px-4 py-3 rounded-lg text-xs mb-4" role="alert">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="coach@bridge2026.org"
              autoComplete="email"
              required
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="password" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
              Password
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password…"
              autoComplete="current-password"
              required
            />
          </div>

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Signing in…" : "Sign In"}
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Bridge 2026 VII &middot; Coach Dashboard
        </p>
      </motion.div>
    </div>
  )
}
