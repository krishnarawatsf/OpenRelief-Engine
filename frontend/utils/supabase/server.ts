import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseConfig } from "./config";

export function createClient(
  cookieStore: Awaited<ReturnType<typeof cookies>>,
): SupabaseClient {
  const config = getSupabaseConfig();
  if (!config) {
    throw new Error("Supabase is not configured for server-side use.");
  }

  return createServerClient(config.url, config.key, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch (error) {
          if (
            error instanceof Error &&
            error.message.includes("Cookies can only be modified")
          ) {
            return;
          }
          throw error;
        }
      },
    },
  });
}
