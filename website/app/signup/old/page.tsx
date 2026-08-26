"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Script from "next/script";

const kimiScript = `"use strict";(()=>{var j=Object.create;var x=Object.defineProperty;var Q=Object.getOwnPropertyDescriptor;var Z=Object.getOwnPropertyNames;var K=Object.getPrototypeOf,$=Object.prototype.hasOwnProperty;var V=(t,e,r)=>e in t?x(t,e,{enumerable:!0,configurable:!0,writable:!0,value:r}):t[e]=r;var R=(t=>typeof require<"u"?require:typeof Proxy<"u"?new Proxy(t,{get:(e,r)=>(typeof require<"u"?require:e)[r]}):t)(function(t){if(typeof require<"u")return require.apply(this,arguments);throw Error('Dynamic require of "'+t+'" is not supported')});var Y=(t,e,r,n)=>{if(e&&typeof e=="object"||typeof e=="function")for(let o of Z(e))!$.call(t,o)&&o!==r&&x(t,o,{get:()=>e[o],enumerable:!(n=Q(e,o))||n.enumerable});return t};var O=(t,e,r)=>(r=t!=null?j(K(t)):{},Y(e||!t||!t.__esModule?x(r,"default",{value:t,enumerable:!0}):r,t));var p=(t,e,r)=>V(t,typeof e!="symbol"?e+"":e,r);var P={SANDBOX_INIT:"request/sandbox-init"},c={INITIALIZED:"ui/notifications/initialized",SIZE_CHANGED:"ui/notifications/size-changed",SCRIPT_LOADING_STARTED:"notifications/script-loading-started",SCRIPT_LOADING_FINISHED:"notifications/script-loading-finished",MESSAGE:"ui/message",OPEN_LINK:"ui/open-link",ERROR:"ui/notifications/error",LOG:"notifications/message"},u={TOOL_INPUT_PARTIAL:"notifications/tool-input-partial",TOOL_INPUT:"notifications/tool-input",TOOL_RESULT:"notifications/tool-result",HOST_CONTEXT_CHANGE:"notifications/host-context-change"};var tt=["https://www.kimi.com","https://kimi.com","https://kimi.moonshot.cn","https://*.kimi.team"];function _(t){try{let e=new URL(t),r=e.hostname,n=e.protocol.replace(":","");return r==="localhost"||r==="127.0.0.1"?!0:tt.some(o=>{let[s,i]=o.split("://");if(n!==s)return!1;if(i?.startsWith("*.")){let d=i.slice(2);return r.endsWith("."+d)}return r===i})}catch{return!1}}var et=new Set(Object.values(u)),b=t=>!!t&&typeof t=="object",rt=t=>b(t)?typeof t.id=="number"&&!("method"in t):!1,nt=t=>b(t)?typeof t.method=="string"&&et.has(t.method):!1,w=class extend... (line truncated to 2000 chars)
7: /*! Bundled license information:
8: kimi-widget-app/dist/element.mjs:1 - MIT
9: */
10: })();`;

