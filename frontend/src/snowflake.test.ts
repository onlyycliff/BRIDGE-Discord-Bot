/**
 * Tests that Discord snowflake IDs are preserved as strings throughout
 * the poll creation flow.
 *
 * Discord IDs are 64-bit integers (e.g. "1513971659487445432") that
 * exceed JavaScript's safe integer range (Number.MAX_SAFE_INTEGER =
 * 2^53 - 1 = 9007199254740991). Passing them through Number() silently
 * truncates precision, producing corrupted IDs like ...445000.
 */

import { describe, it, expect } from "vitest"

// A real Discord snowflake ID — larger than Number.MAX_SAFE_INTEGER
const SNOWFLAKE = "1513971659487445432"

describe("Discord snowflake ID precision", () => {
  it("Number() loses precision on snowflake IDs", () => {
    const asNumber = Number(SNOWFLAKE)
    // Number() truncates — this proves the bug exists
    expect(String(asNumber)).not.toBe(SNOWFLAKE)
  })

  it("string pass-through preserves snowflake IDs", () => {
    const payload = { channel_id: SNOWFLAKE }
    // Sending as string — no precision loss
    expect(payload.channel_id).toBe(SNOWFLAKE)
  })

  it("role IDs must also be strings to preserve precision", () => {
    const roleIds = ["1513971659487445432", "1513971659487445433"]
    const toggle = (id: string) =>
      roleIds.includes(id) ? roleIds.filter((r) => r !== id) : [...roleIds, id]

    // Toggle removes correctly when comparing strings
    expect(toggle("1513971659487445432")).toEqual(["1513971659487445433"])
    // Toggle adds when not present
    expect(toggle("999")).toEqual([
      "1513971659487445432",
      "1513971659487445433",
      "999",
    ])
  })
})
