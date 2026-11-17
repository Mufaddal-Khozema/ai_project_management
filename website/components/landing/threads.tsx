const PATHS = [
  {
    d: "M-50 120C250-40 400 320 700 200S1100 60 1260 260",
    delay: 0,
    color: "text-pink-500",
  },
  {
    d: "M-50 420C200 300 450 560 760 420S1050 330 1260 480",
    delay: 0.2,
    color: "text-violet-500",
  },
  {
    d: "M-50 700C300 560 500 820 820 640S1100 560 1260 700",
    delay: 0.4,
    color: "text-orange-400",
  },
  {
    d: "M-50 260C300 400 500 80 800 340S1050 520 1260 360",
    delay: 0.6,
    color: "text-blue-500",
  },
];

export function Threads({
  className = "",
  tone = "color",
}: {
  className?: string;
  tone?: "color" | "mono";
}) {
  return (
    <svg
      className={className}
      viewBox="0 0 1200 800"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <g
        fill="none"
        strokeWidth={tone === "mono" ? 2 : 1}
        strokeLinecap="round"
        strokeDasharray={1}
        strokeDashoffset={1}
      >
        {PATHS.map((path) => (
          <path
            key={path.d}
            className={`animate-thread-draw thread-line ${
              tone === "mono" ? "text-white" : path.color
            }`}
            stroke="currentColor"
            pathLength={1}
            d={path.d}
            style={path.delay ? { animationDelay: `${path.delay}s` } : undefined}
          />
        ))}
      </g>
    </svg>
  );
}
