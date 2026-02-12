import { getBotLogs } from "@/api/bot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  Download,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  ScrollText,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

type LogLevel = "ALL" | "DEBUG" | "INFO" | "WARNING" | "ERROR";

function getLogLevelColor(line: string): string {
  if (line.includes("ERROR") || line.includes("CRITICAL"))
    return "text-red-500";
  if (line.includes("WARNING") || line.includes("WARN"))
    return "text-amber-500";
  if (line.includes("INFO")) return "text-blue-500";
  if (line.includes("DEBUG")) return "text-gray-400";
  return "text-foreground";
}

function getLogLevelBadgeVariant(
  level: string
): "danger" | "warning" | "info" | "secondary" {
  switch (level) {
    case "ERROR":
      return "danger";
    case "WARNING":
      return "warning";
    case "INFO":
      return "info";
    default:
      return "secondary";
  }
}

const BotLogs = () => {
  const [lines, setLines] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [level, setLevel] = useState<LogLevel>("ALL");
  const [lineCount, setLineCount] = useState(200);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await getBotLogs(
        lineCount,
        level === "ALL" ? undefined : level
      );
      setLines(data.lines);
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [lineCount, level]);

  // Initial load + auto-refresh
  useEffect(() => {
    fetchLogs();

    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 3000);
      return () => clearInterval(interval);
    }
  }, [fetchLogs, autoRefresh]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoRefresh) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [lines, autoRefresh]);

  const handleDownload = () => {
    const content = lines.join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kairos-bot-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Count log levels
  const errorCount = lines.filter(
    (l) => l.includes("ERROR") || l.includes("CRITICAL")
  ).length;
  const warnCount = lines.filter(
    (l) => l.includes("WARNING") || l.includes("WARN")
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/bot">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
          </Link>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <ScrollText className="w-6 h-6 text-primary" />
            Bot Logs
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {/* Level badges */}
          {errorCount > 0 && (
            <Badge variant="danger" className="text-xs">
              {errorCount} errors
            </Badge>
          )}
          {warnCount > 0 && (
            <Badge variant="warning" className="text-xs">
              {warnCount} warnings
            </Badge>
          )}
        </div>
      </div>

      {/* Controls */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Level filter */}
            <Select
              value={level}
              onValueChange={(val) => setLevel(val as LogLevel)}
            >
              <SelectTrigger className="w-[130px] h-9">
                <SelectValue placeholder="Log level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Levels</SelectItem>
                <SelectItem value="DEBUG">Debug</SelectItem>
                <SelectItem value="INFO">Info</SelectItem>
                <SelectItem value="WARNING">Warning</SelectItem>
                <SelectItem value="ERROR">Error</SelectItem>
              </SelectContent>
            </Select>

            {/* Line count */}
            <Select
              value={String(lineCount)}
              onValueChange={(val) => setLineCount(Number(val))}
            >
              <SelectTrigger className="w-[120px] h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="50">50 lines</SelectItem>
                <SelectItem value="100">100 lines</SelectItem>
                <SelectItem value="200">200 lines</SelectItem>
                <SelectItem value="500">500 lines</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex-1" />

            {/* Auto-refresh toggle */}
            <Button
              variant={autoRefresh ? "default" : "outline"}
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {autoRefresh ? "Pause" : "Resume"}
            </Button>

            {/* Manual refresh */}
            <Button
              variant="outline"
              size="sm"
              onClick={fetchLogs}
              disabled={isRefreshing}
            >
              {isRefreshing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Refresh
            </Button>

            {/* Download */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={lines.length === 0}
            >
              <Download className="w-4 h-4" />
              Download
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Log output */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm text-muted-foreground">
              {lines.length} lines
              {autoRefresh && (
                <span className="ml-2 text-green-500 text-xs animate-pulse">
                  Live
                </span>
              )}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 15 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : lines.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No log lines available.
            </div>
          ) : (
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <pre className="p-4 text-xs font-mono leading-relaxed">
                {lines.map((line, i) => (
                  <div
                    key={i}
                    className={cn(
                      "px-2 py-0.5 hover:bg-muted/30 rounded-sm",
                      getLogLevelColor(line)
                    )}
                  >
                    <span className="text-muted-foreground/50 select-none mr-2 inline-block w-8 text-right">
                      {i + 1}
                    </span>
                    {line}
                  </div>
                ))}
                <div ref={logsEndRef} />
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default BotLogs;