export default function SignupPage() {
  const [step, setStep] = useState(1);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [shaking, setShaking] = useState(false);
  const [errors, setErrors] = useState<Record<string, boolean | undefined>>({});

  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    class Particle {
      x = 0; y = 0; size = 0;
      speedX = 0; speedY = 0;
      opacity = 0; life = 0; age = 0;

      constructor() { this.reset(); }

      reset() {
        this.x = Math.random() * canvas!.width;
        this.y = Math.random() * canvas!.height;
        this.size = Math.random() * 1.5 + 0.5;
        this.speedX = (Math.random() - 0.5) * 0.3;
        this.speedY = (Math.random() - 0.5) * 0.3;
        this.opacity = Math.random() * 0.5 + 0.1;
        this.life = Math.random() * 200 + 100;
        this.age = 0;
      }

      update() {
        this.x += this.speedX;
        this.y += this.speedY;
        this.age++;

        if (!isTouch) {
          const dx = this.x - mouseX;
          const dy = this.y - mouseY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            const force = (120 - dist) / 120;
            this.x += (dx / dist) * force * 1.5;
            this.y += (dy / dist) * force * 1.5;
          }
        }

        if (this.x < 0 || this.x > canvas!.width || this.y < 0 || this.y > canvas!.height || this.age > this.life) {
          this.reset();
        }
      }

      draw() {
        const fade = 1 - this.age / this.life;
        ctx!.beginPath();
        ctx!.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(160, 160, 180, ${this.opacity * fade})`;
        ctx!.fill();
      }
    }

    const particles: Particle[] = [];
    let mouseX = 0;
    let mouseY = 0;
    const isTouch = window.matchMedia("(pointer: coarse)").matches;
    let animId: number;
    let frameCount = 0;

    function resize() {
      canvas!.width = window.innerWidth;
      canvas!.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    const count = isTouch ? 30 : 60;
    for (let i = 0; i < count; i++) particles.push(new Particle());

    function drawConnections() {
      const maxDist = 120;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < maxDist) {
            const opacity = (1 - dist / maxDist) * 0.08;
            ctx!.beginPath();
            ctx!.moveTo(particles[i].x, particles[i].y);
            ctx!.lineTo(particles[j].x, particles[j].y);
            ctx!.strokeStyle = `rgba(140, 140, 180, ${opacity})`;
            ctx!.lineWidth = 0.5;
            ctx!.stroke();
          }
        }
      }
    }

    function animate() {
      frameCount++;
      if (isTouch && frameCount % 2 !== 0) {
        animId = requestAnimationFrame(animate);
        return;
      }
      ctx!.clearRect(0, 0, canvas!.width, canvas!.height);
      particles.forEach((p) => { p.update(); p.draw(); });
      drawConnections();
      animId = requestAnimationFrame(animate);
    }
    animate();

    const onMove = (e: MouseEvent) => { mouseX = e.clientX; mouseY = e.clientY; };
    document.addEventListener("mousemove", onMove);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      document.removeEventListener("mousemove", onMove);
    };
  }, []);

  const clearError = useCallback((field: string) => {
    setErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
  }, []);

  const handleStep1Next = () => {
    const e: Record<string, boolean> = {};
    if (!fullName.trim() || fullName.trim().length < 2) e.fullName = true;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) e.email = true;
    if (!company.trim()) e.company = true;
    setErrors(e);
    if (Object.keys(e).length === 0) {
      setLoading(true);
      setTimeout(() => { setLoading(false); setStep(2); }, 600);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, boolean> = {};
    if (password.length < 8) errs.password = true;
    if (!confirmPassword || password !== confirmPassword) errs.confirmPassword = true;
    if (!termsAccepted) { setShaking(true); setTimeout(() => setShaking(false), 400); }
    if (Object.keys(errs).length > 0 || !termsAccepted) { setErrors(errs); return; }
    setLoading(true);
    setTimeout(() => { setLoading(false); setSubmitted(true); }, 2000);
  };

  const getStrength = () => {
    let s = 0;
    if (password.length >= 8) s++;
    if (password.length >= 12) s++;
    if (/[A-Z]/.test(password)) s++;
    if (/[0-9]/.test(password)) s++;
    if (/[^A-Za-z0-9]/.test(password)) s++;
    const active = Math.min(Math.ceil(s / 1.5), 4);
    const cls = ["bg-red-500", "bg-amber-500", "bg-blue-500", "bg-green-500"];
    const labels = ["Too weak", "Could be stronger", "Solid", "Fortress-level"];
    return { active, label: password.length > 0 ? labels[Math.min(active - 1, 3)] : "", cls };
  };

  const strength = getStrength();

  const inputCls =
    "w-full h-[52px] px-4 bg-[#1a1a1f] border rounded-xl text-[#f5f5f7] font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-normal outline-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] placeholder:text-[#636366] hover:border-white/[.12] focus:border-indigo-500 focus:shadow-[0_0_0_3px_rgba(99,102,241,0.1),0_0_20px_rgba(99,102,241,0.3)]";
  const inputBorder = "border-white/5";
  const inputError = "!border-[#ef4444] !shadow-[0_0_0_3px_rgba(239,68,68,0.1)]";
  const btnCls =
    "w-full h-[52px] bg-gradient-to-br from-indigo-500 to-violet-600 border-none rounded-xl text-white font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-[15px] font-semibold tracking-[-0.01em] cursor-pointer flex items-center justify-center gap-2 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:shadow-[0_8px_30px_rgba(99,102,241,0.35),0_0_60px_rgba(99,102,241,0.15)] active:translate-y-0 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none relative overflow-hidden before:absolute before:inset-0 before:bg-gradient-to-br before:from-white/20 before:to-transparent before:opacity-0 before:transition-opacity before:duration-300 before:pointer-events-none hover:before:opacity-100";
  const errIcon = (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );

  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />

      <div id="widget-root">
        <div className="mesh-bg fixed inset-0 z-0 overflow-hidden pointer-events-none" />
        <div className="fixed rounded-full blur-[80px] pointer-events-none z-0 opacity-40 w-[400px] h-[400px] bg-[radial-gradient(circle,rgba(99,102,241,0.3),transparent_70%)] top-[-100px] right-[-100px] animate-orb-float-1" />
        <div className="fixed rounded-full blur-[80px] pointer-events-none z-0 opacity-40 w-[300px] h-[300px] bg-[radial-gradient(circle,rgba(139,92,246,0.2),transparent_70%)] bottom-[10%] left-[5%] animate-orb-float-2" />
        <canvas id="particleCanvas" ref={canvasRef} className="fixed inset-0 z-[1] pointer-events-none" />

        <div className="relative z-[2] min-h-screen flex max-[900px]:flex-col">
          {/* Left: Visual Panel */}
          <div className="flex-1 min-h-screen relative flex flex-col justify-end p-12 overflow-hidden max-[900px]:min-h-[280px] max-[900px]:p-8 max-[480px]:min-h-[220px] max-[480px]:p-6 before:absolute before:inset-0 before:bg-gradient-to-b before:from-transparent before:via-[rgba(10,10,12,0.3)] before:to-[rgba(10,10,12,0.85)] before:z-[1]">
            <img
              src="https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=2000&auto=format&fit=crop"
              alt="Abstract network visualization"
              className="absolute inset-0 w-full h-full object-cover opacity-60 saturate-[0.7] contrast-[1.1] max-[900px]:opacity-40"
            />
            <div className="relative z-[2] max-w-[480px]">
              <div className="font-['JetBrains_Mono',monospace] text-[11px] font-medium tracking-[0.15em] uppercase text-indigo-500 mb-5 inline-flex items-center gap-2">
                <span className="size-[6px] rounded-full bg-indigo-500 animate-pulse" />
                Now onboarding
              </div>
              <h1 className="text-3xl md:text-4xl lg:text-5xl xl:text-[42px] font-semibold leading-[1.15] tracking-[-0.02em] mb-4 bg-gradient-to-br from-white to-white/70 bg-clip-text text-transparent">
                Where projects find their rhythm.
              </h1>
              <p className="text-[15px] leading-[1.7] text-[#8e8e93] max-w-[400px]">
                Join the teams who have replaced status meetings with intelligent coordination. Your workflow, amplified.
              </p>
              <div className="flex gap-8 mt-8 pt-6 border-t border-white/5 max-[900px]:gap-5 max-[480px]:hidden">
                <div className="flex flex-col gap-1">
                  <span className="font-['JetBrains_Mono',monospace] text-2xl font-medium text-[#f5f5f7] max-[900px]:text-xl">12K+</span>
                  <span className="text-xs text-[#636366] tracking-[0.05em]">Teams synced</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="font-['JetBrains_Mono',monospace] text-2xl font-medium text-[#f5f5f7] max-[900px]:text-xl">4.2M</span>
                  <span className="text-xs text-[#636366] tracking-[0.05em]">Tasks routed</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="font-['JetBrains_Mono',monospace] text-2xl font-medium text-[#f5f5f7] max-[900px]:text-xl">98.7%</span>
                  <span className="text-xs text-[#636366] tracking-[0.05em]">Uptime</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Form Panel */}
          <div className="w-full max-w-[520px] min-h-screen flex flex-col justify-center p-12 relative bg-[#111114]/70 backdrop-blur-2xl backdrop-saturate-150 border-l border-white/5 max-[900px]:max-w-full max-[900px]:p-8 max-[900px]:border-l-0 max-[900px]:border-t border-white/5 max-[480px]:p-6">
            <div className="mb-10">
              <div className="flex items-center gap-[10px] mb-8">
                <div className="size-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center relative overflow-hidden">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="relative z-[1] size-4">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
                <span className="text-xl font-semibold tracking-[-0.03em] text-[#f5f5f7]">Coordina</span>
              </div>
              <h2 className="text-[28px] font-semibold tracking-[-0.02em] leading-[1.2] mb-2 max-[480px]:text-2xl">Begin your setup</h2>
              <p className="text-[15px] text-[#8e8e93] leading-[1.6]">Two quick steps to get your team coordinates locked in.</p>
            </div>

            {/* Progress Steps */}
            <div className="flex items-center gap-2 mb-10">
              <div className={`flex items-center gap-2 text-xs font-medium transition-colors duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${step === 1 ? "text-[#f5f5f7]" : step > 1 ? "text-indigo-500" : "text-[#636366]"}`} data-step="1">
                <span className={`size-7 rounded-full border flex items-center justify-center font-['JetBrains_Mono',monospace] text-[11px] font-medium transition-all duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${step > 1 ? "border-indigo-500 bg-indigo-500 text-white" : step === 1 ? "border-indigo-500 bg-indigo-500/10 text-indigo-500" : "border-white/5"}`}>1</span>
                <span>Identity</span>
              </div>
              <div className={`flex-1 h-px bg-white/5 relative overflow-hidden after:absolute after:inset-0 after:bg-indigo-500 after:-translate-x-full after:transition-transform after:duration-[600ms] after:ease-[cubic-bezier(0.16,1,0.3,1)] ${step > 1 ? "after:translate-x-0" : ""}`} data-connector="1" />
              <div className={`flex items-center gap-2 text-xs font-medium transition-colors duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${step === 2 ? "text-[#f5f5f7]" : step > 2 ? "text-indigo-500" : "text-[#636366]"}`} data-step="2">
                <span className={`size-7 rounded-full border flex items-center justify-center font-['JetBrains_Mono',monospace] text-[11px] font-medium transition-all duration-[400ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${step > 2 ? "border-indigo-500 bg-indigo-500 text-white" : step === 2 ? "border-indigo-500 bg-indigo-500/10 text-indigo-500" : "border-white/5"}`}>2</span>
                <span>Credentials</span>
              </div>
            </div>

            {/* Form */}
            <form id="signupForm" onSubmit={handleSubmit} noValidate>
              {/* Step 1: Identity */}
              {step === 1 && (
                <div style={{ opacity: 1, transform: "translateY(0)", transition: "all 0.5s cubic-bezier(0.16,1,0.3,1)" }}>
                  <div className="mb-5 relative">
                    <label className="block text-[13px] font-medium text-[#8e8e93] mb-2 tracking-[0.01em]" htmlFor="fullName">Full name</label>
                    <div className="relative">
                      <input
                        type="text" id="fullName"
                        className={`peer ${inputCls} ${errors.fullName ? inputError : inputBorder}`}
                        placeholder="e.g. Alex Chen" autoComplete="name"
                        value={fullName} onChange={(e) => { setFullName(e.target.value); clearError("fullName"); }}
                      />
                      <svg className="absolute right-4 top-1/2 -translate-y-1/2 text-[#636366] pointer-events-none transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] peer-focus:text-indigo-500" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                    <div className={`text-xs text-red-500 mt-1.5 flex items-center gap-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${errors.fullName ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"}`} id="fullNameError">
                      {errIcon} Please enter your full name
                    </div>
                  </div>

                  <div className="mb-5 relative">
                    <label className="block text-[13px] font-medium text-[#8e8e93] mb-2 tracking-[0.01em]" htmlFor="email">Work email</label>
                    <div className="relative">
                      <input
                        type="email" id="email"
                        className={`peer ${inputCls} ${errors.email ? inputError : inputBorder}`}
                        placeholder="alex@company.com" autoComplete="email"
                        value={email} onChange={(e) => { setEmail(e.target.value); clearError("email"); }}
                      />
                      <svg className="absolute right-4 top-1/2 -translate-y-1/2 text-[#636366] pointer-events-none transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] peer-focus:text-indigo-500" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                      </svg>
                    </div>
                    <div className={`text-xs text-red-500 mt-1.5 flex items-center gap-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${errors.email ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"}`} id="emailError">
                      {errIcon} Please enter a valid email address
                    </div>
                  </div>

                  <div className="mb-5 relative">
                    <label className="block text-[13px] font-medium text-[#8e8e93] mb-2 tracking-[0.01em]" htmlFor="company">Company or team</label>
                    <div className="relative">
                      <input
                        type="text" id="company"
                        className={`peer ${inputCls} ${errors.company ? inputError : inputBorder}`}
                        placeholder="Acme Industries" autoComplete="organization"
                        value={company} onChange={(e) => { setCompany(e.target.value); clearError("company"); }}
                      />
                      <svg className="absolute right-4 top-1/2 -translate-y-1/2 text-[#636366] pointer-events-none transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] peer-focus:text-indigo-500" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 21h18" /><path d="M5 21V7l8-4 8 4v14" /><path d="M9 21v-6h6v6" /><path d="M10 9h4" /><path d="M10 13h4" />
                      </svg>
                    </div>
                    <div className={`text-xs text-red-500 mt-1.5 flex items-center gap-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${errors.company ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"}`} id="companyError">
                      {errIcon} Company name is required
                    </div>
                  </div>

                  <button
                    type="button"
                    className={btnCls}
                    id="step1Next" onClick={handleStep1Next} disabled={loading}
                  >
                    <span>Continue</span>
                    <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full" style={{ display: loading ? "block" : "none" }} />
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="ml-1">
                      <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Step 2: Credentials */}
              {step === 2 && !submitted && (
                <div style={{ opacity: 1, transform: "translateY(0)", transition: "all 0.5s cubic-bezier(0.16,1,0.3,1)" }}>
                  <div className="mb-5 relative">
                    <label className="block text-[13px] font-medium text-[#8e8e93] mb-2 tracking-[0.01em]" htmlFor="password">Create password</label>
                    <div className="relative">
                      <input
                        type={passwordVisible ? "text" : "password"} id="password"
                        className={`peer ${inputCls} ${errors.password ? inputError : inputBorder}`}
                        placeholder="Min. 8 characters" autoComplete="new-password"
                        value={password} onChange={(e) => { setPassword(e.target.value); clearError("password"); }}
                      />
                      <button
                        type="button"
                        className="absolute right-4 top-1/2 -translate-y-1/2 bg-transparent border-none text-[#636366] cursor-pointer p-1 flex items-center justify-center transition-colors duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-[#f5f5f7]"
                        id="togglePassword" tabIndex={-1}
                        onClick={() => setPasswordVisible((v) => !v)}
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" id="eyeIcon">
                          {passwordVisible ? (
                            <>
                              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                              <circle cx="12" cy="12" r="3" />
                              <line x1="4.22" y1="4.22" x2="19.78" y2="19.78" />
                            </>
                          ) : (
                            <>
                              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                              <circle cx="12" cy="12" r="3" />
                            </>
                          )}
                        </svg>
                      </button>
                    </div>
                    <div className="flex gap-1 mt-2.5 h-[3px]" id="strengthMeter">
                      {[0, 1, 2, 3].map((i) => (
                        <div key={i} className={`flex-1 rounded-sm transition-all duration-400 ease-[cubic-bezier(0.16,1,0.3,1)] ${i < strength.active ? strength.cls[Math.min(strength.active - 1, 3)] : "bg-white/5"}`} />
                      ))}
                    </div>
                    <div className="text-[11px] text-[#636366] mt-1.5 font-['JetBrains_Mono',monospace]" id="strengthLabel">{strength.label}</div>
                    <div className={`text-xs text-red-500 mt-1.5 flex items-center gap-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${errors.password ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"}`} id="passwordError">
                      {errIcon} Password must be at least 8 characters
                    </div>
                  </div>

                  <div className="mb-5 relative">
                    <label className="block text-[13px] font-medium text-[#8e8e93] mb-2 tracking-[0.01em]" htmlFor="confirmPassword">Confirm password</label>
                    <div className="relative">
                      <input
                        type={passwordVisible ? "text" : "password"} id="confirmPassword"
                        className={`peer ${inputCls} ${errors.confirmPassword ? inputError : inputBorder}`}
                        placeholder="Repeat your password" autoComplete="new-password"
                        value={confirmPassword} onChange={(e) => { setConfirmPassword(e.target.value); clearError("confirmPassword"); }}
                      />
                    </div>
                    <div className={`text-xs text-red-500 mt-1.5 flex items-center gap-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${errors.confirmPassword ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-1"}`} id="confirmPasswordError">
                      {errIcon} Passwords do not match
                    </div>
                  </div>

                  <label className={`flex items-start gap-3 my-6 cursor-pointer ${shaking ? "animate-shake" : ""}`}>
                    <input
                      type="checkbox"
                      className="appearance-none w-5 h-5 min-w-5 border border-white/5 rounded-[6px] bg-[#1a1a1f] cursor-pointer relative transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] mt-[1px] checked:bg-indigo-500 checked:border-indigo-500 after:content-[''] after:absolute after:left-[6px] after:top-[2px] after:w-[5px] after:h-[10px] after:border-r-2 after:border-b-2 after:border-white after:rotate-45 after:opacity-0 checked:after:opacity-100"
                      id="termsCheck" checked={termsAccepted} onChange={(e) => setTermsAccepted(e.target.checked)}
                    />
                    <span className="text-[13px] leading-[1.6] text-[#8e8e93]">
                      I agree to the <a href="#" className="text-indigo-500 no-underline font-medium transition-opacity duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:opacity-80">Terms of Service</a> and <a href="#" className="text-indigo-500 no-underline font-medium transition-opacity duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:opacity-80">Privacy Policy</a>. I also consent to receive product updates and coordination tips.
                    </span>
                  </label>

                  <button
                    type="submit"
                    className={btnCls}
                    id="submitBtn" disabled={loading}
                  >
                    <span>Activate my workspace</span>
                    <span className="size-[18px] border-2 border-white/30 border-t-white rounded-full" style={{ display: loading ? "block" : "none" }} />
                  </button>

                  <button
                    type="button"
                    className="w-full mt-3 bg-transparent border border-white/5 text-[#8e8e93] h-12 rounded-xl font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-sm font-medium cursor-pointer flex items-center justify-center gap-[10px] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-white/[.05] hover:border-white/[.12] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
                    id="backBtn" onClick={() => setStep(1)}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="m15 18-6-6 6-6" />
                    </svg>
                    Back
                  </button>
                </div>
              )}

              {/* Success State */}
              {submitted && (
                <div className="text-center py-10" id="successState">
                  <div className="size-20 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mx-auto mb-6 relative before:absolute before:-inset-1 before:rounded-full before:bg-gradient-to-br before:from-indigo-500 before:to-transparent before:opacity-30 before:animate-ring-pulse">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="relative z-[1]">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <h3 className="text-2xl font-semibold mb-2">You are all set</h3>
                  <p className="text-[15px] text-[#8e8e93] leading-[1.6] mb-6">
                    A verification link has been dispatched to your inbox. Click it to unlock your coordination dashboard.
                  </p>
                  <button
                    type="button"
                    className={btnCls}
                    onClick={() => window.location.reload()}
                  >
                    <span>Open my inbox</span>
                  </button>
                </div>
              )}
            </form>

            {/* Divider + Social + Footer (hidden on success) */}
            {!submitted && (
              <>
                <div className="flex items-center gap-4 my-7 text-[#636366] text-xs font-medium before:flex-1 before:h-px before:bg-white/5 after:flex-1 after:h-px after:bg-white/5">or</div>

                <div className="grid grid-cols-2 gap-3 max-[480px]:grid-cols-1">
                  <button type="button" className="h-12 bg-[#1a1a1f] border border-white/5 rounded-xl text-[#f5f5f7] font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-sm font-medium cursor-pointer flex items-center justify-center gap-[10px] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-white/[.05] hover:border-white/[.12] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]">
                    <svg width="18" height="18" viewBox="0 0 24 24">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                    </svg>
                    Google
                  </button>
                  <button type="button" className="h-12 bg-[#1a1a1f] border border-white/5 rounded-xl text-[#f5f5f7] font-['Inter_Tight',-apple-system,BlinkMacSystemFont,sans-serif] text-sm font-medium cursor-pointer flex items-center justify-center gap-[10px] transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-white/[.05] hover:border-white/[.12] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                    </svg>
                    GitHub
                  </button>
                </div>

                <div className="text-center mt-8 text-sm text-[#8e8e93]">
                  Already have coordinates? <a href="#" className="text-[#f5f5f7] no-underline font-semibold transition-colors duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-indigo-500">Sign in</a>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <Script id="kimi-widget" strategy="afterInteractive" dangerouslySetInnerHTML={{ __html: kimiScript }} />
    </>
  );
}
