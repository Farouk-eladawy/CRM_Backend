"use client";

import { useState, useMemo } from "react";
import {
  LayoutDashboard,
  CalendarClock,
  Briefcase,
  DollarSign,
  BarChart3,
  Lock,
  ClipboardList,
  MapPin,
  Car,
  Users,
  UserCheck,
  Building2,
  Truck,
  ShieldCheck,
  Building,
  MessageCircle,
  Search,
  BookOpen,
  ListOrdered,
  Lightbulb,
  Globe,
  Tag,
  DollarSignIcon,
  Cloud,
  Palette,
  Mail,
  Settings2,
  BusFront,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

// ─── Section definitions ────────────────────────────────────
interface HelpSection {
  id: string;
  icon: React.ElementType;
  titleKey: string;
  overviewKey: string;
  stepsKey: string;
  tipsKey: string;
}

const sections: HelpSection[] = [
  { id: "dashboard", icon: LayoutDashboard, titleKey: "help.dashboard.title", overviewKey: "help.dashboard.overview", stepsKey: "help.dashboard.steps", tipsKey: "help.dashboard.tips" },
  { id: "dispatch", icon: CalendarClock, titleKey: "help.dispatch.title", overviewKey: "help.dispatch.overview", stepsKey: "help.dispatch.steps", tipsKey: "help.dispatch.tips" },
  { id: "traffic-jobs", icon: Briefcase, titleKey: "help.trafficJobs.title", overviewKey: "help.trafficJobs.overview", stepsKey: "help.trafficJobs.steps", tipsKey: "help.trafficJobs.tips" },
  { id: "finance", icon: DollarSign, titleKey: "help.finance.title", overviewKey: "help.finance.overview", stepsKey: "help.finance.steps", tipsKey: "help.finance.tips" },
  { id: "reports", icon: BarChart3, titleKey: "help.reports.title", overviewKey: "help.reports.overview", stepsKey: "help.reports.steps", tipsKey: "help.reports.tips" },
  { id: "job-locks", icon: Lock, titleKey: "help.jobLocks.title", overviewKey: "help.jobLocks.overview", stepsKey: "help.jobLocks.steps", tipsKey: "help.jobLocks.tips" },
  { id: "activity-log", icon: ClipboardList, titleKey: "help.activityLog.title", overviewKey: "help.activityLog.overview", stepsKey: "help.activityLog.steps", tipsKey: "help.activityLog.tips" },
  { id: "locations", icon: MapPin, titleKey: "help.locations.title", overviewKey: "help.locations.overview", stepsKey: "help.locations.steps", tipsKey: "help.locations.tips" },
  { id: "vehicles", icon: Car, titleKey: "help.vehicles.title", overviewKey: "help.vehicles.overview", stepsKey: "help.vehicles.steps", tipsKey: "help.vehicles.tips" },
  { id: "drivers", icon: Users, titleKey: "help.drivers.title", overviewKey: "help.drivers.overview", stepsKey: "help.drivers.steps", tipsKey: "help.drivers.tips" },
  { id: "reps", icon: UserCheck, titleKey: "help.reps.title", overviewKey: "help.reps.overview", stepsKey: "help.reps.steps", tipsKey: "help.reps.tips" },
  { id: "agents", icon: Building2, titleKey: "help.agents.title", overviewKey: "help.agents.overview", stepsKey: "help.agents.steps", tipsKey: "help.agents.tips" },
  { id: "customers", icon: Users, titleKey: "help.customers.title", overviewKey: "help.customers.overview", stepsKey: "help.customers.steps", tipsKey: "help.customers.tips" },
  { id: "suppliers", icon: Truck, titleKey: "help.suppliers.title", overviewKey: "help.suppliers.overview", stepsKey: "help.suppliers.steps", tipsKey: "help.suppliers.tips" },
  { id: "users", icon: ShieldCheck, titleKey: "help.users.title", overviewKey: "help.users.overview", stepsKey: "help.users.steps", tipsKey: "help.users.tips" },
  { id: "company", icon: Building, titleKey: "help.company.title", overviewKey: "help.company.overview", stepsKey: "help.company.steps", tipsKey: "help.company.tips" },
  { id: "whatsapp", icon: MessageCircle, titleKey: "help.whatsapp.title", overviewKey: "help.whatsapp.overview", stepsKey: "help.whatsapp.steps", tipsKey: "help.whatsapp.tips" },
  { id: "guest-bookings", icon: Globe, titleKey: "help.guestBookings.title", overviewKey: "help.guestBookings.overview", stepsKey: "help.guestBookings.steps", tipsKey: "help.guestBookings.tips" },
  { id: "public-prices", icon: Tag, titleKey: "help.publicPrices.title", overviewKey: "help.publicPrices.overview", stepsKey: "help.publicPrices.steps", tipsKey: "help.publicPrices.tips" },
  { id: "driver-tariffs", icon: DollarSign, titleKey: "help.driverTariffs.title", overviewKey: "help.driverTariffs.overview", stepsKey: "help.driverTariffs.steps", tipsKey: "help.driverTariffs.tips" },
  { id: "google-drive", icon: Cloud, titleKey: "help.googleDrive.title", overviewKey: "help.googleDrive.overview", stepsKey: "help.googleDrive.steps", tipsKey: "help.googleDrive.tips" },
  { id: "styling", icon: Palette, titleKey: "help.styling.title", overviewKey: "help.styling.overview", stepsKey: "help.styling.steps", tipsKey: "help.styling.tips" },
  { id: "email-settings", icon: Mail, titleKey: "help.emailSettings.title", overviewKey: "help.emailSettings.overview", stepsKey: "help.emailSettings.steps", tipsKey: "help.emailSettings.tips" },
  { id: "job-control", icon: Settings2, titleKey: "help.jobControl.title", overviewKey: "help.jobControl.overview", stepsKey: "help.jobControl.steps", tipsKey: "help.jobControl.tips" },
  { id: "car-dispatch", icon: BusFront, titleKey: "help.carDispatch.title", overviewKey: "help.carDispatch.overview", stepsKey: "help.carDispatch.steps", tipsKey: "help.carDispatch.tips" },
];

// ─── Main Page ──────────────────────────────────────────────
export default function HelpPage() {
  const t = useT();
  const [activeSection, setActiveSection] = useState("dashboard");
  const [searchQuery, setSearchQuery] = useState("");

  // Filter sections based on search
  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return sections;
    const q = searchQuery.toLowerCase();
    return sections.filter((s) =>
      [s.titleKey, s.overviewKey, s.stepsKey, s.tipsKey].some((key) =>
        t(key).toLowerCase().includes(q)
      )
    );
  }, [searchQuery, t]);

  // Auto-select first match if current selection is filtered out
  const active = useMemo(() => {
    if (filteredSections.find((s) => s.id === activeSection)) return activeSection;
    return filteredSections[0]?.id ?? "dashboard";
  }, [filteredSections, activeSection]);

  const currentSection = sections.find((s) => s.id === active);

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("help.title")}
        description={t("help.description")}
      />

      {/* Search */}
      <div className="relative w-full max-w-sm">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={t("help.searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8 border-border bg-muted/50 text-foreground placeholder:text-muted-foreground/50 h-9"
        />
      </div>

      {/* Mobile topic selector (visible below lg) */}
      <div className="lg:hidden">
        <Select value={active} onValueChange={setActiveSection}>
          <SelectTrigger className="w-full border-border bg-muted/50 text-foreground h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="border-border bg-popover text-popover-foreground">
            {filteredSections.map((s) => {
              const Icon = s.icon;
              return (
                <SelectItem key={s.id} value={s.id}>
                  <span className="flex items-center gap-2">
                    <Icon className="h-3.5 w-3.5" />
                    {t(s.titleKey)}
                  </span>
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      </div>

      {/* Main layout */}
      <div className="flex gap-6">
        {/* Left nav (hidden on mobile) */}
        <nav className="hidden lg:block w-60 shrink-0 space-y-0.5 sticky top-0 max-h-[calc(100vh-12rem)] overflow-y-auto pr-2">
          {filteredSections.length === 0 ? (
            <p className="px-3 py-4 text-sm text-muted-foreground">
              {t("help.noResults")}
            </p>
          ) : (
            filteredSections.map((s) => {
              const Icon = s.icon;
              const isActive = s.id === active;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSection(s.id)}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors text-left",
                    isActive
                      ? "bg-accent text-foreground"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{t(s.titleKey)}</span>
                </button>
              );
            })
          )}
        </nav>

        {/* Right content */}
        <div className="flex-1 min-w-0">
          {filteredSections.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <BookOpen className="mb-2 h-8 w-8" />
              <p className="text-sm">{t("help.noResults")}</p>
            </div>
          ) : currentSection ? (
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                    <currentSection.icon className="h-5 w-5 text-foreground" />
                  </div>
                  <CardTitle className="text-lg text-foreground">
                    {t(currentSection.titleKey)}
                  </CardTitle>
                </div>
                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                  {t(currentSection.overviewKey)}
                </p>
              </CardHeader>
              <CardContent>
                <Accordion type="multiple" defaultValue={["steps", "tips"]}>
                  {/* Steps */}
                  <AccordionItem value="steps">
                    <AccordionTrigger className="text-foreground">
                      <span className="flex items-center gap-2">
                        <ListOrdered className="h-4 w-4 text-blue-500" />
                        {t("help.stepsLabel")}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground leading-relaxed">
                        {t(currentSection.stepsKey)
                          .split("\n")
                          .filter(Boolean)
                          .map((step, i) => (
                            <li key={i} className="pl-1">
                              {step}
                            </li>
                          ))}
                      </ol>
                    </AccordionContent>
                  </AccordionItem>

                  {/* Tips */}
                  <AccordionItem value="tips" className="border-b-0">
                    <AccordionTrigger className="text-foreground">
                      <span className="flex items-center gap-2">
                        <Lightbulb className="h-4 w-4 text-amber-500" />
                        {t("help.tipsLabel")}
                      </span>
                    </AccordionTrigger>
                    <AccordionContent>
                      <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground leading-relaxed">
                        {t(currentSection.tipsKey)
                          .split("\n")
                          .filter(Boolean)
                          .map((tip, i) => (
                            <li key={i} className="pl-1">
                              {tip}
                            </li>
                          ))}
                      </ul>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
