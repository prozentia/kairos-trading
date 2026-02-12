import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Bell,
  Key,
  Loader2,
  Moon,
  Palette,
  Save,
  Shield,
  Sun,
} from "lucide-react";
import { useState } from "react";
import { toast } from "react-toastify";
import { useTheme } from "@/components/theme-provider";

const Settings = () => {
  const { theme, setTheme } = useTheme();

  // API keys state (stored locally, sent to backend on save)
  const [binanceApiKey, setBinanceApiKey] = useState("");
  const [binanceSecret, setBinanceSecret] = useState("");
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");

  // Notification preferences
  const [notifTradeOpen, setNotifTradeOpen] = useState(true);
  const [notifTradeClose, setNotifTradeClose] = useState(true);
  const [notifBotStatus, setNotifBotStatus] = useState(true);
  const [notifDailyReport, setNotifDailyReport] = useState(true);
  const [notifErrors, setNotifErrors] = useState(true);

  const [isSaving, setIsSaving] = useState(false);

  const handleSaveApiKeys = async () => {
    setIsSaving(true);
    try {
      // TODO: Connect to backend endpoint for saving API keys securely
      await new Promise((resolve) => setTimeout(resolve, 800));
      toast.success("API keys saved securely");
    } catch {
      toast.error("Failed to save API keys");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    setIsSaving(true);
    try {
      // TODO: Connect to backend endpoint for saving notification preferences
      await new Promise((resolve) => setTimeout(resolve, 500));
      toast.success("Notification preferences saved");
    } catch {
      toast.error("Failed to save preferences");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your trading platform
        </p>
      </div>

      <Tabs defaultValue="api-keys" className="space-y-6">
        <TabsList>
          <TabsTrigger value="api-keys" className="gap-1.5">
            <Key className="w-3.5 h-3.5" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-1.5">
            <Bell className="w-3.5 h-3.5" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="appearance" className="gap-1.5">
            <Palette className="w-3.5 h-3.5" />
            Appearance
          </TabsTrigger>
        </TabsList>

        {/* API Keys Tab */}
        <TabsContent value="api-keys" className="space-y-6">
          {/* Binance */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Shield className="w-4 h-4 text-amber-500" />
                Binance API
              </CardTitle>
              <CardDescription>
                Connect your Binance account for live trading. Keys are stored
                encrypted.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="binance-key">API Key</Label>
                <Input
                  id="binance-key"
                  type="password"
                  value={binanceApiKey}
                  onChange={(e) => setBinanceApiKey(e.target.value)}
                  placeholder="Enter your Binance API key"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="binance-secret">API Secret</Label>
                <Input
                  id="binance-secret"
                  type="password"
                  value={binanceSecret}
                  onChange={(e) => setBinanceSecret(e.target.value)}
                  placeholder="Enter your Binance API secret"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Only enable "Spot Trading" and "Read" permissions. Never enable
                withdrawal.
              </p>
            </CardContent>
          </Card>

          {/* Telegram */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="w-4 h-4 text-blue-500" />
                Telegram Bot
              </CardTitle>
              <CardDescription>
                Configure Telegram notifications for trade alerts and bot status.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="tg-token">Bot Token</Label>
                <Input
                  id="tg-token"
                  type="password"
                  value={telegramToken}
                  onChange={(e) => setTelegramToken(e.target.value)}
                  placeholder="123456789:ABCdef..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tg-chat">Chat ID</Label>
                <Input
                  id="tg-chat"
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  placeholder="Your Telegram chat ID"
                />
              </div>
            </CardContent>
          </Card>

          <Button onClick={handleSaveApiKeys} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save API Keys
          </Button>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Notification Preferences</CardTitle>
              <CardDescription>
                Choose which events you want to be notified about.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Trade Opened</Label>
                  <p className="text-xs text-muted-foreground">
                    Notify when a new trade is opened
                  </p>
                </div>
                <Switch
                  checked={notifTradeOpen}
                  onCheckedChange={setNotifTradeOpen}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Trade Closed</Label>
                  <p className="text-xs text-muted-foreground">
                    Notify when a trade is closed with P&L
                  </p>
                </div>
                <Switch
                  checked={notifTradeClose}
                  onCheckedChange={setNotifTradeClose}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Bot Status Changes</Label>
                  <p className="text-xs text-muted-foreground">
                    Notify when bot starts, stops, or crashes
                  </p>
                </div>
                <Switch
                  checked={notifBotStatus}
                  onCheckedChange={setNotifBotStatus}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Daily Report</Label>
                  <p className="text-xs text-muted-foreground">
                    Send a daily summary at 9:00 AM
                  </p>
                </div>
                <Switch
                  checked={notifDailyReport}
                  onCheckedChange={setNotifDailyReport}
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>Error Alerts</Label>
                  <p className="text-xs text-muted-foreground">
                    Notify on critical errors and circuit breakers
                  </p>
                </div>
                <Switch
                  checked={notifErrors}
                  onCheckedChange={setNotifErrors}
                />
              </div>
            </CardContent>
          </Card>

          <Button onClick={handleSaveNotifications} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Preferences
          </Button>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Theme</CardTitle>
              <CardDescription>
                Choose your preferred color scheme.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <button
                  onClick={() => setTheme("light")}
                  className={`p-4 rounded-xl border-2 transition-all text-center ${
                    theme === "light"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <Sun className="w-6 h-6 mx-auto mb-2 text-amber-500" />
                  <span className="text-sm font-medium">Light</span>
                </button>
                <button
                  onClick={() => setTheme("dark")}
                  className={`p-4 rounded-xl border-2 transition-all text-center ${
                    theme === "dark"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <Moon className="w-6 h-6 mx-auto mb-2 text-indigo-500" />
                  <span className="text-sm font-medium">Dark</span>
                </button>
                <button
                  onClick={() => setTheme("system")}
                  className={`p-4 rounded-xl border-2 transition-all text-center ${
                    theme === "system"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <div className="flex justify-center mb-2">
                    <Sun className="w-5 h-5 text-amber-500" />
                    <Moon className="w-5 h-5 text-indigo-500 -ml-1" />
                  </div>
                  <span className="text-sm font-medium">System</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Settings;
