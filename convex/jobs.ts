import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const createJob = mutation({
  args: { idea: v.string() },
  handler: async (ctx, { idea }) => {
    const jobId = await ctx.db.insert("jobs", {
      idea,
      status: "running",
      progress: 5,
      stage_label: "Initializing",
      created_at: Date.now(),
    });
    return jobId;
  },
});

export const updateProgress = mutation({
  args: {
    job_id: v.id("jobs"),
    progress: v.number(),
    stage_label: v.string(),
  },
  handler: async (ctx, { job_id, progress, stage_label }) => {
    await ctx.db.patch(job_id, { progress, stage_label });
  },
});

export const completeJob = mutation({
  args: {
    job_id: v.id("jobs"),
    result: v.string(),
  },
  handler: async (ctx, { job_id, result }) => {
    const job = await ctx.db.get(job_id);
    if (!job) throw new Error("Job not found");

    await ctx.db.patch(job_id, {
      status: "completed",
      progress: 100,
      stage_label: "Done",
    });

    await ctx.db.insert("analyses", {
      idea: job.idea,
      job_id,
      result,
      created_at: Date.now(),
    });
  },
});

export const failJob = mutation({
  args: {
    job_id: v.id("jobs"),
    error: v.string(),
  },
  handler: async (ctx, { job_id, error }) => {
    await ctx.db.patch(job_id, {
      status: "failed",
      stage_label: "Failed",
      error,
    });
  },
});

export const getJob = query({
  args: { job_id: v.id("jobs") },
  handler: async (ctx, { job_id }) => {
    return await ctx.db.get(job_id);
  },
});

export const listAnalyses = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("analyses").order("desc").take(50);
  },
});

export const getAnalysis = query({
  args: { job_id: v.id("jobs") },
  handler: async (ctx, { job_id }) => {
    return await ctx.db
      .query("analyses")
      .withIndex("by_job_id", (q) => q.eq("job_id", job_id))
      .first();
  },
});
