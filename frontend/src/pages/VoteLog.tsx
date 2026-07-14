import { useCallback, useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { api } from "@/api/client"
import type { PaginatedVotes } from "@/api/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { usePolling } from "@/hooks/use-polling"
import { Download, RefreshCw, AlertCircle, ClipboardList, ChevronLeft, ChevronRight } from "lucide-react"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000"
const PAGE_SIZE = 25

type State =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: PaginatedVotes }

function TableSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
      <Skeleton className="h-10 w-full" />
    </div>
  )
}

const rowVariants = {
  hidden: { opacity: 0, x: -8 },
  visible: { opacity: 1, x: 0 },
}

function formatTimestamp(ts: string) {
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

export function VoteLog() {
  const [state, setState] = useState<State>({ status: "loading" })
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const searchRef = useRef<HTMLInputElement>(null)

  const fetchVotes = useCallback(async (p: number, q: string, options?: { silent?: boolean }) => {
    try {
      const params = new URLSearchParams({ page: String(p), limit: String(PAGE_SIZE) })
      if (q.trim()) {
        params.set("username", q.trim())
      }
      const data = await api.get<PaginatedVotes>(`/api/votes?${params}`)
      if (data.votes.length === 0) {
        setState({ status: "empty" })
      } else {
        setState({ status: "loaded", data })
      }
    } catch (err) {
      setState((prev) => {
        if (options?.silent && prev.status === "loaded") return prev
        return { status: "error", message: err instanceof Error ? err.message : "Failed to load votes" }
      })
    }
  }, [])

  useEffect(() => {
    fetchVotes(page, search)
  }, [page, search, fetchVotes])

  const hasActiveSearch = search.trim().length > 0
  usePolling(
    () => fetchVotes(page, search, { silent: true }),
    undefined,
    !hasActiveSearch,
  )

  const handleSearch = () => {
    setPage(1)
    setSearch(searchRef.current?.value ?? "")
  }

  const handleExport = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/export/csv`)
      if (!resp.ok) throw new Error("Export failed")
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "poll_feedback.csv"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setState({ status: "error", message: err instanceof Error ? err.message : "Export failed" })
    }
  }

  if (state.status === "loading") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold font-display">Vote Log</h1>
        </div>
        <TableSkeleton />
      </div>
    )
  }

  if (state.status === "error") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold font-display">Vote Log</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <p className="text-center text-muted-foreground">{state.message}</p>
            <Button onClick={() => fetchVotes(page, search)}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (state.status === "empty") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold font-display">Vote Log</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <ClipboardList className="h-12 w-12 text-muted-foreground" />
            <p className="text-center text-muted-foreground">
              {search.trim() ? "No votes match your search." : "No votes recorded yet."}
            </p>
            <Button variant="outline" onClick={() => fetchVotes(page, search)}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { data } = state

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Vote Log</h1>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      <div className="flex gap-2">
        <label htmlFor="vote-search" className="sr-only">Search by username</label>
        <Input
          id="vote-search"
          ref={searchRef}
          placeholder="Search by username…"
          defaultValue={search}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="max-w-xs"
        />
        <Button variant="secondary" size="sm" onClick={handleSearch}>Search</Button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 font-medium">Timestamp</th>
                <th className="text-left p-3 font-medium">Username</th>
                <th className="text-left p-3 font-medium">Question</th>
                <th className="text-left p-3 font-medium">Choice</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence mode="popLayout">
                {data.votes.map((vote, idx) => (
                  <motion.tr
                    key={`${vote.timestamp}-${vote.user_id}-${idx}`}
                    variants={rowVariants}
                    initial="hidden"
                    animate="visible"
                    exit="hidden"
                    transition={{ duration: 0.2, delay: idx * 0.02 }}
                    className="border-b last:border-0 hover:bg-muted/30 focus-visible:bg-muted/50 outline-none transition-colors"
                    tabIndex={0}
                  >
                    <td className="p-3 text-muted-foreground whitespace-nowrap">{formatTimestamp(vote.timestamp)}</td>
                    <td className="p-3">{vote.username}</td>
                    <td className="p-3 max-w-xs truncate">{vote.question}</td>
                    <td className="p-3 font-medium">{vote.choice}</td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex items-center justify-between text-sm">
        <p className="text-muted-foreground">
          Page {data.page} of {data.total_pages} ({data.total} total)
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            aria-label="Previous page"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.total_pages}
            aria-label="Next page"
            onClick={() => setPage((p) => p + 1)}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
