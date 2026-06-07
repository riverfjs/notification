import { Activity, Banknote, Factory, Flame, Gauge, Github, LayoutGrid, Percent } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import type { GroupSpec } from "../charts/types";

const ICONS: Record<string, typeof Activity> = {
  overview: Gauge,
  consumption: Banknote,
  supply: Factory,
  inflation: Flame,
  rates: Percent,
  sentiment: Activity,
  breadth: LayoutGrid,
};

/** 用 shadcn Sidebar 原语:collapsible="icon" 自带折叠成图标轨、Cmd/Ctrl+B
 *  快捷键、折叠状态 cookie 持久化、移动端 off-canvas、折叠时图标 tooltip。 */
export function AppSidebar({
  groups,
  active,
  onNav,
}: {
  groups: GroupSpec[];
  active: string;
  onNav: (id: string) => void;
}) {
  const items = [{ id: "overview", title: "总览" }, ...groups.map((g) => ({ id: g.id, title: g.title }))];
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="h-14 justify-center border-b">
        <div className="flex items-center gap-2.5 px-1">
          <svg viewBox="0 0 32 32" className="size-6 shrink-0 rounded text-primary" aria-hidden>
            <rect width="32" height="32" rx="6" fill="#131316" />
            <path d="M6 22 L13 13 L18 17 L26 8" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="leading-none group-data-[collapsible=icon]:hidden">
            <div className="font-semibold text-[15px] tracking-tight">Macro Terminal</div>
            <a
              href="https://github.com/riverfjs/notification"
              target="_blank"
              rel="noreferrer"
              className="num inline-flex items-center gap-1 text-[10px] text-muted-foreground/60 mt-1 hover:text-primary transition-colors"
              title="打开 GitHub 仓库"
            >
              <Github size={10} />
              riverfjs/notification
            </a>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((it) => {
                const Icon = ICONS[it.id] ?? Activity;
                return (
                  <SidebarMenuItem key={it.id}>
                    <SidebarMenuButton
                      isActive={active === it.id}
                      onClick={() => onNav(it.id)}
                      tooltip={it.title}
                    >
                      <Icon />
                      <span>{it.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t group-data-[collapsible=icon]:hidden">
        <p className="px-1 py-1 text-[10px] leading-relaxed text-muted-foreground/60">
          数据:官方免费源,GitHub Actions 每个交易日收盘后自动更新。
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}
