"use client";

import { useSyncExternalStore } from "react";

const UTC_FORMAT = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

const NOOP_SUBSCRIBE = () => () => {};

/** True only after hydration; false during SSR and the first client render. */
function useIsHydrated(): boolean {
  return useSyncExternalStore(
    NOOP_SUBSCRIBE,
    () => true,
    () => false,
  );
}

/**
 * Renders a timestamp in the viewer's own timezone.
 *
 * Calling `toLocaleString()` directly inside a server component formats against
 * the *server's* locale and timezone, so every viewer sees the deploy region's
 * clock. Render a fixed UTC string on the server (identical on both sides, so
 * no hydration mismatch), then reformat locally once hydrated.
 */
export function Timestamp({
  iso,
  className,
}: {
  iso: string;
  className?: string;
}) {
  const isHydrated = useIsHydrated();
  const date = new Date(iso);

  if (Number.isNaN(date.getTime())) {
    return <span className={className}>{iso}</span>;
  }

  return (
    <time dateTime={iso} className={className}>
      {isHydrated ? date.toLocaleString() : `${UTC_FORMAT.format(date)} UTC`}
    </time>
  );
}
