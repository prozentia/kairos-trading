import {
  activateStrategy,
  deactivateStrategy,
  deleteStrategy,
  getStrategies,
} from "@/api/strategies";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { formatDate } from "@/lib/utils";
import type { Strategy } from "@/types";
import {
  BrainCircuit,
  Copy,
  Edit,
  Eye,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

const StrategiesList = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Strategy | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchStrategies = useCallback(async () => {
    try {
      const data = await getStrategies();
      setStrategies(data.strategies);
    } catch (err) {
      console.error("Failed to fetch strategies:", err);
      toast.error("Failed to load strategies");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  // Toggle active status
  const handleToggle = async (strategy: Strategy) => {
    setTogglingId(strategy.id);
    try {
      if (strategy.is_active) {
        await deactivateStrategy(strategy.id);
        toast.info(`"${strategy.name}" deactivated`);
      } else {
        await activateStrategy(strategy.id);
        toast.success(`"${strategy.name}" activated`);
      }
      // Update local state
      setStrategies((prev) =>
        prev.map((s) =>
          s.id === strategy.id ? { ...s, is_active: !s.is_active } : s
        )
      );
    } catch {
      toast.error("Failed to toggle strategy");
    } finally {
      setTogglingId(null);
    }
  };

  // Delete strategy
  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteStrategy(deleteTarget.id);
      setStrategies((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      toast.success(`"${deleteTarget.name}" deleted`);
      setDeleteTarget(null);
    } catch {
      toast.error("Failed to delete strategy");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Strategies</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your trading strategies
          </p>
        </div>
        <Link to="/strategies/new">
          <Button>
            <Plus className="w-4 h-4" />
            New Strategy
          </Button>
        </Link>
      </div>

      {/* Strategy cards grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <Skeleton className="h-5 w-40 mb-3" />
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-3/4 mb-4" />
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : strategies.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <BrainCircuit className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              No strategies yet
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create your first trading strategy to get started.
            </p>
            <Link to="/strategies/new">
              <Button>
                <Plus className="w-4 h-4" />
                Create Strategy
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {strategies.map((strategy) => (
            <Card
              key={strategy.id}
              className="hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate">
                      {strategy.name}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      v{strategy.version}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-2">
                    <Switch
                      checked={strategy.is_active}
                      onCheckedChange={() => handleToggle(strategy)}
                      disabled={togglingId === strategy.id}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Description */}
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {strategy.description || "No description"}
                </p>

                {/* Metadata */}
                <div className="flex flex-wrap gap-1.5">
                  {strategy.pairs.slice(0, 3).map((pair) => (
                    <Badge
                      key={pair}
                      variant="outline"
                      className="text-[10px] px-2 py-0"
                    >
                      {pair}
                    </Badge>
                  ))}
                  {strategy.pairs.length > 3 && (
                    <Badge
                      variant="outline"
                      className="text-[10px] px-2 py-0"
                    >
                      +{strategy.pairs.length - 3}
                    </Badge>
                  )}
                  <Badge variant="secondary" className="text-[10px] px-2 py-0">
                    {strategy.timeframe}
                  </Badge>
                </div>

                {/* Conditions count */}
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span>
                    {strategy.entry_conditions.length} entry condition
                    {strategy.entry_conditions.length !== 1 ? "s" : ""}
                  </span>
                  <span>
                    {strategy.exit_conditions.length} exit condition
                    {strategy.exit_conditions.length !== 1 ? "s" : ""}
                  </span>
                </div>

                {/* Updated at */}
                <p className="text-[10px] text-muted-foreground/60">
                  Updated {formatDate(strategy.updated_at ?? strategy.created_at)}
                </p>

                {/* Action buttons */}
                <div className="flex items-center gap-1.5 pt-2 border-t border-border">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/strategies/${strategy.id}`)}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    View
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      navigate(`/strategies/${strategy.id}/edit`)
                    }
                  >
                    <Edit className="w-3.5 h-3.5" />
                    Edit
                  </Button>
                  <Button variant="ghost" size="icon-sm">
                    <Copy className="w-3.5 h-3.5" />
                  </Button>
                  <div className="flex-1" />
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setDeleteTarget(strategy)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <Dialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Strategy</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteTarget?.name}"? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StrategiesList;
