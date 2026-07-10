import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { PollResults } from "./PollResults"
import { api } from "@/api/client"

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
  },
}))

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="barchart">{children}</div>,
  Bar: ({ children }: { children: React.ReactNode }) => <div data-testid="bar">{children}</div>,
  Cell: () => <div data-testid="cell" />,
  XAxis: () => <div data-testid="xaxis" />,
  YAxis: () => <div data-testid="yaxis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}))

const mockedApiGet = vi.mocked(api.get)

beforeEach(() => {
  vi.clearAllMocks()
})

describe("PollResults", () => {
  it("shows loading skeletons while fetching", () => {
    mockedApiGet.mockReturnValue(new Promise(() => {}))
    render(<PollResults />)
    expect(screen.getByText("Poll Results")).toBeInTheDocument()
    const skeletons = document.querySelectorAll(".animate-pulse")
    expect(skeletons.length).toBeGreaterThanOrEqual(3)
  })

  it("shows empty state when no polls exist", async () => {
    mockedApiGet.mockResolvedValue([])
    render(<PollResults />)
    await waitFor(() => {
      expect(screen.getByText(/No polls yet/i)).toBeInTheDocument()
    })
  })

  it("shows error state with retry button on API failure", async () => {
    mockedApiGet.mockRejectedValue(new Error("Network error"))
    render(<PollResults />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })

  it("renders poll cards on successful load", async () => {
    mockedApiGet.mockResolvedValue([
      {
        poll_id: 1,
        question: "Favorite color?",
        options: [
          { name: "Red", votes: 10 },
          { name: "Blue", votes: 5 },
        ],
        total_votes: 15,
        timestamp: "2026-07-10T12:00:00Z",
        active: true,
      },
      {
        poll_id: 2,
        question: "Best framework?",
        options: [
          { name: "React", votes: 8 },
          { name: "Vue", votes: 3 },
        ],
        total_votes: 11,
        timestamp: "2026-07-10T13:00:00Z",
        active: false,
      },
    ])

    render(<PollResults />)

    await waitFor(() => {
      expect(screen.getByText("Favorite color?")).toBeInTheDocument()
      expect(screen.getByText("Best framework?")).toBeInTheDocument()
    })

    expect(screen.getByText("15 total votes")).toBeInTheDocument()
    expect(screen.getByText(/Live/)).toBeInTheDocument()
    expect(screen.getByText(/Ended/)).toBeInTheDocument()
  })

  it("retries on retry button click after error", async () => {
    mockedApiGet.mockRejectedValueOnce(new Error("First failure"))
    render(<PollResults />)

    await waitFor(() => {
      expect(screen.getByText(/First failure/i)).toBeInTheDocument()
    })

    mockedApiGet.mockResolvedValueOnce([
      {
        poll_id: 3,
        question: "Retry worked?",
        options: [{ name: "Yes", votes: 1 }],
        total_votes: 1,
        timestamp: "2026-07-10T14:00:00Z",
        active: true,
      },
    ])

    const retryBtn = screen.getByRole("button", { name: /retry/i })
    await userEvent.click(retryBtn)

    await waitFor(() => {
      expect(screen.getByText("Retry worked?")).toBeInTheDocument()
    })
  })
})
