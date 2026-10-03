const assert = require("node:assert/strict")
const fs = require("node:fs")
const test = require("node:test")
const vm = require("node:vm")

function makeHarness(fetchImpl = async () => ({
  ok: true,
  status: 200,
  json: async () => ({ ok: true, job: { status: "generating" } }),
})) {
  let nextTimerId = 1
  const timers = new Map()
  const state = { messages: [] }
  const window = {
    NovaChatState: { state },
    setTimeout(callback, delay) {
      const id = nextTimerId++
      timers.set(id, { callback, delay })
      return id
    },
    clearTimeout(id) { timers.delete(id) },
    addEventListener() {},
  }
  const document = {
    readyState: "loading",
    getElementById() { return null },
    querySelector() { return null },
    addEventListener() {},
  }
  const context = {
    window,
    document,
    fetch: fetchImpl,
    console,
    encodeURIComponent,
    setTimeout: window.setTimeout,
    clearTimeout: window.clearTimeout,
  }
  vm.runInNewContext(
    fs.readFileSync("static/js/chat-messages.js", "utf8"),
    context,
    { filename: "chat-messages.js" },
  )
  return {
    state,
    api: window.NovaChatMessages,
    timers,
    async runNextTimer() {
      const [id, timer] = timers.entries().next().value || []
      if (!timer) return false
      timers.delete(id)
      await timer.callback()
      return true
    },
  }
}

test("persisted terminal jobs create no browser polling timer", () => {
  const harness = makeHarness()
  for (const status of ["failed", "completed", "cancelled", "canceled", "interrupted"]) {
    harness.api.resumePendingVideoPolls([{
      role: "assistant",
      meta: { video_job_id: `job-${status}`, video_status: status },
    }])
  }
  assert.equal(harness.timers.size, 0)
})

test("repeated renders keep one poll timer for a pending job", async () => {
  let fetches = 0
  const harness = makeHarness(async () => {
    fetches += 1
    return { ok: true, status: 200, json: async () => ({ ok: true, job: { status: "generating" } }) }
  })
  const message = { role: "assistant", meta: { video_job_id: "job-pending", video_status: "queued" } }
  harness.state.messages = [message]
  harness.api.resumePendingVideoPolls(harness.state.messages)
  harness.api.resumePendingVideoPolls(harness.state.messages)
  harness.api.resumePendingVideoPolls(harness.state.messages)
  assert.equal(harness.timers.size, 1)
  await harness.runNextTimer()
  harness.api.resumePendingVideoPolls(harness.state.messages)
  assert.equal(fetches, 1)
  assert.equal(harness.timers.size, 1)
})

test("switching conversations pauses the old timer and reopening resumes its same job", () => {
  const harness = makeHarness()
  const pending = { role: "assistant", meta: { video_job_id: "job-session-a", video_status: "generating" } }
  harness.api.resumePendingVideoPolls([pending])
  assert.equal(harness.timers.size, 1)
  harness.api.resumePendingVideoPolls([])
  assert.equal(harness.timers.size, 0)
  harness.api.resumePendingVideoPolls([pending])
  assert.equal(harness.timers.size, 1)
})

test("a failed job response stops polling and applies its persisted final message", async () => {
  const harness = makeHarness(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ok: true,
      job: {
        status: "failed",
        assistant_message: {
          text: "Video generation couldn't start because the video provider account doesn't have enough credits.",
          meta: { video_job_id: "job-failed", video_status: "failed" },
        },
      },
    }),
  }))
  const message = { role: "assistant", meta: { video_job_id: "job-failed", video_status: "queued" } }
  harness.state.messages = [message]
  harness.api.resumePendingVideoPolls(harness.state.messages)
  await harness.runNextTimer()
  assert.equal(message.meta.video_status, "failed")
  assert.match(message.text, /doesn't have enough credits/)
  assert.equal(harness.timers.size, 0)
})

test("a completed job response stops polling and restores the saved video attachment", async () => {
  const harness = makeHarness(async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      ok: true,
      job: {
        status: "completed",
        assistant_message: {
          text: "Your video is ready.",
          attachments: [{ type: "video", url: "/api/video/jobs/job-done/content", mime_type: "video/mp4" }],
          meta: { video_job_id: "job-done", video_status: "completed" },
        },
      },
    }),
  }))
  const message = { role: "assistant", meta: { video_job_id: "job-done", video_status: "generating" } }
  harness.state.messages = [message]
  harness.api.resumePendingVideoPolls(harness.state.messages)
  await harness.runNextTimer()
  assert.equal(message.meta.video_status, "completed")
  assert.equal(message.attachments[0].url, "/api/video/jobs/job-done/content")
  assert.equal(harness.timers.size, 0)
})
