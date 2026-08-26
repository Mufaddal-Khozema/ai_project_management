import { Suspense } from "react";
import Link from "next/link";
import LandingAnimations from "./LandingAnimations";
import PricingPlans from "./pricing-plans";

export default function Home() {
  return (
    <>
      <LandingAnimations />
    <div className="hero-bg-custom"></div>

    <header className="fixed! z-50! w-full bg-[#09090b]/80 backdrop-blur-md z-50 border-b border-zinc-800/60">
        <div className="w-full px-6 lg:px-12 h-16 flex items-center justify-between">
            <div className="font-bold text-xl tracking-tight text-white">Coordina<span className="text-zinc-500">AI</span></div>
            <nav className="hidden md:flex space-x-8 text-sm font-medium text-zinc-400">
                <a href="#problem" className="hover:text-zinc-100 transition-colors">The Pain</a>
                <a href="#solution" className="hover:text-zinc-100 transition-colors">The Solution</a>
                <a href="#features" className="hover:text-zinc-100 transition-colors">Features</a>
                <a href="#pricing" className="hover:text-zinc-100 transition-colors">Pricing</a>
            </nav>
            <a href="#cta" className="bg-white text-zinc-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors">
                Book Demo
            </a>
        </div>
    </header>

    <section className="relative pt-32 pb-16 px-6 lg:px-12 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center perspective-container min-h-[90vh]">
        <div className="lg:col-span-6 space-y-8 z-10 hero-text-trigger mt-12 lg:mt-0">
            <h1 className="text-5xl md:text-7xl tracking-tighter leading-none font-medium text-white">
                Stop chasing <br /> <span className="text-zinc-500">project updates.</span>
            </h1>
            <p className="text-lg text-zinc-400 leading-relaxed max-w-xl">
                Our AI coordinator automatically follows up with teammates, synchronizes Jira and Slack, generates reports, and keeps your projects moving without constant manual coordination.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                <a href="#cta" className="bg-white text-zinc-950 px-6 py-3 rounded-lg text-center font-medium hover:bg-zinc-200 transition-colors">
                    Book Demo
                </a>
                <a href="#demo" className="bg-transparent text-zinc-300 border border-zinc-700 px-6 py-3 rounded-lg text-center font-medium hover:bg-zinc-900 transition-colors flex items-center justify-center gap-2">
                    <i className="ph ph-play-circle text-lg"></i> Watch 2-min Demo
                </a>
            </div>
        </div>

        <div className="lg:col-span-6 z-10 hero-3d-trigger">
            <div className="three-d-card bg-zinc-900/80 border border-zinc-800 p-6 rounded-xl shadow-2xl space-y-3 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-zinc-800 via-zinc-500 to-zinc-800 opacity-50"></div>

                <div className="flex items-center gap-3 text-sm font-medium text-zinc-300 bg-zinc-950 p-3 rounded-lg border border-zinc-800/80">
                    <div className="bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded text-xs">Engineer</div> 
                    <span className="text-zinc-600">→</span> <span className="font-mono text-zinc-400 text-xs">git commit -m "feat: core auth"</span>
                </div>

                <div className="flex items-center justify-between gap-4 text-sm font-medium text-zinc-100 bg-zinc-800/50 p-3 rounded-lg border border-zinc-700 ml-4">
                    <div className="flex items-center gap-2">
                        <i className="ph ph-robot text-lg text-zinc-400"></i>
                        <span>AI Coordinator Agent</span>
                    </div>
                    <span className="text-zinc-400 text-xs font-mono">Scanning Slack</span>
                </div>

                <div className="flex items-center gap-3 text-sm font-medium text-zinc-300 bg-zinc-950 p-3 rounded-lg border border-zinc-800/80 ml-8">
                    <div className="bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded text-xs">Dashboard</div> 
                    <span className="text-zinc-600">→</span> <span className="text-zinc-400 text-xs">Jira Sync Complete</span>
                </div>

                <div className="flex items-center gap-3 text-sm font-medium text-zinc-300 bg-zinc-950 p-3 rounded-lg border border-zinc-800/80 ml-12">
                    <div className="bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded text-xs">Leadership</div> 
                    <span className="text-zinc-600">→</span> <span className="text-zinc-400 text-xs">Auto-Notified via Digest</span>
                </div>
            </div>
        </div>
    </section>

    <section className="border-y border-zinc-800/60 bg-zinc-900/20 py-8 overflow-hidden px-6 lg:px-12">
        <div className="flex flex-col md:flex-row items-center justify-center gap-8 md:gap-16">
            <span className="text-xs text-zinc-500 font-medium tracking-wide">Trusted by operators at</span>
            <div className="flex flex-wrap justify-center gap-8 md:gap-16 text-zinc-400 opacity-70">
                <span className="flex items-center gap-2 font-bold text-lg tracking-tight"><i className="ph-fill ph-square-logo"></i> Acme Corp</span>
                <span className="flex items-center gap-2 font-bold text-lg tracking-tight"><i className="ph-fill ph-circle-notch"></i> GlobalTech</span>
                <span className="flex items-center gap-2 font-bold text-lg tracking-tight"><i className="ph-fill ph-triangle"></i> Vertex</span>
                <span className="flex items-center gap-2 font-bold text-lg tracking-tight"><i className="ph-fill ph-hexagon"></i> Nexus</span>
            </div>
        </div>
    </section>

    <section id="problem" className="py-24 bg-[#09090b] edge-bottom px-6 lg:px-12">
        <div className="text-center space-y-12">
            <h2 className="text-3xl md:text-5xl font-medium text-white tracking-tight leading-tight">
                Project managers spend more time <br /><span className="text-zinc-500">collecting updates</span> than making decisions.
            </h2>

            <div className="flex flex-wrap justify-center items-center gap-3 text-zinc-400 font-mono text-xs">
                <span className="bg-zinc-900 px-3 py-1.5 rounded-md border border-zinc-800">Slack</span>
                <i className="ph ph-arrow-right text-zinc-600"></i>
                <span className="bg-zinc-900 px-3 py-1.5 rounded-md border border-zinc-800">Jira</span>
                <i className="ph ph-arrow-right text-zinc-600"></i>
                <span className="bg-zinc-900 px-3 py-1.5 rounded-md border border-zinc-800">Excel</span>
                <i className="ph ph-arrow-right text-zinc-600"></i>
                <span className="bg-zinc-900 px-3 py-1.5 rounded-md border border-zinc-800">Zoom</span>
                <i className="ph ph-arrow-right text-zinc-600"></i>
                <span className="bg-zinc-200 text-zinc-900 border border-zinc-300 px-3 py-1.5 rounded-md font-bold">Repeat</span>
            </div>

            <div className="grid md:grid-cols-3 gap-6 pt-8 text-left">
                <div className="problem-card bg-zinc-900/40 p-6 rounded-xl border border-zinc-800/80 space-y-3">
                    <i className="ph ph-users text-xl text-zinc-400"></i>
                    <h3 className="font-medium text-white">Meaningless Meetings</h3>
                    <p className="text-zinc-500 text-sm leading-relaxed">Status meetings that exist only because project information isn't automatically shared.</p>
                </div>
                <div className="problem-card bg-zinc-900/40 p-6 rounded-xl border border-zinc-800/80 space-y-3">
                    <i className="ph ph-file-text text-xl text-zinc-400"></i>
                    <h3 className="font-medium text-white">Manual Reports</h3>
                    <p className="text-zinc-500 text-sm leading-relaxed">Hours spent every week collecting information that already exists across multiple tools.</p>
                </div>
                <div className="problem-card bg-zinc-900/40 p-6 rounded-xl border border-zinc-800/80 space-y-3">
                    <i className="ph ph-arrows-left-right text-xl text-zinc-400"></i>
                    <h3 className="font-medium text-white">Context Switching</h3>
                    <p className="text-zinc-500 text-sm leading-relaxed">Constantly switching between planning and reporting tools increases cognitive load.</p>
                </div>
            </div>
        </div>
    </section>

    <section id="solution" className="py-24 bg-zinc-950 edge-bottom px-6 lg:px-12">
        <div className="text-center space-y-4 mb-20">
            <h2 className="text-3xl md:text-5xl font-medium text-white tracking-tight">One unified coordinator.</h2>
            <p className="text-zinc-400 text-lg">Connect your existing tools once. Let the system handle the repetitive coordination architecture.</p>
        </div>

        <div className="grid lg:grid-cols-12 gap-12 items-center solution-trigger">
            <div className="lg:col-span-5 bg-zinc-900/30 border border-zinc-800/60 rounded-xl p-8 relative overflow-hidden">
                <div className="text-sm font-medium text-white mb-6">Legacy Workflow</div>
                <div className="space-y-3 font-mono text-xs text-zinc-400">
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 flex justify-between items-center">
                        <span>Dev Activity</span> <span className="text-zinc-600">Untracked</span>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 flex justify-between items-center">
                        <span>Slack Ping</span> <span className="text-zinc-500">Manual</span>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 flex justify-between items-center">
                        <span>Sync Meeting</span> <span className="text-zinc-500">Overhead</span>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 flex justify-between items-center">
                        <span>Status Report</span> <span className="text-zinc-600">Outdated</span>
                    </div>
                </div>
            </div>

            <div className="hidden lg:flex lg:col-span-2 justify-center text-zinc-600">
                <i className="ph ph-arrow-right text-2xl"></i>
            </div>

            <div className="lg:col-span-5 bg-zinc-900 border border-zinc-700 rounded-xl p-8 relative">
                <div className="text-sm font-medium text-white mb-6 flex justify-between items-center">
                    <span>Autonomous Core</span>
                    <span className="flex items-center gap-2 text-xs font-mono text-zinc-400"><span className="w-1.5 h-1.5 rounded-full bg-white"></span> Active</span>
                </div>

                <div className="space-y-3">
                    <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 flex items-start gap-3">
                        <i className="ph ph-code-block text-lg text-zinc-400 mt-0.5"></i>
                        <div>
                            <h4 className="text-sm font-medium text-zinc-200">Event Hook</h4>
                            <p className="text-xs text-zinc-500 mt-1">AI detects GitHub commit</p>
                        </div>
                    </div>
                    <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 flex items-start gap-3">
                        <i className="ph ph-arrows-clockwise text-lg text-zinc-400 mt-0.5"></i>
                        <div>
                            <h4 className="text-sm font-medium text-zinc-200">State Synced</h4>
                            <p className="text-xs text-zinc-500 mt-1">Jira updated autonomously</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="features" className="scroller-block bg-[#09090b] relative z-10 edge-bottom overflow-hidden">
      <div className="bg-container absolute inset-0 bg-gradient-to-br from-indigo-900/20 to-purple-900/20 opacity-30 pointer-events-none"></div>

      <div className="scroller-section relative min-h-screen flex flex-col justify-between px-6 lg:px-12 py-10">

        {/* Top progress bar, full width */}
        <div className="w-full h-[2px] bg-zinc-800 absolute top-0 left-0 overflow-hidden">
          <div className="progress_bar h-full bg-white origin-left transform scale-x-0"></div>
        </div>

        {/* Index + Headline row */}
        <div className="flex items-start justify-between mt-16 lg:mt-24 px-2">
          <div className="text-white font-mono text-sm md:text-base tracking-widest index_current">01</div>
          <h2 className="text-3xl md:text-6xl font-medium tracking-tight text-white text-right max-w-3xl leading-tight">
            Engineered Around Jobs,<br className="hidden md:block" /> Not Tech Jargon.
          </h2>
        </div>

        {/* Scroller Content, lower-left */}
        <div className="relative min-h-[220px] md:min-h-[220px] w-full max-w-xl mt-auto mb-40 md:mb-40 overflow-hidden">

          {/* Item 01 */}
          <div className="main_item absolute inset-0 flex flex-col justify-end gap-3 invisible">
            <h3 className="font-bold text-white text-xl md:text-2xl">Collect Information</h3>
            <p className="text-zinc-400 text-xl md:text-2xl leading-relaxed">
              No more chasing status in five different tabs. CoordinaAI follows up automatically, pulls context from every standup, and turns scattered replies into one clean record — without anyone lifting a finger.
            </p>
          </div>

          {/* Item 02 */}
          <div className="main_item absolute inset-0 flex flex-col justify-end gap-3 invisible">
            <h3 className="font-bold text-white text-xl md:text-2xl">Organize Syncs</h3>
            <p className="text-zinc-400 text-xl md:text-2xl leading-relaxed">
              Meetings stop being the only source of truth. Sprint progress updates itself in real time, milestones adjust as work shifts, and your dashboard always reflects where the team actually stands.
            </p>
          </div>

          {/* Item 03 */}
          <div className="main_item absolute inset-0 flex flex-col justify-end gap-3 invisible">
            <h3 className="font-bold text-white text-xl md:text-2xl">Communicate</h3>
            <p className="text-zinc-400 text-xl md:text-2xl leading-relaxed">
              Leadership gets clarity without a status meeting. Executive summaries write themselves after every sync, stakeholder maps stay current, and nothing important gets lost in translation.
            </p>
          </div>

	  {/* Item 04 */}
          <div className="main_item absolute inset-0 flex flex-col justify-end gap-3 invisible">
            <h3 className="font-bold text-white text-xl md:text-2xl">Predict Risk</h3>
            <p className="text-zinc-400 text-xl md:text-2xl leading-relaxed">
              See the fire before it starts. Deadline risk is flagged early, burn-down trends are read continuously, and your team gets a warning while there's still time to course-correct.
            </p>
          </div>

        </div>

	{/* Bottom-right counter */}
        <div className="absolute bottom-8 right-6 lg:right-12 text-zinc-600 font-mono text-sm">04</div>
      </div>
    </section>

    <section className="py-24 bg-zinc-900/20 relative edge-bottom px-6 lg:px-12">
        <div className="text-center space-y-12">
            <h2 className="text-2xl font-medium text-zinc-400 tracking-tight">Validated by Engineering Operators</h2>
            <div className="grid md:grid-cols-2 gap-8 text-left">
                <div className="bg-zinc-900/60 p-8 rounded-2xl border border-zinc-800 flex gap-4 items-start">
                    <img className="w-12 h-12 rounded-full object-cover grayscale opacity-80" src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80" alt="User" />
                    <div className="space-y-3">
                        <p className="text-zinc-300 text-sm italic leading-relaxed">"CoordinaAI eliminated the constant daily standup hunting. The team stays in flow states, while the dashboard stays perfectly accurate."</p>
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Marcus Chen — VP of Engineering</h4>
                    </div>
                </div>
                <div className="bg-zinc-900/60 p-8 rounded-2xl border border-zinc-800 flex gap-4 items-start">
                    <img className="w-12 h-12 rounded-full object-cover grayscale opacity-80" src="https://images.unsplash.com/photo-1501196354995-cbb51c65aaea?auto=format&fit=crop&w=150&q=80" alt="User" />
                    <div className="space-y-3">
                        <p className="text-zinc-300 text-sm italic leading-relaxed">"Setup took us 5 minutes. The context switching drop has dramatically boosted our deployment velocity."</p>
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Elena Rostova — Technical PM</h4>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="pricing" className="py-24 bg-[#09090b] edge-bottom px-6 lg:px-12">
        <div className="text-center mb-16 space-y-3">
            <h2 className="text-3xl md:text-5xl font-medium tracking-tight text-white">Pricing That Maps to Value.</h2>
            <p className="text-zinc-400 text-base">Scale safely as your product organizations accelerate.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 items-center pricing-trigger">
            <Suspense fallback={
              <>
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-zinc-900/40 rounded-2xl border border-zinc-800 p-8 text-center space-y-6 animate-pulse">
                    <div className="h-4 bg-zinc-800 rounded w-20 mx-auto" />
                    <div className="h-8 bg-zinc-800 rounded w-24 mx-auto" />
                    <div className="h-10 bg-zinc-800 rounded-xl w-full" />
                    <div className="h-3 bg-zinc-800 rounded w-48 mx-auto" />
                  </div>
                ))}
              </>
            }>
                <PricingPlans />
            </Suspense>
        </div>
    </section>

    <section id="cta" className="py-24 bg-zinc-950 text-center relative px-6">
        <div className="space-y-10 relative z-10">
            <h2 className="text-4xl md:text-6xl font-medium text-white tracking-tighter leading-tight">
                Spend less time chasing updates.<br />
                <span className="text-zinc-500">Spend more time delivering products.</span>
            </h2>
            <button className="bg-white text-zinc-950 px-10 py-4 rounded-xl text-base font-semibold hover:bg-zinc-200 transition shadow-xl">
                Request a Demo
            </button>
        </div>
    </section>

    <footer className="bg-[#09090b] border-t border-zinc-900 overflow-hidden">
        <div className="w-full text-center pt-16 select-none pointer-events-none">
            <h2 className="text-[14vw] font-black uppercase tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-zinc-950 via-zinc-800 to-zinc-950 leading-none">
                Coordina AI
            </h2>
        </div>
        <div className="w-full px-6 lg:px-12 py-8 flex flex-col sm:flex-row items-center justify-between text-xs text-zinc-600 font-medium border-t border-zinc-900/40 mt-8">
            <p>&copy; 2026 CoordinaAI Core Operations. System parameters locked.</p>
            <div className="flex flex-col items-center gap-6 mt-2 sm:mt-0 sm:flex-row">
                <Link href="/terms" className="text-zinc-500 hover:text-zinc-300 transition-colors">
                    Terms of Service
                </Link>
                <Link href="/privacy" className="text-zinc-500 hover:text-zinc-300 transition-colors">
                    Privacy Policy
                </Link>
            </div>
        </div>
    </footer>
  </>);
}
