"use client";

import { useEffect, useState } from "react";

import { fetchAuthConfig } from "@/lib/auth";

/** Whether the API runs in demo mode; defaults to true until the config loads. */
export function useDemoMode() {
  const [demoMode, setDemoMode] = useState(true);
  useEffect(() => {
    let active = true;
    fetchAuthConfig()
      .then((config) => {
        if (active) setDemoMode(config.demoMode);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);
  return demoMode;
}
