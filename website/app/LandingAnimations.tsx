"use client";

import { useLayoutEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

// declare const SplitText: any;

export default function LandingAnimations() {
  useLayoutEffect(() => {
    gsap.registerPlugin(ScrollTrigger, SplitText);

    const ctx = gsap.context(() => {
      gsap.from(".hero-text-trigger", {
        duration: 1.2,
        x: -60,
        opacity: 0,
        ease: "power4.out",
      });

      gsap.from(".hero-3d-trigger", {
        duration: 1.5,
        z: -150,
        rotationX: 25,
        opacity: 0,
        ease: "power3.out",
      });

      gsap.from(".problem-card", {
        scrollTrigger: { trigger: ".problem-card", start: "top 85%" },
        duration: 1,
        y: 80,
        rotationX: -15,
        opacity: 0,
        stagger: 0.15,
        ease: "power2.out",
      });

      gsap.from(".solution-trigger", {
        scrollTrigger: { trigger: ".solution-trigger", start: "top 80%" },
        duration: 1.2,
        scale: 0.95,
        opacity: 0,
        ease: "power3.out",
      });

      gsap.from(".feature-card", {
        scrollTrigger: { trigger: ".features-trigger", start: "top 85%" },
        duration: 0.8,
        y: 50,
        opacity: 0,
        stagger: 0.1,
        ease: "power2.out",
      });

      gsap.from(".pricing-trigger", {
        scrollTrigger: { trigger: ".pricing-trigger", start: "top 85%" },
        duration: 1,
        y: 40,
        opacity: 0,
        ease: "power3.out",
      });

      // -- Scroller section (CustomScroller inlined) --
      const scrollerEl = document.querySelector(".scroller-section");
      console.log("Is it defined", scrollerEl);
      if (!scrollerEl) return;
      const e = scrollerEl.querySelector(".progress_bar") as HTMLElement | null;
      const t = scrollerEl.querySelector(".index_current") as HTMLElement | null;
      const i = scrollerEl.querySelectorAll(".main_item");

      if (e && t && i.length > 0) {
        const a = i.length;
        const h = 0.15,
          r = 0.15,
          d = 0.06,
          w = 0.6,
          g = 1.0,
          b = 1200;

        gsap.set(i[0], { autoAlpha: 1 });
        i.forEach((o, s) => {
          if (s > 0) gsap.set(o, { autoAlpha: 0 });
        });

        const splitTexts: any[] = [];
        i.forEach((o, s) => {
          const n = o.querySelector("p");
          if (n) {
            const c = new SplitText(n, {
              type: "lines, chars",
              linesClass: "line",
              charsClass: "char",
              mask: "lines",
            });
            splitTexts[s] = c;
            gsap.set(c.chars, { opacity: r });
          }
        });

        let u = 0;

        const x = (o: number, s: number) => {
          if (o !== s) {
            let outgoingDuration = 0;
            if (o >= 0 && splitTexts[o]) {
              const lineCount = splitTexts[o].lines.length;
              outgoingDuration = 0.4 + d * Math.max(0, lineCount - 1);
              gsap.to(splitTexts[o].lines, {
                autoAlpha: 0,
                y: -30,
                ease: "power4.out",
                duration: 0.4,
                stagger: d,
                onComplete: () => gsap.set(i[o], { autoAlpha: 0 }),
              });
            }
            const incomingDelay = Math.max(h, outgoingDuration);
            gsap.delayedCall(incomingDelay, () => {
              if (s >= 0 && splitTexts[s]) {
                gsap.set(i[s], { autoAlpha: 1 });
                gsap.fromTo(
                  splitTexts[s].lines,
                  { autoAlpha: 0, y: 30 },
                  {
                    autoAlpha: 1,
                    y: 0,
                    ease: "power4.out",
                    duration: w,
                    stagger: d,
                  },
                );
              }
            });
          }
        };

        ScrollTrigger.create({
          trigger: scrollerEl,
          start: "center center",
          end: `+=${a * b * g}px`,
          pin: true,
          scrub: true,
          markers: false,
          onUpdate: (o) => {
            const s = Math.min(o.progress, g) / g;
            let n = Math.floor(s * a + 1e-6);
            n = Math.max(0, Math.min(a - 1, n));
            gsap.set(e, { scaleX: s });
            const c = n + 1;
            t.textContent = c.toString().padStart(2, "0");
            if (n !== u) {
              x(u, n);
              u = n;
            }
            if (splitTexts[n]) {
              const p = s * a - n;
              const v = Math.min(p * 1.5, 1);
              const y = splitTexts[n].chars.length;
              const m = Math.floor(v * y);
              splitTexts[n].chars.forEach(
                (f: HTMLElement, k: number) => {
                  if (k < m) {
                    gsap.set(f, { opacity: 1 });
                  } else if (k === m) {
                    const S = v * y - m;
                    gsap.set(f, { opacity: r + S * (1 - r) });
                  } else {
                    gsap.set(f, { opacity: r });
                  }
                },
              );
            }
          },
        });

        const block = document.querySelector(
          ".scroller-block",
        ) as HTMLElement | null;
        const background = document.querySelector(
          ".bg-container",
        ) as HTMLElement | null;
        const scroller = scrollerEl as HTMLElement;
        if (block && background) {
          const o = scroller.offsetTop;
          const s = scroller.offsetHeight;
          const n = a * b * g;
          const c = o + s + n;

          ScrollTrigger.create({
            trigger: block,
            start: "top top",
            end: `+=${c}px`,
            pin: background,
            pinSpacing: false,
            markers: false,
            onUpdate: (p) => {
              gsap.set(background, {
                filter: `hue-rotate(${p.progress * 90}deg)`,
              });
            },
          });
        }

        ScrollTrigger.refresh();
      }
    });

    // -- Hero 3D tilt (event listeners outside gsap.context) --
    const heroCard = document.querySelector(
      ".three-d-card",
    ) as HTMLElement | null;
    const mouseMove = (e: MouseEvent) => {
      if (!heroCard) return;
      const xAxis = (window.innerWidth / 2 - e.pageX) / 45;
      const yAxis = (window.innerHeight / 2 - e.pageY) / 45;
      heroCard.style.transform = `rotateY(${xAxis}deg) rotateX(${-yAxis}deg)`;
    };
    const mouseLeave = () => {
      if (!heroCard) return;
      heroCard.style.transform = `rotateX(5deg) rotateY(-5deg)`;
    };
    document.addEventListener("mousemove", mouseMove);
    document.addEventListener("mouseleave", mouseLeave);

    ScrollTrigger.refresh();

    return () => {
      ctx.revert();
      document.removeEventListener("mousemove", mouseMove);
      document.removeEventListener("mouseleave", mouseLeave);
      ScrollTrigger.getAll().forEach((t) => t.kill());
      gsap.killTweensOf("*");
    };
  }, []);

  return null;
}
