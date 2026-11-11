"use client";

import { useApolloClient } from "@apollo/client/react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  type RecruiterSession,
  UNAUTHENTICATED_EVENT,
  fetchSession,
  signOut,
} from "@/lib/auth";

type SessionStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface SessionContextValue {
  status: SessionStatus;
  recruiter: RecruiterSession | null;
  setRecruiter: (recruiter: RecruiterSession) => void;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const client = useApolloClient();
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [recruiter, setRecruiterState] = useState<RecruiterSession | null>(null);

  const refresh = useCallback(async () => {
    try {
      const session = await fetchSession();
      setRecruiterState(session);
      setStatus(session ? "authenticated" : "unauthenticated");
    } catch {
      setRecruiterState(null);
      setStatus("error");
    }
  }, []);

  const setRecruiter = useCallback((session: RecruiterSession) => {
    setRecruiterState(session);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    try {
      await signOut();
    } finally {
      setRecruiterState(null);
      setStatus("unauthenticated");
      await client.clearStore();
    }
  }, [client]);

  useEffect(() => {
    // Checking the session cookie is an external sync, so state is set after the fetch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  useEffect(() => {
    // The Apollo error link fires this when the API rejects an expired session.
    const handleUnauthenticated = () => {
      setRecruiterState(null);
      setStatus("unauthenticated");
    };
    window.addEventListener(UNAUTHENTICATED_EVENT, handleUnauthenticated);
    return () => window.removeEventListener(UNAUTHENTICATED_EVENT, handleUnauthenticated);
  }, []);

  const value = useMemo(
    () => ({ status, recruiter, setRecruiter, refresh, logout }),
    [status, recruiter, setRecruiter, refresh, logout],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider.");
  return context;
}

export function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "TF"
  );
}
