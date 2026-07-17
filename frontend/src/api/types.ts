export interface PollOption {
  name: string
  votes: number
}

export interface Poll {
  poll_id: number
  question: string
  options: PollOption[]
  total_votes: number
  timestamp: string
  active?: boolean
}

export interface PollDetail extends Poll {
  voters_by_choice: Record<string, string[]>
}

export interface PaginatedVotes {
  total: number
  page: number
  limit: number
  total_pages: number
  votes: Vote[]
}

export interface Vote {
  timestamp: string
  username: string
  user_id: string
  question: string
  choice: string
  poll_id: string
}

export interface BotStatusData {
  online: boolean
  uptime: string
  votes_total: number
  votes_today: number
  last_command: string
  latency_ms: number
  avatar_url: string
}

export interface DataStatus {
  total_records: number
  last_timestamp: string
  storage: string
  status: string
}

export interface DashboardOverview {
  total_votes: number
  unique_voters: number
  active_polls: number
  engagement_rate: string
  last_updated: string
}

export interface DiscordChannel {
  id: string
  name: string
}

export interface DiscordRole {
  id: string
  name: string
}

export interface CreatePollResponse {
  success: boolean
  message: string
  question: string
  options: string[]
}

export interface CreatePollPayload {
  question: string
  description?: string
  options: string[]
  channel_id?: string | null
  role_ids?: string[]
  max_votes_per_option?: number | null
}

export interface AuthUser {
  name: string
  email: string
}

export interface Tour {
  id: number
  name: string
  company: string
  date: string | null
}

export interface FeedbackSubmitPayload {
  tour_id: number
  student_name: string
  student_id: number
  rating: number | null
  comments: string | null
}
