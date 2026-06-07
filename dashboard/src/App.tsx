import { useEffect, useMemo, useRef, useState } from "react";
import { Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { GROUPS } from "./charts/groups";
import type { ChartSpec } from "./charts/types";
import { ChartCard } from "./components/ChartCard";
import { AppSidebar } from "./components/Sidebar";
import { Overview } from "./pages/Overview";

/** 路由:#/overview | #/<组>/可选<图 id>(带图 id 时滚动定位并闪烁) */
function useHashRoute(): [string, (path: string) => void] {
  const read = () => location.hash.replace(/^#\/?/, "") || "overview";
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const fn = () => setRoute(read());
    window.addEventListener("hashchange", fn);
    return () => window.removeEventListener("hashchange", fn);
  }, []);
  return [route, (path) => (location.hash = `#/${path}`)];
}

export default function App() {
  const [route, nav] = useHashRoute();
  const [gid, focusId] = route.split("/");
  const group = GROUPS.find((g) => g.id === gid);
  const mainRef = useRef<HTMLDivElement>(null);

  // 全屏 & 对比
  const allCharts = useMemo(() => new Map(GROUPS.flatMap((g) => g.charts.map((c) => [c.id, c] as const))), []);
  const [full, setFull] = useState<ChartSpec | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);
  const togglePick = (id: string) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  // 切组滚到顶;带图 id 时定位 + 闪烁
  useEffect(() => {
    if (!focusId) {
      mainRef.current?.scrollTo(0, 0);
      return;
    }
    const t = setTimeout(() => {
      const el = document.getElementById(`card-${focusId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("flash");
        setTimeout(() => el.classList.remove("flash"), 2400);
      }
    }, 80);
    return () => clearTimeout(t);
  }, [route, focusId]);

  return (
    <TooltipProvider delayDuration={300}>
      <SidebarProvider className="terminal-bg">
        <AppSidebar groups={GROUPS} active={gid} onNav={nav} />
        <SidebarInset className="min-w-0 bg-transparent">
          <header className="h-14 shrink-0 border-b flex items-center gap-2 px-4 md:px-6 bg-background/70 backdrop-blur sticky top-0 z-20">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-1 !h-4" />
            <h1 className="text-[15px] font-semibold tracking-tight">{group ? group.title : "总览"}</h1>
            <span className="num text-[10px] text-muted-foreground/60 ml-auto hidden sm:block">
              free · official sources · daily auto-refresh
            </span>
          </header>
          <div ref={mainRef} className="flex-1 overflow-y-auto p-4 md:p-6">
            {group ? (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 max-w-[1800px]">
                {group.charts.map((c, i) => (
                  <div key={c.id} id={`card-${c.id}`} style={{ animationDelay: `${i * 60}ms` }} className="rise h-[440px] xl:h-[480px]">
                    <ChartCard
                      spec={c}
                      onFullscreen={() => setFull(c)}
                      compared={picked.includes(c.id)}
                      onCompare={() => togglePick(c.id)}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <Overview onNav={nav} />
            )}
          </div>
        </SidebarInset>

        {/* 对比托盘:跨组累积勾选 */}
        {picked.length > 0 && !comparing && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 rounded-full border border-input bg-card/95 backdrop-blur px-4 py-2 shadow-xl">
            <Layers size={14} className="text-primary" />
            <span className="text-xs text-muted-foreground">
              已选 <span className="num text-primary">{picked.length}</span> 张
            </span>
            <Button size="sm" className="h-7 rounded-full" disabled={picked.length < 2} onClick={() => setComparing(true)}>
              对比
            </Button>
            <Button size="sm" variant="ghost" className="h-7 rounded-full text-muted-foreground/60" onClick={() => setPicked([])}>
              清空
            </Button>
          </div>
        )}

        {/* 全屏单图 */}
        <Dialog open={!!full} onOpenChange={(o) => !o && setFull(null)}>
          <DialogContent className="!max-w-[96vw] w-[1700px] h-[92vh] flex flex-col p-4 gap-3">
            <DialogHeader className="shrink-0">
              <DialogTitle className="text-sm">{full?.title}</DialogTitle>
            </DialogHeader>
            <div className="flex-1 min-h-0">{full && <ChartCard spec={full} />}</div>
          </DialogContent>
        </Dialog>

        {/* 对比视图:纵向排,缩放按日期联动 */}
        <Dialog open={comparing} onOpenChange={(o) => !o && setComparing(false)}>
          <DialogContent className="!max-w-[96vw] w-[1700px] h-[92vh] flex flex-col p-4 gap-3">
            <DialogHeader className="shrink-0">
              <DialogTitle className="text-sm">对比 · {picked.length} 张图(缩放按日期联动)</DialogTitle>
            </DialogHeader>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <div className="flex flex-col gap-4">
                {picked
                  .map((id) => allCharts.get(id))
                  .filter((c): c is ChartSpec => !!c)
                  .map((c) => (
                    <div key={c.id} className="h-[40vh] min-h-[300px] shrink-0">
                      <ChartCard spec={c} syncGroup="compare" />
                    </div>
                  ))}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </SidebarProvider>
    </TooltipProvider>
  );
}
