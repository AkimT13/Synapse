import Link from "next/link";

// Landing page proper lands in Phase 8. This stub keeps the route
// discoverable while we scaffold the design system.
export default function Home() {
  return (
    <main className="relative min-h-screen flex items-center justify-center">
      <div className="orb orb-violet -top-24 -left-24 w-96 h-96" />
      <div className="orb orb-cyan -bottom-24 -right-24 w-96 h-96" />

      <div className="relative z-10 text-center space-y-6 px-6">
        <div className="flex items-center justify-center gap-2">
          <span className="brand-dot" />
          <span className="brand-word text-2xl">Synapse</span>
        </div>
        <h1 className="font-serif text-5xl leading-tight text-white max-w-xl">
          Your code and your docs, one vector space.
        </h1>
        <p className="text-white/70 max-w-lg mx-auto">
          Scaffold in progress. Visit the app surfaces once they are wired up.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/onboarding" className="shiny-border">
            <span className="shiny-inner">Launch the demo</span>
          </Link>
          <Link href="/code" className="btn btn-ghost">
            Open workspace
          </Link>
        </div>
      </div>
    </main>
  );
}
