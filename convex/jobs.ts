import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const upsertUserProfile = mutation({
  args: {
    user_id: v.string(),
    email: v.string(),
    name: v.optional(v.string()),
  },
  handler: async (ctx, { user_id, email, name }) => {
    const existing = await ctx.db
      .query("users")
      .withIndex("by_user_id", (q) => q.eq("user_id", user_id))
      .first();
    const now = Date.now();

    if (existing) {
      await ctx.db.patch(existing._id, {
        email,
        name,
        last_seen_at: now,
      });
      return existing._id;
    }

    return await ctx.db.insert("users", {
      user_id,
      email,
      name,
      created_at: now,
      last_seen_at: now,
    });
  },
});

export const createJob = mutation({
  args: { idea: v.string(), user_id: v.string() },
  handler: async (ctx, { idea, user_id }) => {
    const jobId = await ctx.db.insert("jobs", {
      user_id,
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
    user_id: v.string(),
    result: v.string(),
  },
  handler: async (ctx, { job_id, user_id, result }) => {
    const job = await ctx.db.get(job_id);
    if (!job) throw new Error("Job not found");
    if (job.user_id !== user_id) throw new Error("Unauthorized job access");

    await ctx.db.patch(job_id, {
      status: "completed",
      progress: 100,
      stage_label: "Done",
    });

    await ctx.db.insert("analyses", {
      user_id: job.user_id,
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
  args: { job_id: v.id("jobs"), user_id: v.string() },
  handler: async (ctx, { job_id, user_id }) => {
    const job = await ctx.db.get(job_id);
    if (!job || job.user_id !== user_id) return null;
    return job;
  },
});

export const listAnalyses = query({
  args: { user_id: v.string() },
  handler: async (ctx, { user_id }) => {
    return await ctx.db
      .query("analyses")
      .withIndex("by_user_created", (q) => q.eq("user_id", user_id))
      .order("desc")
      .take(50);
  },
});

export const getAnalysis = query({
  args: { job_id: v.id("jobs"), user_id: v.string() },
  handler: async (ctx, { job_id, user_id }) => {
    return await ctx.db
      .query("analyses")
      .withIndex("by_user_job", (q) => q.eq("user_id", user_id).eq("job_id", job_id))
      .first();
  },
});

export const getFreshScrapeCache = query({
  args: { cache_key: v.string() },
  handler: async (ctx, { cache_key }) => {
    const matches = await ctx.db
      .query("scrapeCache")
      .withIndex("by_cache_key", (q) => q.eq("cache_key", cache_key))
      .collect();
    const now = Date.now();
    const fresh = matches
      .filter((item) => item.expires_at > now)
      .sort((a, b) => b.created_at - a.created_at)[0];
    return fresh ?? null;
  },
});

export const putScrapeCache = mutation({
  args: {
    cache_key: v.string(),
    kind: v.string(),
    payload: v.string(),
    expires_at: v.number(),
  },
  handler: async (ctx, { cache_key, kind, payload, expires_at }) => {
    const existing = await ctx.db
      .query("scrapeCache")
      .withIndex("by_cache_key", (q) => q.eq("cache_key", cache_key))
      .collect();

    for (const item of existing) {
      await ctx.db.delete(item._id);
    }

    return await ctx.db.insert("scrapeCache", {
      cache_key,
      kind,
      payload,
      expires_at,
      created_at: Date.now(),
    });
  },
});
