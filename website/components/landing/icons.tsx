const iconClass = "size-5 fill-none stroke-current stroke-2";

export function ThemeIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" strokeLinecap="round" />
      <path
        d="M12 3a9 9 0 0 0 0 18z"
        fill="currentColor"
        stroke="none"
      />
    </svg>
  );
}

export function SendIcon() {
  return (
    <svg className={iconClass} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M4 12l16-8-6 16-3-7z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
