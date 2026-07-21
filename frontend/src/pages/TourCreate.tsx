import { useCallback, useEffect, useState } from "react"
import { motion, AnimatePresence, type Variants } from "framer-motion"
import { api } from "@/api/client"
import type { Tour, CreateTourPayload, CreateTourResponse, DiscordChannel } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Send, Copy, Check, ExternalLink, MapPin } from "lucide-react"

type ToursState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "loaded"; tours: Tour[] }

type FormFields = {
  name: string
  date: string
  company: string
}

const initialForm: FormFields = {
  name: "",
  date: "",
  company: "",
}

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
}

export function TourCreate() {
  const [form, setForm] = useState<FormFields>(initialForm)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string; tour?: CreateTourResponse } | null>(null)
  const [toursState, setToursState] = useState<ToursState>({ status: "loading" })
  const [channels, setChannels] = useState<DiscordChannel[]>([])
  const [selectedChannel, setSelectedChannel] = useState("")
  const [sending, setSending] = useState(false)
  const [copied, setCopied] = useState(false)

  const fetchTours = useCallback(async () => {
    try {
      const tours = await api.get<Tour[]>("/api/tours")
      if (tours.length === 0) {
        setToursState({ status: "empty" })
      } else {
        setToursState({ status: "loaded", tours })
      }
    } catch (err) {
      setToursState({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load tours",
      })
    }
  }, [])

  const fetchChannels = useCallback(async () => {
    try {
      const ch = await api.get<DiscordChannel[]>("/api/discord/channels")
      setChannels(ch)
    } catch {
      // non-critical
    }
  }, [])

  useEffect(() => {
    fetchTours()
    fetchChannels()
  }, [fetchTours, fetchChannels])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) {
      setResult({ ok: false, message: "Tour name is required." })
      return
    }
    if (!form.date.trim()) {
      setResult({ ok: false, message: "Date is required." })
      return
    }
    if (!form.company.trim()) {
      setResult({ ok: false, message: "Company is required." })
      return
    }

    setSubmitting(true)
    setResult(null)
    try {
      const payload: CreateTourPayload = {
        name: form.name.trim(),
        date: form.date.trim(),
        company: form.company.trim(),
      }
      const tour = await api.post<CreateTourResponse>("/api/tours", payload)
      setResult({ ok: true, message: "Tour created with feedback form!", tour })
      setForm(initialForm)
      fetchTours()
    } catch (err) {
      setResult({ ok: false, message: err instanceof Error ? err.message : "Failed to create tour" })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSendToDiscord() {
    if (!result?.tour?.id || !selectedChannel) return
    setSending(true)
    try {
      await api.post(`/api/tours/${result.tour.id}/send-to-discord`, {
        channel_id: selectedChannel,
      })
      setResult((prev) => prev ? { ...prev, message: "Sent to Discord!" } : prev)
    } catch (err) {
      setResult((prev) => prev
        ? { ...prev, message: err instanceof Error ? err.message : "Failed to send to Discord" }
        : prev
      )
    } finally {
      setSending(false)
    }
  }

  function copyFormUrl() {
    if (!result?.tour?.google_form_url) return
    navigator.clipboard.writeText(result.tour.google_form_url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Tours</p>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold font-display">Tour Management</h1>
          <Button variant="outline" size="sm" onClick={fetchTours}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Create Tour */}
        <Card>
          <CardHeader>
            <CardTitle>Create Tour</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="tour-name" className="text-sm font-medium mb-1 block">Tour Name *</label>
                <Input
                  id="tour-name"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Acme Corp Visit"
                  maxLength={200}
                  list="existing-tours"
                />
                <datalist id="existing-tours">
                  {toursState.status === "loaded" &&
                    toursState.tours.map((t) => (
                      <option key={t.id} value={t.name} />
                    ))
                  }
                </datalist>
              </div>

              <div>
                <label htmlFor="tour-date" className="text-sm font-medium mb-1 block">Date *</label>
                <Input
                  id="tour-date"
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                />
              </div>

              <div>
                <label htmlFor="tour-company" className="text-sm font-medium mb-1 block">Company *</label>
                <Input
                  id="tour-company"
                  value={form.company}
                  onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                  placeholder="e.g. Acme Corp"
                  maxLength={200}
                />
              </div>

              <Button type="submit" disabled={submitting} className="w-full">
                <Send className="mr-2 h-4 w-4" />
                {submitting ? "Creating..." : "Create Feedback Form"}
              </Button>

              <AnimatePresence mode="wait">
                {result && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-3 overflow-hidden"
                  >
                    <p className={`text-sm ${result.ok ? "text-emerald-600 dark:text-emerald-400" : "text-destructive"}`}>
                      {result.message}
                    </p>

                    {result.ok && result.tour?.google_form_url && (
                      <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 space-y-3">
                        <div className="flex items-center gap-2">
                          <a
                            href={result.tour.google_form_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-primary hover:underline flex items-center gap-1 flex-1 min-w-0 truncate"
                          >
                            <ExternalLink className="h-4 w-4 shrink-0" />
                            {result.tour.google_form_url}
                          </a>
                          <Button variant="ghost" size="icon" onClick={copyFormUrl} aria-label="Copy form URL">
                            {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                          </Button>
                        </div>

                        <div className="flex gap-2">
                          <select
                            value={selectedChannel}
                            onChange={(e) => setSelectedChannel(e.target.value)}
                            className="flex h-9 flex-1 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                          >
                            <option value="">Select channel</option>
                            {channels.map((ch) => (
                              <option key={ch.id} value={ch.id}>{ch.name}</option>
                            ))}
                          </select>
                          <Button
                            size="sm"
                            disabled={!selectedChannel || sending}
                            onClick={handleSendToDiscord}
                          >
                            <Send className="mr-1 h-3 w-3" />
                            {sending ? "Sending..." : "Send to Discord"}
                          </Button>
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </form>
          </CardContent>
        </Card>

        {/* Existing Tours */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Existing Tours</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => fetchTours()}>
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {toursState.status === "loading" && (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="rounded-lg border p-3 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/4" />
                  </div>
                ))}
              </div>
            )}
            {toursState.status === "error" && (
              <p className="text-sm text-destructive">{toursState.message}</p>
            )}
            {toursState.status === "empty" && (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <MapPin className="h-8 w-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">No tours yet. Create one to start collecting feedback.</p>
              </div>
            )}
            {toursState.status === "loaded" && (
              <div className="space-y-3">
                <AnimatePresence>
                  {toursState.tours.map((tour, i) => (
                    <motion.div
                      key={tour.id}
                      custom={i}
                      variants={cardVariants}
                      initial="hidden"
                      animate="visible"
                      layout
                      className="rounded-lg border-l-2 border border-l-primary/60 bg-gradient-to-r from-primary/5 to-transparent p-3 transition-colors hover:from-primary/8"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium leading-snug">{tour.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {tour.company} {tour.date ? `\u2022 ${tour.date}` : ""}
                          </p>
                          {tour.google_form_url && (
                            <a
                              href={tour.google_form_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary hover:underline flex items-center gap-1 mt-1.5"
                            >
                              <ExternalLink className="h-3 w-3" />
                              Feedback Form
                            </a>
                          )}
                        </div>
                        {tour.feedback_count !== undefined && (
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {tour.feedback_count} response{tour.feedback_count !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
