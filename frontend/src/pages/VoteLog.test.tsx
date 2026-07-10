import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { VoteLog } from "./VoteLog"
import { api } from "@/api/client"

vi.mock("@/api/client", () => ({
  api: { get: vi.fn() },
}))

const mockedApiGet = vi.mocked(api.get)

beforeEach(() => {
  vi.clearAllMocks()
})

function makeVotes(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    timestamp: "2026-07-10T12:00:00Z",
    username: `User${i + 1}`,
    user_id: String(100 + i),
    question: `Question ${i + 1}?`,
    choice: "Option A",
    poll_id: String(i + 1),
  }))
}

describe("VoteLog", () => {
  it("shows loading state while fetching", () => {
    mockedApiGet.mockReturnValue(new Promise(() => {}))
    render(<VoteLog />)
    expect(screen.getByText("Vote Log")).toBeInTheDocument()
  })

  it("shows empty state when no votes exist", async () => {
    mockedApiGet.mockResolvedValue({ total: 0, page: 1, limit: 25, total_pages: 1, votes: [] })
    render(<VoteLog />)
    await waitFor(() => {
      expect(screen.getByText(/No votes recorded yet/i)).toBeInTheDocument()
    })
  })

  it("shows error state with retry on API failure", async () => {
    mockedApiGet.mockRejectedValue(new Error("API unreachable"))
    render(<VoteLog />)
    await waitFor(() => {
      expect(screen.getByText(/API unreachable/i)).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })

  it("renders vote rows on successful load", async () => {
    mockedApiGet.mockResolvedValue({
      total: 3,
      page: 1,
      limit: 25,
      total_pages: 1,
      votes: makeVotes(3),
    })
    render(<VoteLog />)
    await waitFor(() => {
      expect(screen.getByText("User1")).toBeInTheDocument()
      expect(screen.getByText("User2")).toBeInTheDocument()
      expect(screen.getByText("User3")).toBeInTheDocument()
    })
    expect(screen.getByText(/Page 1 of 1/)).toBeInTheDocument()
  })

  it("supports search filtering", async () => {
    const votes = makeVotes(3)
    mockedApiGet.mockResolvedValueOnce({
      total: 3, page: 1, limit: 25, total_pages: 1, votes,
    })
    render(<VoteLog />)

    await waitFor(() => {
      expect(screen.getByText("User1")).toBeInTheDocument()
    })

    mockedApiGet.mockResolvedValueOnce({
      total: 1, page: 1, limit: 25, total_pages: 1, votes: [votes[0]],
    })

    const input = screen.getByPlaceholderText(/search/i)
    await userEvent.type(input, "User1")
    await userEvent.keyboard("{Enter}")

    await waitFor(() => {
      expect(mockedApiGet).toHaveBeenCalledTimes(2)
    })
  })

  it("paginates correctly", async () => {
    mockedApiGet.mockResolvedValue({
      total: 50,
      page: 1,
      limit: 25,
      total_pages: 2,
      votes: makeVotes(25),
    })
    render(<VoteLog />)

    await waitFor(() => {
      expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument()
    })

    const nextBtn = screen.getByRole("button", { name: /next/i })
    expect(nextBtn).not.toBeDisabled()

    mockedApiGet.mockResolvedValueOnce({
      total: 50, page: 2, limit: 25, total_pages: 2, votes: makeVotes(25).map((v, i) => ({ ...v, username: `User${i + 26}` })),
    })

    await userEvent.click(nextBtn)

    await waitFor(() => {
      expect(screen.getByText(/Page 2 of 2/)).toBeInTheDocument()
    })
  })
})
