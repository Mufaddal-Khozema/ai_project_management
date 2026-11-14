"use client";

import { useState } from "react";
import { Orb } from "./orb";
import { SendIcon } from "./icons";

type Answer = { text: string; source: string };

const RESPONSES: { test: RegExp; text: string; source: string }[] = [
  {
    test: /delete|remove/i,
    text: "I can’t delete PAY-31. Deleting needs admin access and yours is write. I can close it instead.",
    source: "Rule: destructive actions need admin",
  },
  {
    test: /due|soon/i,
    text: "Three items are due in two days: PAY-38 (Diego), PAY-41 (Priya) and GRO-12 (Amina). I’ve tagged each owner once today.",
    source: "Source: Jira",
  },
  {
    test: /decid|payment/i,
    text: "Retry failed charges three times, then email the owner. The team decided this in the 6 Nov payments standup.",
    source: "Source: standup, 6 Nov",
  },
  {
    test: /creat|add|task/i,
    text: "Created PAY-42 “Retry failed charges” in Jira and assigned it to you. The board is updated.",
    source: "Source: Jira",
  },
];

const FALLBACK: Answer = {
  text: "I can look up items, create or update them, start a standup, or search past decisions.",
  source: "Try “what’s due soon?”",
};

const CHIPS = [
  "What did we decide about payments?",
  "What’s due soon?",
  "Delete PAY-31",
];

export function TryIt() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);

  const ask = (value: string) => {
    const text = value.trim();
    if (!text) return;
    const match = RESPONSES.find((response) => response.test.test(text));
    setAnswer(match ?? FALLBACK);
  };

  return (
    <div className="relative grid w-full max-w-2xl gap-3.5 rounded-2xl bg-canvas p-5 shadow-raise">
      <Orb size="xl" className="absolute -top-12 right-5" />

      <form
        className="flex items-center gap-2 rounded-xl py-2 pr-2 pl-4 shadow-press focus-within:outline-2 focus-within:outline-blue-500"
        onSubmit={(event) => {
          event.preventDefault();
          ask(query);
          setQuery("");
        }}
      >
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask Coordi about your board"
          aria-label="Ask Coordi"
          className="min-w-0 flex-1 bg-transparent text-base font-medium text-ink outline-none placeholder:text-ink-muted"
        />
        <button
          type="submit"
          aria-label="Send"
          className="inline-flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 text-white shadow-soft active:shadow-press"
        >
          <SendIcon />
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {CHIPS.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => ask(chip)}
            className="rounded-lg bg-canvas px-3 py-2 text-sm font-semibold text-ink shadow-soft active:shadow-press"
          >
            {chip}
          </button>
        ))}
      </div>

      <div
        role="status"
        className="min-h-24 rounded-xl px-4 py-3.5 shadow-press"
      >
        {answer ? (
          <>
            <p>{answer.text}</p>
            <small className="mt-2 inline-block rounded-md px-2.5 py-0.5 font-semibold text-ink-muted shadow-soft">
              {answer.source}
            </small>
          </>
        ) : (
          <span className="text-ink-muted">
            Pick a question to see how Coordi answers.
          </span>
        )}
      </div>
    </div>
  );
}
