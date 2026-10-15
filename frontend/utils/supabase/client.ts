"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseConfig } from "./config";

export function createClient(): SupabaseClient | null {
  const config = getSupabaseConfig();
  if (!config) return null;

  return createBrowserClient(config.url, config.key);
}
