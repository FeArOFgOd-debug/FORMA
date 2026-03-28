import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  jobs: defineTable({
    idea: v.string(),
    status: v.union(
      v.literal("running"),
      v.literal("completed"),
      v.literal("failed")
    ),
    progress: v.number(),
    stage_label: v.string(),
    error: v.optional(v.string()),
    created_at: v.number(),
  }),

  analyses: defineTable({
    idea: v.string(),
    job_id: v.id("jobs"),
    result: v.string(),
    created_at: v.number(),
  }).index("by_job_id", ["job_id"]),
});
