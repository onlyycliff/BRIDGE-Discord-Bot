import { useCallback, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { motion } from "framer-motion"
import { api } from "@/api/client"
import type { Tour, FeedbackSubmitPayload } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckCircle, AlertCircle, Star } from "lucide-react"

export function FeedbackForm() {
  const { tourId } = useParams<{ tourId: string }>()
  const [tour, setTour] = useState<Tour | null>(null)
  const [tourLoading, setTourLoading] = useState(true)
  const [tourError, setTourError] = useState<string | null>(null)

  const [name, setName] = useState("")
  const [studentId, setStudentId] = useState("")
  const [rating, setRating] = useState<number | null>(null)
  const [hoveredStar, setHoveredStar] = useState<number | null>(null)
  const [comments, setComments] = useState("")

  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTour = useCallback(async () => {
    try {
      const data = await api.get<Tour>(`/api/tours/${tourId}`)
      setTour(data)
    } catch (err) {
      setTourError(err instanceof Error ? err.message : "Failed to load tour")
    } finally {
      setTourLoading(false)
    }
  }, [tourId])

  useEffect(() => {
    fetchTour()
  }, [fetchTour])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    const payload: FeedbackSubmitPayload = {
      tour_id: Number(tourId),
      student_name: name.trim() || "Anonymous",
      student_id: Number(studentId),
      rating,
      comments: comments.trim() || null,
    }

    try {
      await api.post("/api/feedback/submit", payload)
      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback")
      setSubmitting(false)
    }
  }

  if (tourLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-[480px] space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  if (tourError || !tour) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-[480px] bg-card border border-border rounded-2xl p-8 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <p className="text-muted-foreground">{tourError || "Tour not found"}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 font-body">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.25 }}
        className="w-full max-w-[480px] bg-card border border-border rounded-2xl p-8"
      >
        <h1 className="text-xl font-bold font-display mb-1">Tour Feedback</h1>
        <p className="text-sm text-muted-foreground mb-6">
          {tour.name} &middot; {tour.company}
          {tour.date && <><br />{new Date(tour.date).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}</>}
        </p>

        {submitted && (
          <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-4 py-4 rounded-lg text-sm mb-4">
            <CheckCircle className="h-5 w-5 shrink-0" />
            Thank you! Your feedback has been submitted.
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 bg-destructive/10 text-destructive px-4 py-3 rounded-lg text-xs mb-4" role="alert">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {!submitted && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="student_name" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
                Your Name <span className="text-destructive">*</span>
              </label>
              <Input
                id="student_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name…"
                autoComplete="name"
                required
              />
            </div>

            <div>
              <label htmlFor="student_id" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
                Student ID <span className="text-destructive">*</span>
              </label>
              <Input
                id="student_id"
                type="number"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="Discord user ID"
                autoComplete="off"
                required
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 block">
                Rating
              </label>
              <div className="flex gap-1" role="radiogroup" aria-label="Rating">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    role="radio"
                    aria-checked={rating === star}
                    aria-label={`${star} star${star !== 1 ? "s" : ""}`}
                    className="p-0.5 transition-colors"
                    onMouseEnter={() => setHoveredStar(star)}
                    onMouseLeave={() => setHoveredStar(null)}
                    onClick={() => setRating(star)}
                  >
                    <Star
                      className={`h-8 w-8 transition-colors ${
                        (hoveredStar !== null ? star <= hoveredStar : star <= (rating ?? 0))
                          ? "fill-amber-400 text-amber-400"
                          : "fill-border text-border"
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="comments" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
                Comments
              </label>
              <textarea
                id="comments"
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="What did you think of the tour? Any suggestions?"
                className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
              />
            </div>

            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Submitting…" : "Submit Feedback"}
            </Button>
          </form>
        )}

        <p className="text-center text-xs text-muted-foreground mt-6">
          Bridge 2026 VII &middot; Industry Tour Feedback
        </p>
      </motion.div>
    </div>
  )
}
