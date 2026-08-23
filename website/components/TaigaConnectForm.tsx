"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  onConnect: (username: string, password: string) => Promise<void>;
  connecting: boolean;
  dark?: boolean;
}

export function TaigaConnectForm({ onConnect, connecting, dark }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const inputClass = dark
    ? "h-8 w-32 rounded-md border border-zinc-700 bg-zinc-900 px-2 text-xs text-white placeholder:text-zinc-500"
    : "h-8 w-32 rounded-md border border-border bg-card px-2 text-xs text-card-foreground placeholder:text-muted-foreground";

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await onConnect(username, password);
    } catch {
      setError("Check your Taiga credentials and try again.");
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col items-start gap-1.5">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Taiga username"
          required
          className={inputClass}
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          required
          className={inputClass}
        />
        <Button type="submit" size="sm" disabled={connecting || !username || !password}>
          {connecting ? "Connecting…" : "Connect"}
        </Button>
      </div>
      {error && (
        <p className={`text-xs ${dark ? "text-red-400" : "text-[var(--color-warning)]"}`}>
          {error}
        </p>
      )}
    </form>
  );
}