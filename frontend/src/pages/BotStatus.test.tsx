import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { BotStatus } from "./BotStatus"
import { api } from "@/api/client"

vi.mock("@/api/client", () => ({
  api: { get: vi.fn() },
}))

const mockedApiGet = vi.mocked(api.get)

beforeEach(() => {
  vi.clearAllMocks()
})

function mockOnline() {
  mockedApiGet
    .mockResolvedValueOnce({
      online: true,
      uptime: "2h 30m 15s",
      votes_total: 150,
      votes_today: 12,
      last_command: "N/A",
      latency_ms: 45.2,
      avatar_url: "",
    })
    .mockResolvedValueOnce({
      total_records: 150,
      last_timestamp: "2026-07-10 12:00:00",
      storage: "excel",
      status: "healthy",
    })
}

describe("BotStatus", () => {
  it("shows loading state while fetching", () => {
    mockedApiGet.mockReturnValue(new Promise(() => {}))
    render(<BotStatus />)
    expect(screen.getByText("Bot Status")).toBeInTheDocument()
  })

  it("shows error state with retry on API failure", async () => {
    mockedApiGet.mockRejectedValue(new Error("Status unavailable"))
    render(<BotStatus />)
    await waitFor(() => {
      expect(screen.getByText(/Status unavailable/i)).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })

  it("renders bot status cards on successful load", async () => {
    mockOnline()
    render(<BotStatus />)

    await waitFor(() => {
      expect(screen.getByText("Discord Bot")).toBeInTheDocument()
    })

    expect(screen.getByText("2h 30m 15s")).toBeInTheDocument()
    expect(screen.getByText("45.2ms")).toBeInTheDocument()
    expect(screen.getAllByText("150").length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText("12")).toBeInTheDocument()
    expect(screen.getByText("Online")).toBeInTheDocument()
    expect(screen.getByText("Healthy")).toBeInTheDocument()
    expect(screen.getByText("Data Storage")).toBeInTheDocument()
  })

  it("shows offline status when bot is offline", async () => {
    mockedApiGet
      .mockResolvedValueOnce({
        online: false,
        uptime: "N/A",
        votes_total: 0,
        votes_today: 0,
        last_command: "N/A",
        latency_ms: 0,
        avatar_url: "",
      })
      .mockResolvedValueOnce({
        total_records: 0,
        last_timestamp: "N/A",
        storage: "excel",
        status: "healthy",
      })

    render(<BotStatus />)

    await waitFor(() => {
      expect(screen.getByText("Offline")).toBeInTheDocument()
    })
  })

  it("retries on button click after error", async () => {
    mockedApiGet.mockRejectedValueOnce(new Error("First failure"))

    render(<BotStatus />)

    await waitFor(() => {
      expect(screen.getByText(/First failure/i)).toBeInTheDocument()
    })

    mockOnline()

    const retryBtn = screen.getByRole("button", { name: /retry/i })
    await userEvent.click(retryBtn)

    await waitFor(() => {
      expect(screen.getByText("Discord Bot")).toBeInTheDocument()
    })
  })
})
