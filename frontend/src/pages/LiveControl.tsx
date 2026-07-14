import { useCallback, useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { api } from "@/api/client"
import type { Poll, DiscordChannel, DiscordRole, CreatePollPayload } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { usePolling } from "@/hooks/use-polling"
import { RefreshCw, AlertCircle, Send, Plus, X } from "lucide-react"

interface ActivePoll extends Poll {
  active: boolean
  poll_id: number
}

type PollsState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "loaded"; polls: ActivePoll[] }

type FormFields = {
  question: string
  description: string
  channelId: string
  options: string[]
  roleIds: number[]
  maxVotes: string
}

const initialForm: FormFields = {
  question: "",
  description: "",
  channelId: "",
  options: ["", ""],
  roleIds: [],
  maxVotes: "",
}

function ActivePollsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-lg border p-3 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/4" />
        </div>
      ))}
    </div>
  )
}

export function LiveControl() {
  const [form, setForm] = useState<FormFields>(initialForm)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [channels, setChannels] = useState<DiscordChannel[]>([])
  const [roles, setRoles] = useState<DiscordRole[]>([])
  const [pollsState, setPollsState] = useState<PollsState>({ status: "loading" })

  const fetchData = useCallback(async () => {
    try {
      const [ch, rl] = await Promise.all([
        api.get<DiscordChannel[]>("/api/discord/channels"),
        api.get<DiscordRole[]>("/api/discord/roles"),
      ])
      setChannels(ch)
      setRoles(rl)
    } catch {
      // non-critical
    }
  }, [])

  const fetchPolls = useCallback(async (options?: { silent?: boolean }) => {
    try {
      const polls = await api.get<ActivePoll[]>("/api/polls")
      const active = polls.filter((p) => p.active !== false)
      if (active.length === 0) {
        setPollsState({ status: "empty" })
      } else {
        setPollsState({ status: "loaded", polls: active })
      }
    } catch (err) {
      setPollsState((prev) => {
        if (options?.silent && prev.status === "loaded") return prev
        return { status: "error", message: err instanceof Error ? err.message : "Failed to load polls" }
      })
    }
  }, [])

  useEffect(() => {
    fetchData()
    fetchPolls()
  }, [fetchData, fetchPolls])

  usePolling(() => fetchPolls({ silent: true }))

  function setOption(idx: number, value: string) {
    setForm((f) => {
      const opts = [...f.options]
      opts[idx] = value
      return { ...f, options: opts }
    })
  }

  function addOption() {
    setForm((f) => {
      if (f.options.length >= 5) return f
      return { ...f, options: [...f.options, ""] }
    })
  }

  function removeOption(idx: number) {
    setForm((f) => {
      if (f.options.length <= 2) return f
      const opts = f.options.filter((_, i) => i !== idx)
      return { ...f, options: opts }
    })
  }

  function toggleRole(id: number) {
    setForm((f) => {
      const has = f.roleIds.includes(id)
      return {
        ...f,
        roleIds: has ? f.roleIds.filter((r) => r !== id) : [...f.roleIds, id],
      }
    })
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmedOpts = form.options.map((o) => o.trim()).filter(Boolean)
    if (!form.question.trim()) {
      setResult({ ok: false, message: "Question is required." })
      return
    }
    if (trimmedOpts.length < 2) {
      setResult({ ok: false, message: "At least 2 options are required." })
      return
    }

    setSubmitting(true)
    setResult(null)
    try {
      const payload: CreatePollPayload = {
        question: form.question.trim(),
        options: trimmedOpts,
      }
      if (form.description.trim()) payload.description = form.description.trim()
      if (form.channelId) payload.channel_id = Number(form.channelId)
      if (form.roleIds.length > 0) payload.role_ids = form.roleIds
      if (form.maxVotes) payload.max_votes_per_option = Number(form.maxVotes)

      await api.post("/api/polls/create", payload)
      setResult({ ok: true, message: "Poll created successfully!" })
      setForm(initialForm)
      fetchPolls()
    } catch (err) {
      setResult({ ok: false, message: err instanceof Error ? err.message : "Failed to create poll" })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold font-display">Live Control</h1>
        <Button variant="outline" size="sm" onClick={() => { fetchData(); fetchPolls() }}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Create Poll */}
        <Card>
          <CardHeader>
            <CardTitle>Create Poll</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="poll-question" className="text-sm font-medium mb-1 block">Question *</label>
                <Input
                  id="poll-question"
                  value={form.question}
                  onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))}
                  placeholder="Poll question"
                  maxLength={200}
                />
              </div>

              <div>
                <label htmlFor="poll-description" className="text-sm font-medium mb-1 block">Description</label>
                <textarea
                  id="poll-description"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Description shown on the Discord embed (optional)"
                  className="flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
                  maxLength={1000}
                />
              </div>

              <div>
                <label htmlFor="poll-channel" className="text-sm font-medium mb-1 block">Channel</label>
                <select
                  id="poll-channel"
                  value={form.channelId}
                  onChange={(e) => setForm((f) => ({ ...f, channelId: e.target.value }))}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="">Default Channel</option>
                  {channels.map((ch) => (
                    <option key={ch.id} value={ch.id}>{ch.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">Options *</label>
                <div className="space-y-2">
                  {form.options.map((opt, idx) => (
                    <div key={idx} className="flex gap-2">
                      <Input
                        value={opt}
                        onChange={(e) => setOption(idx, e.target.value)}
                        placeholder={`Option ${idx + 1}`}
                        maxLength={100}
                        className="flex-1"
                      />
                      {form.options.length > 2 && (
                        <Button type="button" variant="ghost" size="icon" aria-label={`Remove option ${idx + 1}`} onClick={() => removeOption(idx)}>
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between mt-2">
                  <Button type="button" variant="outline" size="sm" onClick={addOption} disabled={form.options.length >= 5}>
                    <Plus className="mr-1 h-4 w-4" />
                    Add Option
                  </Button>
                  <span className="text-xs text-muted-foreground">{form.options.length} / 5</span>
                </div>
              </div>

              {roles.length > 0 && (
                <div>
                  <label className="text-sm font-medium mb-1 block">Role Mentions</label>
                  <div className="flex flex-wrap gap-2">
                    {roles.map((role) => (
                      <button
                        key={role.id}
                        type="button"
                        aria-pressed={form.roleIds.includes(Number(role.id))}
                        onClick={() => toggleRole(Number(role.id))}
                        className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                          ${form.roleIds.includes(Number(role.id))
                            ? "border-transparent bg-primary text-primary-foreground shadow"
                            : "text-foreground"
                          }`}
                      >
                        @{role.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label htmlFor="poll-max-votes" className="text-sm font-medium mb-1 block">Max Votes Per Option</label>
                <Input
                  id="poll-max-votes"
                  type="number"
                  value={form.maxVotes}
                  onChange={(e) => setForm((f) => ({ ...f, maxVotes: e.target.value }))}
                  placeholder="Unlimited"
                  min={1}
                />
              </div>

              <Button type="submit" disabled={submitting} className="w-full">
                <Send className="mr-2 h-4 w-4" />
                {submitting ? "Creating..." : "Create Poll"}
              </Button>

              {result && (
                <p className={`text-sm ${result.ok ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"}`}>
                  {result.message}
                </p>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Active Polls */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Active Polls</CardTitle>
              <Button variant="ghost" size="sm" aria-label="Refresh polls" onClick={() => fetchPolls()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {pollsState.status === "loading" && (
              <ActivePollsSkeleton />
            )}
            {pollsState.status === "error" && (
              <div className="flex flex-col items-center gap-3 py-8">
                <AlertCircle className="h-8 w-8 text-destructive" />
                <p className="text-sm text-muted-foreground text-center">{pollsState.message}</p>
                <Button variant="outline" size="sm" onClick={() => fetchPolls()}>Retry</Button>
              </div>
            )}
            {pollsState.status === "empty" && (
              <p className="text-sm text-muted-foreground">No active polls.</p>
            )}
            {pollsState.status === "loaded" && (
              <AnimatePresence mode="popLayout">
                <motion.div className="space-y-3" layout>
                  {pollsState.polls.map((poll) => (
                    <motion.div
                      key={poll.poll_id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      layout
                    >
                      <div
                        className="rounded-lg border p-3 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors"
                        tabIndex={0}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium leading-snug">{poll.question}</p>
                          <Badge variant="success">Live</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {poll.total_votes} vote{poll.total_votes !== 1 ? "s" : ""}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              </AnimatePresence>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
