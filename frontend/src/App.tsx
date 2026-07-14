import React, { useCallback, useEffect, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { Layout } from "@/components/layout/Layout"
import { PollResults } from "@/pages/PollResults"
import { VoteLog } from "@/pages/VoteLog"
import { BotStatus } from "@/pages/BotStatus"
import { WorkshopSchedule } from "@/pages/WorkshopSchedule"
import { LiveControl } from "@/pages/LiveControl"
import { useTheme } from "@/hooks/use-theme"

type Page = "polls" | "votes" | "bot-status" | "schedule" | "live-control"

const VALID_PAGES: Page[] = ["polls", "votes", "bot-status", "schedule", "live-control"]

function getPageFromURL(): Page {
  const hash = window.location.hash.replace("#/", "").replace("#", "")
  if (VALID_PAGES.includes(hash as Page)) return hash as Page
  return "polls"
}

const pageComponents: Record<Page, () => React.ReactElement> = {
  polls: PollResults,
  votes: VoteLog,
  "bot-status": BotStatus,
  schedule: WorkshopSchedule,
  "live-control": LiveControl,
}

export default function App() {
  useTheme()
  const [activePage, setActivePage] = useState<Page>(getPageFromURL)
  const prefersReduced = useReducedMotion()

  const handleNavigate = useCallback((page: Page) => {
    setActivePage(page)
    window.location.hash = `/${page}`
  }, [])

  useEffect(() => {
    function onHashChange() {
      setActivePage(getPageFromURL())
    }
    window.addEventListener("hashchange", onHashChange)
    return () => window.removeEventListener("hashchange", onHashChange)
  }, [])

  const PageComponent = pageComponents[activePage]

  const variants = prefersReduced
    ? { initial: {}, animate: {}, exit: {} }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -8 },
      }

  return (
    <Layout activePath={`/${activePage}`} onNavigate={(path) => handleNavigate(path.slice(1) as Page)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={activePage}
          variants={variants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{ duration: 0.2 }}
        >
          <PageComponent />
        </motion.div>
      </AnimatePresence>
    </Layout>
  )
}
