import { useCallback, useEffect, useState } from "react"
import { motion } from "framer-motion"
import { api } from "@/api/client"
import type { BotStatusData, DataStatus } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { usePolling } from "@/hooks/use-polling"
import { RefreshCw, AlertCircle, Activity, Database } from "lucide-react"

interface BotPageData {
  bot: BotStatusData
  storage: DataStatus
}

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: BotPageData }

function StatCard({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
      <Card>
        <CardContent className="flex items-center gap-4 py-4">
          <div className="rounded-full bg-primary/10 p-2">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-xl font-bold">{value}</p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function StatSkeleton() {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-4">
        <Skeleton className="h-9 w-9 rounded-full" />
        <div className="space-y-1">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-5 w-16" />
        </div>
      </CardContent>
    </Card>
  )
}

export function BotStatus() {
  const [state, setState] = useState<State>({ status: "loading" })

  const fetchData = useCallback(async (options?: { silent?: boolean }) => {
    try {
      const [bot, storage] = await Promise.all([
        api.get<BotStatusData>("/api/bot-status"),
        api.get<DataStatus>("/api/data/status"),
      ])
      setState({ status: "loaded", data: { bot, storage } })
    } catch (err) {
      setState((prev) => {
        if (options?.silent && prev.status === "loaded") return prev
        return { status: "error", message: err instanceof Error ? err.message : "Failed to load status" }
      })
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  usePolling(() => fetchData({ silent: true }))

  if (state.status === "loading") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Bot Status</h1>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatSkeleton />
          <StatSkeleton />
          <StatSkeleton />
        </div>
      </div>
    )
  }

  if (state.status === "error") {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Bot Status</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <p className="text-center text-muted-foreground">{state.message}</p>
            <Button onClick={() => fetchData()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { bot, storage } = state.data

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Bot Status</h1>
        <Button variant="outline" size="sm" onClick={() => fetchData()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <motion.div layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`h-3 w-3 rounded-full ${bot.online ? "bg-emerald-500" : "bg-destructive"}`} />
              <CardTitle>Discord Bot</CardTitle>
            </div>
            <Badge variant={bot.online ? "success" : "destructive"}>
              {bot.online ? "Online" : "Offline"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Uptime" value={bot.uptime} icon={Activity} />
              <StatCard label="Latency" value={`${bot.latency_ms}ms`} icon={Activity} />
              <StatCard label="Total Votes" value={String(bot.votes_total)} icon={Activity} />
              <StatCard label="Today's Votes" value={String(bot.votes_today)} icon={Activity} />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3, delay: 0.1 }}>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Database className="h-5 w-5 text-primary" />
              <CardTitle>Data Storage</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard label="Records" value={String(storage.total_records)} icon={Database} />
              <StatCard label="Engine" value={storage.storage} icon={Database} />
              <StatCard label="Status" value={storage.status === "healthy" ? "Healthy" : "Unhealthy"} icon={Database} />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Last activity: {storage.last_timestamp !== "N/A" ? new Date(storage.last_timestamp).toLocaleString() : "N/A"}
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
