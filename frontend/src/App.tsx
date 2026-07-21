import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { AuthProvider, useAuth } from "@/hooks/use-auth"
import { ThemeProvider } from "@/hooks/use-theme"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { Layout } from "@/components/layout/Layout"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { Login } from "@/pages/Login"
import { FeedbackForm } from "@/pages/FeedbackForm"
import { PollResults } from "@/pages/PollResults"
import { VoteLog } from "@/pages/VoteLog"
import { BotStatus } from "@/pages/BotStatus"
import { WorkshopSchedule } from "@/pages/WorkshopSchedule"
import { LiveControl } from "@/pages/LiveControl"
import { TourCreate } from "@/pages/TourCreate"

function AnimatedPage({ children }: { children: React.ReactNode }) {
  const prefersReduced = useReducedMotion()
  const variants = prefersReduced
    ? { initial: {}, animate: {}, exit: {} }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -8 },
      }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        variants={variants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ duration: 0.2 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

function DashboardRoutes() {
  return (
    <Layout>
      <ErrorBoundary>
        <AnimatedPage>
          <Routes>
            <Route path="/polls" element={<PollResults />} />
            <Route path="/votes" element={<VoteLog />} />
            <Route path="/bot-status" element={<BotStatus />} />
            <Route path="/schedule" element={<WorkshopSchedule />} />
            <Route path="/live-control" element={<LiveControl />} />
            <Route path="/tours" element={<TourCreate />} />
            <Route path="*" element={<Navigate to="/polls" replace />} />
          </Routes>
        </AnimatedPage>
      </ErrorBoundary>
    </Layout>
  )
}

function AppRoutes() {
  const { isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/feedback/:tourId" element={<FeedbackForm />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <DashboardRoutes />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
