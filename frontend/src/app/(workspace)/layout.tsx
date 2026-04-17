import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";

// Shared shell for the three workspace pages (code / knowledge / ask).
// Grid is: 64px sidebar | 1fr workspace, with a 56px topbar spanning
// both columns.
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <Topbar />
      <Sidebar />
      <main className="workspace">{children}</main>
    </div>
  );
}
