import React, { useState } from "react"
import { Layout } from "@/components/layout/Layout"
import { PollResults } from "@/pages/PollResults"
import { VoteLog } from "@/pages/VoteLog"
import { BotStatus } from "@/pages/BotStatus"
import { WorkshopSchedule } from "@/pages/WorkshopSchedule"
import { LiveControl } from "@/pages/LiveControl"
import { useTheme } from "@/hooks/use-theme"

type Page = "polls" | "votes" | "bot-status" | "schedule" | "live-control"

const pageComponents: Record<Page, () => React.ReactElement> = {
  polls: PollResults,
  votes: VoteLog,
  "bot-status": BotStatus,
  schedule: WorkshopSchedule,
  "live-control": LiveControl,
}

export default function App() {
  useTheme()
  const [activePage, setActivePage] = useState<Page>("polls")

  const PageComponent = pageComponents[activePage]

  return (
    <Layout activePath={`/${activePage}`} onNavigate={(path) => setActivePage(path.slice(1) as Page)}>
      <PageComponent />
    </Layout>
  )
}
