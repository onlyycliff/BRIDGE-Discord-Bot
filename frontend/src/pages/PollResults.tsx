import { useCallback, useEffect, useState } from "react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts"
import { motion } from "framer-motion"
import { api } from "@/api/client"
import type { Poll } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { usePolling } from "@/hooks/use-polling"
import { RefreshCw, AlertCircle, BarChart3 } from "lucide-react"

type State =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "loaded"; polls: Poll[] }

const COLORS = ["#6366F1", "#22C55E", "#EC4899", "#F59E0B", "#06B6D4"]

function chartColor(index: number): string {
  return COLORS[index % COLORS.length]
}

function PollCard({ poll }: { poll: Poll }) {
  const totalVotes = poll.options.reduce((s, o) => s + o.votes, 0)
  const data = poll.options.map((o) => ({ name: o.name, votes: o.votes }))

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25 }}
    >
      <Card className="overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base leading-snug">{poll.question}</CardTitle>
            <Badge variant={poll.active !== false ? "success" : "secondary"}>
              {poll.active !== false ? "Live" : "Ended"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis type="number" className="text-xs fill-muted-foreground" />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={100}
                  className="text-xs fill-muted-foreground"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "var(--radius)",
                    fontSize: "0.875rem",
                  }}
                />
                <Bar dataKey="votes" radius={[0, 4, 4, 0]} maxBarSize={24} animationDuration={400}>
                  {data.map((_, idx) => (
                    <Cell key={idx} fill={chartColor(idx)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {totalVotes} total vote{totalVotes !== 1 ? "s" : ""}
          </p>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function PollSkeleton() {
  return (
    <div className="space-y-3 p-6 border rounded-xl">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-4 w-1/3" />
    </div>
  )
}

export function PollResults() {
  const [state, setState] = useState<State>({ status: "loading" })

  const fetchPolls = useCallback(async (options?: { silent?: boolean }) => {
    try {
      const polls = await api.get<Poll[]>("/api/polls")
      if (polls.length === 0) {
        setState({ status: "empty" })
      } else {
        setState({ status: "loaded", polls })
      }
    } catch (err) {
      setState((prev) => {
        if (options?.silent && prev.status === "loaded") return prev
        return { status: "error", message: err instanceof Error ? err.message : "Failed to load polls" }
      })
    }
  }, [])

  useEffect(() => {
    fetchPolls()
  }, [fetchPolls])

  usePolling(() => fetchPolls({ silent: true }))

  if (state.status === "loading") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Poll Results</h1>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <PollSkeleton />
          <PollSkeleton />
        </div>
      </div>
    )
  }

  if (state.status === "error") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Poll Results</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <p className="text-center text-muted-foreground">{state.message}</p>
            <Button onClick={() => fetchPolls()}>
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
          <h1 className="text-2xl font-bold">Poll Results</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <BarChart3 className="h-12 w-12 text-muted-foreground" />
            <p className="text-center text-muted-foreground">
              No polls yet. Create one from the Live Control panel or Discord.
            </p>
            <Button variant="outline" onClick={() => fetchPolls()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { polls } = state

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Poll Results</h1>
        <Button variant="outline" size="sm" onClick={() => fetchPolls()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>
      <motion.div className="grid gap-4 md:grid-cols-2" layout>
        {polls.map((poll) => (
          <PollCard key={poll.poll_id} poll={poll} />
        ))}
      </motion.div>
    </div>
  )
}
