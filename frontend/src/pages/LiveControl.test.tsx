import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LiveControl } from "./LiveControl"
import { api } from "@/api/client"

vi.mock("@/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}))

const mockedApiGet = vi.mocked(api.get)
const mockedApiPost = vi.mocked(api.post)

beforeEach(() => {
  vi.clearAllMocks()
  mockedApiGet
    .mockResolvedValueOnce([]) // channels
    .mockResolvedValueOnce([]) // roles
    .mockResolvedValueOnce([]) // polls (empty)
})

describe("LiveControl", () => {
  it("renders the title and form elements", async () => {
    render(<LiveControl />)
    expect(screen.getByText("Live Control")).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Poll question")).toBeInTheDocument()
    })
  })

  it("shows active polls on successful load", async () => {
    mockedApiGet
      .mockReset()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        { poll_id: 1, question: "Test Poll", total_votes: 5, active: true, options: [], timestamp: "" },
      ])

    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByText("Test Poll")).toBeInTheDocument()
    })
    expect(screen.getByText("5 votes")).toBeInTheDocument()
    expect(screen.getByText("Live")).toBeInTheDocument()
  })

  it("shows empty state when no active polls", async () => {
    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByText("No active polls.")).toBeInTheDocument()
    })
  })

  it("shows error state with retry on polls fetch failure", async () => {
    mockedApiGet
      .mockReset()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("Network error"))

    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })

  it("validates empty question before submit", async () => {
    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Poll question")).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole("button", { name: /create poll/i }))
    expect(screen.getByText("Question is required.")).toBeInTheDocument()
  })

  it("validates minimum options before submit", async () => {
    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Poll question")).toBeInTheDocument()
    })

    await userEvent.type(screen.getByPlaceholderText("Poll question"), "My Question")
    await userEvent.type(screen.getByPlaceholderText("Option 1"), "Yes")
    await userEvent.type(screen.getByPlaceholderText("Option 2"), "No")
    // Clear both options to trigger validation
    await userEvent.clear(screen.getByPlaceholderText("Option 1"))
    await userEvent.clear(screen.getByPlaceholderText("Option 2"))

    await userEvent.click(screen.getByRole("button", { name: /create poll/i }))
    expect(screen.getByText("At least 2 options are required.")).toBeInTheDocument()
  })

  it("submits the form successfully", async () => {
    mockedApiPost.mockResolvedValueOnce({ success: true, message: "Poll created successfully!", question: "Test", options: ["A", "B"] })

    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Poll question")).toBeInTheDocument()
    })

    await userEvent.type(screen.getByPlaceholderText("Poll question"), "Best framework?")
    await userEvent.type(screen.getByPlaceholderText("Option 1"), "React")
    await userEvent.type(screen.getByPlaceholderText("Option 2"), "Vue")

    await userEvent.click(screen.getByRole("button", { name: /create poll/i }))

    await waitFor(() => {
      expect(screen.getByText("Poll created successfully!")).toBeInTheDocument()
    })
    expect(mockedApiPost).toHaveBeenCalledWith("/api/polls/create", {
      question: "Best framework?",
      options: ["React", "Vue"],
    })
  })

  it("shows error message on submission failure", async () => {
    mockedApiPost.mockRejectedValueOnce(new Error("Rate limited"))

    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Poll question")).toBeInTheDocument()
    })

    await userEvent.type(screen.getByPlaceholderText("Poll question"), "Test")
    await userEvent.type(screen.getByPlaceholderText("Option 1"), "A")
    await userEvent.type(screen.getByPlaceholderText("Option 2"), "B")

    await userEvent.click(screen.getByRole("button", { name: /create poll/i }))

    await waitFor(() => {
      expect(screen.getByText(/Rate limited/i)).toBeInTheDocument()
    })
  })

  it("adds and removes poll option fields", async () => {
    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByText("Add Option")).toBeInTheDocument()
    })

    const addBtn = screen.getByRole("button", { name: /add option/i })
    await userEvent.click(addBtn)
    expect(screen.getByPlaceholderText("Option 3")).toBeInTheDocument()
    expect(screen.getByText("3 / 5")).toBeInTheDocument()

    // Remove the third option
    const removeBtns = screen.getAllByRole("button")
    const xBtn = removeBtns.find((b) => b.querySelector("svg.lucide-x"))
    if (xBtn) await userEvent.click(xBtn)
    expect(screen.queryByPlaceholderText("Option 3")).not.toBeInTheDocument()
  })

  it("renders channel and role selectors when data is available", async () => {
    mockedApiGet
      .mockReset()
      .mockResolvedValueOnce([
        { id: "123", name: "general" },
        { id: "456", name: "polls" },
      ])
      .mockResolvedValueOnce([
        { id: "1", name: "everyone" },
        { id: "2", name: "admin" },
      ])
      .mockResolvedValueOnce([])

    render(<LiveControl />)
    await waitFor(() => {
      expect(screen.getByText("general")).toBeInTheDocument()
    })
    expect(screen.getByText("polls")).toBeInTheDocument()
    expect(screen.getByText("@everyone")).toBeInTheDocument()
    expect(screen.getByText("@admin")).toBeInTheDocument()
  })
})
